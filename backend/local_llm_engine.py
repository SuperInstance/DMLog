"""
Local LLM Engine for Character Brains

This module provides efficient local inference using llama.cpp for running small
language models on RTX 4050 (6GB VRAM). Supports model hot-swapping, batching,
and VRAM budget management.

Key Features:
- Multiple model tiers (Nano, Micro, Small)
- VRAM budget enforcement (<5.5GB total)
- Model caching and hot-swapping
- Async inference with batching
- Performance monitoring

Hardware Target: RTX 4050 with 6GB VRAM
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logging.warning("llama-cpp-python not installed. Local LM features disabled.")

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Model tiers for different use cases"""
    NANO = "nano"      # <1GB VRAM, <100ms response - Ultra fast tactical
    MICRO = "micro"    # 1-2GB VRAM, <500ms response - Standard gameplay
    SMALL = "small"    # 3-4GB VRAM, <3s response - Reflection/planning
    FALLBACK = "fallback"  # Cloud LLM - Novel situations


@dataclass
class ModelConfig:
    """Configuration for a local model"""
    name: str
    tier: ModelTier
    model_path: str
    vram_mb: int  # Expected VRAM usage in MB
    context_size: int = 2048
    n_gpu_layers: int = -1  # -1 = use all
    temperature: float = 0.8
    top_p: float = 0.95
    repeat_penalty: float = 1.1
    max_tokens: int = 256
    
    def __post_init__(self):
        """Validate model path exists"""
        if not Path(self.model_path).exists():
            logger.warning(f"Model path not found: {self.model_path}")


@dataclass
class InferenceRequest:
    """Request for local LM inference"""
    request_id: str
    character_id: str
    prompt: str
    tier: ModelTier = ModelTier.MICRO
    max_tokens: int = 256
    temperature: float = 0.8
    stop_sequences: List[str] = field(default_factory=lambda: ["\n\n", "User:", "DM:"])
    priority: int = 5  # 1=lowest, 10=highest
    created_at: float = field(default_factory=time.time)


@dataclass
class InferenceResponse:
    """Response from local LM inference"""
    request_id: str
    character_id: str
    text: str
    tier_used: ModelTier
    tokens_generated: int
    time_seconds: float
    vram_used_mb: int
    model_name: str
    success: bool = True
    error: Optional[str] = None


class LocalLLMEngine:
    """
    Local LLM inference engine with multi-model support
    
    Manages multiple models, VRAM budget, and efficient inference
    for character brains running on RTX 4050.
    """
    
    def __init__(
        self,
        models_dir: str = "models",
        vram_budget_mb: int = 5500,  # Leave 500MB headroom from 6GB
        max_cache_size: int = 2  # Number of models to keep in memory
    ):
        """
        Initialize local LLM engine
        
        Args:
            models_dir: Directory containing model files
            vram_budget_mb: Maximum VRAM to use (default: 5.5GB)
            max_cache_size: Max models to keep loaded
        """
        self.models_dir = Path(models_dir)
        self.vram_budget_mb = vram_budget_mb
        self.max_cache_size = max_cache_size
        
        # Model registry
        self.model_configs: Dict[str, ModelConfig] = {}
        self.loaded_models: Dict[str, Llama] = {}
        self.model_access_times: Dict[str, float] = {}
        
        # Request queue
        self.request_queue: asyncio.Queue = asyncio.Queue()
        self.response_futures: Dict[str, asyncio.Future] = {}
        
        # Metrics
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_time_seconds": 0.0,
            "model_swaps": 0,
            "vram_peak_mb": 0
        }
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Worker task
        self._worker_task = None
        
        logger.info(f"LocalLLMEngine initialized: VRAM budget={vram_budget_mb}MB")
    
    def register_model(self, config: ModelConfig) -> None:
        """
        Register a model configuration
        
        Args:
            config: Model configuration to register
        """
        self.model_configs[config.name] = config
        logger.info(f"Registered model: {config.name} ({config.tier.value}, ~{config.vram_mb}MB)")
    
    def register_default_models(self) -> None:
        """Register default model configurations"""
        
        # Nano tier: TinyLlama for ultra-fast decisions
        self.register_model(ModelConfig(
            name="tinyllama-1.1b",
            tier=ModelTier.NANO,
            model_path=str(self.models_dir / "tinyllama" / "tinyllama-1.1b-q4.gguf"),
            vram_mb=700,
            context_size=1024,
            max_tokens=128
        ))
        
        # Micro tier: Phi-3-mini for standard gameplay
        self.register_model(ModelConfig(
            name="phi-3-mini",
            tier=ModelTier.MICRO,
            model_path=str(self.models_dir / "phi-3-mini" / "Phi-3-mini-4k-instruct-q4.gguf"),
            vram_mb=2500,
            context_size=2048,
            max_tokens=256
        ))
        
        # Small tier: Llama-3.1-8B for reflection
        self.register_model(ModelConfig(
            name="llama-3.1-8b",
            tier=ModelTier.SMALL,
            model_path=str(self.models_dir / "llama-3.1" / "llama-3.1-8b-q4.gguf"),
            vram_mb=4500,
            context_size=4096,
            max_tokens=512
        ))
    
    async def start(self) -> None:
        """Start the inference engine"""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info("LocalLLMEngine worker started")
    
    async def stop(self) -> None:
        """Stop the inference engine"""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        
        # Unload all models
        for model_name in list(self.loaded_models.keys()):
            await self._unload_model(model_name)
        
        logger.info("LocalLLMEngine stopped")
    
    async def infer(
        self,
        request: InferenceRequest
    ) -> InferenceResponse:
        """
        Submit inference request and wait for response
        
        Args:
            request: Inference request
            
        Returns:
            Inference response
        """
        # Create future for response
        future = asyncio.Future()
        self.response_futures[request.request_id] = future
        
        # Add to queue
        await self.request_queue.put(request)
        
        # Wait for response
        try:
            response = await future
            return response
        except Exception as e:
            logger.error(f"Inference failed for {request.request_id}: {e}")
            return InferenceResponse(
                request_id=request.request_id,
                character_id=request.character_id,
                text="",
                tier_used=request.tier,
                tokens_generated=0,
                time_seconds=0.0,
                vram_used_mb=0,
                model_name="",
                success=False,
                error=str(e)
            )
    
    async def _worker_loop(self) -> None:
        """Background worker processing inference requests"""
        logger.info("Worker loop started")
        
        while True:
            try:
                # Get next request (wait indefinitely)
                request = await self.request_queue.get()
                
                # Process request
                response = await self._process_request(request)
                
                # Set future result
                if request.request_id in self.response_futures:
                    future = self.response_futures.pop(request.request_id)
                    if not future.done():
                        future.set_result(response)
                
                # Mark task done
                self.request_queue.task_done()
                
            except asyncio.CancelledError:
                logger.info("Worker loop cancelled")
                break
            except Exception as e:
                logger.error(f"Worker loop error: {e}", exc_info=True)
    
    async def _process_request(
        self,
        request: InferenceRequest
    ) -> InferenceResponse:
        """
        Process a single inference request
        
        Args:
            request: Request to process
            
        Returns:
            Inference response
        """
        start_time = time.time()
        self.metrics["total_requests"] += 1
        
        try:
            # Get model for this tier
            model_name = await self._get_model_for_tier(request.tier)
            if not model_name:
                raise Exception(f"No model available for tier {request.tier.value}")
            
            # Load model if needed
            model = await self._ensure_model_loaded(model_name)
            
            # Run inference
            result = await asyncio.to_thread(
                self._sync_infer,
                model,
                request
            )
            
            # Calculate metrics
            elapsed = time.time() - start_time
            config = self.model_configs[model_name]
            
            self.metrics["successful_requests"] += 1
            self.metrics["total_tokens"] += result["tokens_generated"]
            self.metrics["total_time_seconds"] += elapsed
            
            # Update VRAM peak
            current_vram = self._estimate_vram_usage()
            if current_vram > self.metrics["vram_peak_mb"]:
                self.metrics["vram_peak_mb"] = current_vram
            
            # Build response
            response = InferenceResponse(
                request_id=request.request_id,
                character_id=request.character_id,
                text=result["text"],
                tier_used=request.tier,
                tokens_generated=result["tokens_generated"],
                time_seconds=elapsed,
                vram_used_mb=current_vram,
                model_name=model_name,
                success=True
            )
            
            logger.debug(f"Inference complete: {model_name} ({elapsed:.2f}s, {result['tokens_generated']} tokens)")
            
            return response
            
        except Exception as e:
            self.metrics["failed_requests"] += 1
            elapsed = time.time() - start_time
            
            logger.error(f"Inference failed: {e}")
            
            return InferenceResponse(
                request_id=request.request_id,
                character_id=request.character_id,
                text="",
                tier_used=request.tier,
                tokens_generated=0,
                time_seconds=elapsed,
                vram_used_mb=self._estimate_vram_usage(),
                model_name="",
                success=False,
                error=str(e)
            )
    
    def _sync_infer(
        self,
        model: Llama,
        request: InferenceRequest
    ) -> Dict[str, Any]:
        """
        Synchronous inference (runs in thread)
        
        Args:
            model: Loaded Llama model
            request: Inference request
            
        Returns:
            Dict with 'text' and 'tokens_generated'
        """
        result = model(
            request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stop=request.stop_sequences,
            echo=False
        )
        
        return {
            "text": result["choices"][0]["text"].strip(),
            "tokens_generated": result["usage"]["completion_tokens"]
        }
    
    async def _get_model_for_tier(
        self,
        tier: ModelTier
    ) -> Optional[str]:
        """
        Get model name for a given tier
        
        Args:
            tier: Model tier
            
        Returns:
            Model name or None if not found
        """
        # Find first registered model for this tier
        for name, config in self.model_configs.items():
            if config.tier == tier:
                return name
        
        logger.warning(f"No model registered for tier {tier.value}")
        return None
    
    async def _ensure_model_loaded(
        self,
        model_name: str
    ) -> Llama:
        """
        Ensure model is loaded, managing VRAM budget
        
        Args:
            model_name: Name of model to load
            
        Returns:
            Loaded Llama model
        """
        async with self._lock:
            # Already loaded?
            if model_name in self.loaded_models:
                self.model_access_times[model_name] = time.time()
                return self.loaded_models[model_name]
            
            # Check if we need to unload models first
            config = self.model_configs[model_name]
            current_vram = self._estimate_vram_usage()
            
            while current_vram + config.vram_mb > self.vram_budget_mb:
                # Unload least recently used model
                lru_model = min(
                    self.loaded_models.keys(),
                    key=lambda x: self.model_access_times.get(x, 0)
                )
                await self._unload_model(lru_model)
                current_vram = self._estimate_vram_usage()
            
            # Load model
            logger.info(f"Loading model: {model_name}")
            
            if not LLAMA_CPP_AVAILABLE:
                raise Exception("llama-cpp-python not installed")
            
            try:
                model = Llama(
                    model_path=config.model_path,
                    n_ctx=config.context_size,
                    n_gpu_layers=config.n_gpu_layers,
                    verbose=False
                )
                
                self.loaded_models[model_name] = model
                self.model_access_times[model_name] = time.time()
                self.metrics["model_swaps"] += 1
                
                logger.info(f"Model loaded successfully: {model_name}")
                
                return model
                
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}")
                raise
    
    async def _unload_model(self, model_name: str) -> None:
        """
        Unload a model from memory
        
        Args:
            model_name: Name of model to unload
        """
        if model_name in self.loaded_models:
            logger.info(f"Unloading model: {model_name}")
            
            # Delete model (frees VRAM)
            del self.loaded_models[model_name]
            del self.model_access_times[model_name]
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Try to free CUDA memory (if available)
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass
    
    def _estimate_vram_usage(self) -> int:
        """
        Estimate current VRAM usage
        
        Returns:
            Estimated VRAM usage in MB
        """
        total_mb = 0
        for model_name in self.loaded_models.keys():
            if model_name in self.model_configs:
                total_mb += self.model_configs[model_name].vram_mb
        return total_mb
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics
        
        Returns:
            Metrics dictionary
        """
        metrics = self.metrics.copy()
        
        # Calculate derived metrics
        if metrics["successful_requests"] > 0:
            metrics["avg_time_seconds"] = (
                metrics["total_time_seconds"] / metrics["successful_requests"]
            )
            metrics["avg_tokens"] = (
                metrics["total_tokens"] / metrics["successful_requests"]
            )
            metrics["tokens_per_second"] = (
                metrics["total_tokens"] / metrics["total_time_seconds"]
                if metrics["total_time_seconds"] > 0 else 0
            )
        else:
            metrics["avg_time_seconds"] = 0
            metrics["avg_tokens"] = 0
            metrics["tokens_per_second"] = 0
        
        # Current state
        metrics["loaded_models"] = list(self.loaded_models.keys())
        metrics["vram_current_mb"] = self._estimate_vram_usage()
        metrics["queue_size"] = self.request_queue.qsize()
        
        return metrics
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get engine status
        
        Returns:
            Status dictionary
        """
        return {
            "running": self._worker_task is not None,
            "loaded_models": list(self.loaded_models.keys()),
            "registered_models": list(self.model_configs.keys()),
            "vram_used_mb": self._estimate_vram_usage(),
            "vram_budget_mb": self.vram_budget_mb,
            "vram_available_mb": self.vram_budget_mb - self._estimate_vram_usage(),
            "queue_size": self.request_queue.qsize(),
            "metrics": self.get_metrics()
        }


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    async def test_engine():
        """Test the local LLM engine"""
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create engine
        engine = LocalLLMEngine(
            models_dir="models",
            vram_budget_mb=5500
        )
        
        # Register default models
        engine.register_default_models()
        
        # Start engine
        await engine.start()
        
        print("\n" + "="*50)
        print("LOCAL LLM ENGINE TEST")
        print("="*50)
        
        try:
            # Test inference with different tiers
            test_prompts = [
                ("Combat decision", ModelTier.NANO, 
                 "You are Thorin, a dwarf fighter. Attack the orc or goblin? Respond briefly:"),
                
                ("Social interaction", ModelTier.MICRO,
                 "You are Elara, an elf ranger. The innkeeper asks what you need. Respond in character:"),
                
                ("Strategic planning", ModelTier.SMALL,
                 "You are Grunk, a barbarian. Plan your next 3 actions to win this battle:")
            ]
            
            for label, tier, prompt in test_prompts:
                print(f"\n{'-'*50}")
                print(f"Test: {label} (Tier: {tier.value})")
                print(f"{'-'*50}")
                
                request = InferenceRequest(
                    request_id=f"test_{label.replace(' ', '_')}",
                    character_id="test_char",
                    prompt=prompt,
                    tier=tier,
                    max_tokens=100
                )
                
                response = await engine.infer(request)
                
                if response.success:
                    print(f"Response: {response.text}")
                    print(f"Time: {response.time_seconds:.2f}s")
                    print(f"Tokens: {response.tokens_generated}")
                    print(f"Model: {response.model_name}")
                    print(f"VRAM: {response.vram_used_mb}MB")
                else:
                    print(f"ERROR: {response.error}")
            
            # Print final metrics
            print(f"\n{'='*50}")
            print("FINAL METRICS")
            print(f"{'='*50}")
            
            metrics = engine.get_metrics()
            print(f"Total Requests: {metrics['total_requests']}")
            print(f"Successful: {metrics['successful_requests']}")
            print(f"Failed: {metrics['failed_requests']}")
            print(f"Avg Time: {metrics['avg_time_seconds']:.2f}s")
            print(f"Avg Tokens: {metrics['avg_tokens']:.1f}")
            print(f"Tokens/sec: {metrics['tokens_per_second']:.1f}")
            print(f"Peak VRAM: {metrics['vram_peak_mb']}MB")
            print(f"Model Swaps: {metrics['model_swaps']}")
            
        finally:
            # Stop engine
            await engine.stop()
            print("\nEngine stopped")
    
    # Run test
    asyncio.run(test_engine())
