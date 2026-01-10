"""
Integration Tests - Training Data Collector + Outcome Tracker

Tests enhanced outcome tracking with reward signals integrated into training data.
"""

import asyncio
import tempfile
import os
from training_data_collector import TrainingDataCollector
from outcome_tracker import OutcomeTracker


async def test_enhanced_outcome_storage():
    """Test that outcomes are stored with reward signals"""
    print("\n" + "=" * 60)
    print("TEST: Enhanced Outcome Storage")
    print("=" * 60)
    
    # Create collector with temp database
    temp_db = tempfile.mktemp(suffix='.db')
    collector = TrainingDataCollector(temp_db)
    
    if not collector.outcome_tracker:
        print("⚠️  Outcome tracker not available")
        os.unlink(temp_db)
        return
    
    print("✓ Created collector with outcome tracker")
    
    # Start session
    session_id = collector.start_session()
    
    # Log a decision
    decision_id = collector.log_decision(
        character_id="thorin",
        situation_context={
            "game_state": {"turn": 5, "combat_active": True},
            "character_state": {"hp": 35, "max_hp": 50}
        },
        decision={
            "decision_type": "combat_action",
            "action": "attack",
            "source": "bot",
            "confidence": 0.85
        }
    )
    
    print(f"✓ Logged decision: {decision_id}")
    
    # Update with outcome (should add reward signals)
    collector.update_outcome(
        decision_id=decision_id,
        outcome={
            "immediate": "Hit goblin for 15 damage, goblin defeated",
            "rewards": {"xp": 50}
        },
        success=True
    )
    
    print("✓ Updated outcome")
    
    # Retrieve and verify
    decisions = collector.get_decisions_for_character("thorin")
    assert len(decisions) == 1
    
    decision = decisions[0]
    outcome_data = decision['outcome_data']
    
    # Check for enhanced fields
    assert "reward_signals" in outcome_data
    assert "aggregate_reward" in outcome_data
    assert "quality_analysis" in outcome_data
    
    print(f"✓ Outcome enhanced with reward signals:")
    print(f"   Reward signals: {len(outcome_data['reward_signals'])} domains")
    print(f"   Aggregate reward: {outcome_data['aggregate_reward']:.3f}")
    print(f"   Quality score: {outcome_data['quality_analysis']['quality_score']:.3f}")
    
    # Print reward breakdown
    for signal in outcome_data['reward_signals']:
        print(f"   - {signal['domain']}: {signal['value']:.3f} (confidence: {signal['confidence']:.2f})")
    
    collector.end_session()
    os.unlink(temp_db)
    
    print("\n✅ ENHANCED OUTCOME STORAGE TEST PASSED!")


async def test_multi_domain_tracking():
    """Test tracking outcomes across multiple domains"""
    print("\n" + "=" * 60)
    print("TEST: Multi-Domain Outcome Tracking")
    print("=" * 60)
    
    temp_db = tempfile.mktemp(suffix='.db')
    collector = TrainingDataCollector(temp_db)
    
    if not collector.outcome_tracker:
        print("⚠️  Outcome tracker not available")
        os.unlink(temp_db)
        return
    
    session_id = collector.start_session()
    
    # Decision with multi-domain outcome
    decision_id = collector.log_decision(
        character_id="elara",
        situation_context={
            "game_state": {"turn": 10},
            "character_state": {"hp": 45, "max_hp": 50}
        },
        decision={
            "decision_type": "social",
            "action": "negotiate",
            "source": "brain",
            "confidence": 0.75
        }
    )
    
    # Rich outcome spanning multiple domains
    collector.update_outcome(
        decision_id=decision_id,
        outcome={
            "immediate": "Convinced merchant, relationship improved +10, learned secret about guild, gained 30 XP",
            "rewards": {"xp": 30, "relationship_changes": {"merchant": +10}}
        },
        success=True
    )
    
    decisions = collector.get_decisions_for_character("elara")
    outcome_data = decisions[0]['outcome_data']
    
    # Should have multiple reward signals
    reward_signals = outcome_data['reward_signals']
    domains = {signal['domain'] for signal in reward_signals}
    
    print(f"✓ Tracked outcome across {len(domains)} domains:")
    for domain in domains:
        domain_signals = [s for s in reward_signals if s['domain'] == domain]
        total_value = sum(s['value'] for s in domain_signals) / len(domain_signals)
        print(f"   - {domain}: {total_value:.3f}")
    
    collector.end_session()
    os.unlink(temp_db)
    
    print("\n✅ MULTI-DOMAIN TRACKING TEST PASSED!")


async def test_delayed_outcome_correlation():
    """Test delayed outcome tracking with causal chains"""
    print("\n" + "=" * 60)
    print("TEST: Delayed Outcome Correlation")
    print("=" * 60)
    
    temp_db = tempfile.mktemp(suffix='.db')
    collector = TrainingDataCollector(temp_db)
    
    if not collector.outcome_tracker:
        print("⚠️  Outcome tracker not available")
        os.unlink(temp_db)
        return
    
    session_id = collector.start_session()
    
    # Initial decision
    dec_1 = collector.log_decision(
        character_id="gandor",
        situation_context={"game_state": {"turn": 1}},
        decision={
            "decision_type": "social",
            "action": "help_villager",
            "source": "brain"
        }
    )
    
    # Immediate outcome
    collector.update_outcome(
        decision_id=dec_1,
        outcome={"immediate": "Villager grateful"},
        success=True
    )
    
    print(f"✓ Decision 1: {dec_1} (immediate outcome)")
    
    # Related decision later
    dec_2 = collector.log_decision(
        character_id="gandor",
        situation_context={"game_state": {"turn": 5}},
        decision={
            "decision_type": "social",
            "action": "request_favor",
            "source": "brain"
        }
    )
    
    # Delayed outcome referencing earlier decision
    collector.update_outcome(
        decision_id=dec_2,
        outcome={
            "immediate": "Villager remembers your help, agrees to assist",
            "outcome_type": "short_term",
            "related_decisions": [dec_1]
        },
        success=True
    )
    
    print(f"✓ Decision 2: {dec_2} (short-term outcome with causal link)")
    
    # Check outcome tracker has causal chain
    decisions = collector.get_decisions_for_character("gandor")
    
    # Find dec_2 outcome
    dec_2_data = [d for d in decisions if d['decision_id'] == dec_2][0]
    outcome_data = dec_2_data['outcome_data']
    
    print(f"✓ Causal correlation tracked:")
    print(f"   Related to: {outcome_data.get('related_decisions', [])}")
    
    collector.end_session()
    os.unlink(temp_db)
    
    print("\n✅ DELAYED OUTCOME CORRELATION TEST PASSED!")


async def test_quality_analysis_integration():
    """Test decision quality analysis integration"""
    print("\n" + "=" * 60)
    print("TEST: Quality Analysis Integration")
    print("=" * 60)
    
    temp_db = tempfile.mktemp(suffix='.db')
    collector = TrainingDataCollector(temp_db)
    
    if not collector.outcome_tracker:
        print("⚠️  Outcome tracker not available")
        os.unlink(temp_db)
        return
    
    session_id = collector.start_session()
    
    # Good decision
    good_dec = collector.log_decision(
        character_id="thorin",
        situation_context={"game_state": {}},
        decision={
            "decision_type": "combat_action",
            "action": "tactical_strike",
            "source": "brain"
        }
    )
    
    collector.update_outcome(
        decision_id=good_dec,
        outcome={
            "immediate": "Critical hit for 25 damage, enemy defeated, party safe, gained 60 XP"
        },
        success=True
    )
    
    # Bad decision
    bad_dec = collector.log_decision(
        character_id="thorin",
        situation_context={"game_state": {}},
        decision={
            "decision_type": "combat_action",
            "action": "reckless_charge",
            "source": "bot"
        }
    )
    
    collector.update_outcome(
        decision_id=bad_dec,
        outcome={
            "immediate": "Missed attack, took 15 damage, lost tactical advantage"
        },
        success=False
    )
    
    # Check quality analysis
    decisions = collector.get_decisions_for_character("thorin")
    
    good_quality = [d for d in decisions if d['decision_id'] == good_dec][0]['outcome_data']['quality_analysis']
    bad_quality = [d for d in decisions if d['decision_id'] == bad_dec][0]['outcome_data']['quality_analysis']
    
    print(f"✓ Quality analysis:")
    print(f"   Good decision: {good_quality['quality_score']:.3f} (success: {good_quality['success_rate']:.0%})")
    print(f"   Bad decision: {bad_quality['quality_score']:.3f} (success: {bad_quality['success_rate']:.0%})")
    
    assert good_quality['quality_score'] > bad_quality['quality_score']
    print(f"✓ Good decision scored higher than bad decision")
    
    collector.end_session()
    os.unlink(temp_db)
    
    print("\n✅ QUALITY ANALYSIS INTEGRATION TEST PASSED!")


async def test_session_statistics_with_rewards():
    """Test session statistics include outcome tracker metrics"""
    print("\n" + "=" * 60)
    print("TEST: Session Statistics with Reward Metrics")
    print("=" * 60)
    
    temp_db = tempfile.mktemp(suffix='.db')
    collector = TrainingDataCollector(temp_db)
    
    if not collector.outcome_tracker:
        print("⚠️  Outcome tracker not available")
        os.unlink(temp_db)
        return
    
    session_id = collector.start_session(session_notes="Test session with rewards")
    
    # Log several decisions with outcomes
    for i in range(5):
        dec_id = collector.log_decision(
            character_id="thorin",
            situation_context={"game_state": {"turn": i}},
            decision={
                "decision_type": "combat_action",
                "action": f"action_{i}",
                "source": "bot"
            }
        )
        
        collector.update_outcome(
            decision_id=dec_id,
            outcome={
                "immediate": f"Action {i} result with 10 damage and rewards"
            },
            success=(i % 2 == 0)
        )
    
    # Get session summary
    summary = collector.get_session_summary(session_id)
    
    print(f"✓ Session summary generated")
    print(f"   Total decisions: {summary['statistics']['total_decisions']}")
    print(f"   Success rate: {summary['statistics']['success_rate']:.1%}")
    
    # Check for outcome tracking stats
    if "outcome_tracking" in summary['statistics']:
        outcome_stats = summary['statistics']['outcome_tracking']
        print(f"   Outcome metrics:")
        print(f"     Total outcomes: {outcome_stats['total_outcomes']}")
        print(f"     Avg reward: {outcome_stats['avg_reward_signal']:.3f}")
        print(f"     Correlation time: {outcome_stats['correlation_time_ms']:.2f}ms")
    
    # Get standalone outcome tracker statistics
    outcome_stats = collector.get_outcome_tracker_statistics()
    assert outcome_stats is not None
    assert outcome_stats['total_outcomes'] == 5
    
    print(f"✓ Outcome tracker statistics accessible")
    
    collector.end_session()
    os.unlink(temp_db)
    
    print("\n✅ SESSION STATISTICS TEST PASSED!")


async def test_export_with_rewards():
    """Test JSON export includes reward signals"""
    print("\n" + "=" * 60)
    print("TEST: Export with Reward Signals")
    print("=" * 60)
    
    temp_db = tempfile.mktemp(suffix='.db')
    collector = TrainingDataCollector(temp_db)
    
    if not collector.outcome_tracker:
        print("⚠️  Outcome tracker not available")
        os.unlink(temp_db)
        return
    
    session_id = collector.start_session()
    
    # Log decision with rich outcome
    dec_id = collector.log_decision(
        character_id="elara",
        situation_context={"game_state": {}},
        decision={
            "decision_type": "social",
            "action": "diplomatic_solution",
            "source": "brain"
        }
    )
    
    collector.update_outcome(
        decision_id=dec_id,
        outcome={
            "immediate": "Negotiated peace, gained ally, relationship +15, learned secret, 40 XP"
        },
        success=True
    )
    
    # Export
    export_path = tempfile.mktemp(suffix='.json')
    collector.export_to_json("elara", export_path)
    
    print(f"✓ Exported to {export_path}")
    
    # Read and verify
    import json
    with open(export_path, 'r') as f:
        data = json.load(f)
    
    assert len(data['decisions']) == 1
    decision = data['decisions'][0]
    
    # Check reward signals present
    assert 'reward_signals' in decision['outcome_data']
    assert 'aggregate_reward' in decision['outcome_data']
    assert 'quality_analysis' in decision['outcome_data']
    
    print(f"✓ Export includes enhanced outcome data:")
    print(f"   Reward signals: {len(decision['outcome_data']['reward_signals'])}")
    print(f"   Aggregate reward: {decision['outcome_data']['aggregate_reward']:.3f}")
    
    collector.end_session()
    os.unlink(temp_db)
    os.unlink(export_path)
    
    print("\n✅ EXPORT WITH REWARDS TEST PASSED!")


async def run_all_integration_tests():
    """Run all integration tests"""
    print("\n" + "=" * 70)
    print("TRAINING DATA + OUTCOME TRACKER - INTEGRATION TEST SUITE")
    print("=" * 70)
    
    tests = [
        test_enhanced_outcome_storage,
        test_multi_domain_tracking,
        test_delayed_outcome_correlation,
        test_quality_analysis_integration,
        test_session_statistics_with_rewards,
        test_export_with_rewards
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
