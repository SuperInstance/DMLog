"""
AI Society D&D - Digital Twin Learning System
==============================================
Creates AI doubles of human players by learning from their behavior.

Captures:
- Explicit decisions (actions, dialogue, strategies)
- Implicit behavior (timing, hesitation, focus patterns)
- Contextual patterns (when they act cautiously vs boldly)
- Social patterns (who they trust, help, avoid)

Learns:
- Decision-making patterns
- Risk tolerance
- Personality traits
- Play style
- Strategic preferences

Applications:
- Fill in for absent players
- Practice encounters with AI versions
- Analyze player behavior for DM prep
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import numpy as np
from collections import defaultdict, Counter
import statistics


# ============================================================================
# BEHAVIOR TRACKING
# ============================================================================

class BehaviorType(Enum):
    """Types of behaviors to track"""
    EXPLICIT_DECISION = "explicit_decision"    # Direct actions taken
    TIMING_PATTERN = "timing_pattern"          # Speed of decisions
    FOCUS_PATTERN = "focus_pattern"            # What they pay attention to
    RISK_BEHAVIOR = "risk_behavior"            # Risk-taking patterns
    SOCIAL_BEHAVIOR = "social_behavior"        # Interaction patterns
    STRATEGIC_CHOICE = "strategic_choice"      # Long-term planning


@dataclass
class BehaviorObservation:
    """Single observed behavior"""
    observation_id: str
    player_id: str
    behavior_type: BehaviorType
    timestamp: datetime
    
    # Context
    game_state: Dict[str, Any] = field(default_factory=dict)
    situation_description: str = ""
    
    # Action taken
    action_taken: str = ""
    alternatives_considered: List[str] = field(default_factory=list)
    
    # Outcome
    success: bool = True
    consequences: List[str] = field(default_factory=list)
    
    # Timing
    decision_time_seconds: float = 0.0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BehaviorPattern:
    """Identified pattern in behavior"""
    pattern_id: str
    pattern_type: str
    description: str
    
    # Evidence
    supporting_observations: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    # Characteristics
    triggers: List[str] = field(default_factory=list)  # When this pattern appears
    typical_actions: List[str] = field(default_factory=list)
    
    # Statistics
    frequency: int = 0
    success_rate: float = 0.0


# ============================================================================
# BEHAVIOR CAPTURE SYSTEM
# ============================================================================

class BehaviorCapture:
    """
    Captures and logs human player behavior.
    Instrumented into the game to record everything.
    """
    
    def __init__(self, player_id: str):
        self.player_id = player_id
        self.observations: List[BehaviorObservation] = []
        
        # Session tracking
        self.current_session_start: Optional[datetime] = None
        self.last_action_time: Optional[datetime] = None
        
        # Real-time tracking
        self.current_focus: Optional[str] = None
        self.screen_time: Dict[str, float] = defaultdict(float)
        self.scroll_events: List[Dict] = []
    
    def start_session(self):
        """Begin tracking session"""
        self.current_session_start = datetime.now()
        self.last_action_time = datetime.now()
    
    def record_decision(
        self,
        situation: str,
        action_taken: str,
        alternatives: List[str] = None,
        game_state: Dict = None
    ) -> BehaviorObservation:
        """Record an explicit decision"""
        
        # Calculate decision time
        now = datetime.now()
        decision_time = 0.0
        if self.last_action_time:
            decision_time = (now - self.last_action_time).total_seconds()
        
        obs = BehaviorObservation(
            observation_id=f"obs_{len(self.observations)}",
            player_id=self.player_id,
            behavior_type=BehaviorType.EXPLICIT_DECISION,
            timestamp=now,
            situation_description=situation,
            action_taken=action_taken,
            alternatives_considered=alternatives or [],
            game_state=game_state or {},
            decision_time_seconds=decision_time
        )
        
        self.observations.append(obs)
        self.last_action_time = now
        
        return obs
    
    def record_screen_view(self, screen_name: str, duration_seconds: float):
        """Record time spent viewing a screen"""
        self.screen_time[screen_name] += duration_seconds
    
    def record_scroll_event(self, element: str, scroll_position: float):
        """Record scroll behavior (what they're reading closely)"""
        self.scroll_events.append({
            "timestamp": datetime.now().isoformat(),
            "element": element,
            "position": scroll_position
        })
    
    def record_hesitation(self, situation: str, hesitation_time: float):
        """Record when player hesitates before acting"""
        obs = BehaviorObservation(
            observation_id=f"obs_{len(self.observations)}",
            player_id=self.player_id,
            behavior_type=BehaviorType.TIMING_PATTERN,
            timestamp=datetime.now(),
            situation_description=situation,
            decision_time_seconds=hesitation_time,
            metadata={"type": "hesitation"}
        )
        self.observations.append(obs)
    
    def record_social_interaction(
        self,
        interaction_type: str,
        target_character: str,
        action: str
    ):
        """Record social behavior"""
        obs = BehaviorObservation(
            observation_id=f"obs_{len(self.observations)}",
            player_id=self.player_id,
            behavior_type=BehaviorType.SOCIAL_BEHAVIOR,
            timestamp=datetime.now(),
            action_taken=action,
            metadata={
                "interaction_type": interaction_type,
                "target": target_character
            }
        )
        self.observations.append(obs)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session"""
        if not self.current_session_start:
            return {}
        
        session_duration = (datetime.now() - self.current_session_start).total_seconds() / 60.0
        
        return {
            "player_id": self.player_id,
            "session_duration_minutes": session_duration,
            "total_decisions": len([o for o in self.observations 
                                   if o.behavior_type == BehaviorType.EXPLICIT_DECISION]),
            "average_decision_time": statistics.mean(
                [o.decision_time_seconds for o in self.observations 
                 if o.decision_time_seconds > 0]
            ) if self.observations else 0.0,
            "screen_time": dict(self.screen_time),
            "most_viewed_screen": max(self.screen_time.items(), key=lambda x: x[1])[0] 
                                  if self.screen_time else None
        }


# ============================================================================
# PATTERN RECOGNITION
# ============================================================================

class BehaviorAnalyzer:
    """
    Analyzes captured behavior to identify patterns.
    """
    
    def __init__(self):
        self.identified_patterns: Dict[str, List[BehaviorPattern]] = defaultdict(list)
    
    def analyze_decision_patterns(
        self,
        observations: List[BehaviorObservation]
    ) -> List[BehaviorPattern]:
        """
        Identify decision-making patterns.
        
        Looks for:
        - Always attacks when outnumbered
        - Always tries diplomacy first
        - Avoids traps/suspicious situations
        - Takes risks when health is high
        """
        patterns = []
        
        # Filter to decisions only
        decisions = [o for o in observations 
                    if o.behavior_type == BehaviorType.EXPLICIT_DECISION]
        
        if len(decisions) < 5:
            return patterns  # Not enough data
        
        # Pattern: Combat preference
        combat_situations = [d for d in decisions if 'combat' in d.situation_description.lower()]
        if combat_situations:
            attack_actions = sum(1 for d in combat_situations if 'attack' in d.action_taken.lower())
            if len(combat_situations) >= 3 and attack_actions / len(combat_situations) > 0.7:
                patterns.append(BehaviorPattern(
                    pattern_id="combat_aggressive",
                    pattern_type="combat_style",
                    description="Prefers aggressive combat approach",
                    supporting_observations=[d.observation_id for d in combat_situations[:3]],
                    confidence=attack_actions / len(combat_situations),
                    triggers=["combat", "enemy"],
                    typical_actions=["attack", "charge", "aggressive"],
                    frequency=len(combat_situations)
                ))
        
        # Pattern: Diplomacy preference
        social_situations = [d for d in decisions if any(
            word in d.situation_description.lower() 
            for word in ['npc', 'talk', 'negotiate', 'persuade']
        )]
        if social_situations:
            diplomatic_actions = sum(1 for d in social_situations 
                                    if any(word in d.action_taken.lower() 
                                          for word in ['talk', 'persuade', 'negotiate', 'ask']))
            if len(social_situations) >= 3 and diplomatic_actions / len(social_situations) > 0.7:
                patterns.append(BehaviorPattern(
                    pattern_id="social_diplomatic",
                    pattern_type="social_style",
                    description="Prefers diplomatic solutions",
                    supporting_observations=[d.observation_id for d in social_situations[:3]],
                    confidence=diplomatic_actions / len(social_situations),
                    triggers=["social", "npc", "conflict"],
                    typical_actions=["talk", "persuade", "negotiate"],
                    frequency=len(social_situations)
                ))
        
        # Pattern: Caution level
        decision_times = [d.decision_time_seconds for d in decisions if d.decision_time_seconds > 0]
        if decision_times:
            avg_time = statistics.mean(decision_times)
            if avg_time > 30:  # Takes time to decide
                patterns.append(BehaviorPattern(
                    pattern_id="decision_cautious",
                    pattern_type="decision_speed",
                    description="Cautious decision-maker (thinks before acting)",
                    confidence=0.8,
                    triggers=["any decision"],
                    typical_actions=["careful planning"],
                    frequency=len(decision_times)
                ))
            elif avg_time < 5:  # Quick decisions
                patterns.append(BehaviorPattern(
                    pattern_id="decision_impulsive",
                    pattern_type="decision_speed",
                    description="Quick decision-maker (acts on instinct)",
                    confidence=0.8,
                    triggers=["any decision"],
                    typical_actions=["rapid action"],
                    frequency=len(decision_times)
                ))
        
        return patterns
    
    def analyze_risk_tolerance(
        self,
        observations: List[BehaviorObservation]
    ) -> Dict[str, Any]:
        """
        Analyze player's risk tolerance.
        
        Returns risk profile.
        """
        decisions = [o for o in observations 
                    if o.behavior_type == BehaviorType.EXPLICIT_DECISION]
        
        if not decisions:
            return {"risk_level": "UNKNOWN", "confidence": 0.0}
        
        # Categorize decisions by risk
        risky_keywords = ['charge', 'attack all', 'rush', 'fight', 'confront']
        safe_keywords = ['retreat', 'avoid', 'hide', 'sneak', 'careful']
        
        risky_count = sum(1 for d in decisions 
                         if any(kw in d.action_taken.lower() for kw in risky_keywords))
        safe_count = sum(1 for d in decisions 
                        if any(kw in d.action_taken.lower() for kw in safe_keywords))
        
        if risky_count + safe_count == 0:
            return {"risk_level": "MODERATE", "confidence": 0.3}
        
        risk_ratio = risky_count / (risky_count + safe_count)
        
        if risk_ratio > 0.7:
            risk_level = "VERY_HIGH"
        elif risk_ratio > 0.5:
            risk_level = "HIGH"
        elif risk_ratio > 0.3:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"
        
        return {
            "risk_level": risk_level,
            "risk_ratio": risk_ratio,
            "confidence": min((risky_count + safe_count) / 10.0, 1.0),
            "risky_decisions": risky_count,
            "safe_decisions": safe_count
        }


# ============================================================================
# DIGITAL TWIN MODEL
# ============================================================================

@dataclass
class DigitalTwin:
    """
    AI model of a human player.
    Can predict/mimic their behavior.
    """
    player_id: str
    created_at: datetime
    
    # Learned patterns
    decision_patterns: List[BehaviorPattern] = field(default_factory=list)
    risk_profile: Dict[str, Any] = field(default_factory=dict)
    
    # Personality model
    personality_traits: Dict[str, float] = field(default_factory=dict)
    
    # Strategy preferences
    preferred_strategies: List[str] = field(default_factory=list)
    avoided_strategies: List[str] = field(default_factory=list)
    
    # Social model
    trusted_characters: List[str] = field(default_factory=list)
    avoided_characters: List[str] = field(default_factory=list)
    
    # Training metadata
    training_observations: int = 0
    model_confidence: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def predict_action(
        self,
        situation: str,
        available_actions: List[str],
        game_state: Dict[str, Any]
    ) -> Tuple[str, float]:
        """
        Predict what the human would do.
        
        Returns: (predicted_action, confidence)
        """
        # Check patterns
        for pattern in self.decision_patterns:
            # Does this situation match pattern triggers?
            if any(trigger in situation.lower() for trigger in pattern.triggers):
                # Find action that matches pattern
                for action in available_actions:
                    if any(typical in action.lower() for typical in pattern.typical_actions):
                        return action, pattern.confidence
        
        # Fallback: use risk profile
        risk_level = self.risk_profile.get('risk_level', 'MODERATE')
        
        if risk_level in ['VERY_HIGH', 'HIGH']:
            # Prefer aggressive actions
            for action in available_actions:
                if any(word in action.lower() for word in ['attack', 'charge', 'fight']):
                    return action, 0.5
        elif risk_level == 'LOW':
            # Prefer safe actions
            for action in available_actions:
                if any(word in action.lower() for word in ['retreat', 'avoid', 'careful']):
                    return action, 0.5
        
        # Default: first action with low confidence
        return available_actions[0] if available_actions else "Do nothing", 0.2
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary"""
        return {
            "player_id": self.player_id,
            "created_at": self.created_at.isoformat(),
            "decision_patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "description": p.description,
                    "confidence": p.confidence,
                    "triggers": p.triggers,
                    "typical_actions": p.typical_actions
                }
                for p in self.decision_patterns
            ],
            "risk_profile": self.risk_profile,
            "personality_traits": self.personality_traits,
            "preferred_strategies": self.preferred_strategies,
            "training_observations": self.training_observations,
            "model_confidence": self.model_confidence,
            "last_updated": self.last_updated.isoformat()
        }


# ============================================================================
# TWIN TRAINING SYSTEM
# ============================================================================

class DigitalTwinTrainer:
    """
    Trains digital twin models from captured behavior.
    """
    
    def __init__(self):
        self.twins: Dict[str, DigitalTwin] = {}
        self.analyzer = BehaviorAnalyzer()
    
    def train_twin(
        self,
        player_id: str,
        observations: List[BehaviorObservation],
        incremental: bool = True
    ) -> DigitalTwin:
        """
        Train or update digital twin.
        
        Args:
            player_id: Player to model
            observations: Behavior data
            incremental: Update existing twin vs rebuild
        """
        # Get or create twin
        if incremental and player_id in self.twins:
            twin = self.twins[player_id]
        else:
            twin = DigitalTwin(
                player_id=player_id,
                created_at=datetime.now()
            )
        
        # Analyze patterns
        patterns = self.analyzer.analyze_decision_patterns(observations)
        twin.decision_patterns = patterns
        
        # Analyze risk
        risk_profile = self.analyzer.analyze_risk_tolerance(observations)
        twin.risk_profile = risk_profile
        
        # Extract personality traits
        twin.personality_traits = self._extract_personality(observations, patterns)
        
        # Update metadata
        twin.training_observations = len(observations)
        twin.model_confidence = min(len(observations) / 50.0, 1.0)  # Confident after 50+ observations
        twin.last_updated = datetime.now()
        
        self.twins[player_id] = twin
        
        return twin
    
    def _extract_personality(
        self,
        observations: List[BehaviorObservation],
        patterns: List[BehaviorPattern]
    ) -> Dict[str, float]:
        """Extract Big Five personality traits from behavior"""
        
        traits = {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5
        }
        
        # Openness: creative, tries new things
        creative_patterns = [p for p in patterns if 'creative' in p.description.lower()]
        if creative_patterns:
            traits["openness"] = 0.7
        
        # Conscientiousness: plans, cautious
        if any(p.pattern_id == "decision_cautious" for p in patterns):
            traits["conscientiousness"] = 0.7
        elif any(p.pattern_id == "decision_impulsive" for p in patterns):
            traits["conscientiousness"] = 0.3
        
        # Extraversion: social, talkative
        social_patterns = [p for p in patterns if 'social' in p.pattern_type]
        if social_patterns:
            traits["extraversion"] = 0.7
        
        # Agreeableness: diplomatic, cooperative
        if any(p.pattern_id == "social_diplomatic" for p in patterns):
            traits["agreeableness"] = 0.7
        elif any(p.pattern_id == "combat_aggressive" for p in patterns):
            traits["agreeableness"] = 0.3
        
        return traits
    
    def get_twin(self, player_id: str) -> Optional[DigitalTwin]:
        """Get trained twin"""
        return self.twins.get(player_id)
    
    def compare_to_human(
        self,
        player_id: str,
        test_decisions: List[Tuple[str, str, List[str]]]  # (situation, actual_action, available)
    ) -> Dict[str, Any]:
        """
        Compare twin predictions to actual human decisions.
        
        Args:
            test_decisions: List of (situation, actual_action, available_actions)
        
        Returns:
            Accuracy metrics
        """
        twin = self.get_twin(player_id)
        if not twin:
            return {"error": "Twin not trained"}
        
        correct = 0
        predictions = []
        
        for situation, actual, available in test_decisions:
            predicted, confidence = twin.predict_action(situation, available, {})
            is_correct = predicted == actual
            if is_correct:
                correct += 1
            
            predictions.append({
                "situation": situation,
                "predicted": predicted,
                "actual": actual,
                "correct": is_correct,
                "confidence": confidence
            })
        
        accuracy = correct / len(test_decisions) if test_decisions else 0.0
        
        return {
            "player_id": player_id,
            "test_size": len(test_decisions),
            "accuracy": accuracy,
            "correct": correct,
            "model_confidence": twin.model_confidence,
            "predictions": predictions
        }
