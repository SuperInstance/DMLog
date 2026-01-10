"""
Mechanical Bot Framework

Base framework for scripted character behaviors. Bots handle routine decisions
with deterministic algorithms, escalating to LLM brain when uncertain.

Key Features:
- Parameter-driven behavior (personality without LLM)
- Fast execution (<10ms for most decisions)
- Confidence scoring
- Escalation triggers
- Bot composition (multiple bots per character)
- Performance tracking
"""

import time
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging
import random

logger = logging.getLogger(__name__)


class BotType(Enum):
    """Types of mechanical bots"""
    COMBAT = "combat"
    SOCIAL = "social"
    EXPLORATION = "exploration"
    UTILITY = "utility"
    COORDINATOR = "coordinator"


class BotPriority(Enum):
    """Bot execution priority"""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


@dataclass
class BotParameters:
    """Base parameters for all bots"""
    # Core parameters
    aggression: float = 0.5       # 0=passive, 1=aggressive
    risk_tolerance: float = 0.5   # 0=cautious, 1=reckless
    creativity: float = 0.5       # 0=by-the-book, 1=creative
    cooperation: float = 0.7      # 0=solo, 1=team-player
    
    # Decision making
    escalation_threshold: float = 0.6  # Confidence below this = escalate
    think_time_ms: int = 10           # Base thinking time
    
    # Personality quirks (affect decisions)
    imperfection_rate: float = 0.1    # Rate of sub-optimal choices
    hesitation_rate: float = 0.05     # Rate of delayed decisions
    
    def __post_init__(self):
        """Validate parameters"""
        self._clamp("aggression")
        self._clamp("risk_tolerance")
        self._clamp("creativity")
        self._clamp("cooperation")
        self._clamp("escalation_threshold")
        self._clamp("imperfection_rate")
        self._clamp("hesitation_rate")
    
    def _clamp(self, attr: str, min_val: float = 0.0, max_val: float = 1.0):
        """Clamp attribute to range"""
        value = getattr(self, attr)
        setattr(self, attr, max(min_val, min(max_val, value)))


@dataclass
class BotPerception:
    """Perception data for bot decisions"""
    # Visual
    visible_entities: List[Dict[str, Any]] = field(default_factory=list)
    visible_terrain: List[str] = field(default_factory=list)
    
    # Audio
    audible_sounds: List[str] = field(default_factory=list)
    
    # Status
    self_status: Dict[str, Any] = field(default_factory=dict)
    allies_status: List[Dict[str, Any]] = field(default_factory=list)
    enemies_status: List[Dict[str, Any]] = field(default_factory=list)
    
    # Context
    current_location: str = ""
    time_of_day: str = ""
    weather: str = ""
    
    # Recent changes
    changes_since_last: List[str] = field(default_factory=list)


@dataclass
class BotAction:
    """Action decided by bot"""
    action_type: str
    target: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    reasoning: Optional[str] = None
    priority: BotPriority = BotPriority.NORMAL
    estimated_duration_ms: int = 0


@dataclass
class BotDecision:
    """Complete bot decision with metadata"""
    bot_name: str
    bot_type: BotType
    action: BotAction
    confidence: float
    should_escalate: bool = False
    escalation_reason: Optional[str] = None
    execution_time_ms: float = 0.0


class MechanicalBot(ABC):
    """
    Base class for all mechanical bots
    
    Bots use deterministic algorithms and parameters to make fast decisions.
    When uncertain, they escalate to the character's LLM brain.
    """
    
    def __init__(
        self,
        name: str,
        bot_type: BotType,
        parameters: BotParameters
    ):
        """
        Initialize mechanical bot
        
        Args:
            name: Bot name (e.g., "combat_targeting")
            bot_type: Type of bot
            parameters: Bot parameters
        """
        self.name = name
        self.bot_type = bot_type
        self.parameters = parameters
        
        # Metrics
        self.metrics = {
            "total_decisions": 0,
            "escalations": 0,
            "avg_confidence": 0.0,
            "avg_execution_time_ms": 0.0
        }
        
        logger.debug(f"Bot initialized: {name} ({bot_type.value})")
    
    @abstractmethod
    def perceive(self, perception: BotPerception) -> Dict[str, Any]:
        """
        Process perception data (extract relevant info)
        
        Args:
            perception: Raw perception data
            
        Returns:
            Processed perception specific to this bot
        """
        pass
    
    @abstractmethod
    def decide(self, processed_perception: Dict[str, Any]) -> BotAction:
        """
        Make a decision based on processed perception
        
        Args:
            processed_perception: Processed perception data
            
        Returns:
            Bot action
        """
        pass
    
    def execute(self, perception: BotPerception) -> BotDecision:
        """
        Execute full bot decision cycle
        
        Args:
            perception: Perception data
            
        Returns:
            Bot decision with metadata
        """
        start_time = time.time()
        
        # Simulate thinking time
        if self.parameters.think_time_ms > 0:
            time.sleep(self.parameters.think_time_ms / 1000.0)
        
        try:
            # Perceive
            processed = self.perceive(perception)
            
            # Decide
            action = self.decide(processed)
            
            # Add imperfection (sometimes choose sub-optimal)
            if random.random() < self.parameters.imperfection_rate:
                action = self._add_imperfection(action, processed)
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Check if should escalate
            should_escalate = action.confidence < self.parameters.escalation_threshold
            escalation_reason = None
            
            if should_escalate:
                escalation_reason = self._get_escalation_reason(action, processed)
            
            # Update metrics
            self._update_metrics(action.confidence, execution_time_ms, should_escalate)
            
            # Build decision
            decision = BotDecision(
                bot_name=self.name,
                bot_type=self.bot_type,
                action=action,
                confidence=action.confidence,
                should_escalate=should_escalate,
                escalation_reason=escalation_reason,
                execution_time_ms=execution_time_ms
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"Bot {self.name} execution failed: {e}")
            
            # Return fallback decision
            return BotDecision(
                bot_name=self.name,
                bot_type=self.bot_type,
                action=BotAction(
                    action_type="wait",
                    confidence=0.0,
                    reasoning=f"Error: {e}"
                ),
                confidence=0.0,
                should_escalate=True,
                escalation_reason="Execution error",
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def _add_imperfection(
        self,
        action: BotAction,
        processed_perception: Dict[str, Any]
    ) -> BotAction:
        """
        Add human-like imperfection to action
        
        Args:
            action: Original action
            processed_perception: Perception data
            
        Returns:
            Modified action (sometimes sub-optimal but interesting)
        """
        # By default, just lower confidence slightly
        action.confidence *= 0.9
        action.reasoning = f"{action.reasoning or ''} (acting on instinct)"
        return action
    
    def _get_escalation_reason(
        self,
        action: BotAction,
        processed_perception: Dict[str, Any]
    ) -> str:
        """
        Get reason for escalation
        
        Args:
            action: Action decided
            processed_perception: Perception data
            
        Returns:
            Escalation reason
        """
        if action.confidence < 0.3:
            return "Very low confidence"
        elif action.confidence < 0.5:
            return "Low confidence, multiple good options"
        else:
            return "Below escalation threshold"
    
    def _update_metrics(
        self,
        confidence: float,
        execution_time_ms: float,
        escalated: bool
    ) -> None:
        """Update bot metrics"""
        total = self.metrics["total_decisions"]
        
        # Update counts
        self.metrics["total_decisions"] += 1
        if escalated:
            self.metrics["escalations"] += 1
        
        # Update averages
        self.metrics["avg_confidence"] = (
            (self.metrics["avg_confidence"] * total + confidence) / (total + 1)
        )
        self.metrics["avg_execution_time_ms"] = (
            (self.metrics["avg_execution_time_ms"] * total + execution_time_ms) / (total + 1)
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get bot metrics"""
        metrics = self.metrics.copy()
        if metrics["total_decisions"] > 0:
            metrics["escalation_rate"] = metrics["escalations"] / metrics["total_decisions"]
        else:
            metrics["escalation_rate"] = 0.0
        return metrics


class BotRegistry:
    """
    Registry for available bots
    
    Manages bot templates and instantiation.
    """
    
    def __init__(self):
        """Initialize bot registry"""
        self._bot_classes: Dict[str, type] = {}
        logger.info("BotRegistry initialized")
    
    def register(self, bot_class: type, name: Optional[str] = None) -> None:
        """
        Register a bot class
        
        Args:
            bot_class: Bot class to register
            name: Optional name (defaults to class name)
        """
        bot_name = name or bot_class.__name__
        self._bot_classes[bot_name] = bot_class
        logger.info(f"Registered bot: {bot_name}")
    
    def create(
        self,
        bot_name: str,
        parameters: BotParameters,
        **kwargs
    ) -> MechanicalBot:
        """
        Create a bot instance
        
        Args:
            bot_name: Name of bot class to create
            parameters: Bot parameters
            **kwargs: Additional bot-specific arguments
            
        Returns:
            Bot instance
        """
        if bot_name not in self._bot_classes:
            raise ValueError(f"Bot not registered: {bot_name}")
        
        bot_class = self._bot_classes[bot_name]
        return bot_class(parameters=parameters, **kwargs)
    
    def list_available(self) -> List[str]:
        """
        List available bot types
        
        Returns:
            List of bot names
        """
        return list(self._bot_classes.keys())


class BotSwarm:
    """
    Swarm of bots for a single character
    
    Coordinates multiple bots working together.
    """
    
    def __init__(self, character_id: str):
        """
        Initialize bot swarm
        
        Args:
            character_id: Character these bots control
        """
        self.character_id = character_id
        self.bots: Dict[str, MechanicalBot] = {}
        self.active_bots: List[str] = []
        
        logger.info(f"BotSwarm initialized for: {character_id}")
    
    def add_bot(self, bot: MechanicalBot) -> None:
        """
        Add a bot to the swarm
        
        Args:
            bot: Bot to add
        """
        self.bots[bot.name] = bot
        self.active_bots.append(bot.name)
        logger.debug(f"Bot added to swarm: {bot.name}")
    
    def remove_bot(self, bot_name: str) -> None:
        """
        Remove a bot from swarm
        
        Args:
            bot_name: Name of bot to remove
        """
        if bot_name in self.bots:
            del self.bots[bot_name]
            self.active_bots.remove(bot_name)
            logger.debug(f"Bot removed from swarm: {bot_name}")
    
    def execute_all(
        self,
        perception: BotPerception,
        bot_filter: Optional[Callable[[MechanicalBot], bool]] = None
    ) -> List[BotDecision]:
        """
        Execute all active bots
        
        Args:
            perception: Perception data
            bot_filter: Optional filter function for bots
            
        Returns:
            List of bot decisions
        """
        decisions = []
        
        for bot_name in self.active_bots:
            bot = self.bots[bot_name]
            
            # Apply filter if provided
            if bot_filter and not bot_filter(bot):
                continue
            
            # Execute bot
            decision = bot.execute(perception)
            decisions.append(decision)
        
        return decisions
    
    def execute_by_type(
        self,
        perception: BotPerception,
        bot_type: BotType
    ) -> List[BotDecision]:
        """
        Execute only bots of a specific type
        
        Args:
            perception: Perception data
            bot_type: Type of bots to execute
            
        Returns:
            List of bot decisions
        """
        return self.execute_all(
            perception,
            bot_filter=lambda b: b.bot_type == bot_type
        )
    
    def get_best_decision(
        self,
        decisions: List[BotDecision],
        prefer_no_escalation: bool = True
    ) -> Optional[BotDecision]:
        """
        Get best decision from list
        
        Args:
            decisions: List of decisions
            prefer_no_escalation: Prefer non-escalating decisions
            
        Returns:
            Best decision or None
        """
        if not decisions:
            return None
        
        # Filter and sort
        if prefer_no_escalation:
            # Prefer decisions that don't escalate
            no_escalation = [d for d in decisions if not d.should_escalate]
            if no_escalation:
                decisions = no_escalation
        
        # Sort by confidence
        decisions.sort(key=lambda d: d.confidence, reverse=True)
        
        return decisions[0]
    
    def get_swarm_metrics(self) -> Dict[str, Any]:
        """
        Get metrics for entire swarm
        
        Returns:
            Swarm metrics
        """
        swarm_metrics = {
            "character_id": self.character_id,
            "total_bots": len(self.bots),
            "active_bots": len(self.active_bots),
            "bots": {}
        }
        
        for bot_name, bot in self.bots.items():
            swarm_metrics["bots"][bot_name] = bot.get_metrics()
        
        return swarm_metrics


# Example bot implementations

class WaitBot(MechanicalBot):
    """Simple bot that just waits/observes"""
    
    def __init__(self, parameters: BotParameters):
        super().__init__("wait_bot", BotType.UTILITY, parameters)
    
    def perceive(self, perception: BotPerception) -> Dict[str, Any]:
        return {"action": "wait"}
    
    def decide(self, processed_perception: Dict[str, Any]) -> BotAction:
        return BotAction(
            action_type="wait",
            confidence=1.0,
            reasoning="Observing situation"
        )


class SimpleTargetingBot(MechanicalBot):
    """Simple combat targeting bot"""
    
    def __init__(self, parameters: BotParameters):
        super().__init__("simple_targeting", BotType.COMBAT, parameters)
    
    def perceive(self, perception: BotPerception) -> Dict[str, Any]:
        """Extract enemy info"""
        enemies = perception.enemies_status
        
        processed = {
            "enemies": enemies,
            "num_enemies": len(enemies),
            "threats": []
        }
        
        # Calculate threat scores
        for enemy in enemies:
            threat = self._calculate_threat(enemy)
            processed["threats"].append({
                "enemy": enemy,
                "threat_score": threat
            })
        
        # Sort by threat
        processed["threats"].sort(key=lambda x: x["threat_score"], reverse=True)
        
        return processed
    
    def decide(self, processed_perception: Dict[str, Any]) -> BotAction:
        """Select target"""
        threats = processed_perception["threats"]
        
        if not threats:
            return BotAction(
                action_type="wait",
                confidence=1.0,
                reasoning="No enemies detected"
            )
        
        # Target highest threat (with some randomness for imperfection)
        if random.random() < self.parameters.aggression:
            # More aggressive = target highest threat
            target = threats[0]
        else:
            # Less aggressive = might target weaker enemies
            target = random.choice(threats[:min(3, len(threats))])
        
        confidence = 0.8 if len(threats) == 1 else 0.6
        
        return BotAction(
            action_type="attack",
            target=target["enemy"].get("id"),
            parameters={"threat_score": target["threat_score"]},
            confidence=confidence,
            reasoning=f"Targeting enemy (threat={target['threat_score']:.2f})"
        )
    
    def _calculate_threat(self, enemy: Dict[str, Any]) -> float:
        """Calculate threat score for enemy"""
        threat = 0.5
        
        # Higher HP = higher threat
        hp_ratio = enemy.get("hp", 50) / enemy.get("max_hp", 100)
        threat += hp_ratio * 0.3
        
        # Closer = higher threat
        distance = enemy.get("distance", 30)
        if distance < 10:
            threat += 0.3
        elif distance < 20:
            threat += 0.2
        
        # Higher level = higher threat
        level = enemy.get("level", 1)
        threat += min(level / 20, 0.3)
        
        return min(threat, 1.0)


# Example usage and testing
if __name__ == "__main__":
    
    def test_mechanical_bots():
        """Test mechanical bot system"""
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        print("\n" + "="*50)
        print("MECHANICAL BOT FRAMEWORK TEST")
        print("="*50)
        
        # Create bot registry
        registry = BotRegistry()
        registry.register(WaitBot)
        registry.register(SimpleTargetingBot)
        
        print(f"\nRegistered bots: {registry.list_available()}")
        
        # Create bot swarm for character
        swarm = BotSwarm("thorin")
        
        # Add bots
        params = BotParameters(
            aggression=0.7,
            risk_tolerance=0.6,
            escalation_threshold=0.5
        )
        
        targeting_bot = SimpleTargetingBot(parameters=params)
        wait_bot = WaitBot(parameters=params)
        
        swarm.add_bot(targeting_bot)
        swarm.add_bot(wait_bot)
        
        print(f"Swarm bots: {list(swarm.bots.keys())}")
        
        # Test with perception
        print(f"\n{'-'*50}")
        print("TEST: Combat Situation")
        print(f"{'-'*50}")
        
        perception = BotPerception(
            enemies_status=[
                {"id": "orc_1", "hp": 30, "max_hp": 50, "distance": 15, "level": 3},
                {"id": "goblin_1", "hp": 10, "max_hp": 15, "distance": 10, "level": 1},
                {"id": "orc_2", "hp": 45, "max_hp": 50, "distance": 25, "level": 3}
            ],
            self_status={"hp": 40, "max_hp": 50}
        )
        
        # Execute combat bots
        decisions = swarm.execute_by_type(perception, BotType.COMBAT)
        
        print(f"\nBot decisions:")
        for decision in decisions:
            print(f"  {decision.bot_name}:")
            print(f"    Action: {decision.action.action_type}")
            if decision.action.target:
                print(f"    Target: {decision.action.target}")
            print(f"    Confidence: {decision.confidence:.2f}")
            print(f"    Escalate: {decision.should_escalate}")
            if decision.escalation_reason:
                print(f"    Reason: {decision.escalation_reason}")
            print(f"    Time: {decision.execution_time_ms:.2f}ms")
        
        # Get best decision
        best = swarm.get_best_decision(decisions)
        print(f"\nBest decision: {best.bot_name} - {best.action.action_type}")
        print(f"  Reasoning: {best.action.reasoning}")
        
        # Run multiple times to test consistency and metrics
        print(f"\n{'-'*50}")
        print("TEST: Multiple Executions")
        print(f"{'-'*50}")
        
        for i in range(10):
            decisions = swarm.execute_by_type(perception, BotType.COMBAT)
        
        # Print metrics
        print("\nSwarm Metrics:")
        metrics = swarm.get_swarm_metrics()
        print(f"Total bots: {metrics['total_bots']}")
        
        for bot_name, bot_metrics in metrics['bots'].items():
            if bot_metrics['total_decisions'] > 0:
                print(f"\n{bot_name}:")
                print(f"  Decisions: {bot_metrics['total_decisions']}")
                print(f"  Avg confidence: {bot_metrics['avg_confidence']:.2f}")
                print(f"  Avg time: {bot_metrics['avg_execution_time_ms']:.2f}ms")
                print(f"  Escalation rate: {bot_metrics['escalation_rate']:.2%}")
        
        print("\nTest complete!")
    
    # Run test
    test_mechanical_bots()
