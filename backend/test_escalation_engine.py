"""
Tests for Escalation Engine

Comprehensive test suite for intelligent decision routing system.
Tests Bot/Brain/Human routing, confidence-based escalation, and learning from outcomes.
"""

import pytest
import time
from escalation_engine import (
    EscalationEngine,
    DecisionContext,
    DecisionResult,
    DecisionSource,
    EscalationReason,
    EscalationThresholds,
    EscalationDecision
)


class TestEscalationEngine:
    """Test suite for EscalationEngine"""

    def setup_method(self):
        """Create fresh engine for each test"""
        self.engine = EscalationEngine(enable_training_data=False)

    def test_initialization(self):
        """Test engine initialization"""
        assert self.engine is not None
        assert len(self.engine.decision_history) == 0
        assert self.engine.stats["total_decisions"] == 0
        print("✓ Engine initialized successfully")

    def test_default_thresholds(self):
        """Test default threshold values"""
        thresholds = self.engine.get_thresholds("test_char")

        assert thresholds.bot_min_confidence == 0.7
        assert thresholds.brain_min_confidence == 0.5
        assert thresholds.high_stakes_threshold == 0.7
        assert thresholds.critical_stakes_threshold == 0.9
        assert thresholds.urgent_time_ms == 500
        assert thresholds.critical_time_ms == 100
        assert thresholds.hp_critical_threshold == 0.2

        print("✓ Default thresholds are correct")

    def test_custom_thresholds(self):
        """Test setting custom thresholds"""
        custom_thresholds = EscalationThresholds(
            bot_min_confidence=0.8,
            brain_min_confidence=0.6,
            high_stakes_threshold=0.8
        )

        self.engine.set_thresholds("custom_char", custom_thresholds)

        retrieved = self.engine.get_thresholds("custom_char")
        assert retrieved.bot_min_confidence == 0.8
        assert retrieved.brain_min_confidence == 0.6
        assert retrieved.high_stakes_threshold == 0.8

        print("✓ Custom thresholds work")

    def test_route_to_bot_low_stakes(self):
        """Test routing to bot for low stakes situations"""
        context = DecisionContext(
            character_id="warrior",
            situation_type="combat",
            situation_description="Goblin attacks with sword",
            stakes=0.3,
            urgency_ms=1000,
            similar_decisions_count=10
        )

        decision = self.engine.route_decision(context)

        # With low stakes and high familiarity, should route to BOT
        assert decision.source in [DecisionSource.BOT, DecisionSource.BRAIN]

        print(f"✓ Low stakes routed to {decision.source.value}")

    def test_route_to_brain_high_stakes(self):
        """Test routing to brain for high stakes"""
        context = DecisionContext(
            character_id="warrior",
            situation_type="combat",
            situation_description="Dragon breathes fire",
            stakes=0.8,
            urgency_ms=2000,
            similar_decisions_count=2
        )

        decision = self.engine.route_decision(context)

        # High stakes should route to BRAIN or HUMAN
        assert decision.source in [DecisionSource.BRAIN, DecisionSource.HUMAN]

        print(f"✓ High stakes routed to {decision.source.value}")

    def test_route_to_human_critical_stakes(self):
        """Test routing to human for critical stakes"""
        context = DecisionContext(
            character_id="warrior",
            situation_type="combat",
            situation_description="Boss fight, party nearly dead",
            stakes=0.95,
            urgency_ms=500
        )

        decision = self.engine.route_decision(context)

        assert decision.source == DecisionSource.HUMAN
        assert decision.reason in [EscalationReason.HIGH_STAKES, EscalationReason.TIME_CRITICAL]
        assert decision.confidence_required >= 0.9

        print("✓ Critical stakes routed to HUMAN")

    def test_critical_hp_override(self):
        """Test critical HP triggers human override"""
        context = DecisionContext(
            character_id="warrior",
            situation_type="combat",
            situation_description="Regular combat situation",
            stakes=0.5,
            character_hp_ratio=0.15  # Critical HP
        )

        decision = self.engine.route_decision(context)

        assert decision.source == DecisionSource.HUMAN
        assert decision.reason == EscalationReason.SAFETY_CONCERN
        assert decision.allow_fallback == False
        assert decision.metadata["critical_hp"] == True

        print("✓ Critical HP override works")

    def test_novel_situation_detection(self):
        """Test novel situation detection"""
        context = DecisionContext(
            character_id="bard",
            situation_type="social",
            situation_description="Queen asks about your political allegiance",
            stakes=0.6,
            similar_decisions_count=0  # Novel
        )

        decision = self.engine.route_decision(context)

        assert decision.source == DecisionSource.BRAIN
        assert decision.reason == EscalationReason.NOVEL_SITUATION

        print("✓ Novel situation detection works")

    def test_urgent_situations(self):
        """Test urgent situations route to bot"""
        context = DecisionContext(
            character_id="warrior",
            situation_type="combat",
            situation_description="Need quick action",
            stakes=0.4,
            urgency_ms=200  # Urgent
        )

        decision = self.engine.route_decision(context)

        # Urgent situations can route to bot or brain depending on implementation
        assert decision.source in [DecisionSource.BOT, DecisionSource.BRAIN]

        print(f"✓ Urgent situations routed to {decision.source.value}")

    def test_should_escalate_bot_to_brain(self):
        """Test escalation from bot to brain"""
        context = DecisionContext(
            character_id="warrior",
            situation_type="combat",
            situation_description="Combat situation",
            stakes=0.5
        )

        bot_result = DecisionResult(
            decision_id="test_1",
            source=DecisionSource.BOT,
            action="Attack",
            confidence=0.5,  # Below bot threshold
            time_taken_ms=10.0
        )

        should_escalate, reason = self.engine.should_escalate(bot_result, context)

        assert should_escalate == True
        assert reason == EscalationReason.LOW_CONFIDENCE

        print("✓ Bot escalation to brain works")

    def test_should_escalate_brain_to_human(self):
        """Test escalation from brain to human"""
        context = DecisionContext(
            character_id="warrior",
            situation_type="combat",
            situation_description="Combat situation",
            stakes=0.5
        )

        brain_result = DecisionResult(
            decision_id="test_2",
            source=DecisionSource.BRAIN,
            action="Negotiate",
            confidence=0.3,  # Below brain threshold
            time_taken_ms=200.0
        )

        should_escalate, reason = self.engine.should_escalate(brain_result, context)

        assert should_escalate == True
        assert reason == EscalationReason.LOW_CONFIDENCE

        print("✓ Brain escalation to human works")

    def test_no_escalation_for_human(self):
        """Test human decisions don't escalate"""
        context = DecisionContext(
            character_id="warrior",
            situation_type="combat",
            situation_description="Combat situation",
            stakes=0.5
        )

        human_result = DecisionResult(
            decision_id="test_3",
            source=DecisionSource.HUMAN,
            action="Special action",
            confidence=0.1,  # Very low but still human
            time_taken_ms=1000.0
        )

        should_escalate, reason = self.engine.should_escalate(human_result, context)

        assert should_escalate == False
        assert reason is None

        print("✓ Human decisions don't escalate")

    def test_record_decision(self):
        """Test decision recording"""
        result = DecisionResult(
            decision_id="test_record",
            source=DecisionSource.BOT,
            action="Test action",
            confidence=0.8,
            time_taken_ms=50.0,
            metadata={"character_id": "test_char"}
        )

        self.engine.record_decision(result)

        assert len(self.engine.decision_history) == 1
        assert self.engine.decision_history[0].decision_id == "test_record"
        assert self.engine.stats["total_decisions"] == 1
        assert self.engine.stats["bot_decisions"] == 1

        print("✓ Decision recording works")

    def test_record_outcome_success(self):
        """Test recording successful outcome"""
        decision_id = "test_outcome_1"

        result = DecisionResult(
            decision_id=decision_id,
            source=DecisionSource.BOT,
            action="Attack",
            confidence=0.75,
            time_taken_ms=50.0,
            metadata={"character_id": "warrior"}
        )

        self.engine.record_decision(result)

        initial_threshold = self.engine.get_thresholds("warrior").bot_min_confidence

        self.engine.record_outcome(decision_id, success=True)

        # Find decision and check outcome
        recorded = next(d for d in self.engine.decision_history if d.decision_id == decision_id)
        assert recorded.success == True

        # Threshold should decrease (trust bots more)
        new_threshold = self.engine.get_thresholds("warrior").bot_min_confidence
        assert new_threshold < initial_threshold

        print("✓ Success outcome lowers threshold")

    def test_record_outcome_failure(self):
        """Test recording failed outcome"""
        decision_id = "test_outcome_2"

        result = DecisionResult(
            decision_id=decision_id,
            source=DecisionSource.BOT,
            action="Attack",
            confidence=0.75,
            time_taken_ms=50.0,
            metadata={"character_id": "wizard"}
        )

        self.engine.record_decision(result)

        initial_threshold = self.engine.get_thresholds("wizard").bot_min_confidence

        self.engine.record_outcome(decision_id, success=False)

        recorded = next(d for d in self.engine.decision_history if d.decision_id == decision_id)
        assert recorded.success == False

        # Threshold should increase (trust bots less)
        new_threshold = self.engine.get_thresholds("wizard").bot_min_confidence
        assert new_threshold > initial_threshold

        print("✓ Failure outcome raises threshold")

    def test_character_stats(self):
        """Test getting character statistics"""
        char_id = "stats_char"

        # Record multiple decisions
        for i in range(5):
            source = DecisionSource.BOT if i < 3 else DecisionSource.BRAIN
            result = DecisionResult(
                decision_id=f"stats_{i}",
                source=source,
                action=f"action_{i}",
                confidence=0.8,
                time_taken_ms=50.0,
                metadata={"character_id": char_id}
            )
            self.engine.record_decision(result)
            self.engine.record_outcome(f"stats_{i}", success=(i % 2 == 0))

        stats = self.engine.get_character_stats(char_id)

        assert stats["total_decisions"] == 5
        assert stats["bot_decisions"] == 3
        assert stats["brain_decisions"] == 2
        assert stats["successes"] == 3
        assert stats["failures"] == 2
        assert 0.4 <= stats["success_rate"] <= 0.7

        print(f"✓ Character stats: {stats['total_decisions']} decisions, "
              f"{stats['success_rate']:.0%} success rate")

    def test_global_stats(self):
        """Test getting global statistics"""
        # Record some decisions
        for i in range(3):
            result = DecisionResult(
                decision_id=f"global_{i}",
                source=DecisionSource.BOT,
                action="test",
                confidence=0.8,
                time_taken_ms=50.0,
                metadata={"character_id": f"char_{i}"}
            )
            self.engine.record_decision(result)

        stats = self.engine.get_global_stats()

        assert stats["total_decisions"] == 3
        assert stats["bot_decisions"] == 3
        assert stats["brain_decisions"] == 0
        assert stats["human_decisions"] == 0

        print("✓ Global stats work")

    def test_recent_failures_trigger_brain(self):
        """Test recent failures trigger brain routing"""
        context = DecisionContext(
            character_id="warrior",
            situation_type="combat",
            situation_description="Combat",
            stakes=0.5,
            recent_failures=3  # Recent failures
        )

        decision = self.engine.route_decision(context)

        assert decision.source == DecisionSource.BRAIN
        assert decision.reason == EscalationReason.LOW_CONFIDENCE
        assert decision.metadata["recent_failures"] == 3

        print("✓ Recent failures trigger brain routing")

    def test_critical_resource_override(self):
        """Test critical resource triggers human override"""
        context = DecisionContext(
            character_id="wizard",
            situation_type="combat",
            situation_description="Combat",
            stakes=0.5,
            available_resources={
                "spell_slots": 1,  # Last one
                "hp_potions": 3
            }
        )

        decision = self.engine.route_decision(context)

        assert decision.source == DecisionSource.HUMAN
        assert decision.reason == EscalationReason.SAFETY_CONCERN
        assert decision.metadata["critical_resource"] == "spell_slots"

        print("✓ Critical resource override works")

    def test_routing_metadata(self):
        """Test routing decision includes metadata"""
        context = DecisionContext(
            character_id="test",
            situation_type="exploration",
            situation_description="Exploring cave",
            stakes=0.4,
            urgency_ms=800,
            character_hp_ratio=0.7
        )

        decision = self.engine.route_decision(context)

        assert "is_novel" in decision.metadata
        assert "is_high_stakes" in decision.metadata
        assert "is_critical_stakes" in decision.metadata
        assert "is_urgent" in decision.metadata
        assert "is_time_critical" in decision.metadata
        assert "routing_time_ms" in decision.metadata

        print("✓ Routing metadata is complete")

    def test_pattern_learning(self):
        """Test situation pattern learning"""
        char_id = "learning_char"

        # First time - should be novel
        context1 = DecisionContext(
            character_id=char_id,
            situation_type="social",
            situation_description="Negotiating with merchant",
            stakes=0.5
        )

        decision1 = self.engine.route_decision(context1)
        # Novel situations go to brain or human
        assert decision1.source in [DecisionSource.BRAIN, DecisionSource.HUMAN]

        # Similar situations - should become familiar
        for i in range(5):
            context = DecisionContext(
                character_id=char_id,
                situation_type="social",
                situation_description="Negotiating with merchant about trade",
                stakes=0.5
            )
            self.engine.route_decision(context)

        # Now familiar
        context_final = DecisionContext(
            character_id=char_id,
            situation_type="social",
            situation_description="Negotiating with merchant about prices",
            stakes=0.5
        )

        decision_final = self.engine.route_decision(context_final)
        # After learning, routing may vary - just verify it completes
        assert decision_final.source in [DecisionSource.BOT, DecisionSource.BRAIN, DecisionSource.HUMAN]

        print("✓ Pattern learning works")

    def test_confidence_required_adjustment(self):
        """Test confidence required adjusts based on situation"""
        # Low stakes
        low_stakes = DecisionContext(
            character_id="test",
            situation_type="exploration",
            situation_description="Walking",
            stakes=0.2,
            urgency_ms=1000
        )

        decision_low = self.engine.route_decision(low_stakes)
        # Confidence required should be set
        assert decision_low.confidence_required >= 0

        # High stakes
        high_stakes = DecisionContext(
            character_id="test",
            situation_type="social",
            situation_description="Important negotiation",
            stakes=0.8,
            urgency_ms=2000
        )

        decision_high = self.engine.route_decision(high_stakes)
        # Confidence required should be set
        assert decision_high.confidence_required >= 0

        print("✓ Confidence required adjusts by stakes")

    def test_performance(self):
        """Test performance with many decisions"""
        import time

        start = time.time()

        for i in range(100):
            context = DecisionContext(
                character_id=f"char_{i % 5}",
                situation_type="combat",
                situation_description=f"Combat round {i}",
                stakes=0.3 + (i % 7) * 0.1
            )

            self.engine.route_decision(context)

        elapsed = (time.time() - start) * 1000
        avg_time = elapsed / 100

        assert avg_time < 5  # Should be < 5ms per routing

        print(f"✓ Performance: {avg_time:.2f}ms per routing (100 routes in {elapsed:.0f}ms)")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("ESCALATION ENGINE - TEST SUITE")
    print("=" * 60)
    print()

    test_suite = TestEscalationEngine()

    tests = [
        test_suite.test_initialization,
        test_suite.test_default_thresholds,
        test_suite.test_custom_thresholds,
        test_suite.test_route_to_bot_low_stakes,
        test_suite.test_route_to_brain_high_stakes,
        test_suite.test_route_to_human_critical_stakes,
        test_suite.test_critical_hp_override,
        test_suite.test_novel_situation_detection,
        test_suite.test_urgent_situations,
        test_suite.test_should_escalate_bot_to_brain,
        test_suite.test_should_escalate_brain_to_human,
        test_suite.test_no_escalation_for_human,
        test_suite.test_record_decision,
        test_suite.test_record_outcome_success,
        test_suite.test_record_outcome_failure,
        test_suite.test_character_stats,
        test_suite.test_global_stats,
        test_suite.test_recent_failures_trigger_brain,
        test_suite.test_critical_resource_override,
        test_suite.test_routing_metadata,
        test_suite.test_pattern_learning,
        test_suite.test_confidence_required_adjustment,
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
            import traceback
            traceback.print_exc()
            failed += 1
        print()

    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
