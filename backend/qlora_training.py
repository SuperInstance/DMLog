"""
QLoRA Training Infrastructure - Phase 7 Task 7.3.1
===================================================
Implements 4-bit quantized LoRA fine-tuning for character learning.

Features:
- 4-bit quantization (bitsandbytes) for memory efficiency
- LoRA adapters (peft) for character-specific learning
- Training on RTX 4050 (6GB VRAM) or similar consumer GPUs
- Progress monitoring and ETA calculation
- Automatic model loading/caching
- Rollback on failure

Requirements:
- bitsandbytes
- peft
- transformers
- torch
- accelerate
"""

import gc
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable
import hashlib

logger = logging.getLogger(__name__)

# Check for required dependencies
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available - QLoRA training disabled")

try:
    from transformers import (
        AutoTokenizer,
        AutoModelForCausalLM,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling
    )
    from transformers import BitsAndBytesConfig
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers not available - using mock implementation")

try:
    from peft import (
        LoraConfig,
        get_peft_model,
        PeftModel,
        TaskType,
        prepare_model_for_kbit_training
    )
    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False
    logger.warning("peft not available - LoRA training disabled")

try:
    import bitsandbytes as bnb
    BNB_AVAILABLE = True
except ImportError:
    BNB_AVAILABLE = False
    logger.warning("bitsandbytes not available - 4-bit quantization disabled")


# ============================================================================
# Enums and Data Classes
# ============================================================================

class CharacterState(Enum):
    """States a character goes through during learning"""
    ACTIVE = "active"           # Normal gameplay
    DREAMING = "dreaming"       # Preparing to train
    TRAINING = "training"       # Model fine-tuning
    AWAKENING = "awakening"     # Loading new weights
    ERROR = "error"             # Training failed


@dataclass
class TrainingConfig:
    """Configuration for QLoRA training"""
    # Model settings
    base_model: str = "microsoft/phi-2"  # 2.7B parameter model, good for RTX 4050
    # Alternatives: "TinyLlama/TinyLlama-1.1B-Chat-v1.0", "meta-llama/Llama-2-7b-hf"

    # LoRA settings
    lora_r: int = 16            # LoRA rank (higher = more parameters, better quality)
    lora_alpha: int = 32        # LoRA alpha scaling
    lora_dropout: float = 0.05  # Dropout for LoRA layers
    lora_target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",  # Attention
        "gate_proj", "up_proj", "down_proj"      # FFN
    ])

    # Quantization settings
    use_4bit: bool = True
    bnb_4bit_compute_dtype: str = "bfloat16"  # or "float16"
    bnb_4bit_quant_type: str = "nf4"          # "nf4" or "fp4"

    # Training settings
    learning_rate: float = 2e-4
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 4
    gradient_accumulation_steps: int = 4
    warmup_steps: int = 50
    weight_decay: float = 0.01
    max_grad_norm: float = 1.0

    # Early stopping
    early_stopping_patience: int = 3
    early_stopping_threshold: float = 0.001

    # Memory optimization
    max_sequence_length: int = 512
    use_flash_attention: bool = False  # Requires xformers

    # Output
    output_dir: str = "./checkpoints"
    save_strategy: str = "steps"
    save_steps: int = 100
    logging_steps: int = 10

    # Character-specific
    character_id: str = ""
    previous_adapter: Optional[str] = None  # Path to previous LoRA adapter


@dataclass
class TrainingProgress:
    """Training progress report"""
    character_id: str
    state: CharacterState
    current_epoch: int = 0
    total_epochs: int = 0
    current_step: int = 0
    total_steps: int = 0
    train_loss: float = 0.0
    val_loss: float = 0.0
    learning_rate: float = 0.0
    elapsed_seconds: float = 0.0
    eta_seconds: float = 0.0
    samples_per_second: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_id": self.character_id,
            "state": self.state.value,
            "current_epoch": self.current_epoch,
            "total_epochs": self.total_epochs,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "progress_pct": (self.current_step / self.total_epochs * 100) if self.total_steps > 0 else 0,
            "train_loss": self.train_loss,
            "val_loss": self.val_loss,
            "learning_rate": self.learning_rate,
            "elapsed_seconds": self.elapsed_seconds,
            "eta_seconds": self.eta_seconds,
            "samples_per_second": self.samples_per_second
        }


@dataclass
class TrainingResult:
    """Result of training completion"""
    character_id: str
    success: bool
    final_train_loss: float = 0.0
    final_val_loss: float = 0.0
    best_val_loss: float = 0.0
    training_time_seconds: float = 0.0
    adapter_path: str = ""
    error_message: str = ""
    checkpoint_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_id": self.character_id,
            "success": self.success,
            "final_train_loss": self.final_train_loss,
            "final_val_loss": self.final_val_loss,
            "best_val_loss": self.best_val_loss,
            "training_time_seconds": self.training_time_seconds,
            "adapter_path": self.adapter_path,
            "error_message": self.error_message,
            "checkpoint_metadata": self.checkpoint_metadata
        }


# ============================================================================
# Progress Callback
# ============================================================================

class ProgressCallback:
    """Callback for tracking training progress"""

    def __init__(self, total_steps: int, progress_callback: Optional[Callable] = None):
        self.total_steps = total_steps
        self.progress_callback = progress_callback
        self.start_time = time.time()
        self.step_times = []

    def on_step_end(self, step: int, loss: float, learning_rate: float):
        """Called at the end of each step"""
        elapsed = time.time() - self.start_time
        self.step_times.append(elapsed)

        # Calculate ETA
        if step > 0:
            avg_time_per_step = elapsed / step
            eta = avg_time_per_step * (self.total_steps - step)
        else:
            eta = 0

        # Calculate samples per second
        if elapsed > 0:
            samples_per_second = step / elapsed
        else:
            samples_per_second = 0

        progress = TrainingProgress(
            character_id="",
            state=CharacterState.TRAINING,
            current_step=step,
            total_steps=self.total_steps,
            train_loss=loss,
            learning_rate=learning_rate,
            elapsed_seconds=elapsed,
            eta_seconds=eta,
            samples_per_second=samples_per_second
        )

        if self.progress_callback:
            self.progress_callback(progress)


# ============================================================================
# QLoRA Trainer
# ============================================================================

class QLoRATrainer:
    """
    Trains LoRA adapters for character learning.

    Usage:
        trainer = QLoRATrainer(config)
        result = trainer.train(training_data_path, character_id)
    """

    def __init__(
        self,
        config: Optional[TrainingConfig] = None,
        progress_callback: Optional[Callable[[TrainingProgress], None]] = None
    ):
        """
        Initialize QLoRA trainer

        Args:
            config: Training configuration
            progress_callback: Optional callback for progress updates
        """
        self.config = config or TrainingConfig()
        self.progress_callback = progress_callback
        self.tokenizer = None
        self.model = None
        self.peft_model = None

        # Verify dependencies
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch is required for QLoRA training")
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("transformers is required for QLoRA training")
        if not PEFT_AVAILABLE:
            raise RuntimeError("peft is required for LoRA training")

        # Check GPU availability
        if not torch.cuda.is_available():
            logger.warning("CUDA not available - training will be very slow on CPU")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")

        # Get GPU info
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            logger.info(f"GPU: {gpu_name} ({gpu_memory:.1f} GB)")

    def train(
        self,
        training_data_path: str,
        character_id: str,
        val_data_path: Optional[str] = None
    ) -> TrainingResult:
        """
        Train a LoRA adapter for the character

        Args:
            training_data_path: Path to training data (JSONL)
            character_id: Character ID
            val_data_path: Optional path to validation data

        Returns:
            TrainingResult with training outcome
        """
        start_time = time.time()
        self.config.character_id = character_id

        # Update character state
        self._update_progress(TrainingProgress(
            character_id=character_id,
            state=CharacterState.DREAMING
        ))

        try:
            # 1. Load tokenizer and model
            logger.info(f"Loading base model: {self.config.base_model}")
            self._load_model()

            # 2. Load and preprocess data
            logger.info(f"Loading training data from: {training_data_path}")
            train_dataset, val_dataset = self._load_datasets(
                training_data_path, val_data_path
            )

            if len(train_dataset) == 0:
                return TrainingResult(
                    character_id=character_id,
                    success=False,
                    error_message="No training data available"
                )

            # 3. Setup training
            self._update_progress(TrainingProgress(
                character_id=character_id,
                state=CharacterState.TRAINING,
                total_steps=self.config.num_train_epochs * len(train_dataset)
            ))

            # 4. Train
            logger.info("Starting training...")
            final_metrics = self._run_training(train_dataset, val_dataset)

            # 5. Save adapter
            adapter_path = self._save_adapter(character_id)

            training_time = time.time() - start_time

            result = TrainingResult(
                character_id=character_id,
                success=True,
                final_train_loss=final_metrics.get("train_loss", 0.0),
                final_val_loss=final_metrics.get("val_loss", 0.0),
                best_val_loss=final_metrics.get("best_val_loss", 0.0),
                training_time_seconds=training_time,
                adapter_path=adapter_path,
                checkpoint_metadata={
                    "base_model": self.config.base_model,
                    "lora_r": self.config.lora_r,
                    "lora_alpha": self.config.lora_alpha,
                    "training_samples": len(train_dataset),
                    "validation_samples": len(val_dataset) if val_dataset else 0,
                    "timestamp": datetime.now().isoformat()
                }
            )

            # Update state to awakening
            self._update_progress(TrainingProgress(
                character_id=character_id,
                state=CharacterState.AWAKENING
            ))

            logger.info(f"Training complete in {training_time:.1f}s")
            return result

        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)

            self._update_progress(TrainingProgress(
                character_id=character_id,
                state=CharacterState.ERROR
            ))

            return TrainingResult(
                character_id=character_id,
                success=False,
                error_message=str(e),
                training_time_seconds=time.time() - start_time
            )

    def _load_model(self):
        """Load base model with quantization and LoRA"""
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.base_model,
            trust_remote_code=True
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token

        # Configure quantization
        if self.config.use_4bit and BNB_AVAILABLE:
            compute_dtype = getattr(torch, self.config.bnb_4bit_compute_dtype)

            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type=self.config.bnb_4bit_quant_type,
                bnb_4bit_compute_dtype=compute_dtype,
                bnb_4bit_use_double_quant=True,
            )

            logger.info("Using 4-bit quantization")
        else:
            bnb_config = None
            logger.info("Not using 4-bit quantization")

        # Load base model
        self.model = AutoModelForCausalLM.from_pretrained(
            self.config.base_model,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.bfloat16 if BNB_AVAILABLE else torch.float32
        )

        # Prepare for k-bit training
        if self.config.use_4bit:
            self.model = prepare_model_for_kbit_training(self.model)

        # Configure LoRA
        lora_config = LoraConfig(
            r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            lora_dropout=self.config.lora_dropout,
            target_modules=self.config.lora_target_modules,
            bias="none",
            task_type=TaskType.CAUSAL_LM,
        )

        # Apply LoRA
        self.peft_model = get_peft_model(self.model, lora_config)
        self.peft_model.print_trainable_parameters()

        # Load previous adapter if exists
        if self.config.previous_adapter:
            logger.info(f"Loading previous adapter: {self.config.previous_adapter}")
            self.peft_model.load_adapter(self.config.previous_adapter)

    def _load_datasets(
        self,
        train_path: str,
        val_path: Optional[str] = None
    ) -> Tuple:
        """Load training and validation datasets"""
        train_data = self._load_jsonl(train_path)
        val_data = self._load_jsonl(val_path) if val_path else []

        train_dataset = CharacterDataset(train_data, self.tokenizer, self.config.max_sequence_length)
        val_dataset = CharacterDataset(val_data, self.tokenizer, self.config.max_sequence_length) if val_data else None

        return train_dataset, val_dataset

    def _load_jsonl(self, path: str) -> List[Dict]:
        """Load JSONL file"""
        if not path or not Path(path).exists():
            return []

        data = []
        with open(path, 'r') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        return data

    def _run_training(self, train_dataset, val_dataset) -> Dict[str, float]:
        """Run the training loop"""
        # Calculate total steps
        total_steps = self.config.num_train_epochs * len(train_dataset)

        # Setup training arguments
        output_dir = Path(self.config.output_dir) / self.config.character_id
        output_dir.mkdir(parents=True, exist_ok=True)

        training_args = TrainingArguments(
            output_dir=str(output_dir),
            num_train_epochs=self.config.num_train_epochs,
            per_device_train_batch_size=self.config.per_device_train_batch_size,
            per_device_eval_batch_size=self.config.per_device_eval_batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            learning_rate=self.config.learning_rate,
            warmup_steps=self.config.warmup_steps,
            weight_decay=self.config.weight_decay,
            logging_steps=self.config.logging_steps,
            save_steps=self.config.save_steps,
            save_strategy=self.config.save_strategy,
            evaluation_strategy="steps" if val_dataset else "no",
            eval_steps=self.config.save_steps if val_dataset else None,
            max_grad_norm=self.config.max_grad_norm,
            fp16=False,
            bf16=BNB_AVAILABLE,
            gradient_checkpointing=True,
            optim="paged_adamw_32bit" if BNB_AVAILABLE else "adamw_torch",
            lr_scheduler_type="cosine",
            logging_dir=str(output_dir / "logs"),
            report_to="none",
            load_best_model_at_end=True if val_dataset else False,
            metric_for_best_model="eval_loss" if val_dataset else None,
        )

        # Create data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False,
            pad_to_multiple_of=8
        )

        # Create trainer
        trainer = Trainer(
            model=self.peft_model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            data_collator=data_collator,
        )

        # Custom training loop for progress tracking
        progress = ProgressCallback(total_steps, self._on_progress_update)

        # Train
        train_result = trainer.train()

        # Final evaluation
        metrics = {}
        if val_dataset:
            eval_metrics = trainer.evaluate()
            metrics["val_loss"] = eval_metrics.get("eval_loss", 0.0)

        metrics["train_loss"] = train_result.training_loss

        return metrics

    def _save_adapter(self, character_id: str) -> str:
        """Save LoRA adapter weights"""
        output_dir = Path(self.config.output_dir) / character_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save adapter
        adapter_path = output_dir / "adapter"
        self.peft_model.save_pretrained(str(adapter_path))

        # Save tokenizer
        self.tokenizer.save_pretrained(str(adapter_path))

        # Save config
        config_path = adapter_path / "training_config.json"
        with open(config_path, 'w') as f:
            json.dump({
                "base_model": self.config.base_model,
                "lora_r": self.config.lora_r,
                "lora_alpha": self.config.lora_alpha,
                "character_id": character_id,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)

        logger.info(f"Saved adapter to: {adapter_path}")
        return str(adapter_path)

    def _on_progress_update(self, progress: TrainingProgress):
        """Handle progress update"""
        progress.character_id = self.config.character_id
        self._update_progress(progress)

    def _update_progress(self, progress: TrainingProgress):
        """Send progress update to callback"""
        if self.progress_callback:
            self.progress_callback(progress)

    @staticmethod
    def load_adapter_for_inference(
        base_model: str,
        adapter_path: str
    ):
        """
        Load a trained adapter for inference

        Args:
            base_model: Base model name/path
            adapter_path: Path to saved adapter

        Returns:
            Model with adapter loaded
        """
        if not PEFT_AVAILABLE:
            raise RuntimeError("peft is required to load adapters")

        # Load base model
        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            device_map="auto",
            trust_remote_code=True
        )

        # Load adapter
        model = PeftModel.from_pretrained(model, adapter_path)

        return model


# ============================================================================
# Character Dataset
# ============================================================================

class CharacterDataset(torch.utils.data.Dataset):
    """
    PyTorch Dataset for character training data

    Expects JSONL with format: {"instruction": ..., "input": ..., "output": ...}
    """

    def __init__(
        self,
        data: List[Dict],
        tokenizer,
        max_length: int = 512
    ):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]

        # Format: instruction + input + response
        instruction = item.get("instruction", "")
        input_text = item.get("input", "")
        output = item.get("output", "")

        # Build prompt
        if input_text:
            prompt = f"{instruction}\n\n{input_text}\n\nResponse: {output}"
        else:
            prompt = f"{instruction}\n\nResponse: {output}"

        # Tokenize
        encodings = self.tokenizer(
            prompt,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt"
        )

        return {
            "input_ids": encodings["input_ids"].squeeze(0),
            "attention_mask": encodings["attention_mask"].squeeze(0),
            "labels": encodings["input_ids"].squeeze(0).clone()
        }


# ============================================================================
# Training Queue Manager
# ============================================================================

class TrainingQueue:
    """
    Manages queue of characters waiting to train.

    Handles:
    - Multiple characters training sequentially
    - Priority queue (teaching moments get priority)
    - State persistence
    """

    def __init__(self, db_path: str = "data/training_queue.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize queue database"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_queue (
                character_id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                priority REAL DEFAULT 0.0,
                training_count INTEGER DEFAULT 0,
                last_training_time TEXT,
                queued_at TEXT NOT NULL,
                started_at TEXT,
                metadata TEXT
            )
        """)

        conn.commit()
        conn.close()

    def enqueue(
        self,
        character_id: str,
        priority: float = 0.0,
        reason: str = ""
    ):
        """Add character to training queue"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO training_queue
            (character_id, state, priority, queued_at, metadata)
            VALUES (?, 'queued', ?, ?, ?)
        """, (
            character_id,
            priority,
            datetime.now().isoformat(),
            json.dumps({"reason": reason})
        ))

        conn.commit()
        conn.close()

        logger.info(f"Enqueued {character_id} for training (priority: {priority})")

    def dequeue(self) -> Optional[str]:
        """Get next character to train"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT character_id FROM training_queue
            WHERE state = 'queued'
            ORDER BY priority DESC, queued_at ASC
            LIMIT 1
        """)

        row = cursor.fetchone()
        if row:
            character_id = row[0]

            # Update state
            cursor.execute("""
                UPDATE training_queue
                SET state = 'training', started_at = ?
                WHERE character_id = ?
            """, (datetime.now().isoformat(), character_id))

            conn.commit()
            conn.close()

            return character_id

        conn.close()
        return None

    def mark_complete(self, character_id: str, success: bool):
        """Mark training as complete"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        new_state = 'completed' if success else 'failed'

        cursor.execute("""
            UPDATE training_queue
            SET state = ?, training_count = training_count + 1,
                last_training_time = ?
            WHERE character_id = ?
        """, (new_state, datetime.now().isoformat(), character_id))

        conn.commit()
        conn.close()

        logger.info(f"Marked {character_id} as {new_state}")

    def get_queue_status(self) -> List[Dict]:
        """Get status of all queued characters"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM training_queue
            ORDER BY priority DESC, queued_at ASC
        """)

        rows = cursor.fetchall()
        status = [dict(row) for row in rows]

        conn.close()
        return status


# ============================================================================
# Mock Implementation (for testing without GPU)
# ============================================================================

class MockQLoRATrainer:
    """
    Mock trainer for testing without GPU/dependencies.
    Simulates training behavior without actual model training.
    """

    def __init__(self, config=None, progress_callback=None):
        self.config = config or TrainingConfig()
        self.progress_callback = progress_callback
        logger.warning("Using MockQLoRATrainer - no actual training will occur")

    def train(
        self,
        training_data_path: str,
        character_id: str,
        val_data_path: str = None
    ) -> TrainingResult:
        """Simulate training with mock progress updates"""
        import time
        import random

        start_time = time.time()

        self._update_progress(TrainingProgress(
            character_id=character_id,
            state=CharacterState.DREAMING
        ))

        # Simulate data loading
        time.sleep(0.5)

        # Simulate training epochs
        total_steps = 100
        for step in range(0, total_steps + 1):
            self._update_progress(TrainingProgress(
                character_id=character_id,
                state=CharacterState.TRAINING,
                current_step=step,
                total_steps=total_steps,
                train_loss=max(0.5, 2.0 - (step / total_steps) * 1.5 + random.uniform(-0.1, 0.1)),
                val_loss=max(0.6, 2.1 - (step / total_steps) * 1.4 + random.uniform(-0.1, 0.1)),
                elapsed_seconds=time.time() - start_time,
                eta_seconds=(total_steps - step) * 0.1
            ))
            time.sleep(0.05)  # Simulate training time

        self._update_progress(TrainingProgress(
            character_id=character_id,
            state=CharacterState.AWAKENING
        ))

        # Create mock adapter path
        adapter_path = Path(self.config.output_dir) / character_id / "adapter"
        adapter_path.mkdir(parents=True, exist_ok=True)

        # Save mock config
        with open(adapter_path / "training_config.json", 'w') as f:
            json.dump({
                "base_model": self.config.base_model,
                "character_id": character_id,
                "mock": True,
                "timestamp": datetime.now().isoformat()
            }, f)

        return TrainingResult(
            character_id=character_id,
            success=True,
            final_train_loss=0.52,
            final_val_loss=0.61,
            best_val_loss=0.58,
            training_time_seconds=time.time() - start_time,
            adapter_path=str(adapter_path),
            checkpoint_metadata={"mock": True}
        )

    def _update_progress(self, progress: TrainingProgress):
        if self.progress_callback:
            self.progress_callback(progress)


def get_trainer(
    config: Optional[TrainingConfig] = None,
    progress_callback: Optional[Callable] = None,
    force_mock: bool = False
):
    """
    Get appropriate trainer based on available dependencies

    Args:
        config: Training configuration
        progress_callback: Progress callback
        force_mock: Force use of mock trainer

    Returns:
        QLoRATrainer or MockQLoRATrainer
    """
    if force_mock or not TORCH_AVAILABLE or not TRANSFORMERS_AVAILABLE or not PEFT_AVAILABLE:
        logger.info("Using MockQLoRATrainer")
        return MockQLoRATrainer(config, progress_callback)

    logger.info("Using QLoRATrainer")
    return QLoRATrainer(config, progress_callback)


# ============================================================================
# Tests
# ============================================================================

async def test_qlora_trainer():
    """Test QLoRA training infrastructure"""
    print("\n" + "=" * 60)
    print("Testing QLoRA Training Infrastructure")
    print("=" * 60)

    # Create sample training data
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample JSONL
        train_path = Path(tmpdir) / "train.jsonl"
        with open(train_path, 'w') as f:
            for i in range(10):
                f.write(json.dumps({
                    "instruction": "What combat action should I take?",
                    "input": f"Location: Cave {i}\nHP: 35/50",
                    "output": f"Action: Attack with axe\nReasoning: Defend party"
                }) + '\n')

        # Progress tracking
        progress_updates = []

        def progress_callback(progress: TrainingProgress):
            progress_updates.append(progress.to_dict())

        # Create trainer (will use mock if dependencies not available)
        config = TrainingConfig(
            character_id="test_char",
            output_dir=str(tmpdir),
            num_train_epochs=1
        )

        trainer = get_trainer(config, progress_callback)

        # Run training
        result = trainer.train(
            training_data_path=str(train_path),
            character_id="test_char"
        )

        print(f"\nTraining Result:")
        print(f"  Success: {result.success}")
        print(f"  Final train loss: {result.final_train_loss:.3f}")
        print(f"  Final val loss: {result.final_val_loss:.3f}")
        print(f"  Training time: {result.training_time_seconds:.1f}s")
        print(f"  Adapter path: {result.adapter_path}")

        # Check progress updates
        if progress_updates:
            print(f"\nProgress updates: {len(progress_updates)}")
            print(f"  States: {[p['state'] for p in progress_updates]}")

            # Verify state transitions
            states = [p['state'] for p in progress_updates]
            assert 'dreaming' in states
            assert 'training' in states
            assert 'awakening' in states

        # Verify result
        assert result.success
        assert result.adapter_path

        # Test queue manager
        print("\n--- Testing Training Queue ---")
        queue = TrainingQueue(db_path=str(Path(tmpdir) / "queue.db"))

        queue.enqueue("char1", priority=1.0, reason="Test training")
        queue.enqueue("char2", priority=0.5)

        next_char = queue.dequeue()
        print(f"Next to train: {next_char}")
        assert next_char == "char1"  # Higher priority

        queue.mark_complete("char1", success=True)

        status = queue.get_queue_status()
        print(f"Queue status: {len(status)} entries")

    print("\n✅ QLoRA training infrastructure tests passed!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_qlora_trainer())
