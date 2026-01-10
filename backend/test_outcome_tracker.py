"""
Tests for Outcome Tracker (Phase 7.1.2)

Comprehensive test suite for reward signal calculation and outcome analysis.
"""

import pytest
from outcome_tracker import (
    OutcomeTracker,
    OutcomeType,
    RewardDomain,
    RewardSignal,
    OutcomeRecord
)


class TestOutcomeTracker:
    """Test suite for OutcomeTracker"""
    
    def setup_method(self):
        """Create fresh tracker for each test"""
        self.tracker = OutcomeTracker()
    
    def test_initialization(self):
        """Test tracker initialization"""
        assert self.tracker is not None
        assert len(self.tracker.outcomes) == 0
        assert self.tracker.metrics["total_outcomes"] == 0
        print("✓ Tracker initialized successfully")
    
    def test_combat_reward_calculation(self):
        """Test combat reward signals"""
        outcome = self.tracker.track_immediate_outcome(
            decision_id="dec_001",
            description="Hit goblin for 15 damage, goblin defeated, party safe",
            success=True,
            context={"decision_type": "combat_action"}
        )
        
        assert len(outcome.rewards) > 0
        
        # Check for combat reward
        combat_rewards = [r for r in outcome.rewards if r.domain == RewardDomain.COMBAT]
        assert len(combat_rewards) > 0
        
        combat_reward = combat_rewards[0]
        assert combat_reward.value > 0  # Positive reward for success
        assert "damage_dealt" in combat_reward.components
        assert "enemy_defeated" in combat_reward.components
        
        print(f"✓ Combat reward: {combat_reward.value:.3f}")
        print(f"   Components: {combat_reward.components}")
    
    def test_social_reward_calculation(self):
        """Test social reward signals"""
        outcome = self.tracker.track_immediate_outcome(
            decision_id="dec_002",
            description="Convinced merchant, relationship improved +5, learned secret about guild",
            success=True,
            context={"decision_type": "social"}
        )
        
        social_rewards = [r for r in outcome.rewards if r.domain == RewardDomain.SOCIAL]
        assert len(social_rewards) > 0
        
        social_reward = social_rewards[0]
        assert social_reward.value > 0
        assert "relationship_gain" in social_reward.components or "persuasion_success" in social_reward.components
        
        print(f"✓ Social reward: {social_reward.value:.3f}")
        print(f"   Components: {social_reward.components}")
    
    def test_exploration_reward_calculation(self):
        """Test exploration reward signals"""
        outcome = self.tracker.track_immediate_outcome(
            decision_id="dec_003",
            description="Found hidden passage, discovered secret room, avoided trap",
            success=True,
            context={"decision_type": "exploration"}
        )
        
        exploration_rewards = [r for r in outcome.rewards if r.domain == RewardDomain.EXPLORATION]
        assert len(exploration_rewards) > 0
        
        exploration_reward = exploration_rewards[0]
        assert exploration_reward.value > 0
        assert "discovery" in exploration_reward.components or "secret_revealed" in exploration_reward.components
        
        print(f"✓ Exploration reward: {exploration_reward.value:.3f}")
        print(f"   Components: {exploration_reward.components}")
    
    def test_resource_reward_calculation(self):
        """Test resource reward signals"""
        outcome = self.tracker.track_immediate_outcome(
            decision_id="dec_004",
            description="Gained 50 XP, found treasure worth 100 gold",
            success=True,
            context={"decision_type": "combat_action"}
        )
        
        resource_rewards = [r for r in outcome.rewards if r.domain == RewardDomain.RESOURCE]
        assert len(resource_rewards) > 0
        
        resource_reward = resource_rewards[0]
        assert resource_reward.value > 0
        assert "xp_gained" in resource_reward.components or "wealth_gained" in resource_reward.components
        
        print(f"✓ Resource reward: {resource_reward.value:.3f}")
        print(f"   Components: {resource_reward.components}")
    
    def test_strategic_reward_calculation(self):
        """Test strategic reward signals"""
        outcome = self.tracker.track_immediate_outcome(
            decision_id="dec_005",
            description="Secured high ground position, opens opportunity for flanking",
            success=True,
            context={"decision_type": "combat_action"}
        )
        
        strategic_rewards = [r for r in outcome.rewards if r.domain == RewardDomain.STRATEGIC]
        assert len(strategic_rewards) > 0
        
        strategic_reward = strategic_rewards[0]
        assert strategic_reward.value > 0
        
        print(f"✓ Strategic reward: {strategic_reward.value:.3f}")
        print(f"   Components: {strategic_reward.components}")
    
    def test_negative_rewards(self):
        """Test negative rewards for failures"""
        outcome = self.tracker.track_immediate_outcome(
            decision_id="dec_006",
            description="Attack missed, took 10 damage from counterattack",
            success=False,
            context={"decision_type": "combat_action"}
        )
        
        combat_rewards = [r for r in outcome.rewards if r.domain == RewardDomain.COMBAT]
        if combat_rewards:
            combat_reward = combat_rewards[0]
            # Should have negative component for damage taken
            assert "damage_taken" in combat_reward.components
            assert combat_reward.components["damage_taken"] < 0
        
        print("✓ Negative rewards calculated correctly")
    
    def test_delayed_outcome(self):
        """Test delayed outcome tracking"""
        # Initial outcome
        self.tracker.track_immediate_outcome(
            decision_id="dec_007",
            description="Negotiated truce",
            success=True,
            context={"decision_type": "social"}
        )
        
        # Delayed outcome
        delayed = self.tracker.track_delayed_outcome(
            decision_id="dec_007",
            description="Truce led to alliance, gained powerful ally",
            success=True,
            context={"decision_type": "social"},
            outcome_type=OutcomeType.LONG_TERM,
            related_decisions=["dec_006", "dec_007"]
        )
        
        assert delayed.outcome_type == OutcomeType.LONG_TERM
        assert len(delayed.causal_chain) > 0
        assert "dec_007" in delayed.causal_chain
        
        print(f"✓ Delayed outcome tracked")
        print(f"   Causal chain: {delayed.causal_chain}")
    
    def test_aggregate_reward(self):
        """Test aggregate reward calculation"""
        decision_id = "dec_008"
        
        # Multiple outcomes for same decision
        self.tracker.track_immediate_outcome(
            decision_id=decision_id,
            description="Hit enemy for 10 damage",
            success=True,
            context={"decision_type": "combat_action"}
        )
        
        self.tracker.track_delayed_outcome(
            decision_id=decision_id,
            description="Enemy defeated, party safe, gained 30 XP",
            success=True,
            context={"decision_type": "combat_action"},
            outcome_type=OutcomeType.SHORT_TERM
        )
        
        # Get aggregate
        aggregate = self.tracker.get_aggregate_reward(decision_id)
        assert aggregate > 0  # Should be positive for successful outcomes
        
        # Get by domain
        combat_aggregate = self.tracker.get_aggregate_reward(decision_id, RewardDomain.COMBAT)
        assert combat_aggregate > 0
        
        print(f"✓ Aggregate reward: {aggregate:.3f}")
        print(f"   Combat aggregate: {combat_aggregate:.3f}")
    
    def test_success_rate_calculation(self):
        """Test success rate tracking"""
        # Add successful decisions
        for i in range(7):
            self.tracker.track_immediate_outcome(
                decision_id=f"dec_success_{i}",
                description="Successful action",
                success=True,
                context={"decision_type": "combat_action"}
            )
        
        # Add failures
        for i in range(3):
            self.tracker.track_immediate_outcome(
                decision_id=f"dec_fail_{i}",
                description="Failed action",
                success=False,
                context={"decision_type": "combat_action"}
            )
        
        success_rate = self.tracker.get_success_rate("combat_action")
        assert 0.6 < success_rate < 0.8  # Should be around 70%
        
        print(f"✓ Success rate: {success_rate:.1%}")
    
    def test_decision_quality_analysis(self):
        """Test decision quality analysis"""
        decision_id = "dec_quality"
        
        # Add outcome with mixed rewards
        self.tracker.track_immediate_outcome(
            decision_id=decision_id,
            description="Hit enemy for 20 damage, took 5 damage, enemy defeated, gained 40 XP",
            success=True,
            context={"decision_type": "combat_action"}
        )
        
        quality = self.tracker.analyze_decision_quality(decision_id)
        
        assert "quality_score" in quality
        assert "confidence" in quality
        assert "success_rate" in quality
        assert "domain_scores" in quality
        
        assert quality["success_rate"] == 1.0  # 100% success
        assert quality["quality_score"] > 0  # Positive quality
        
        print(f"✓ Quality analysis:")
        print(f"   Score: {quality['quality_score']:.3f}")
        print(f"   Confidence: {quality['confidence']:.2f}")
        print(f"   Domains: {quality['domain_scores']}")
    
    def test_statistics(self):
        """Test statistics generation"""
        # Add various outcomes
        for i in range(5):
            self.tracker.track_immediate_outcome(
                decision_id=f"dec_{i}",
                description=f"Action {i}",
                success=(i % 2 == 0),
                context={"decision_type": "combat_action"}
            )
        
        stats = self.tracker.get_statistics()
        
        assert stats["total_outcomes"] == 5
        assert stats["immediate_outcomes"] == 5
        assert 0 <= stats["success_rate_overall"] <= 1
        assert stats["avg_reward_signal"] != 0
        
        print(f"✓ Statistics:")
        print(f"   Total outcomes: {stats['total_outcomes']}")
        print(f"   Success rate: {stats['success_rate_overall']:.1%}")
        print(f"   Avg reward: {stats['avg_reward_signal']:.3f}")
        print(f"   Correlation time: {stats['correlation_time_ms']:.2f}ms")
    
    def test_multi_domain_rewards(self):
        """Test decision with rewards across multiple domains"""
        outcome = self.tracker.track_immediate_outcome(
            decision_id="dec_multi",
            description="Defeated enemy (15 damage), found treasure (100 gold), gained ally (relationship +10)",
            success=True,
            context={"decision_type": "combat_action"}
        )
        
        # Should have rewards in multiple domains
        domains = {r.domain for r in outcome.rewards}
        assert len(domains) >= 2  # At least combat and resource
        
        print(f"✓ Multi-domain rewards: {len(outcome.rewards)} rewards across {len(domains)} domains")
        for reward in outcome.rewards:
            print(f"   {reward.domain.value}: {reward.value:.3f}")
    
    def test_causal_chain_tracking(self):
        """Test causal chain building"""
        # Series of related decisions
        self.tracker.track_delayed_outcome(
            decision_id="dec_chain_3",
            description="Final outcome",
            success=True,
            context={"decision_type": "combat_action"},
            outcome_type=OutcomeType.LONG_TERM,
            related_decisions=["dec_chain_1", "dec_chain_2"]
        )
        
        assert len(self.tracker.causal_chains) > 0
        chain = self.tracker.causal_chains[0]
        assert "dec_chain_3" in chain
        
        print(f"✓ Causal chain: {chain}")
    
    def test_outcome_type_distribution(self):
        """Test tracking of outcome types"""
        # Add different types
        self.tracker.track_immediate_outcome(
            "dec_1", "Immediate", True, {"decision_type": "combat_action"}
        )
        self.tracker.track_delayed_outcome(
            "dec_2", "Short term", True, {"decision_type": "combat_action"},
            outcome_type=OutcomeType.SHORT_TERM
        )
        self.tracker.track_delayed_outcome(
            "dec_3", "Long term", True, {"decision_type": "combat_action"},
            outcome_type=OutcomeType.LONG_TERM
        )
        
        stats = self.tracker.get_statistics()
        
        assert stats["immediate_outcomes"] == 1
        assert stats["short_term_outcomes"] == 1
        assert stats["long_term_outcomes"] == 1
        assert stats["total_outcomes"] == 3
        
        print(f"✓ Outcome type distribution:")
        print(f"   Immediate: {stats['immediate_pct']:.1%}")
        print(f"   Short-term: {stats['short_term_pct']:.1%}")
        print(f"   Long-term: {stats['long_term_pct']:.1%}")
    
    def test_performance(self):
        """Test performance with many outcomes"""
        import time
        
        start = time.time()
        for i in range(100):
            self.tracker.track_immediate_outcome(
                decision_id=f"dec_perf_{i}",
                description=f"Action {i} with damage and rewards",
                success=(i % 3 != 0),
                context={"decision_type": "combat_action"}
            )
        elapsed = (time.time() - start) * 1000
        
        avg_time = elapsed / 100
        assert avg_time < 10  # Should be < 10ms per outcome
        
        print(f"✓ Performance: {avg_time:.2f}ms per outcome (100 outcomes in {elapsed:.0f}ms)")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("OUTCOME TRACKER - TEST SUITE")
    print("=" * 60)
    print()
    
    test_suite = TestOutcomeTracker()
    
    tests = [
        test_suite.test_initialization,
        test_suite.test_combat_reward_calculation,
        test_suite.test_social_reward_calculation,
        test_suite.test_exploration_reward_calculation,
        test_suite.test_resource_reward_calculation,
        test_suite.test_strategic_reward_calculation,
        test_suite.test_negative_rewards,
        test_suite.test_delayed_outcome,
        test_suite.test_aggregate_reward,
        test_suite.test_success_rate_calculation,
        test_suite.test_decision_quality_analysis,
        test_suite.test_statistics,
        test_suite.test_multi_domain_rewards,
        test_suite.test_causal_chain_tracking,
        test_suite.test_outcome_type_distribution,
        test_suite.test_performance
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        test_suite.setup_method()
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
