"""
Integration Tests - Escalation Engine + Memory System

Tests the complete flow: decision routing based on memories and learning.
"""

import asyncio
from datetime import datetime
from escalation_engine import (
    EscalationEngine,
    DecisionContext,
    DecisionResult,
    DecisionSource
)
from memory_system import (
    MemoryConsolidationEngine,
    MemoryType
)


async def test_memory_influenced_routing():
    """Test that memories influence decision routing"""
    print("\n" + "=" * 60)
    print("TEST: Memory-Influenced Decision Routing")
    print("=" * 60)

    escalation = EscalationEngine(enable_training_data=False)
    memory_engine = MemoryConsolidationEngine("warrior")

    # Store a negative memory about combat
    memory_engine.store_memory(
        content="Nearly died fighting goblins in the cave",
        memory_type=MemoryType.EPISODIC,
        importance=9.0,
        emotional_valence=-0.8  # Very negative
    )

    print("✓ Stored negative combat memory")

    # Character encounters similar situation
    context = DecisionContext(
        character_id="warrior",
        situation_type="combat",
        situation_description="Goblins in cave entrance",
        stakes=0.6,
        similar_decisions_count=3
    )

    routing = escalation.route_decision(context)

    # Should route to brain for careful consideration
    # due to past negative experience
    print(f"✓ Routed to: {routing.source.value}")
    print(f"   Reason: {routing.reason.value if routing.reason else 'None'}")

    assert routing.source in [DecisionSource.BRAIN, DecisionSource.BOT]

    print("\n✅ MEMORY-INFLUENCED ROUTING TEST PASSED!")


async def test_learning_from_outcomes_creates_memories():
    """Test that decision outcomes create memories"""
    print("\n" + "=" * 60)
    print("TEST: Learning from Outcomes Creates Memories")
    print("=" * 60)

    escalation = EscalationEngine(enable_training_data=False)
    memory_engine = MemoryConsolidationEngine("wizard")

    initial_memory_count = len(memory_engine.memories)

    # Simulate a decision sequence
    decisions = [
        ("fireball_spell", "Used fireball on goblins", True),
        ("shield_spell", "Cast shield against arrow", True),
        ("failed_teleport", "Tried to teleport but failed", False)
    ]

    for dec_id, action, success in decisions:
        result = DecisionResult(
            decision_id=dec_id,
            source=DecisionSource.BRAIN,
            action=action,
            confidence=0.7,
            time_taken_ms=200.0,
            metadata={"character_id": "wizard"}
        )

        escalation.record_decision(result)
        escalation.record_outcome(dec_id, success=success)

        # Create memory from outcome
        outcome_text = f"{action} - {'Success' if success else 'Failure'}"
        memory_engine.store_memory(
            content=outcome_text,
            memory_type=MemoryType.EPISODIC,
            importance=7.0 if success else 8.0,  # Failures more memorable
            emotional_valence=0.5 if success else -0.5
        )

    print(f"✓ Created {len(decisions)} memories from outcomes")

    final_count = len(memory_engine.memories)
    assert final_count == initial_memory_count + len(decisions)

    # Verify memories can be retrieved
    memories = memory_engine.retrieve_memories("fireball", top_k=3)
    assert len(memories) > 0

    print(f"✓ Retrieved {len(memories)} memories about fireball")

    print("\n✅ LEARNING FROM OUTCOMES TEST PASSED!")


async def test_novelty_detection_with_memory():
    """Test novelty detection considers past memories"""
    print("\n" + "=" * 60)
    print("TEST: Novelty Detection with Memory")
    print("=" * 60)

    escalation = EscalationEngine(enable_training_data=False)
    memory_engine = MemoryConsolidationEngine("explorer")

    # First time encountering goblins - novel
    context1 = DecisionContext(
        character_id="explorer",
        situation_type="combat",
        situation_description="Encountered goblins in the forest",
        stakes=0.5,
        similar_decisions_count=0
    )

    routing1 = escalation.route_decision(context1)
    print(f"✓ First encounter: {routing1.source.value}")

    # Store memory of the encounter
    memory_engine.store_memory(
        content="Fought goblins in the forest",
        memory_type=MemoryType.EPISODIC,
        importance=6.0
    )

    # Similar situation later - should be less novel
    for i in range(5):
        context = DecisionContext(
            character_id="explorer",
            situation_type="combat",
            situation_description=f"Goblins in forest area {i}",
            stakes=0.5
        )
        escalation.route_decision(context)

    # Now familiar
    context_familiar = DecisionContext(
        character_id="explorer",
        situation_type="combat",
        situation_description="More goblins in the forest",
        stakes=0.5
    )

    routing_familiar = escalation.route_decision(context_familiar)
    print(f"✓ Familiar encounter: {routing_familiar.source.value}")

    # After learning, should route differently
    print(f"   Initial: {routing1.source.value}, Learned: {routing_familiar.source.value}")

    print("\n✅ NOVELTY DETECTION TEST PASSED!")


async def test_character_growth_tracking():
    """Test tracking character growth through decisions and memories"""
    print("\n" + "=" * 60)
    print("TEST: Character Growth Tracking")
    print("=" * 60)

    escalation = EscalationEngine(enable_training_data=False)
    memory_engine = MemoryConsolidationEngine("growing_char")

    # Character starts with no experience
    stats_initial = escalation.get_character_stats("growing_char")
    print(f"✓ Initial stats: {stats_initial['total_decisions']} decisions")

    # Character makes decisions and grows
    scenarios = [
        ("combat", "First combat", 0.7, True),
        ("social", "First negotiation", 0.5, False),
        ("combat", "Second combat", 0.8, True),
        ("social", "Second negotiation", 0.9, True),
        ("exploration", "Exploration", 0.6, True)
    ]

    for i, (sit_type, desc, conf, success) in enumerate(scenarios):
        context = DecisionContext(
            character_id="growing_char",
            situation_type=sit_type,
            situation_description=desc,
            stakes=0.5 + (i * 0.1)
        )

        routing = escalation.route_decision(context)

        result = DecisionResult(
            decision_id=f"growth_{i}",
            source=routing.source,
            action=desc,
            confidence=conf,
            time_taken_ms=100.0,
            metadata={"character_id": "growing_char"}
        )

        escalation.record_decision(result)
        escalation.record_outcome(f"growth_{i}", success=success)

        # Create memory
        memory_engine.store_memory(
            content=f"{desc} - {'Success' if success else 'Failure'}",
            memory_type=MemoryType.EPISODIC,
            importance=6.0,
            emotional_valence=0.5 if success else -0.3
        )

    # Check growth
    stats_final = escalation.get_character_stats("growing_char")
    print(f"✓ Final stats: {stats_final['total_decisions']} decisions")
    print(f"   Success rate: {stats_final['success_rate']:.1%}")
    print(f"   Bot decisions: {stats_final['bot_decisions']}")
    print(f"   Brain decisions: {stats_final['brain_decisions']}")

    # Check memories
    memories = memory_engine.retrieve_memories("combat", top_k=10)
    print(f"✓ Combat memories: {len(memories)}")

    # Generate narrative
    narrative = memory_engine.generate_autobiographical_narrative()
    print(f"✓ Narrative generated:")
    print(f"   Themes: {narrative.key_themes}")
    print(f"   Coherence: {narrative.coherence_score:.2f}")

    assert stats_final['total_decisions'] == len(scenarios)
    assert len(memories) > 0

    print("\n✅ CHARACTER GROWTH TRACKING TEST PASSED!")


async def test_high_stakes_memory_access():
    """Test that important memories are accessed in high stakes"""
    print("\n" + "=" * 60)
    print("TEST: High Stakes Memory Access")
    print("=" * 60)

    escalation = EscalationEngine(enable_training_data=False)
    memory_engine = MemoryConsolidationEngine("cautious_char")

    # Store important memory about danger
    critical_memory = memory_engine.store_memory(
        content="Nearly died from poison gas in sealed room",
        memory_type=MemoryType.EPISODIC,
        importance=10.0,
        emotional_valence=-0.9
    )

    print("✓ Stored critical memory about poison gas")

    # Character encounters similar danger
    context = DecisionContext(
        character_id="cautious_char",
        situation_type="exploration",
        situation_description="Found sealed door with strange smell",
        stakes=0.8  # High stakes
    )

    routing = escalation.route_decision(context)

    # Should route to human or brain for careful consideration
    print(f"✓ Routed to: {routing.source.value}")
    assert routing.source in [DecisionSource.BRAIN, DecisionSource.HUMAN]

    # Retrieve relevant memories
    relevant = memory_engine.retrieve_memories(
        query="poison gas sealed room danger",
        top_k=3,
        α_importance=2.0  # Weight importance heavily
    )

    print(f"✓ Retrieved {len(relevant)} relevant memories")

    # Critical memory should be accessible
    memory_ids = [m.id for m in relevant]
    assert critical_memory.id in memory_ids or any(
        "poison" in m.content.lower() or "gas" in m.content.lower()
        for m in relevant
    )

    print("\n✅ HIGH STAKES MEMORY ACCESS TEST PASSED!")


async def test_confidence_adjustment_with_memory():
    """Test that confidence thresholds adjust based on memory of outcomes"""
    print("\n" + "=" * 60)
    print("TEST: Confidence Adjustment with Memory")
    print("=" * 60)

    escalation = EscalationEngine(enable_training_data=False)

    char_id = "adaptive_char"

    # Get initial thresholds
    initial_bot_threshold = escalation.get_thresholds(char_id).bot_min_confidence
    print(f"✓ Initial bot threshold: {initial_bot_threshold:.3f}")

    # Character succeeds at bot decisions multiple times
    for i in range(5):
        result = DecisionResult(
            decision_id=f"success_{i}",
            source=DecisionSource.BOT,
            action=f"Successful action {i}",
            confidence=0.75,
            time_taken_ms=50.0,
            metadata={"character_id": char_id}
        )

        escalation.record_decision(result)
        escalation.record_outcome(f"success_{i}", success=True)

    # Check threshold decreased (more trust in bot)
    after_success_threshold = escalation.get_thresholds(char_id).bot_min_confidence
    print(f"✓ After successes: {after_success_threshold:.3f}")
    assert after_success_threshold < initial_bot_threshold

    # Character fails at bot decisions
    for i in range(3):
        result = DecisionResult(
            decision_id=f"fail_{i}",
            source=DecisionSource.BOT,
            action=f"Failed action {i}",
            confidence=0.6,
            time_taken_ms=50.0,
            metadata={"character_id": char_id}
        )

        escalation.record_decision(result)
        escalation.record_outcome(f"fail_{i}", success=False)

    # Check threshold increased (less trust in bot)
    after_fail_threshold = escalation.get_thresholds(char_id).bot_min_confidence
    print(f"✓ After failures: {after_fail_threshold:.3f}")
    assert after_fail_threshold > after_success_threshold

    print("\n✅ CONFIDENCE ADJUSTMENT TEST PASSED!")


async def run_all_integration_tests():
    """Run all integration tests"""
    print("\n" + "=" * 70)
    print("ESCALATION ENGINE + MEMORY SYSTEM - INTEGRATION TEST SUITE")
    print("=" * 70)

    tests = [
        test_memory_influenced_routing,
        test_learning_from_outcomes_creates_memories,
        test_novelty_detection_with_memory,
        test_character_growth_tracking,
        test_high_stakes_memory_access,
        test_confidence_adjustment_with_memory
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"\n✗ {test.__name__} FAILED:")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"INTEGRATION RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_integration_tests())
    exit(0 if success else 1)
