"""
AI Society D&D - Model Routing System
======================================
Intelligent LLM selection based on task complexity, cost, and latency requirements.

Routes tasks to:
- GPT-4 / Claude Opus: Complex reasoning, deep roleplay, strategic planning
- GPT-3.5 / Claude Sonnet: Standard gameplay, simple decisions
- Phi-3 / Local models: Mechanical operations, quick checks

Implements:
- Complexity scoring
- Cost optimization
- Latency management
- Fallback strategies
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
import asyncio

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage


# ============================================================================
# TASK COMPLEXITY ANALYSIS
# ============================================================================

class TaskComplexity(Enum):
    """Task complexity levels"""
    TRIVIAL = 1      # "Roll a die", "What's my HP?"
    SIMPLE = 2       # "Make a perception check", "Attack the goblin"
    MODERATE = 3     # "Decide what to do", "Roleplay dialogue"
    COMPLEX = 4      # "Analyze situation deeply", "Multi-step planning"
    EXPERT = 5       # "Strategic planning", "Moral dilemma", "Complex social interaction"


@dataclass
class ComplexitySignals:
    """Signals that indicate task complexity"""
    
    # Content indicators
    word_count: int = 0
    question_marks: int = 0
    has_moral_dilemma: bool = False
    requires_planning: bool = False
    involves_multiple_npcs: bool = False
    
    # Context indicators
    recent_history_length: int = 0
    memory_queries_needed: int = 0
    requires_creativity: bool = False
    
    # Decision indicators
    number_of_options: int = 0
    has_consequences: bool = False
    time_pressure: bool = False


class ComplexityAnalyzer:
    """
    Analyzes tasks to determine their complexity level.
    Used to route to appropriate model.
    """
    
    # Keywords indicating different complexity levels
    TRIVIAL_KEYWORDS = ['roll', 'check', 'hp', 'ac', 'stat', 'dice', 'number']
    SIMPLE_KEYWORDS = ['attack', 'move', 'look', 'search', 'grab', 'take']
    MODERATE_KEYWORDS = ['decide', 'think', 'consider', 'talk', 'say', 'ask']
    COMPLEX_KEYWORDS = ['plan', 'strategy', 'analyze', 'evaluate', 'negotiate']
    EXPERT_KEYWORDS = ['moral', 'ethical', 'dilemma', 'philosophical', 'existential']
    
    @staticmethod
    def analyze(
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[TaskComplexity, ComplexitySignals, float]:
        """
        Analyze task complexity.
        
        Returns:
            (complexity_level, signals, confidence_score)
        """
        signals = ComplexitySignals()
        
        # Basic text analysis
        task_lower = task_description.lower()
        signals.word_count = len(task_description.split())
        signals.question_marks = task_description.count('?')
        
        # Keyword matching
        trivial_score = sum(1 for kw in ComplexityAnalyzer.TRIVIAL_KEYWORDS if kw in task_lower)
        simple_score = sum(1 for kw in ComplexityAnalyzer.SIMPLE_KEYWORDS if kw in task_lower)
        moderate_score = sum(1 for kw in ComplexityAnalyzer.MODERATE_KEYWORDS if kw in task_lower)
        complex_score = sum(1 for kw in ComplexityAnalyzer.COMPLEX_KEYWORDS if kw in task_lower)
        expert_score = sum(1 for kw in ComplexityAnalyzer.EXPERT_KEYWORDS if kw in task_lower)
        
        # Check for moral dilemmas
        moral_indicators = ['should i', 'is it right', 'morally', 'ethical', 'wrong']
        signals.has_moral_dilemma = any(ind in task_lower for ind in moral_indicators)
        
        # Check for planning requirements
        planning_indicators = ['plan', 'strategy', 'prepare', 'next steps', 'long term']
        signals.requires_planning = any(ind in task_lower for ind in planning_indicators)
        
        # Context analysis
        if context:
            signals.recent_history_length = context.get('history_length', 0)
            signals.memory_queries_needed = context.get('memory_queries', 0)
            signals.requires_creativity = context.get('creative', False)
            signals.number_of_options = context.get('options', 0)
            signals.has_consequences = context.get('has_consequences', False)
            signals.involves_multiple_npcs = context.get('npc_count', 0) > 1
        
        # Calculate complexity score
        score = 0.0
        confidence = 1.0
        
        # Word count contribution
        if signals.word_count < 10:
            score += 1.0
        elif signals.word_count < 50:
            score += 2.0
        elif signals.word_count < 150:
            score += 3.0
        else:
            score += 4.0
        
        # Keyword contributions
        if expert_score > 0:
            score += 5.0
            confidence = 0.9
        elif complex_score > 0:
            score += 4.0
            confidence = 0.85
        elif moderate_score > 0:
            score += 3.0
        elif simple_score > 0:
            score += 2.0
        elif trivial_score > 0:
            score += 1.0
        
        # Special case boosters
        if signals.has_moral_dilemma:
            score += 2.0
        if signals.requires_planning:
            score += 1.5
        if signals.involves_multiple_npcs:
            score += 1.0
        if signals.has_consequences:
            score += 1.0
        if signals.number_of_options > 3:
            score += 1.0
        
        # Normalize to 1-5 scale
        normalized_score = min(max(score / 3.0, 1.0), 5.0)
        
        # Map to complexity enum
        if normalized_score < 1.5:
            complexity = TaskComplexity.TRIVIAL
        elif normalized_score < 2.5:
            complexity = TaskComplexity.SIMPLE
        elif normalized_score < 3.5:
            complexity = TaskComplexity.MODERATE
        elif normalized_score < 4.5:
            complexity = TaskComplexity.COMPLEX
        else:
            complexity = TaskComplexity.EXPERT
        
        return complexity, signals, confidence


# ============================================================================
# MODEL SELECTION & ROUTING
# ============================================================================

@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    name: str
    provider: str  # "openai", "anthropic", "local"
    model_id: str
    
    # Capabilities
    max_tokens: int
    supports_streaming: bool = True
    
    # Performance
    avg_latency_ms: float = 1000.0
    cost_per_1k_tokens: float = 0.0
    
    # Routing preferences
    min_complexity: TaskComplexity = TaskComplexity.TRIVIAL
    max_complexity: TaskComplexity = TaskComplexity.EXPERT
    preferred_for: List[str] = field(default_factory=list)


class ModelRouter:
    """
    Routes tasks to appropriate LLM based on complexity and constraints.
    
    Optimization goals:
    1. Match task complexity to model capability
    2. Minimize cost when possible
    3. Meet latency requirements
    4. Maintain quality standards
    """
    
    def __init__(self):
        self.models = self._initialize_models()
        self.routing_history: List[Dict] = []
        
        # Performance tracking
        self.model_performance: Dict[str, Dict] = {}
        
        # Configuration
        self.cost_weight = 0.3
        self.latency_weight = 0.2
        self.capability_weight = 0.5
    
    def _initialize_models(self) -> Dict[str, ModelConfig]:
        """Initialize available models"""
        return {
            # Premium models - complex reasoning
            "gpt-4": ModelConfig(
                name="GPT-4",
                provider="openai",
                model_id="gpt-4",
                max_tokens=8192,
                avg_latency_ms=3000.0,
                cost_per_1k_tokens=0.03,
                min_complexity=TaskComplexity.COMPLEX,
                preferred_for=["strategic", "moral", "creative", "complex_social"]
            ),
            
            "claude-opus": ModelConfig(
                name="Claude Opus 4",
                provider="anthropic",
                model_id="claude-opus-4",
                max_tokens=200000,
                avg_latency_ms=2500.0,
                cost_per_1k_tokens=0.015,
                min_complexity=TaskComplexity.COMPLEX,
                preferred_for=["nuanced", "analytical", "long_context"]
            ),
            
            # Standard models - everyday tasks
            "gpt-4o-mini": ModelConfig(
                name="GPT-4o Mini",
                provider="openai",
                model_id="gpt-4o-mini",
                max_tokens=16384,
                avg_latency_ms=800.0,
                cost_per_1k_tokens=0.00015,
                min_complexity=TaskComplexity.SIMPLE,
                max_complexity=TaskComplexity.COMPLEX,
                preferred_for=["standard", "gameplay", "dialogue"]
            ),
            
            "claude-sonnet": ModelConfig(
                name="Claude Sonnet 4",
                provider="anthropic",
                model_id="claude-sonnet-4",
                max_tokens=200000,
                avg_latency_ms=1200.0,
                cost_per_1k_tokens=0.003,
                min_complexity=TaskComplexity.SIMPLE,
                max_complexity=TaskComplexity.COMPLEX,
                preferred_for=["balanced", "efficient"]
            ),
            
            # Budget models - simple operations
            "gpt-3.5-turbo": ModelConfig(
                name="GPT-3.5 Turbo",
                provider="openai",
                model_id="gpt-3.5-turbo",
                max_tokens=4096,
                avg_latency_ms=500.0,
                cost_per_1k_tokens=0.0005,
                min_complexity=TaskComplexity.TRIVIAL,
                max_complexity=TaskComplexity.MODERATE,
                preferred_for=["quick", "simple", "mechanical"]
            ),
        }
    
    def route(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Tuple[ModelConfig, Dict[str, Any]]:
        """
        Route task to best model.
        
        Args:
            task_description: What needs to be done
            context: Additional context about the task
            constraints: Constraints (max_latency_ms, max_cost, required_quality)
        
        Returns:
            (selected_model, routing_metadata)
        """
        constraints = constraints or {}
        
        # Analyze complexity
        complexity, signals, confidence = ComplexityAnalyzer.analyze(
            task_description,
            context
        )
        
        # Score each model
        model_scores = {}
        for model_name, model in self.models.items():
            score = self._score_model(
                model,
                complexity,
                signals,
                constraints
            )
            model_scores[model_name] = score
        
        # Select best model
        best_model_name = max(model_scores, key=model_scores.get)
        best_model = self.models[best_model_name]
        
        # Check constraints
        if 'max_latency_ms' in constraints:
            if best_model.avg_latency_ms > constraints['max_latency_ms']:
                # Find faster model
                valid_models = [
                    (name, model) for name, model in self.models.items()
                    if model.avg_latency_ms <= constraints['max_latency_ms']
                    and model.min_complexity.value <= complexity.value
                ]
                if valid_models:
                    best_model_name, best_model = max(
                        valid_models,
                        key=lambda x: model_scores.get(x[0], 0)
                    )
        
        # Record routing decision
        metadata = {
            "complexity": complexity.name,
            "complexity_score": complexity.value,
            "confidence": confidence,
            "signals": signals,
            "model_scores": model_scores,
            "selected_model": best_model_name,
            "timestamp": datetime.now().isoformat()
        }
        
        self.routing_history.append(metadata)
        
        return best_model, metadata
    
    def _score_model(
        self,
        model: ModelConfig,
        complexity: TaskComplexity,
        signals: ComplexitySignals,
        constraints: Dict[str, Any]
    ) -> float:
        """
        Score a model for this task.
        
        Higher score = better match.
        """
        score = 0.0
        
        # Capability match (most important)
        if model.min_complexity.value <= complexity.value <= model.max_complexity.value:
            score += 10.0 * self.capability_weight
            
            # Bonus for being in preferred range
            optimal_complexity = (model.min_complexity.value + model.max_complexity.value) / 2
            complexity_distance = abs(complexity.value - optimal_complexity)
            score += (3.0 - complexity_distance) * self.capability_weight
        else:
            # Penalize if outside range
            if complexity.value < model.min_complexity.value:
                score -= 5.0  # Overkill
            else:
                score -= 10.0  # Can't handle it
        
        # Cost efficiency
        if 'max_cost' in constraints:
            if model.cost_per_1k_tokens <= constraints['max_cost']:
                # Prefer cheaper within budget
                cost_score = 5.0 * (1.0 - model.cost_per_1k_tokens / constraints['max_cost'])
                score += cost_score * self.cost_weight
        else:
            # General preference for lower cost
            cost_score = 5.0 * (1.0 - min(model.cost_per_1k_tokens, 0.05) / 0.05)
            score += cost_score * self.cost_weight
        
        # Latency
        if 'max_latency_ms' in constraints:
            if model.avg_latency_ms <= constraints['max_latency_ms']:
                latency_score = 5.0 * (1.0 - model.avg_latency_ms / constraints['max_latency_ms'])
                score += latency_score * self.latency_weight
            else:
                score -= 10.0  # Too slow
        else:
            # General preference for lower latency
            latency_score = 5.0 * (1.0 - min(model.avg_latency_ms, 5000.0) / 5000.0)
            score += latency_score * self.latency_weight
        
        # Performance history
        if model.name in self.model_performance:
            perf = self.model_performance[model.name]
            if 'success_rate' in perf:
                score += perf['success_rate'] * 2.0
        
        return score
    
    async def invoke(
        self,
        task_description: str,
        messages: List[BaseMessage],
        context: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Route and invoke the appropriate model.
        
        Returns:
            (response_text, routing_metadata)
        """
        # Route to best model
        model_config, metadata = self.route(
            task_description,
            context,
            constraints
        )
        
        # Create LLM instance
        try:
            if model_config.provider == "openai":
                llm = ChatOpenAI(
                    model=model_config.model_id,
                    temperature=0.7
                )
            elif model_config.provider == "anthropic":
                llm = ChatAnthropic(
                    model=model_config.model_id,
                    temperature=0.7
                )
            else:
                raise ValueError(f"Unknown provider: {model_config.provider}")
            
            # Invoke
            start_time = datetime.now()
            response = await llm.ainvoke(messages)
            end_time = datetime.now()
            
            # Track performance
            actual_latency = (end_time - start_time).total_seconds() * 1000
            metadata['actual_latency_ms'] = actual_latency
            metadata['success'] = True
            
            # Update performance tracking
            if model_config.name not in self.model_performance:
                self.model_performance[model_config.name] = {
                    'total_calls': 0,
                    'successful_calls': 0,
                    'avg_latency': 0.0
                }
            
            perf = self.model_performance[model_config.name]
            perf['total_calls'] += 1
            perf['successful_calls'] += 1
            perf['avg_latency'] = (
                (perf['avg_latency'] * (perf['total_calls'] - 1) + actual_latency) /
                perf['total_calls']
            )
            perf['success_rate'] = perf['successful_calls'] / perf['total_calls']
            
            return response.content, metadata
            
        except Exception as e:
            metadata['success'] = False
            metadata['error'] = str(e)
            
            # Try fallback
            fallback_response = "I encountered an error processing that request."
            return fallback_response, metadata
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get statistics about routing decisions"""
        if not self.routing_history:
            return {"message": "No routing history yet"}
        
        complexity_counts = {}
        model_usage = {}
        
        for entry in self.routing_history:
            complexity = entry['complexity']
            model = entry['selected_model']
            
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
            model_usage[model] = model_usage.get(model, 0) + 1
        
        return {
            "total_routings": len(self.routing_history),
            "complexity_distribution": complexity_counts,
            "model_usage": model_usage,
            "model_performance": self.model_performance
        }


# ============================================================================
# INTEGRATION WITH CHARACTER SYSTEM
# ============================================================================

class RoutedCharacterDecisionMaker:
    """
    Enhanced character decision making with intelligent model routing.
    Replaces simple model selection with complexity-aware routing.
    """
    
    def __init__(self, character):
        self.character = character
        self.router = ModelRouter()
    
    async def make_decision(
        self,
        situation: str,
        available_actions: List[str] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make character decision with intelligent model routing.
        """
        # Build context
        context = {
            'history_length': len(self.character.memory_engine.memories),
            'memory_queries': 5 if available_actions else 3,
            'creative': 'roleplay' in situation.lower() or 'creative' in situation.lower(),
            'options': len(available_actions) if available_actions else 0,
            'has_consequences': 'consequence' in situation.lower() or 'important' in situation.lower()
        }
        
        # Get character context
        char_context = self.character.get_full_context(include_recent_memories=5)
        
        # Build prompt
        prompt_parts = [
            char_context,
            f"\n=== Current Situation ===\n{situation}"
        ]
        
        if available_actions:
            prompt_parts.append("\n=== Available Actions ===")
            for i, action in enumerate(available_actions, 1):
                prompt_parts.append(f"{i}. {action}")
        
        prompt_parts.append("\nWhat do you do? Respond in character.")
        
        full_prompt = "\n".join(prompt_parts)
        
        # Route and invoke
        messages = [
            SystemMessage(content=f"You are {self.character.name}, a {self.character.race} {self.character.character_class.name}."),
            HumanMessage(content=full_prompt)
        ]
        
        response, metadata = await self.router.invoke(
            task_description=situation,
            messages=messages,
            context=context,
            constraints=constraints
        )
        
        return {
            "action": response,
            "reasoning": f"Used {metadata['selected_model']} (complexity: {metadata['complexity']})",
            "confidence": metadata['confidence'],
            "model_metadata": metadata
        }
