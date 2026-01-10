"""
Outcome Tracker

Tracks decision outcomes with sophisticated reward signals and temporal correlation.
Calculates success metrics across combat, social, and exploration contexts.

Phase 7.1.2 - Outcome Tracker
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class OutcomeType(Enum):
    """Types of outcomes"""
    IMMEDIATE = "immediate"      # Happens right away (hit/miss, accept/reject)
    SHORT_TERM = "short_term"    # Within same encounter (5-10 turns)
    LONG_TERM = "long_term"      # Multiple encounters (session-wide)


class RewardDomain(Enum):
    """Domains for reward calculation"""
    COMBAT = "combat"
    SOCIAL = "social"
    EXPLORATION = "exploration"
    RESOURCE = "resource"
    STRATEGIC = "strategic"


@dataclass
class RewardSignal:
    """Calculated reward signal for an outcome"""
    domain: RewardDomain
    value: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    components: Dict[str, float] = field(default_factory=dict)
    reasoning: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "domain": self.domain.value,
            "value": self.value,
            "confidence": self.confidence,
            "components": self.components,
            "reasoning": self.reasoning
        }


@dataclass
class OutcomeRecord:
    """Record of a decision outcome"""
    decision_id: str
    outcome_type: OutcomeType
    timestamp: float
    
    # Outcome details
    description: str
    success: bool
    
    # Reward signals
    rewards: List[RewardSignal] = field(default_factory=list)
    
    # Correlation
    related_decisions: List[str] = field(default_factory=list)
    causal_chain: List[str] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "decision_id": self.decision_id,
            "outcome_type": self.outcome_type.value,
            "timestamp": self.timestamp,
            "description": self.description,
            "success": self.success,
            "rewards": [r.to_dict() for r in self.rewards],
            "related_decisions": self.related_decisions,
            "causal_chain": self.causal_chain,
            "metadata": self.metadata
        }


class OutcomeTracker:
    """
    Tracks and analyzes decision outcomes with reward signals.
    
    Features:
    - Temporal correlation (short-term vs long-term outcomes)
    - Reward signal calculation (combat, social, exploration)
    - Causal chain tracking (decision → outcome → consequence)
    - Multi-domain reward aggregation
    - Performance metrics
    """
    
    def __init__(self):
        """Initialize outcome tracker"""
        # Outcome records
        self.outcomes: Dict[str, List[OutcomeRecord]] = {}  # decision_id -> outcomes
        
        # Pending outcomes (waiting for delayed results)
        self.pending_outcomes: Dict[str, Dict[str, Any]] = {}
        
        # Causal chains
        self.causal_chains: List[List[str]] = []  # Chains of related decisions
        
        # Performance metrics
        self.metrics = {
            "total_outcomes": 0,
            "immediate_outcomes": 0,
            "short_term_outcomes": 0,
            "long_term_outcomes": 0,
            "avg_reward_signal": 0.0,
            "correlation_time_ms": 0.0
        }
        
        logger.info("OutcomeTracker initialized")
    
    def track_immediate_outcome(
        self,
        decision_id: str,
        description: str,
        success: bool,
        context: Dict[str, Any]
    ) -> OutcomeRecord:
        """
        Track an immediate outcome (happens right after decision)
        
        Args:
            decision_id: ID of the decision
            description: What happened
            success: Whether it succeeded
            context: Decision context for reward calculation
            
        Returns:
            OutcomeRecord
        """
        start_time = time.time()
        
        # Calculate reward signals
        rewards = self._calculate_rewards(context, description, success)
        
        # Create outcome record
        outcome = OutcomeRecord(
            decision_id=decision_id,
            outcome_type=OutcomeType.IMMEDIATE,
            timestamp=time.time(),
            description=description,
            success=success,
            rewards=rewards,
            metadata={"context": context}
        )
        
        # Store outcome
        if decision_id not in self.outcomes:
            self.outcomes[decision_id] = []
        self.outcomes[decision_id].append(outcome)
        
        # Update metrics
        self.metrics["total_outcomes"] += 1
        self.metrics["immediate_outcomes"] += 1
        self._update_reward_metrics(rewards)
        
        correlation_time = (time.time() - start_time) * 1000
        self.metrics["correlation_time_ms"] = (
            self.metrics["correlation_time_ms"] * 0.9 + correlation_time * 0.1
        )
        
        logger.debug(
            f"Tracked immediate outcome for {decision_id}: "
            f"{'success' if success else 'failure'}"
        )
        
        return outcome
    
    def track_delayed_outcome(
        self,
        decision_id: str,
        description: str,
        success: bool,
        context: Dict[str, Any],
        outcome_type: OutcomeType = OutcomeType.SHORT_TERM,
        related_decisions: Optional[List[str]] = None
    ) -> OutcomeRecord:
        """
        Track a delayed outcome (happens later)
        
        Args:
            decision_id: Original decision ID
            description: What happened
            success: Whether it succeeded
            context: Context for reward calculation
            outcome_type: SHORT_TERM or LONG_TERM
            related_decisions: Other decisions that contributed
            
        Returns:
            OutcomeRecord
        """
        start_time = time.time()
        
        # Calculate rewards
        rewards = self._calculate_rewards(context, description, success)
        
        # Create outcome
        outcome = OutcomeRecord(
            decision_id=decision_id,
            outcome_type=outcome_type,
            timestamp=time.time(),
            description=description,
            success=success,
            rewards=rewards,
            related_decisions=related_decisions or [],
            metadata={"context": context}
        )
        
        # Attempt to correlate with causal chain
        if related_decisions:
            outcome.causal_chain = self._build_causal_chain(
                decision_id,
                related_decisions
            )
        
        # Store
        if decision_id not in self.outcomes:
            self.outcomes[decision_id] = []
        self.outcomes[decision_id].append(outcome)
        
        # Update metrics
        self.metrics["total_outcomes"] += 1
        if outcome_type == OutcomeType.SHORT_TERM:
            self.metrics["short_term_outcomes"] += 1
        else:
            self.metrics["long_term_outcomes"] += 1
        
        self._update_reward_metrics(rewards)
        
        correlation_time = (time.time() - start_time) * 1000
        self.metrics["correlation_time_ms"] = (
            self.metrics["correlation_time_ms"] * 0.9 + correlation_time * 0.1
        )
        
        logger.debug(
            f"Tracked {outcome_type.value} outcome for {decision_id}"
        )
        
        return outcome
    
    def _calculate_rewards(
        self,
        context: Dict[str, Any],
        description: str,
        success: bool
    ) -> List[RewardSignal]:
        """
        Calculate reward signals across multiple domains
        
        Args:
            context: Decision context
            description: Outcome description
            success: Whether it succeeded
            
        Returns:
            List of reward signals
        """
        rewards = []
        decision_type = context.get("decision_type", "unknown")
        
        # Combat rewards
        if decision_type == "combat_action" or "combat" in description.lower():
            combat_reward = self._calculate_combat_reward(context, description, success)
            if combat_reward:
                rewards.append(combat_reward)
        
        # Social rewards
        if decision_type == "social" or any(
            word in description.lower() 
            for word in ["persuade", "negotiate", "relationship", "trust"]
        ):
            social_reward = self._calculate_social_reward(context, description, success)
            if social_reward:
                rewards.append(social_reward)
        
        # Exploration rewards
        if decision_type == "exploration" or any(
            word in description.lower()
            for word in ["discover", "investigate", "explore", "find"]
        ):
            exploration_reward = self._calculate_exploration_reward(
                context, description, success
            )
            if exploration_reward:
                rewards.append(exploration_reward)
        
        # Resource rewards
        if any(word in description.lower() for word in ["gold", "item", "xp", "reward"]):
            resource_reward = self._calculate_resource_reward(context, description, success)
            if resource_reward:
                rewards.append(resource_reward)
        
        # Strategic rewards (long-term positioning)
        strategic_reward = self._calculate_strategic_reward(context, description, success)
        if strategic_reward:
            rewards.append(strategic_reward)
        
        return rewards
    
    def _calculate_combat_reward(
        self,
        context: Dict[str, Any],
        description: str,
        success: bool
    ) -> Optional[RewardSignal]:
        """Calculate combat reward signal"""
        components = {}
        
        # Damage dealt
        damage_dealt = 0.0
        if "damage" in description.lower():
            # Try to extract damage number
            import re
            match = re.search(r'(\d+)\s+damage', description.lower())
            if match:
                damage_dealt = float(match.group(1))
                components["damage_dealt"] = min(damage_dealt / 20.0, 1.0)  # Normalize
        
        # Damage taken (negative)
        damage_taken = 0.0
        if "hit for" in description.lower() or "took" in description.lower():
            match = re.search(r'took\s+(\d+)', description.lower())
            if match:
                damage_taken = float(match.group(1))
                components["damage_taken"] = -min(damage_taken / 30.0, 1.0)
        
        # Tactical advantage
        tactical_bonus = 0.0
        if any(word in description.lower() for word in ["flank", "advantage", "critical"]):
            tactical_bonus = 0.3
            components["tactical_advantage"] = tactical_bonus
        
        # Enemy defeated
        if "defeated" in description.lower() or "killed" in description.lower():
            components["enemy_defeated"] = 0.5
        
        # Party safety
        if "party safe" in description.lower():
            components["party_safety"] = 0.3
        
        # Calculate total
        if not components:
            return None
        
        value = sum(components.values())
        value = max(-1.0, min(1.0, value))  # Clamp to [-1, 1]
        
        # Base success bonus
        if success:
            value = max(value, 0.3)  # Minimum reward for success
        
        return RewardSignal(
            domain=RewardDomain.COMBAT,
            value=value,
            confidence=0.8,
            components=components,
            reasoning=f"Combat outcome: {description[:50]}..."
        )
    
    def _calculate_social_reward(
        self,
        context: Dict[str, Any],
        description: str,
        success: bool
    ) -> Optional[RewardSignal]:
        """Calculate social reward signal"""
        components = {}
        
        # Relationship changes
        if "relationship" in description.lower():
            if "improved" in description.lower() or "+" in description:
                components["relationship_gain"] = 0.4
            elif "worsened" in description.lower() or "-" in description:
                components["relationship_loss"] = -0.4
        
        # Information gained
        if any(word in description.lower() for word in ["learned", "discovered", "told"]):
            components["information_gained"] = 0.3
        
        # Trust building
        if "trust" in description.lower():
            components["trust"] = 0.3 if success else -0.3
        
        # Persuasion success
        if "convinced" in description.lower() or "agreed" in description.lower():
            components["persuasion_success"] = 0.5
        
        # Conflict resolution
        if "resolved" in description.lower() or "peace" in description.lower():
            components["conflict_resolution"] = 0.4
        
        if not components:
            return None
        
        value = sum(components.values())
        value = max(-1.0, min(1.0, value))
        
        return RewardSignal(
            domain=RewardDomain.SOCIAL,
            value=value,
            confidence=0.7,
            components=components,
            reasoning=f"Social outcome: {description[:50]}..."
        )
    
    def _calculate_exploration_reward(
        self,
        context: Dict[str, Any],
        description: str,
        success: bool
    ) -> Optional[RewardSignal]:
        """Calculate exploration reward signal"""
        components = {}
        
        # Discovery
        if any(word in description.lower() for word in ["found", "discovered", "uncovered"]):
            components["discovery"] = 0.5
        
        # Progress toward goal
        if "progress" in description.lower() or "closer" in description.lower():
            components["progress"] = 0.3
        
        # Danger avoided
        if "avoided" in description.lower() or "safe" in description.lower():
            components["danger_avoided"] = 0.2
        
        # Secret revealed
        if "secret" in description.lower() or "hidden" in description.lower():
            components["secret_revealed"] = 0.4
        
        # Map knowledge
        if "map" in description.lower() or "path" in description.lower():
            components["map_knowledge"] = 0.2
        
        if not components:
            return None
        
        value = sum(components.values())
        value = max(-1.0, min(1.0, value))
        
        return RewardSignal(
            domain=RewardDomain.EXPLORATION,
            value=value,
            confidence=0.75,
            components=components,
            reasoning=f"Exploration outcome: {description[:50]}..."
        )
    
    def _calculate_resource_reward(
        self,
        context: Dict[str, Any],
        description: str,
        success: bool
    ) -> Optional[RewardSignal]:
        """Calculate resource reward signal"""
        components = {}
        
        # XP gained
        if "xp" in description.lower():
            import re
            match = re.search(r'(\d+)\s*xp', description.lower())
            if match:
                xp = float(match.group(1))
                components["xp_gained"] = min(xp / 100.0, 1.0)
        
        # Gold/treasure
        if "gold" in description.lower() or "treasure" in description.lower():
            components["wealth_gained"] = 0.4
        
        # Items acquired
        if "item" in description.lower() or "equipment" in description.lower():
            components["items_gained"] = 0.3
        
        # Resources consumed (negative)
        if "used" in description.lower() or "consumed" in description.lower():
            components["resources_spent"] = -0.2
        
        if not components:
            return None
        
        value = sum(components.values())
        value = max(-1.0, min(1.0, value))
        
        return RewardSignal(
            domain=RewardDomain.RESOURCE,
            value=value,
            confidence=0.9,  # Resource rewards are concrete
            components=components,
            reasoning=f"Resource outcome: {description[:50]}..."
        )
    
    def _calculate_strategic_reward(
        self,
        context: Dict[str, Any],
        description: str,
        success: bool
    ) -> Optional[RewardSignal]:
        """Calculate strategic reward signal (long-term positioning)"""
        components = {}
        
        # Positioning advantage
        if "position" in description.lower() or "advantage" in description.lower():
            components["positioning"] = 0.3 if success else -0.2
        
        # Future opportunities
        if "opportunity" in description.lower() or "opens" in description.lower():
            components["opportunities_created"] = 0.4
        
        # Risk mitigation
        if "safe" in description.lower() or "secure" in description.lower():
            components["risk_mitigation"] = 0.3
        
        # Goal progress
        if "goal" in description.lower() or "objective" in description.lower():
            components["goal_progress"] = 0.5 if success else -0.3
        
        if not components:
            # Base strategic value from success
            if success:
                components["base_strategic"] = 0.2
            else:
                return None
        
        value = sum(components.values())
        value = max(-1.0, min(1.0, value))
        
        return RewardSignal(
            domain=RewardDomain.STRATEGIC,
            value=value,
            confidence=0.6,  # Strategic rewards are harder to assess
            components=components,
            reasoning=f"Strategic outcome: {description[:50]}..."
        )
    
    def _build_causal_chain(
        self,
        decision_id: str,
        related_decisions: List[str]
    ) -> List[str]:
        """
        Build causal chain showing how decisions led to this outcome
        
        Args:
            decision_id: Current decision
            related_decisions: Other contributing decisions
            
        Returns:
            Ordered list of decision IDs forming causal chain
        """
        # Start with related decisions
        chain = list(related_decisions)
        
        # Add current decision
        if decision_id not in chain:
            chain.append(decision_id)
        
        # Sort by timestamp (if available from outcomes)
        # For now, just return as-is
        
        # Store chain for analysis
        if chain not in self.causal_chains:
            self.causal_chains.append(chain)
        
        return chain
    
    def _update_reward_metrics(self, rewards: List[RewardSignal]) -> None:
        """Update average reward metrics"""
        if not rewards:
            return
        
        avg_reward = sum(r.value for r in rewards) / len(rewards)
        
        total = self.metrics["total_outcomes"]
        current_avg = self.metrics["avg_reward_signal"]
        
        # Running average
        self.metrics["avg_reward_signal"] = (
            (current_avg * (total - 1) + avg_reward) / total
        )
    
    def get_outcomes_for_decision(
        self,
        decision_id: str
    ) -> List[OutcomeRecord]:
        """
        Get all outcomes for a decision
        
        Args:
            decision_id: Decision ID
            
        Returns:
            List of outcome records
        """
        return self.outcomes.get(decision_id, [])
    
    def get_aggregate_reward(
        self,
        decision_id: str,
        domain: Optional[RewardDomain] = None
    ) -> float:
        """
        Get aggregate reward for a decision
        
        Args:
            decision_id: Decision ID
            domain: Optional domain filter
            
        Returns:
            Aggregate reward value
        """
        outcomes = self.get_outcomes_for_decision(decision_id)
        
        if not outcomes:
            return 0.0
        
        rewards = []
        for outcome in outcomes:
            for reward in outcome.rewards:
                if domain is None or reward.domain == domain:
                    rewards.append(reward.value * reward.confidence)
        
        if not rewards:
            return 0.0
        
        return sum(rewards) / len(rewards)
    
    def get_success_rate(
        self,
        decision_type: Optional[str] = None
    ) -> float:
        """
        Get overall success rate
        
        Args:
            decision_type: Optional filter by decision type
            
        Returns:
            Success rate (0.0 to 1.0)
        """
        total = 0
        successes = 0
        
        for decision_outcomes in self.outcomes.values():
            for outcome in decision_outcomes:
                # Filter by type if specified
                if decision_type:
                    if outcome.metadata.get("context", {}).get("decision_type") != decision_type:
                        continue
                
                total += 1
                if outcome.success:
                    successes += 1
        
        if total == 0:
            return 0.0
        
        return successes / total
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get outcome tracking statistics"""
        stats = dict(self.metrics)
        
        # Add success rates by type
        stats["success_rate_overall"] = self.get_success_rate()
        stats["success_rate_combat"] = self.get_success_rate("combat_action")
        stats["success_rate_social"] = self.get_success_rate("social")
        stats["success_rate_exploration"] = self.get_success_rate("exploration")
        
        # Outcome type distribution
        total = self.metrics["total_outcomes"]
        if total > 0:
            stats["immediate_pct"] = self.metrics["immediate_outcomes"] / total
            stats["short_term_pct"] = self.metrics["short_term_outcomes"] / total
            stats["long_term_pct"] = self.metrics["long_term_outcomes"] / total
        
        # Causal chain stats
        stats["total_causal_chains"] = len(self.causal_chains)
        if self.causal_chains:
            chain_lengths = [len(chain) for chain in self.causal_chains]
            stats["avg_chain_length"] = sum(chain_lengths) / len(chain_lengths)
            stats["max_chain_length"] = max(chain_lengths)
        
        return stats
    
    def analyze_decision_quality(
        self,
        decision_id: str
    ) -> Dict[str, Any]:
        """
        Analyze the quality of a decision based on its outcomes
        
        Args:
            decision_id: Decision ID
            
        Returns:
            Analysis dictionary
        """
        outcomes = self.get_outcomes_for_decision(decision_id)
        
        if not outcomes:
            return {
                "quality_score": 0.0,
                "confidence": 0.0,
                "reasoning": "No outcomes available"
            }
        
        # Aggregate rewards by domain
        domain_rewards = {}
        for outcome in outcomes:
            for reward in outcome.rewards:
                if reward.domain not in domain_rewards:
                    domain_rewards[reward.domain] = []
                domain_rewards[reward.domain].append(reward.value * reward.confidence)
        
        # Calculate average per domain
        domain_scores = {
            domain.value: sum(rewards) / len(rewards)
            for domain, rewards in domain_rewards.items()
        }
        
        # Overall quality score
        if domain_scores:
            quality_score = sum(domain_scores.values()) / len(domain_scores)
        else:
            quality_score = 0.0
        
        # Success factor
        success_count = sum(1 for o in outcomes if o.success)
        success_rate = success_count / len(outcomes)
        
        # Weighted quality (success matters more)
        weighted_quality = quality_score * 0.7 + (success_rate * 2 - 1) * 0.3
        
        # Confidence based on number of outcomes
        confidence = min(len(outcomes) / 3.0, 1.0)
        
        return {
            "quality_score": weighted_quality,
            "confidence": confidence,
            "success_rate": success_rate,
            "domain_scores": domain_scores,
            "total_outcomes": len(outcomes),
            "reasoning": f"Based on {len(outcomes)} outcomes across {len(domain_scores)} domains"
        }


# Test functionality
async def test_outcome_tracker():
    """Test the outcome tracker"""
    print("Testing OutcomeTracker...")
    
    tracker = OutcomeTracker()
    
    # Test 1: Immediate combat outcome
    outcome1 = tracker.track_immediate_outcome(
        decision_id="dec_123",
        description="Hit goblin for 15 damage, goblin defeated",
        success=True,
        context={
            "decision_type": "combat_action",
            "character_id": "thorin"
        }
    )
    print(f"✓ Tracked immediate outcome: {len(outcome1.rewards)} rewards")
    
    # Test 2: Social outcome
    outcome2 = tracker.track_immediate_outcome(
        decision_id="dec_456",
        description="Convinced merchant, relationship improved +5, learned secret",
        success=True,
        context={
            "decision_type": "social",
            "character_id": "elara"
        }
    )
    print(f"✓ Tracked social outcome: {len(outcome2.rewards)} rewards")
    
    # Test 3: Delayed outcome
    outcome3 = tracker.track_delayed_outcome(
        decision_id="dec_123",
        description="Party safe, gained 50 XP, found treasure",
        success=True,
        context={"decision_type": "combat_action"},
        outcome_type=OutcomeType.SHORT_TERM,
        related_decisions=["dec_122", "dec_123"]
    )
    print(f"✓ Tracked delayed outcome with causal chain")
    
    # Test 4: Get aggregate reward
    total_reward = tracker.get_aggregate_reward("dec_123")
    print(f"✓ Aggregate reward for dec_123: {total_reward:.3f}")
    
    # Test 5: Analyze decision quality
    quality = tracker.analyze_decision_quality("dec_123")
    print(f"✓ Decision quality: {quality['quality_score']:.3f} (confidence: {quality['confidence']:.2f})")
    
    # Test 6: Get statistics
    stats = tracker.get_statistics()
    print(f"✓ Statistics:")
    print(f"    Total outcomes: {stats['total_outcomes']}")
    print(f"    Success rate: {stats['success_rate_overall']:.1%}")
    print(f"    Avg reward: {stats['avg_reward_signal']:.3f}")
    print(f"    Correlation time: {stats['correlation_time_ms']:.2f}ms")
    
    print("\n✅ All outcome tracker tests passed!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_outcome_tracker())
