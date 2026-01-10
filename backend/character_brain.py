"""
Character Brain System

Integrates local LLM inference with character personalities, memory, and context.
Each character has a "brain" that uses Small LMs for decision-making while
maintaining personality consistency.

Key Features:
- Personality-driven prompt construction
- Context window management
- Memory integration (vector DB + recent history)
- Tier selection (Nano/Micro/Small based on situation)
- Consistency tracking
- LoRA weight support
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from pathlib import Path

from local_llm_engine import LocalLLMEngine, ModelTier, InferenceRequest

logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """Types of decisions characters make"""
    COMBAT = "combat"           # Combat actions (attack, defend, move)
    SOCIAL = "social"           # Dialogue, persuasion, deception
    EXPLORATION = "exploration" # Perception, investigation, navigation
    PLANNING = "planning"       # Strategic thinking, multi-turn plans
    REFLECTION = "reflection"   # Self-analysis, memory consolidation
    CREATIVE = "creative"       # Problem-solving, out-of-box thinking


@dataclass
class BrainConfig:
    """Configuration for a character's brain"""
    # Model preferences
    default_tier: ModelTier = ModelTier.MICRO
    combat_tier: ModelTier = ModelTier.NANO      # Fast decisions
    social_tier: ModelTier = ModelTier.MICRO     # Personality matters
    planning_tier: ModelTier = ModelTier.SMALL   # Deep thinking
    
    # Context management
    context_size: int = 1024
    max_recent_memories: int = 5
    max_conversation_history: int = 10
    
    # Response generation
    temperature: float = 0.8
    max_tokens: int = 200
    
    # LoRA
    lora_path: Optional[str] = None
    use_lora: bool = False
    
    # Consistency
    personality_strength: float = 0.8  # 0-1, how much to emphasize personality
    creativity: float = 0.7             # 0-1, how creative vs predictable


@dataclass
class DecisionContext:
    """Context for a character decision"""
    decision_type: DecisionType
    situation: str
    options: List[str] = field(default_factory=list)
    urgency: float = 0.5  # 0=can wait, 1=immediate
    stakes: float = 0.5   # 0=trivial, 1=life-or-death
    novelty: float = 0.5  # 0=familiar, 1=never seen before
    
    # Additional context
    recent_events: List[str] = field(default_factory=list)
    relevant_memories: List[str] = field(default_factory=list)
    active_goals: List[str] = field(default_factory=list)
    relationship_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrainDecision:
    """Decision made by character brain"""
    character_id: str
    decision_text: str
    decision_type: DecisionType
    confidence: float
    reasoning: Optional[str] = None
    tier_used: ModelTier = ModelTier.MICRO
    time_seconds: float = 0.0
    tokens_used: int = 0


class CharacterBrain:
    """
    Character brain that uses local LLM for decision-making
    
    Manages prompt construction, context, and personality consistency
    for a single character.
    """
    
    def __init__(
        self,
        character_id: str,
        character_data: Dict[str, Any],
        llm_engine: LocalLLMEngine,
        config: Optional[BrainConfig] = None
    ):
        """
        Initialize character brain
        
        Args:
            character_id: Unique character identifier
            character_data: Character profile (name, class, personality, etc.)
            llm_engine: Local LLM engine instance
            config: Brain configuration
        """
        self.character_id = character_id
        self.character_data = character_data
        self.llm_engine = llm_engine
        self.config = config or BrainConfig()
        
        # Extract personality info
        self.name = character_data.get("name", "Unknown")
        self.character_class = character_data.get("class", "Adventurer")
        self.background = character_data.get("background", "")
        self.personality = character_data.get("personality", {})
        
        # Decision history
        self.decision_history: List[BrainDecision] = []
        self.conversation_history: List[Dict[str, str]] = []
        
        # State
        self.current_mood = "neutral"
        self.stress_level = 0.0
        
        # Metrics
        self.metrics = {
            "total_decisions": 0,
            "decisions_by_type": {},
            "decisions_by_tier": {},
            "avg_response_time": 0.0,
            "personality_consistency_score": 100.0
        }
        
        logger.info(f"CharacterBrain initialized: {self.name} ({character_id})")
    
    async def make_decision(
        self,
        context: DecisionContext
    ) -> BrainDecision:
        """
        Make a decision based on context
        
        Args:
            context: Decision context
            
        Returns:
            Brain decision
        """
        start_time = time.time()
        
        # Select appropriate tier
        tier = self._select_tier(context)
        
        # Build prompt
        prompt = self._build_prompt(context)
        
        # Create inference request
        request = InferenceRequest(
            request_id=f"{self.character_id}_{int(time.time() * 1000)}",
            character_id=self.character_id,
            prompt=prompt,
            tier=tier,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature
        )
        
        try:
            # Run inference
            response = await self.llm_engine.infer(request)
            
            if not response.success:
                raise Exception(f"Inference failed: {response.error}")
            
            # Parse response
            decision_text = response.text.strip()
            
            # Calculate confidence (simple heuristic for now)
            confidence = self._estimate_confidence(context, decision_text)
            
            # Create decision
            decision = BrainDecision(
                character_id=self.character_id,
                decision_text=decision_text,
                decision_type=context.decision_type,
                confidence=confidence,
                tier_used=tier,
                time_seconds=response.time_seconds,
                tokens_used=response.tokens_generated
            )
            
            # Update history
            self._update_history(decision, context)
            
            # Update metrics
            self._update_metrics(decision)
            
            logger.debug(
                f"{self.name} decision: {decision_text[:50]}... "
                f"(tier={tier.value}, time={decision.time_seconds:.2f}s)"
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"Decision failed for {self.name}: {e}")
            
            # Return fallback decision
            return BrainDecision(
                character_id=self.character_id,
                decision_text="I need a moment to think...",
                decision_type=context.decision_type,
                confidence=0.0,
                tier_used=tier,
                time_seconds=time.time() - start_time,
                tokens_used=0
            )
    
    def _select_tier(self, context: DecisionContext) -> ModelTier:
        """
        Select appropriate model tier based on context
        
        Args:
            context: Decision context
            
        Returns:
            Model tier to use
        """
        # High urgency + low stakes = Fast tier
        if context.urgency > 0.7 and context.stakes < 0.5:
            return ModelTier.NANO
        
        # High novelty or high stakes = Smart tier
        if context.novelty > 0.7 or context.stakes > 0.7:
            return self.config.planning_tier
        
        # Planning/reflection = Smart tier
        if context.decision_type in [DecisionType.PLANNING, DecisionType.REFLECTION]:
            return self.config.planning_tier
        
        # Combat = Fast tier (unless high stakes)
        if context.decision_type == DecisionType.COMBAT:
            if context.stakes > 0.6:
                return ModelTier.MICRO
            return self.config.combat_tier
        
        # Social = Standard tier (personality matters)
        if context.decision_type == DecisionType.SOCIAL:
            return self.config.social_tier
        
        # Default
        return self.config.default_tier
    
    def _build_prompt(self, context: DecisionContext) -> str:
        """
        Build prompt for LLM inference
        
        Args:
            context: Decision context
            
        Returns:
            Formatted prompt
        """
        # Start with character identity
        prompt_parts = [
            f"You are {self.name}, a {self.character_class}."
        ]
        
        # Add personality traits
        if self.personality:
            traits = self.personality.get("traits", [])
            if traits:
                prompt_parts.append(f"Personality: {', '.join(traits)}.")
            
            values = self.personality.get("values", [])
            if values:
                prompt_parts.append(f"You value: {', '.join(values)}.")
            
            speaking_style = self.personality.get("speaking_style", "")
            if speaking_style:
                prompt_parts.append(f"Speaking style: {speaking_style}.")
        
        # Add background (brief)
        if self.background:
            bg_brief = self.background[:200]  # Keep it short
            prompt_parts.append(f"Background: {bg_brief}")
        
        # Add current state
        prompt_parts.append(f"\nCurrent mood: {self.current_mood}")
        
        # Add recent events
        if context.recent_events:
            recent = context.recent_events[-3:]  # Last 3 events
            prompt_parts.append("\nRecent events:")
            for event in recent:
                prompt_parts.append(f"- {event}")
        
        # Add relevant memories
        if context.relevant_memories:
            memories = context.relevant_memories[:3]  # Top 3 relevant
            prompt_parts.append("\nRelevant memories:")
            for memory in memories:
                prompt_parts.append(f"- {memory}")
        
        # Add active goals
        if context.active_goals:
            prompt_parts.append(f"\nYour goals: {', '.join(context.active_goals)}")
        
        # Add relationship context
        if context.relationship_context:
            prompt_parts.append("\nRelationships:")
            for person, relation in list(context.relationship_context.items())[:3]:
                prompt_parts.append(f"- {person}: {relation}")
        
        # Add the actual situation
        prompt_parts.append(f"\n{'-'*40}")
        prompt_parts.append(f"SITUATION: {context.situation}")
        
        # Add options if provided
        if context.options:
            prompt_parts.append("\nOptions:")
            for i, option in enumerate(context.options, 1):
                prompt_parts.append(f"{i}. {option}")
        
        # Add decision prompt based on type
        if context.decision_type == DecisionType.COMBAT:
            prompt_parts.append("\nWhat do you do? (Describe your action briefly)")
        elif context.decision_type == DecisionType.SOCIAL:
            prompt_parts.append("\nWhat do you say or do? (Stay in character)")
        elif context.decision_type == DecisionType.PLANNING:
            prompt_parts.append("\nWhat's your plan? (Think strategically)")
        elif context.decision_type == DecisionType.REFLECTION:
            prompt_parts.append("\nWhat are your thoughts? (Reflect deeply)")
        else:
            prompt_parts.append("\nWhat do you do?")
        
        # Add format instruction
        prompt_parts.append("\nRespond in 1-3 sentences as your character:")
        
        return "\n".join(prompt_parts)
    
    def _estimate_confidence(
        self,
        context: DecisionContext,
        decision_text: str
    ) -> float:
        """
        Estimate confidence in decision
        
        Args:
            context: Decision context
            decision_text: Generated decision
            
        Returns:
            Confidence score (0-1)
        """
        confidence = 0.7  # Base confidence
        
        # Higher confidence for familiar situations
        confidence += (1.0 - context.novelty) * 0.2
        
        # Lower confidence for high stakes
        confidence -= context.stakes * 0.2
        
        # Check if decision seems complete
        if len(decision_text) < 10:
            confidence -= 0.3
        
        # Check for uncertainty words
        uncertainty_words = ["maybe", "perhaps", "not sure", "don't know", "uncertain"]
        if any(word in decision_text.lower() for word in uncertainty_words):
            confidence -= 0.2
        
        # Clamp to 0-1
        return max(0.0, min(1.0, confidence))
    
    def _update_history(
        self,
        decision: BrainDecision,
        context: DecisionContext
    ) -> None:
        """
        Update decision and conversation history
        
        Args:
            decision: Brain decision
            context: Decision context
        """
        # Add to decision history
        self.decision_history.append(decision)
        
        # Keep history bounded
        max_history = 100
        if len(self.decision_history) > max_history:
            self.decision_history = self.decision_history[-max_history:]
        
        # Add to conversation history (for social decisions)
        if context.decision_type == DecisionType.SOCIAL:
            self.conversation_history.append({
                "situation": context.situation,
                "response": decision.decision_text,
                "timestamp": time.time()
            })
            
            # Keep conversation history bounded
            if len(self.conversation_history) > self.config.max_conversation_history:
                self.conversation_history = self.conversation_history[-self.config.max_conversation_history:]
    
    def _update_metrics(self, decision: BrainDecision) -> None:
        """
        Update brain metrics
        
        Args:
            decision: Brain decision
        """
        self.metrics["total_decisions"] += 1
        
        # Update by type
        dtype = decision.decision_type.value
        self.metrics["decisions_by_type"][dtype] = \
            self.metrics["decisions_by_type"].get(dtype, 0) + 1
        
        # Update by tier
        tier = decision.tier_used.value
        self.metrics["decisions_by_tier"][tier] = \
            self.metrics["decisions_by_tier"].get(tier, 0) + 1
        
        # Update average response time
        total = self.metrics["total_decisions"]
        old_avg = self.metrics["avg_response_time"]
        self.metrics["avg_response_time"] = (
            (old_avg * (total - 1) + decision.time_seconds) / total
        )
    
    def get_recent_decisions(self, n: int = 10) -> List[BrainDecision]:
        """
        Get recent decisions
        
        Args:
            n: Number of decisions to return
            
        Returns:
            List of recent decisions
        """
        return self.decision_history[-n:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get brain metrics
        
        Returns:
            Metrics dictionary
        """
        return self.metrics.copy()
    
    def update_mood(self, new_mood: str) -> None:
        """
        Update character's current mood
        
        Args:
            new_mood: New mood state
        """
        self.current_mood = new_mood
        logger.debug(f"{self.name} mood changed to: {new_mood}")
    
    def update_stress(self, stress_delta: float) -> None:
        """
        Update character's stress level
        
        Args:
            stress_delta: Change in stress (-1 to +1)
        """
        self.stress_level = max(0.0, min(1.0, self.stress_level + stress_delta))
        logger.debug(f"{self.name} stress: {self.stress_level:.2f}")


class BrainManager:
    """
    Manages multiple character brains
    
    Coordinates LLM engine usage across multiple characters,
    handles batching, and tracks overall system performance.
    """
    
    def __init__(self, llm_engine: LocalLLMEngine):
        """
        Initialize brain manager
        
        Args:
            llm_engine: Local LLM engine instance
        """
        self.llm_engine = llm_engine
        self.brains: Dict[str, CharacterBrain] = {}
        
        logger.info("BrainManager initialized")
    
    def register_brain(
        self,
        character_id: str,
        character_data: Dict[str, Any],
        config: Optional[BrainConfig] = None
    ) -> CharacterBrain:
        """
        Register a new character brain
        
        Args:
            character_id: Unique character identifier
            character_data: Character profile
            config: Brain configuration
            
        Returns:
            Character brain instance
        """
        brain = CharacterBrain(
            character_id=character_id,
            character_data=character_data,
            llm_engine=self.llm_engine,
            config=config
        )
        
        self.brains[character_id] = brain
        
        logger.info(f"Registered brain: {brain.name} ({character_id})")
        
        return brain
    
    def get_brain(self, character_id: str) -> Optional[CharacterBrain]:
        """
        Get brain for a character
        
        Args:
            character_id: Character identifier
            
        Returns:
            Character brain or None
        """
        return self.brains.get(character_id)
    
    async def make_decisions(
        self,
        decisions: List[Tuple[str, DecisionContext]]
    ) -> List[BrainDecision]:
        """
        Make multiple decisions (potentially batched)
        
        Args:
            decisions: List of (character_id, context) tuples
            
        Returns:
            List of brain decisions
        """
        tasks = []
        
        for character_id, context in decisions:
            brain = self.get_brain(character_id)
            if brain:
                task = brain.make_decision(context)
                tasks.append(task)
            else:
                logger.warning(f"No brain found for character: {character_id}")
        
        # Run all decisions concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        decisions = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Decision failed: {result}")
            else:
                decisions.append(result)
        
        return decisions
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get metrics for all brains
        
        Returns:
            Combined metrics dictionary
        """
        all_metrics = {
            "total_brains": len(self.brains),
            "brains": {}
        }
        
        for char_id, brain in self.brains.items():
            all_metrics["brains"][char_id] = {
                "name": brain.name,
                "metrics": brain.get_metrics()
            }
        
        return all_metrics


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    async def test_character_brain():
        """Test character brain system"""
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create LLM engine
        engine = LocalLLMEngine(
            models_dir="models",
            vram_budget_mb=5500
        )
        engine.register_default_models()
        await engine.start()
        
        # Create brain manager
        manager = BrainManager(engine)
        
        print("\n" + "="*50)
        print("CHARACTER BRAIN TEST")
        print("="*50)
        
        try:
            # Register test characters
            thorin_data = {
                "name": "Thorin Ironforge",
                "class": "Fighter",
                "background": "Thorin is a gruff dwarf from the mountain clans, dedicated to honor and clan.",
                "personality": {
                    "traits": ["brave", "loyal", "stubborn", "direct"],
                    "values": ["honor", "clan", "duty"],
                    "speaking_style": "gruff and direct, occasional dwarvish phrases"
                }
            }
            
            elara_data = {
                "name": "Elara Moonwhisper",
                "class": "Ranger",
                "background": "Elara is a wise elf ranger who protects the forest.",
                "personality": {
                    "traits": ["calm", "observant", "protective", "wise"],
                    "values": ["nature", "balance", "peace"],
                    "speaking_style": "calm and thoughtful, speaks of nature"
                }
            }
            
            thorin_brain = manager.register_brain("thorin", thorin_data)
            elara_brain = manager.register_brain("elara", elara_data)
            
            # Test 1: Combat decision
            print(f"\n{'-'*50}")
            print("TEST 1: Combat Decision (Thorin)")
            print(f"{'-'*50}")
            
            combat_context = DecisionContext(
                decision_type=DecisionType.COMBAT,
                situation="An orc and a goblin attack! The orc is wounded but strong. The goblin is nimble but weak.",
                options=["Attack the orc", "Attack the goblin", "Defend", "Retreat"],
                urgency=0.8,
                stakes=0.6,
                novelty=0.2,
                recent_events=["Entered dark cave", "Heard growling"],
                active_goals=["Protect the party", "Reach the treasure"]
            )
            
            decision = await thorin_brain.make_decision(combat_context)
            print(f"Decision: {decision.decision_text}")
            print(f"Confidence: {decision.confidence:.2f}")
            print(f"Tier: {decision.tier_used.value}")
            print(f"Time: {decision.time_seconds:.2f}s")
            
            # Test 2: Social interaction
            print(f"\n{'-'*50}")
            print("TEST 2: Social Interaction (Elara)")
            print(f"{'-'*50}")
            
            social_context = DecisionContext(
                decision_type=DecisionType.SOCIAL,
                situation="The innkeeper looks worried and says: 'Strange things have been happening in the woods. People are afraid.'",
                urgency=0.3,
                stakes=0.4,
                novelty=0.5,
                recent_events=["Arrived at village", "Heard rumors"],
                active_goals=["Learn about the threat", "Help the villagers"],
                relationship_context={"innkeeper": "friendly but worried"}
            )
            
            decision = await elara_brain.make_decision(social_context)
            print(f"Decision: {decision.decision_text}")
            print(f"Confidence: {decision.confidence:.2f}")
            print(f"Tier: {decision.tier_used.value}")
            print(f"Time: {decision.time_seconds:.2f}s")
            
            # Test 3: Batch decisions
            print(f"\n{'-'*50}")
            print("TEST 3: Batch Decisions")
            print(f"{'-'*50}")
            
            batch_decisions = [
                ("thorin", DecisionContext(
                    decision_type=DecisionType.EXPLORATION,
                    situation="You see a suspicious door with strange markings.",
                    urgency=0.4,
                    stakes=0.5,
                    novelty=0.6
                )),
                ("elara", DecisionContext(
                    decision_type=DecisionType.EXPLORATION,
                    situation="You notice tracks leading deeper into the forest.",
                    urgency=0.4,
                    stakes=0.5,
                    novelty=0.4
                ))
            ]
            
            results = await manager.make_decisions(batch_decisions)
            
            for decision in results:
                brain = manager.get_brain(decision.character_id)
                print(f"\n{brain.name}: {decision.decision_text}")
                print(f"  Time: {decision.time_seconds:.2f}s, Tier: {decision.tier_used.value}")
            
            # Print metrics
            print(f"\n{'='*50}")
            print("METRICS")
            print(f"{'='*50}")
            
            all_metrics = manager.get_all_metrics()
            print(f"Total brains: {all_metrics['total_brains']}")
            
            for char_id, data in all_metrics['brains'].items():
                print(f"\n{data['name']}:")
                metrics = data['metrics']
                print(f"  Total decisions: {metrics['total_decisions']}")
                print(f"  Avg time: {metrics['avg_response_time']:.2f}s")
                print(f"  By type: {metrics['decisions_by_type']}")
                print(f"  By tier: {metrics['decisions_by_tier']}")
            
        finally:
            # Stop engine
            await engine.stop()
            print("\nTest complete!")
    
    # Run test
    asyncio.run(test_character_brain())
