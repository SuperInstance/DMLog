"""
Hyperparameter Optimization Hints - Phase 7 Task 7.3.2
========================================================
Provides character-class-specific hyperparameter recommendations
for QLoRA fine-tuning.

Features:
- Character class detection based on decision patterns
- Per-class hyperparameter templates
- Dynamic adjustment based on data statistics
- Configurable defaults

Usage:
    from hyperparameter_hints import (
        get_hyperparameter_hints,
        detect_character_class,
        export_training_config
    )

    hints = get_hyperparameter_hints(character_id, db_path)
    config = hints.to_training_config()
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from collections import Counter

logger = logging.getLogger(__name__)


# ============================================================================
# Hyperparameter Data Classes
# ============================================================================

@dataclass
class HyperparameterHints:
    """Hyperparameter recommendations for a character"""
    character_id: str
    character_class: str
    confidence: float  # How confident we are in this classification (0-1)

    # LoRA settings
    lora_r: int
    lora_alpha: int
    lora_dropout: float
    lora_target_modules: List[str]

    # Training settings
    learning_rate: float
    num_train_epochs: int
    per_device_batch_size: int
    gradient_accumulation_steps: int
    warmup_steps: int
    weight_decay: float

    # Data curation settings
    min_confidence: float
    min_quality_score: float
    target_success_ratio: float
    teaching_moment_weight: int

    # Quantization
    use_4bit: bool
    bnb_4bit_quant_type: str
    max_sequence_length: int

    # Reasoning
    reasoning: str
    data_requirements: Dict[str, Any]

    def to_training_config(self) -> Dict[str, Any]:
        """Convert to TrainingConfig format for qlora_training"""
        return {
            "character_id": self.character_id,
            "lora_r": self.lora_r,
            "lora_alpha": self.lora_alpha,
            "lora_dropout": self.lora_dropout,
            "lora_target_modules": self.lora_target_modules,
            "learning_rate": self.learning_rate,
            "num_train_epochs": self.num_train_epochs,
            "per_device_train_batch_size": self.per_device_batch_size,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "warmup_steps": self.warmup_steps,
            "weight_decay": self.weight_decay,
            "max_sequence_length": self.max_sequence_length,
            "use_4bit": self.use_4bit,
            "bnb_4bit_quant_type": self.bnb_4bit_quant_type
        }

    def to_curation_config(self) -> Dict[str, Any]:
        """Convert to CurationConfig format for data_curation_pipeline"""
        return {
            "min_confidence": self.min_confidence,
            "min_quality_score": self.min_quality_score,
            "target_success_ratio": self.target_success_ratio,
            "teaching_moment_weight": self.teaching_moment_weight,
            "balance_success_failure": True,
            "deduplication_enabled": True
        }

    def to_dict(self) -> Dict[str, Any]:
        """Full dictionary representation"""
        return asdict(self)

    def save(self, path: str):
        """Save hints to JSON file"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Saved hyperparameter hints to {path}")


@dataclass
class CharacterClassProfile:
    """Profile defining hyperparameters for a character class"""
    name: str = ""
    description: str = ""
    decision_type_patterns: List[str] = field(default_factory=list)  # What decision types indicate this class

    # LoRA settings
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ])

    # Training settings
    learning_rate: float = 2e-4
    num_train_epochs: int = 3
    per_device_batch_size: int = 4
    gradient_accumulation_steps: int = 4
    warmup_ratio: float = 0.1  # Ratio of total steps for warmup
    weight_decay: float = 0.01

    # Data curation
    min_confidence: float = 0.3
    min_quality_score: float = 0.4
    target_success_ratio: float = 0.65
    teaching_moment_weight: int = 3

    # Advanced
    use_4bit: bool = True
    bnb_4bit_quant_type: str = "nf4"
    max_sequence_length: int = 512

    # Reasoning
    reasoning: str = ""
    data_requirements: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate required fields are set"""
        if not self.name:
            raise ValueError("name is required")
        if not self.description:
            raise ValueError("description is required")

    def calculate_confidence(self, decision_distribution: Dict[str, int],
                            quality_stats: Dict[str, Any]) -> float:
        """Calculate confidence score for this class match"""
        # Base confidence from decision type matching
        total_decisions = sum(decision_distribution.values())
        if total_decisions == 0:
            return 0.0

        matching_decisions = sum(
            decision_distribution.get(dt, 0)
            for dt in self.decision_type_patterns
        )
        type_confidence = matching_decisions / total_decisions

        # Adjust based on quality (lower quality = lower confidence)
        avg_quality = quality_stats.get('avg_quality_score', 0.5)
        quality_factor = min(1.0, avg_quality * 1.5)

        return min(1.0, type_confidence * quality_factor)


# ============================================================================
# Character Class Profiles
# ============================================================================

# Default target modules for LoRA
DEFAULT_TARGET_MODULES = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj"
]

# Lightweight target modules for smaller models
LIGHTWEIGHT_TARGET_MODULES = [
    "q_proj", "v_proj", "o_proj"
]

CHARACTER_CLASSES = {
    "combat_focused": CharacterClassProfile(
        name="combat_focused",
        description="Characters primarily making combat and tactical decisions",
        decision_type_patterns=["combat_action", "skill_check"],
        lora_r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        learning_rate=2e-4,
        num_train_epochs=3,
        per_device_batch_size=4,
        min_confidence=0.3,
        min_quality_score=0.5,
        target_success_ratio=0.65,
        reasoning="Combat decisions require moderate model capacity. Focus on successful tactical patterns.",
        data_requirements={
            "min_decisions": 50,
            "preferred_decisions": 100,
            "critical_teaching_moments": 5
        }
    ),

    "social_focused": CharacterClassProfile(
        name="social_focused",
        description="Characters primarily making social and dialogue decisions",
        decision_type_patterns=["social", "roleplay", "persuasion"],
        lora_r=32,
        lora_alpha=64,
        lora_dropout=0.1,
        learning_rate=1e-4,
        num_train_epochs=4,
        per_device_batch_size=2,
        min_confidence=0.4,
        min_quality_score=0.45,
        target_success_ratio=0.6,
        reasoning="Social interactions require higher capacity for nuance, context, and emotional intelligence.",
        data_requirements={
            "min_decisions": 75,
            "preferred_decisions": 150,
            "critical_teaching_moments": 10
        }
    ),

    "exploration_focused": CharacterClassProfile(
        name="exploration_focused",
        description="Characters focused on exploration and discovery",
        decision_type_patterns=["exploration", "investigation", "perception"],
        lora_r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        learning_rate=2e-4,
        num_train_epochs=2,
        per_device_batch_size=4,
        min_confidence=0.3,
        min_quality_score=0.5,
        target_success_ratio=0.7,
        reasoning="Exploration patterns are simpler. Faster training with moderate capacity.",
        data_requirements={
            "min_decisions": 40,
            "preferred_decisions": 80,
            "critical_teaching_moments": 3
        }
    ),

    "resource_focused": CharacterClassProfile(
        name="resource_focused",
        description="Characters focused on resource management and crafting",
        decision_type_patterns=["resource", "crafting", "inventory", "trade"],
        lora_r=12,
        lora_alpha=24,
        lora_dropout=0.05,
        learning_rate=2e-4,
        num_train_epochs=2,
        per_device_batch_size=4,
        min_confidence=0.3,
        min_quality_score=0.5,
        target_success_ratio=0.7,
        reasoning="Resource management is relatively straightforward. Lower rank sufficient.",
        data_requirements={
            "min_decisions": 30,
            "preferred_decisions": 60,
            "critical_teaching_moments": 2
        }
    ),

    "balanced": CharacterClassProfile(
        name="balanced",
        description="Characters with mixed decision types across domains",
        decision_type_patterns=[],  # Empty = matches anything
        lora_r=24,
        lora_alpha=48,
        lora_dropout=0.05,
        learning_rate=1.5e-4,
        num_train_epochs=3,
        per_device_batch_size=4,
        min_confidence=0.3,
        min_quality_score=0.5,
        target_success_ratio=0.65,
        reasoning="Balanced characters need medium complexity to handle diverse scenarios.",
        data_requirements={
            "min_decisions": 60,
            "preferred_decisions": 120,
            "critical_teaching_moments": 5
        }
    ),

    "high_variance": CharacterClassProfile(
        name="high_variance",
        description="Characters with inconsistent performance (many teaching moments)",
        decision_type_patterns=[],  # Detected via quality metrics
        lora_r=32,
        lora_alpha=64,
        lora_dropout=0.1,
        learning_rate=5e-5,
        num_train_epochs=5,
        per_device_batch_size=2,
        gradient_accumulation_steps=8,
        min_confidence=0.2,
        min_quality_score=0.4,
        target_success_ratio=0.55,
        teaching_moment_weight=5,
        reasoning="High variance requires more careful learning with lower rates and more epochs.",
        data_requirements={
            "min_decisions": 100,
            "preferred_decisions": 200,
            "critical_teaching_moments": 15
        }
    ),

    "expert": CharacterClassProfile(
        name="expert",
        description="Characters with consistently high performance (>80% success)",
        decision_type_patterns=[],
        lora_r=32,
        lora_alpha=32,  # Lower alpha for fine-tuning expert behavior
        lora_dropout=0.0,
        learning_rate=1e-4,
        num_train_epochs=2,
        per_device_batch_size=4,
        min_confidence=0.5,
        min_quality_score=0.7,
        target_success_ratio=0.8,
        reasoning="Expert characters need subtle fine-tuning. Preserve existing good patterns.",
        data_requirements={
            "min_decisions": 50,
            "preferred_decisions": 100,
            "critical_teaching_moments": 0
        }
    ),

    "novice": CharacterClassProfile(
        name="novice",
        description="Characters with limited data or low performance",
        decision_type_patterns=[],
        lora_r=8,
        lora_alpha=16,
        lora_dropout=0.1,
        learning_rate=3e-4,
        num_train_epochs=5,
        per_device_batch_size=2,
        min_confidence=0.2,
        min_quality_score=0.3,
        target_success_ratio=0.55,
        reasoning="Novice characters need more learning with lower capacity to avoid overfitting.",
        data_requirements={
            "min_decisions": 20,
            "preferred_decisions": 50,
            "critical_teaching_moments": 3
        }
    ),
}


# ============================================================================
# Character Detection
# ============================================================================

def detect_character_class(
    decision_distribution: Dict[str, int],
    quality_stats: Dict[str, Any],
    decision_count: int
) -> Tuple[str, float]:
    """
    Detect the most appropriate character class.

    Args:
        decision_distribution: Count of decisions by type
        quality_stats: Quality metrics (avg_quality_score, success_rate, etc.)
        decision_count: Total number of decisions

    Returns:
        Tuple of (class_name, confidence)
    """
    if decision_count == 0:
        return "novice", 0.0

    # Check for special conditions first
    success_rate = quality_stats.get('success_rate', 0.5)
    avg_quality = quality_stats.get('avg_quality_score', 0.5)
    teaching_moments = quality_stats.get('teaching_moments', 0)
    poor_ratio = quality_stats.get('poor_ratio', 0.0)

    # High variance detection
    if poor_ratio > 0.3 or teaching_moments > decision_count * 0.2:
        return "high_variance", 0.8

    # Expert detection
    if success_rate > 0.8 and avg_quality > 0.7 and decision_count >= 30:
        return "expert", 0.9

    # Novice detection
    if decision_count < 25:
        return "novice", 0.7

    # Calculate confidence for each class
    class_scores = {}
    for class_name, profile in CHARACTER_CLASSES.items():
        if class_name in ["high_variance", "expert", "novice"]:
            continue  # Already handled above
        confidence = profile.calculate_confidence(decision_distribution, quality_stats)
        class_scores[class_name] = confidence

    # Get best match
    best_class = max(class_scores, key=class_scores.get)
    best_confidence = class_scores[best_class]

    # Minimum confidence threshold
    if best_confidence < 0.3:
        return "balanced", best_confidence

    return best_class, best_confidence


# ============================================================================
# Hyperparameter Generation
# ============================================================================

def get_hyperparameter_hints(
    character_id: str,
    decision_distribution: Dict[str, int],
    quality_stats: Dict[str, Any],
    decision_count: int,
    custom_overrides: Optional[Dict[str, Any]] = None
) -> HyperparameterHints:
    """
    Generate hyperparameter hints for a character.

    Args:
        character_id: Character ID
        decision_distribution: Count of decisions by type
        quality_stats: Quality metrics
        decision_count: Total decision count
        custom_overrides: Optional custom parameter overrides

    Returns:
        HyperparameterHints with recommendations
    """
    # Detect character class
    class_name, confidence = detect_character_class(
        decision_distribution,
        quality_stats,
        decision_count
    )

    profile = CHARACTER_CLASSES[class_name]

    # Calculate warmup steps based on data size
    estimated_steps = max(100, decision_count * profile.num_train_epochs // profile.per_device_batch_size)
    warmup_steps = int(estimated_steps * profile.warmup_ratio)

    # Build hints
    hints = HyperparameterHints(
        character_id=character_id,
        character_class=class_name,
        confidence=confidence,

        # LoRA settings
        lora_r=profile.lora_r,
        lora_alpha=profile.lora_alpha,
        lora_dropout=profile.lora_dropout,
        lora_target_modules=profile.lora_target_modules.copy(),

        # Training settings
        learning_rate=profile.learning_rate,
        num_train_epochs=profile.num_train_epochs,
        per_device_batch_size=profile.per_device_batch_size,
        gradient_accumulation_steps=profile.gradient_accumulation_steps,
        warmup_steps=warmup_steps,
        weight_decay=profile.weight_decay,

        # Data curation
        min_confidence=profile.min_confidence,
        min_quality_score=profile.min_quality_score,
        target_success_ratio=profile.target_success_ratio,
        teaching_moment_weight=profile.teaching_moment_weight,

        # Quantization
        use_4bit=profile.use_4bit,
        bnb_4bit_quant_type=profile.bnb_4bit_quant_type,
        max_sequence_length=profile.max_sequence_length,

        # Reasoning
        reasoning=profile.reasoning,
        data_requirements=profile.data_requirements.copy()
    )

    # Apply custom overrides
    if custom_overrides:
        for key, value in custom_overrides.items():
            if hasattr(hints, key):
                setattr(hints, key, value)

    return hints


def get_hyperparameter_hints_from_db(
    character_id: str,
    db_path: str = "data/decisions.db",
    custom_overrides: Optional[Dict[str, Any]] = None
) -> Optional[HyperparameterHints]:
    """
    Generate hyperparameter hints from database data.

    Args:
        character_id: Character ID
        db_path: Path to decisions database
        custom_overrides: Optional custom parameter overrides

    Returns:
        HyperparameterHints or None if data unavailable
    """
    try:
        import sqlite3

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get decision distribution
        cursor.execute("""
            SELECT decision_type, COUNT(*) as count
            FROM decisions
            WHERE character_id = ?
            GROUP BY decision_type
        """, (character_id,))
        decision_distribution = {row['decision_type']: row['count'] for row in cursor.fetchall()}

        # Get quality stats
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                outcome_data
            FROM decisions
            WHERE character_id = ? AND outcome_data IS NOT NULL
        """, (character_id,))
        rows = cursor.fetchall()

        total_successes = sum(row['successes'] for row in rows) if rows else 0
        total_decisions = len(rows)

        # Calculate quality metrics
        quality_sum = 0.0
        quality_count = 0
        teaching_moments = 0
        poor_count = 0

        for row in rows:
            try:
                outcome = json.loads(row['outcome_data'])
                quality = outcome.get('quality_analysis', {}).get('quality_score', 0.5)
                quality_sum += quality
                quality_count += 1

                if quality < 0:
                    teaching_moments += 1
                if quality < 0.4:
                    poor_count += 1
            except:
                pass

        avg_quality = quality_sum / quality_count if quality_count > 0 else 0.5
        success_rate = total_successes / total_decisions if total_decisions > 0 else 0.5
        poor_ratio = poor_count / quality_count if quality_count > 0 else 0.0

        quality_stats = {
            'avg_quality_score': avg_quality,
            'success_rate': success_rate,
            'teaching_moments': teaching_moments,
            'poor_ratio': poor_ratio
        }

        conn.close()

        return get_hyperparameter_hints(
            character_id,
            decision_distribution,
            quality_stats,
            total_decisions,
            custom_overrides
        )

    except Exception as e:
        logger.error(f"Failed to generate hints from database: {e}")
        return None


# ============================================================================
# Export Functions
# ============================================================================

def export_training_config(
    character_id: str,
    output_path: str,
    db_path: str = "data/decisions.db"
) -> bool:
    """
    Export training configuration JSON for a character.

    Args:
        character_id: Character ID
        output_path: Output JSON file path
        db_path: Path to decisions database

    Returns:
        True if successful
    """
    hints = get_hyperparameter_hints_from_db(character_id, db_path)

    if not hints:
        logger.error(f"Could not generate hints for {character_id}")
        return False

    # Create full training config
    config = {
        "character_id": character_id,
        "character_class": hints.character_class,
        "classification_confidence": hints.confidence,

        # Training config for qlora_training.py
        "training_config": hints.to_training_config(),

        # Curation config for data_curation_pipeline.py
        "curation_config": hints.to_curation_config(),

        # Metadata
        "reasoning": hints.reasoning,
        "data_requirements": hints.data_requirements,
        "generated_at": __import__('datetime').datetime.now().isoformat()
    }

    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)

    logger.info(f"Exported training config to {output_path}")
    return True


def list_character_classes() -> Dict[str, CharacterClassProfile]:
    """Get all available character class profiles"""
    return CHARACTER_CLASSES.copy()


def print_character_class_info(class_name: str):
    """Print information about a character class"""
    if class_name not in CHARACTER_CLASSES:
        print(f"Unknown class: {class_name}")
        print(f"Available classes: {', '.join(CHARACTER_CLASSES.keys())}")
        return

    profile = CHARACTER_CLASSES[class_name]

    print(f"\n{class_name.upper()}")
    print(f"{'=' * 60}")
    print(f"Description: {profile.description}")
    print(f"\nHyperparameters:")
    print(f"  lora_r: {profile.lora_r}")
    print(f"  lora_alpha: {profile.lora_alpha}")
    print(f"  lora_dropout: {profile.lora_dropout}")
    print(f"  learning_rate: {profile.learning_rate}")
    print(f"  num_train_epochs: {profile.num_train_epochs}")
    print(f"  per_device_batch_size: {profile.per_device_batch_size}")
    print(f"\nData Settings:")
    print(f"  min_confidence: {profile.min_confidence}")
    print(f"  min_quality_score: {profile.min_quality_score}")
    print(f"  target_success_ratio: {profile.target_success_ratio}")
    print(f"\nReasoning: {profile.reasoning}")
    print(f"\nData Requirements: {profile.data_requirements}")


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    """CLI for hyperparameter hints"""
    import argparse

    parser = argparse.ArgumentParser(
        description="DMLog Hyperparameter Optimization Hints"
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # List classes
    subparsers.add_parser('list-classes', help='List all character classes')

    # Show class info
    class_info_parser = subparsers.add_parser('class-info', help='Show character class details')
    class_info_parser.add_argument('class_name', help='Character class name')

    # Generate hints
    hints_parser = subparsers.add_parser('generate', help='Generate hyperparameter hints')
    hints_parser.add_argument('character_id', help='Character ID')
    hints_parser.add_argument('--db-path', default='data/decisions.db', help='Database path')
    hints_parser.add_argument('--output', help='Output JSON file path')
    hints_parser.add_argument('--print', action='store_true', help='Print to console')

    args = parser.parse_args()

    if args.command == 'list-classes':
        print("\nAvailable Character Classes:")
        print("=" * 50)
        for name in CHARACTER_CLASSES.keys():
            profile = CHARACTER_CLASSES[name]
            print(f"\n{name}:")
            print(f"  {profile.description}")

    elif args.command == 'class-info':
        print_character_class_info(args.class_name)

    elif args.command == 'generate':
        hints = get_hyperparameter_hints_from_db(args.character_id, args.db_path)

        if not hints:
            print(f"Error: Could not generate hints for {args.character_id}")
            return

        config = {
            "training_config": hints.to_training_config(),
            "curation_config": hints.to_curation_config(),
            "character_class": hints.character_class,
            "confidence": hints.confidence,
            "reasoning": hints.reasoning
        }

        if args.print:
            print(json.dumps(config, indent=2))

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"Saved to {args.output}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
