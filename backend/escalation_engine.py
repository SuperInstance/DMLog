"""
Escalation Engine

Intelligent decision routing system that determines when to use:
- Bots (fast, deterministic)
- Brain (LLM, personality-driven)
- Human (critical decisions, novel situations)

Key Features:
- Confidence-based escalation
- Context-aware routing
- Escalation history tracking
- Learning from outcomes
- Configurable thresholds per character
- Emergency override system
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Import training data collector for Phase 7
try:
    from training_data_collector import TrainingDataCollector
    TRAINING_DATA_AVAILABLE = True
except ImportError:
    TRAINING_DATA_AVAILABLE = False
    logger.warning("TrainingDataCollector not available - training data logging disabled")


class DecisionSource(Enum):
    """Where the decision came from"""
    BOT = "bot"
    BRAIN = "brain"
    HUMAN = "human"
    OVERRIDE = "override"


class EscalationReason(Enum):
    """Why a decision was escalated"""
    LOW_CONFIDENCE = "low_confidence"
    HIGH_STAKES = "high_stakes"
    NOVEL_SITUATION = "novel_situation"
    TIME_CRITICAL = "time_critical"
    CONFLICTING_BOTS = "conflicting_bots"
    SAFETY_CONCERN = "safety_concern"
    CHARACTER_GROWTH = "character_growth"
    PLAYER_REQUEST = "player_request"


@dataclass
class EscalationThresholds:
    """Thresholds for escalation decisions"""
    # Confidence thresholds
    bot_min_confidence: float = 0.7        # Below this, escalate to brain
    brain_min_confidence: float = 0.5      # Below this, escalate to human
    
    # Stakes thresholds
    high_stakes_threshold: float = 0.7     # Above this = high stakes
    critical_stakes_threshold: float = 0.9 # Above this = critical
    
    # Urgency thresholds
    urgent_time_ms: int = 500             # Less than this = urgent
    critical_time_ms: int = 100           # Less than this = critical
    
    # Novelty detection
    novelty_threshold: float = 0.6        # Above this = novel situation
    
    # Safety margins
    hp_critical_threshold: float = 0.2    # Below this HP = critical
    resource_critical_threshold: float = 0.15  # Below this resources = critical
    
    # Learning settings
    confidence_boost_per_success: float = 0.05  # Increase confidence on success
    confidence_penalty_per_failure: float = 0.1  # Decrease on failure


@dataclass
class DecisionContext:
    """Context for a decision that needs routing"""
    # Core context
    character_id: str
    situation_type: str  # "combat", "social", "exploration", "planning"
    situation_description: str
    
    # Importance
    stakes: float = 0.5              # 0=trivial, 1=life-or-death
    urgency_ms: Optional[int] = None # Time available for decision
    
    # State
    character_hp_ratio: float = 1.0
    available_resources: Dict[str, int] = field(default_factory=dict)
    
    # History
    similar_decisions_count: int = 0  # How many times seen similar
    recent_failures: int = 0          # Recent failed decisions
    
    # Metadata
    timestamp: float = field(default_factory=time.time)


@dataclass
class EscalationDecision:
    """Result of escalation routing"""
    source: DecisionSource
    reason: Optional[EscalationReason] = None
    confidence_required: float = 0.0
    time_budget_ms: Optional[int] = None
    allow_fallback: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionResult:
    """Result of a routed decision"""
    decision_id: str
    source: DecisionSource
    action: str
    confidence: float
    time_taken_ms: float
    escalated_from: Optional[DecisionSource] = None
    escalation_reason: Optional[EscalationReason] = None
    success: Optional[bool] = None  # Set after outcome known
    metadata: Dict[str, Any] = field(default_factory=dict)


class EscalationEngine:
    """
    Escalation engine for intelligent decision routing
    
    Routes decisions through the optimal path:
    1. Try bot if appropriate
    2. Escalate to brain if bot uncertain
    3. Escalate to human if brain uncertain or critical
    4. Learn from outcomes to improve routing
    """
    
    def __init__(self, enable_training_data: bool = True):
        """Initialize escalation engine"""
        # Character-specific thresholds
        self.thresholds: Dict[str, EscalationThresholds] = {}
        
        # Decision history
        self.decision_history: List[DecisionResult] = []
        self.decisions_by_character: Dict[str, List[DecisionResult]] = {}
        
        # Pattern recognition
        self.situation_patterns: Dict[str, List[str]] = {}  # situation_type -> patterns
        self.novel_situations: List[str] = []
        
        # Statistics
        self.stats = {
            "total_decisions": 0,
            "bot_decisions": 0,
            "brain_decisions": 0,
            "human_decisions": 0,
            "escalations": 0,
            "escalation_rate": 0.0,
            "avg_confidence": 0.0
        }
        
        # Training data collector (Phase 7)
        self.training_data_collector = None
        if enable_training_data and TRAINING_DATA_AVAILABLE:
            try:
                self.training_data_collector = TrainingDataCollector()
                logger.info("Training data collection enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize training data collector: {e}")
        
        logger.info("EscalationEngine initialized")
    
    def get_thresholds(self, character_id: str) -> EscalationThresholds:
        """Get thresholds for a character, creating defaults if needed"""
        if character_id not in self.thresholds:
            self.thresholds[character_id] = EscalationThresholds()
        return self.thresholds[character_id]
    
    def set_thresholds(
        self,
        character_id: str,
        thresholds: EscalationThresholds
    ) -> None:
        """Set custom thresholds for a character"""
        self.thresholds[character_id] = thresholds
        logger.info(f"Updated thresholds for {character_id}")
    
    def route_decision(
        self,
        context: DecisionContext
    ) -> EscalationDecision:
        """
        Route a decision to the appropriate source
        
        Args:
            context: Decision context
            
        Returns:
            EscalationDecision with routing information
        """
        start_time = time.time()
        
        character_id = context.character_id
        thresholds = self.get_thresholds(character_id)
        
        # Check for critical overrides first
        critical_override = self._check_critical_override(context, thresholds)
        if critical_override:
            return critical_override
        
        # Check if situation is novel
        is_novel = self._is_novel_situation(context, thresholds)
        
        # Check stakes level
        is_high_stakes = context.stakes >= thresholds.high_stakes_threshold
        is_critical_stakes = context.stakes >= thresholds.critical_stakes_threshold
        
        # Check urgency
        is_urgent = (context.urgency_ms is not None and 
                    context.urgency_ms <= thresholds.urgent_time_ms)
        is_time_critical = (context.urgency_ms is not None and
                           context.urgency_ms <= thresholds.critical_time_ms)
        
        # Determine routing
        decision = None
        
        # Critical situations → Human
        if is_critical_stakes or is_time_critical:
            decision = EscalationDecision(
                source=DecisionSource.HUMAN,
                reason=EscalationReason.HIGH_STAKES if is_critical_stakes else EscalationReason.TIME_CRITICAL,
                confidence_required=0.9,
                time_budget_ms=context.urgency_ms,
                allow_fallback=True
            )
        
        # Novel situations with high stakes → Brain (or Human if very high)
        elif is_novel and is_high_stakes:
            decision = EscalationDecision(
                source=DecisionSource.BRAIN if not is_critical_stakes else DecisionSource.HUMAN,
                reason=EscalationReason.NOVEL_SITUATION,
                confidence_required=thresholds.brain_min_confidence,
                time_budget_ms=context.urgency_ms,
                allow_fallback=True
            )
        
        # Novel situations with low stakes → Brain
        elif is_novel:
            decision = EscalationDecision(
                source=DecisionSource.BRAIN,
                reason=EscalationReason.NOVEL_SITUATION,
                confidence_required=thresholds.brain_min_confidence,
                time_budget_ms=context.urgency_ms,
                allow_fallback=True
            )
        
        # High stakes but familiar → Brain
        elif is_high_stakes:
            decision = EscalationDecision(
                source=DecisionSource.BRAIN,
                reason=EscalationReason.HIGH_STAKES,
                confidence_required=thresholds.brain_min_confidence + 0.1,
                time_budget_ms=context.urgency_ms,
                allow_fallback=True
            )
        
        # Urgent but familiar → Bot (fast response)
        elif is_urgent:
            decision = EscalationDecision(
                source=DecisionSource.BOT,
                reason=None,
                confidence_required=thresholds.bot_min_confidence - 0.1,  # Lower bar for urgent
                time_budget_ms=context.urgency_ms,
                allow_fallback=True
            )
        
        # Routine situation → Bot
        else:
            decision = EscalationDecision(
                source=DecisionSource.BOT,
                reason=None,
                confidence_required=thresholds.bot_min_confidence,
                time_budget_ms=context.urgency_ms,
                allow_fallback=True
            )
        
        # Add metadata
        decision.metadata = {
            "is_novel": is_novel,
            "is_high_stakes": is_high_stakes,
            "is_critical_stakes": is_critical_stakes,
            "is_urgent": is_urgent,
            "is_time_critical": is_time_critical,
            "routing_time_ms": (time.time() - start_time) * 1000
        }
        
        logger.debug(
            f"Routed {character_id} decision to {decision.source.value}: "
            f"stakes={context.stakes:.2f}, novel={is_novel}, urgent={is_urgent}"
        )
        
        return decision
    
    def _check_critical_override(
        self,
        context: DecisionContext,
        thresholds: EscalationThresholds
    ) -> Optional[EscalationDecision]:
        """Check for critical situations that override normal routing"""
        
        # Critical HP → Human
        if context.character_hp_ratio <= thresholds.hp_critical_threshold:
            return EscalationDecision(
                source=DecisionSource.HUMAN,
                reason=EscalationReason.SAFETY_CONCERN,
                confidence_required=0.95,
                time_budget_ms=context.urgency_ms,
                allow_fallback=False,
                metadata={"critical_hp": True}
            )
        
        # Critical resources → Human (for important resources)
        for resource, amount in context.available_resources.items():
            if resource in ["spell_slots", "hp_potions", "resurrection"]:
                if amount <= 1:  # Last of critical resource
                    return EscalationDecision(
                        source=DecisionSource.HUMAN,
                        reason=EscalationReason.SAFETY_CONCERN,
                        confidence_required=0.95,
                        time_budget_ms=context.urgency_ms,
                        allow_fallback=False,
                        metadata={"critical_resource": resource}
                    )
        
        # Recent failures → Brain or Human
        if context.recent_failures >= 3:
            return EscalationDecision(
                source=DecisionSource.BRAIN,
                reason=EscalationReason.LOW_CONFIDENCE,
                confidence_required=0.8,
                time_budget_ms=context.urgency_ms,
                allow_fallback=True,
                metadata={"recent_failures": context.recent_failures}
            )
        
        return None
    
    def _is_novel_situation(
        self,
        context: DecisionContext,
        thresholds: EscalationThresholds
    ) -> bool:
        """Determine if situation is novel (unseen or rare)"""
        
        # Check if we've seen this situation type before
        situation_key = f"{context.character_id}:{context.situation_type}"
        
        if situation_key not in self.situation_patterns:
            self.situation_patterns[situation_key] = []
        
        patterns = self.situation_patterns[situation_key]
        
        # If we haven't seen many similar situations, it's novel
        if len(patterns) < 5:
            return True
        
        # Check if description is similar to known patterns
        # Simple keyword matching for now
        description_lower = context.situation_description.lower()
        description_words = set(description_lower.split())
        
        max_similarity = 0.0
        for pattern in patterns:
            pattern_words = set(pattern.lower().split())
            if not pattern_words:
                continue
            
            common_words = description_words & pattern_words
            similarity = len(common_words) / len(pattern_words)
            max_similarity = max(max_similarity, similarity)
        
        # If max similarity is low, situation is novel
        is_novel = max_similarity < (1.0 - thresholds.novelty_threshold)
        
        # Store pattern if novel
        if is_novel or len(patterns) < 20:
            patterns.append(context.situation_description[:100])  # Store first 100 chars
        
        return is_novel
    
    def should_escalate(
        self,
        result: DecisionResult,
        context: DecisionContext
    ) -> Tuple[bool, Optional[EscalationReason]]:
        """
        Determine if a decision should be escalated to next level
        
        Args:
            result: The decision that was made
            context: Original decision context
            
        Returns:
            (should_escalate, reason)
        """
        thresholds = self.get_thresholds(context.character_id)
        
        # Already from human, can't escalate further
        if result.source == DecisionSource.HUMAN:
            return False, None
        
        # Check confidence
        if result.source == DecisionSource.BOT:
            if result.confidence < thresholds.bot_min_confidence:
                return True, EscalationReason.LOW_CONFIDENCE
        elif result.source == DecisionSource.BRAIN:
            if result.confidence < thresholds.brain_min_confidence:
                return True, EscalationReason.LOW_CONFIDENCE
        
        # Check if stakes warrant escalation
        if context.stakes >= thresholds.critical_stakes_threshold:
            if result.source == DecisionSource.BOT:
                return True, EscalationReason.HIGH_STAKES
        
        return False, None
    
    def record_decision(
        self,
        result: DecisionResult
    ) -> None:
        """
        Record a decision for history and learning
        
        Args:
            result: Decision result to record
        """
        # Add to history
        self.decision_history.append(result)
        
        # Add to character history
        char_id = result.metadata.get("character_id")
        if char_id:
            if char_id not in self.decisions_by_character:
                self.decisions_by_character[char_id] = []
            self.decisions_by_character[char_id].append(result)
        
        # Update stats
        self.stats["total_decisions"] += 1
        
        if result.source == DecisionSource.BOT:
            self.stats["bot_decisions"] += 1
        elif result.source == DecisionSource.BRAIN:
            self.stats["brain_decisions"] += 1
        elif result.source == DecisionSource.HUMAN:
            self.stats["human_decisions"] += 1
        
        if result.escalated_from is not None:
            self.stats["escalations"] += 1
        
        # Update rates
        if self.stats["total_decisions"] > 0:
            self.stats["escalation_rate"] = (
                self.stats["escalations"] / self.stats["total_decisions"]
            )
        
        # Log to training data collector (Phase 7)
        if self.training_data_collector and char_id:
            try:
                # Extract context from metadata
                situation_context = result.metadata.get("situation_context", {})
                
                # Build decision data
                decision_data = {
                    "decision_type": result.metadata.get("decision_type", "unknown"),
                    "action": result.action,
                    "confidence": result.confidence,
                    "source": result.source.value,
                    "escalated_from": result.escalated_from.value if result.escalated_from else None,
                    "escalation_reason": result.escalation_reason.value if result.escalation_reason else None,
                    "time_taken_ms": result.time_taken_ms
                }
                
                # Log the decision
                training_decision_id = self.training_data_collector.log_decision(
                    character_id=char_id,
                    situation_context=situation_context,
                    decision=decision_data
                )
                
                # Store training decision ID in result metadata for later outcome tracking
                if training_decision_id:
                    result.metadata["training_decision_id"] = training_decision_id
                
            except Exception as e:
                logger.warning(f"Failed to log training data: {e}")
        
        logger.debug(f"Recorded decision from {result.source.value}")
    
    def record_outcome(
        self,
        decision_id: str,
        success: bool,
        outcome_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record the outcome of a decision for learning
        
        Args:
            decision_id: ID of the decision
            success: Whether the decision was successful
            outcome_details: Optional detailed outcome information
        """
        # Find the decision
        for result in self.decision_history:
            if result.decision_id == decision_id:
                result.success = success
                
                # Update character thresholds based on outcome
                char_id = result.metadata.get("character_id")
                if char_id:
                    self._update_thresholds(char_id, result, success)
                
                # Log outcome to training data collector (Phase 7)
                if self.training_data_collector:
                    training_decision_id = result.metadata.get("training_decision_id")
                    if training_decision_id:
                        try:
                            outcome_data = outcome_details or {}
                            outcome_data["success"] = success
                            self.training_data_collector.update_outcome(
                                decision_id=training_decision_id,
                                outcome=outcome_data,
                                success=success
                            )
                        except Exception as e:
                            logger.warning(f"Failed to log outcome to training data: {e}")
                
                logger.debug(
                    f"Recorded outcome for {decision_id}: "
                    f"{'success' if success else 'failure'}"
                )
                return
        
        logger.warning(f"Decision {decision_id} not found for outcome recording")
    
    def _update_thresholds(
        self,
        character_id: str,
        result: DecisionResult,
        success: bool
    ) -> None:
        """Update character thresholds based on decision outcome"""
        thresholds = self.get_thresholds(character_id)
        
        # Adjust confidence thresholds based on success
        if result.source == DecisionSource.BOT:
            if success:
                # Bot succeeded, can lower threshold slightly (trust bots more)
                thresholds.bot_min_confidence = max(
                    0.5,
                    thresholds.bot_min_confidence - thresholds.confidence_boost_per_success
                )
            else:
                # Bot failed, raise threshold (trust bots less)
                thresholds.bot_min_confidence = min(
                    0.9,
                    thresholds.bot_min_confidence + thresholds.confidence_penalty_per_failure
                )
        
        elif result.source == DecisionSource.BRAIN:
            if success:
                # Brain succeeded, can lower threshold slightly
                thresholds.brain_min_confidence = max(
                    0.3,
                    thresholds.brain_min_confidence - thresholds.confidence_boost_per_success
                )
            else:
                # Brain failed, raise threshold
                thresholds.brain_min_confidence = min(
                    0.8,
                    thresholds.brain_min_confidence + thresholds.confidence_penalty_per_failure
                )
    
    def get_character_stats(
        self,
        character_id: str
    ) -> Dict[str, Any]:
        """Get decision statistics for a character"""
        if character_id not in self.decisions_by_character:
            return {"total_decisions": 0}
        
        decisions = self.decisions_by_character[character_id]
        
        bot_decisions = sum(1 for d in decisions if d.source == DecisionSource.BOT)
        brain_decisions = sum(1 for d in decisions if d.source == DecisionSource.BRAIN)
        human_decisions = sum(1 for d in decisions if d.source == DecisionSource.HUMAN)
        escalations = sum(1 for d in decisions if d.escalated_from is not None)
        
        successes = sum(1 for d in decisions if d.success is True)
        failures = sum(1 for d in decisions if d.success is False)
        
        avg_confidence = sum(d.confidence for d in decisions) / len(decisions)
        avg_time = sum(d.time_taken_ms for d in decisions) / len(decisions)
        
        return {
            "total_decisions": len(decisions),
            "bot_decisions": bot_decisions,
            "brain_decisions": brain_decisions,
            "human_decisions": human_decisions,
            "escalations": escalations,
            "escalation_rate": escalations / len(decisions) if decisions else 0,
            "successes": successes,
            "failures": failures,
            "success_rate": successes / (successes + failures) if (successes + failures) > 0 else 0,
            "avg_confidence": avg_confidence,
            "avg_time_ms": avg_time
        }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global decision statistics"""
        return self.stats.copy()


# Test code
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("Testing Escalation Engine...\n")
    
    # Create engine
    engine = EscalationEngine()
    
    # Test 1: Routine combat situation
    print("=== Test 1: Routine Combat (Low Stakes) ===")
    context1 = DecisionContext(
        character_id="warrior1",
        situation_type="combat",
        situation_description="Goblin attacks with sword",
        stakes=0.3,
        urgency_ms=1000,
        character_hp_ratio=0.8,
        similar_decisions_count=10
    )
    
    decision1 = engine.route_decision(context1)
    print(f"Route to: {decision1.source.value}")
    print(f"Reason: {decision1.reason}")
    print(f"Confidence required: {decision1.confidence_required}")
    print(f"Expected: BOT (routine, low stakes)")
    print()
    
    # Test 2: High stakes combat
    print("=== Test 2: High Stakes Combat ===")
    context2 = DecisionContext(
        character_id="warrior1",
        situation_type="combat",
        situation_description="Dragon breathes fire at party",
        stakes=0.9,
        urgency_ms=500,
        character_hp_ratio=0.4,
        similar_decisions_count=2
    )
    
    decision2 = engine.route_decision(context2)
    print(f"Route to: {decision2.source.value}")
    print(f"Reason: {decision2.reason}")
    print(f"Expected: HUMAN or BRAIN (high stakes, novel)")
    print()
    
    # Test 3: Critical HP situation
    print("=== Test 3: Critical HP Override ===")
    context3 = DecisionContext(
        character_id="warrior1",
        situation_type="combat",
        situation_description="Enemy attacks while near death",
        stakes=0.5,
        urgency_ms=1000,
        character_hp_ratio=0.15,  # Critical HP
        similar_decisions_count=5
    )
    
    decision3 = engine.route_decision(context3)
    print(f"Route to: {decision3.source.value}")
    print(f"Reason: {decision3.reason}")
    print(f"Expected: HUMAN (critical HP override)")
    print()
    
    # Test 4: Novel social situation
    print("=== Test 4: Novel Social Situation ===")
    context4 = DecisionContext(
        character_id="bard1",
        situation_type="social",
        situation_description="Queen asks about your political allegiance",
        stakes=0.6,
        urgency_ms=5000,
        character_hp_ratio=1.0,
        similar_decisions_count=0  # Never seen before
    )
    
    decision4 = engine.route_decision(context4)
    print(f"Route to: {decision4.source.value}")
    print(f"Reason: {decision4.reason}")
    print(f"Expected: BRAIN (novel situation)")
    print()
    
    # Test 5: Escalation check
    print("=== Test 5: Escalation Check ===")
    bot_result = DecisionResult(
        decision_id="test_decision",
        source=DecisionSource.BOT,
        action="Attack goblin",
        confidence=0.55,  # Low confidence
        time_taken_ms=8.5
    )
    
    should_escalate, reason = engine.should_escalate(bot_result, context1)
    print(f"Should escalate: {should_escalate}")
    print(f"Reason: {reason}")
    print(f"Expected: True (low confidence)")
    print()
    
    # Test 6: Record and learn
    print("=== Test 6: Learning from Outcomes ===")
    
    # Get initial threshold
    initial_threshold = engine.get_thresholds("warrior1").bot_min_confidence
    print(f"Initial bot threshold: {initial_threshold:.3f}")
    
    # Record successful bot decision
    result = DecisionResult(
        decision_id="learn1",
        source=DecisionSource.BOT,
        action="Attack",
        confidence=0.75,
        time_taken_ms=8.0,
        metadata={"character_id": "warrior1"}
    )
    engine.record_decision(result)
    engine.record_outcome("learn1", success=True)
    
    new_threshold = engine.get_thresholds("warrior1").bot_min_confidence
    print(f"After success: {new_threshold:.3f}")
    print(f"Expected: Lower (trust bots more)")
    print()
    
    # Test 7: Statistics
    print("=== Test 7: Statistics ===")
    stats = engine.get_character_stats("warrior1")
    print(f"Character stats: {stats}")
    
    global_stats = engine.get_global_stats()
    print(f"Global stats: {global_stats}")
    print()
    
    print("✅ All escalation tests completed!")
