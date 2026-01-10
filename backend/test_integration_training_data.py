"""
Integration Tests - Escalation Engine + Training Data Collector

Tests the complete flow: decision routing → logging → outcome tracking
"""

import asyncio
import uuid
from escalation_engine import (
    EscalationEngine,
    DecisionContext,
    DecisionResult,
    DecisionSource,
    EscalationReason
)
from training_data_collector import TrainingDataCollector


async def test_integration_basic():
    """Test basic integration between escalation and training data"""
    print("\n" + "=" * 60)
    print("TEST: Basic Integration")
    print("=" * 60)
    
    # Create engines
    escalation = EscalationEngine(enable_training_data=True)
    
    if not escalation.training_data_collector:
        print("⚠️  Training data collector not initialized (module not available)")
        return
    
    # Start a session
    session_id = escalation.training_data_collector.start_session(
        session_notes="Integration test session"
    )
    print(f"✓ Started session: {session_id}")
    
    # Create a decision context
    context = DecisionContext(
        character_id="thorin",
        situation_type="combat",
        situation_description="Goblin attacking party",
        stakes=0.6,
        urgency_ms=1000
    )
    
    # Route the decision
    routing = escalation.route_decision(context)
    print(f"✓ Routed decision to: {routing.source.value}")
    
    # Simulate a decision being made
    decision_id = f"dec_{uuid.uuid4().hex[:8]}"
    result = DecisionResult(
        decision_id=decision_id,
        source=routing.source,
        action="attack_goblin",
        confidence=0.85,
        time_taken_ms=45.5,
        metadata={
            "character_id": "thorin",
            "decision_type": "combat_action",
            "situation_context": {
                "game_state": {
                    "turn": 5,
                    "combat_active": True,
                    "location": "Cave entrance"
                },
                "character_state": {
                    "hp": 35,
                    "max_hp": 50,
                    "position": {"x": 10, "y": 5}
                }
            }
        }
    )
    
    # Record the decision (should also log to training data)
    escalation.record_decision(result)
    print(f"✓ Recorded decision: {decision_id}")
    
    # Record outcome
    outcome_details = {
        "immediate": "Hit goblin for 15 damage",
        "delayed": "Goblin defeated, party safe",
        "rewards": {"xp": 50}
    }
    escalation.record_outcome(decision_id, success=True, outcome_details=outcome_details)
    print(f"✓ Recorded outcome: success")
    
    # Verify in training data
    training_decisions = escalation.training_data_collector.get_decisions_for_character("thorin")
    assert len(training_decisions) > 0, "No training decisions found!"
    
    latest = training_decisions[0]
    assert latest['decision_data']['action'] == "attack_goblin"
    assert latest['success'] == 1
    assert latest['outcome_data']['immediate'] == "Hit goblin for 15 damage"
    
    print(f"✓ Verified in training database")
    
    # End session
    escalation.training_data_collector.end_session()
    print(f"✓ Ended session")
    
    print("\n✅ INTEGRATION TEST PASSED!")


async def test_integration_escalation_flow():
    """Test escalation flow with training data"""
    print("\n" + "=" * 60)
    print("TEST: Escalation Flow with Training Data")
    print("=" * 60)
    
    escalation = EscalationEngine(enable_training_data=True)
    
    if not escalation.training_data_collector:
        print("⚠️  Training data collector not initialized")
        return
    
    session_id = escalation.training_data_collector.start_session()
    print(f"✓ Started session: {session_id}")
    
    # Test 1: Low stakes → Bot decision
    context1 = DecisionContext(
        character_id="thorin",
        situation_type="exploration",
        situation_description="Walking down a corridor",
        stakes=0.2,
        urgency_ms=2000
    )
    
    routing1 = escalation.route_decision(context1)
    print(f"\n1. Low stakes exploration:")
    print(f"   Routed to: {routing1.source.value}")
    assert routing1.source == DecisionSource.BOT
    
    decision1 = DecisionResult(
        decision_id=f"dec_{uuid.uuid4().hex[:8]}",
        source=routing1.source,
        action="continue_walking",
        confidence=0.9,
        time_taken_ms=5.0,
        metadata={
            "character_id": "thorin",
            "decision_type": "exploration",
            "situation_context": {"stakes": context1.stakes}
        }
    )
    
    escalation.record_decision(decision1)
    escalation.record_outcome(decision1.decision_id, success=True)
    print(f"   ✓ Logged to training data")
    
    # Test 2: High stakes → Brain decision
    context2 = DecisionContext(
        character_id="thorin",
        situation_type="social",
        situation_description="Negotiating with hostile NPC",
        stakes=0.8,
        urgency_ms=5000
    )
    
    routing2 = escalation.route_decision(context2)
    print(f"\n2. High stakes negotiation:")
    print(f"   Routed to: {routing2.source.value}")
    assert routing2.source == DecisionSource.BRAIN
    
    decision2 = DecisionResult(
        decision_id=f"dec_{uuid.uuid4().hex[:8]}",
        source=routing2.source,
        action="offer_compromise",
        confidence=0.75,
        time_taken_ms=450.0,
        metadata={
            "character_id": "thorin",
            "decision_type": "social",
            "situation_context": {"stakes": context2.stakes}
        }
    )
    
    escalation.record_decision(decision2)
    escalation.record_outcome(decision2.decision_id, success=True)
    print(f"   ✓ Logged to training data")
    
    # Test 3: Critical stakes → Human decision
    context3 = DecisionContext(
        character_id="thorin",
        situation_type="combat",
        situation_description="Life or death combat",
        stakes=0.95,
        urgency_ms=500,
        character_hp_ratio=0.15  # Critical HP
    )
    
    routing3 = escalation.route_decision(context3)
    print(f"\n3. Critical life-or-death:")
    print(f"   Routed to: {routing3.source.value}")
    assert routing3.source == DecisionSource.HUMAN
    
    decision3 = DecisionResult(
        decision_id=f"dec_{uuid.uuid4().hex[:8]}",
        source=routing3.source,
        action="use_healing_potion",
        confidence=0.95,
        time_taken_ms=1200.0,
        metadata={
            "character_id": "thorin",
            "decision_type": "combat_action",
            "situation_context": {"stakes": context3.stakes, "hp_critical": True}
        }
    )
    
    escalation.record_decision(decision3)
    escalation.record_outcome(decision3.decision_id, success=True)
    print(f"   ✓ Logged to training data")
    
    # Verify all logged
    training_decisions = escalation.training_data_collector.get_decisions_for_character("thorin")
    print(f"\n✓ Total decisions logged: {len(training_decisions)}")
    
    # Check by source
    bot_count = sum(1 for d in training_decisions if d['decision_source'] == 'bot')
    brain_count = sum(1 for d in training_decisions if d['decision_source'] == 'brain')
    human_count = sum(1 for d in training_decisions if d['decision_source'] == 'human')
    
    print(f"   Bot decisions: {bot_count}")
    print(f"   Brain decisions: {brain_count}")
    print(f"   Human decisions: {human_count}")
    
    assert bot_count == 1
    assert brain_count == 1
    assert human_count == 1
    
    # Get statistics
    stats = escalation.training_data_collector.get_statistics(character_id="thorin")
    print(f"\n✓ Statistics:")
    print(f"   Total: {stats['total_decisions']}")
    print(f"   Success rate: {stats['success_rate']:.1%}")
    
    escalation.training_data_collector.end_session()
    
    print("\n✅ ESCALATION FLOW TEST PASSED!")


async def test_integration_multi_character():
    """Test with multiple characters"""
    print("\n" + "=" * 60)
    print("TEST: Multi-Character Integration")
    print("=" * 60)
    
    escalation = EscalationEngine(enable_training_data=True)
    
    if not escalation.training_data_collector:
        print("⚠️  Training data collector not initialized")
        return
    
    session_id = escalation.training_data_collector.start_session()
    
    characters = ["thorin", "elara", "gandor"]
    
    # Each character makes decisions
    for char in characters:
        for turn in range(2):
            context = DecisionContext(
                character_id=char,
                situation_type="combat",
                situation_description=f"{char} in combat (turn {turn})",
                stakes=0.5
            )
            
            routing = escalation.route_decision(context)
            
            decision = DecisionResult(
                decision_id=f"dec_{uuid.uuid4().hex[:8]}",
                source=routing.source,
                action=f"{char}_action_{turn}",
                confidence=0.8,
                time_taken_ms=50.0,
                metadata={
                    "character_id": char,
                    "decision_type": "combat_action",
                    "situation_context": {"turn": turn}
                }
            )
            
            escalation.record_decision(decision)
            escalation.record_outcome(decision.decision_id, success=True)
    
    # Verify each character
    for char in characters:
        decisions = escalation.training_data_collector.get_decisions_for_character(char)
        print(f"✓ {char}: {len(decisions)} decisions logged")
        assert len(decisions) == 2
    
    # Check total
    stats = escalation.training_data_collector.get_statistics()
    print(f"✓ Total decisions: {stats['total_decisions']}")
    assert stats['total_decisions'] == 6
    
    escalation.training_data_collector.end_session()
    
    print("\n✅ MULTI-CHARACTER TEST PASSED!")


async def test_integration_privacy():
    """Test privacy settings integration"""
    print("\n" + "=" * 60)
    print("TEST: Privacy Settings Integration")
    print("=" * 60)
    
    escalation = EscalationEngine(enable_training_data=True)
    
    if not escalation.training_data_collector:
        print("⚠️  Training data collector not initialized")
        return
    
    # Disable bot decisions for thorin
    settings = escalation.training_data_collector.get_character_settings("thorin")
    settings.collect_bot_decisions = False
    escalation.training_data_collector.update_character_settings(settings)
    print("✓ Disabled bot decision collection for thorin")
    
    session_id = escalation.training_data_collector.start_session()
    
    # Make bot decision
    context = DecisionContext(
        character_id="thorin",
        situation_type="exploration",
        situation_description="Walking",
        stakes=0.2
    )
    
    routing = escalation.route_decision(context)
    
    decision = DecisionResult(
        decision_id=f"dec_{uuid.uuid4().hex[:8]}",
        source=DecisionSource.BOT,
        action="walk",
        confidence=0.9,
        time_taken_ms=5.0,
        metadata={
            "character_id": "thorin",
            "decision_type": "exploration",
            "situation_context": {}
        }
    )
    
    escalation.record_decision(decision)
    
    # Verify NOT logged
    decisions = escalation.training_data_collector.get_decisions_for_character("thorin")
    print(f"✓ Bot decisions logged: {len(decisions)} (should be 0)")
    assert len(decisions) == 0
    
    # Now make brain decision (should be logged)
    decision2 = DecisionResult(
        decision_id=f"dec_{uuid.uuid4().hex[:8]}",
        source=DecisionSource.BRAIN,
        action="think",
        confidence=0.8,
        time_taken_ms=300.0,
        metadata={
            "character_id": "thorin",
            "decision_type": "social",
            "situation_context": {}
        }
    )
    
    escalation.record_decision(decision2)
    
    decisions = escalation.training_data_collector.get_decisions_for_character("thorin")
    print(f"✓ Brain decisions logged: {len(decisions)} (should be 1)")
    assert len(decisions) == 1
    assert decisions[0]['decision_source'] == 'brain'
    
    escalation.training_data_collector.end_session()
    
    print("\n✅ PRIVACY SETTINGS TEST PASSED!")


async def run_all_integration_tests():
    """Run all integration tests"""
    print("\n" + "=" * 70)
    print("ESCALATION ENGINE + TRAINING DATA - INTEGRATION TEST SUITE")
    print("=" * 70)
    
    tests = [
        test_integration_basic,
        test_integration_escalation_flow,
        test_integration_multi_character,
        test_integration_privacy
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
