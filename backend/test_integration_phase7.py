"""
Integration Tests - Phase 7 Learning Pipeline
==============================================

Tests the complete Phase 7 learning pipeline:
1. Decision collection (TrainingDataCollector)
2. Outcome tracking (OutcomeTracker)
3. Reflection analysis (ReflectionPipeline)
4. Data curation (DataCurationPipeline)
5. QLoRA training (QLoRATrainer)
6. Memory consolidation (LearningAwareConsolidation)
7. Dream cycle orchestration (DreamCycleCoordinator)

Run with: python test_integration_phase7.py
"""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any

# Import Phase 7 components
try:
    from training_data_collector import TrainingDataCollector, CharacterDataSettings
    TRAINING_DATA_AVAILABLE = True
except ImportError as e:
    print(f"Warning: TrainingDataCollector not available: {e}")
    TRAINING_DATA_AVAILABLE = False

try:
    from outcome_tracker import OutcomeTracker, OutcomeType
    OUTCOME_TRACKER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: OutcomeTracker not available: {e}")
    OUTCOME_TRACKER_AVAILABLE = False

try:
    from reflection_pipeline import ReflectionPipeline, ReflectionQuality
    REFLECTION_PIPELINE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: ReflectionPipeline not available: {e}")
    REFLECTION_PIPELINE_AVAILABLE = False

try:
    from data_curation_pipeline import DataCurationPipeline, CurationConfig
    DATA_CURATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: DataCurationPipeline not available: {e}")
    DATA_CURATION_AVAILABLE = False

try:
    from qlora_training import QLoRATrainer, get_trainer, TrainingConfig, CharacterState
    QLORA_TRAINING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: QLoRATrainer not available: {e}")
    QLORA_TRAINING_AVAILABLE = False

try:
    from advanced_consolidation import (
        LearningAwareConsolidation,
        DreamCycleCoordinator,
        AdvancedConsolidationManager
    )
    ADVANCED_CONSOLIDATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Advanced consolidation not available: {e}")
    ADVANCED_CONSOLIDATION_AVAILABLE = False

try:
    from memory_system import MemoryConsolidationEngine
    MEMORY_SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Memory system not available: {e}")
    MEMORY_SYSTEM_AVAILABLE = False


# ============================================================================
# Test Data Generation
# ============================================================================

def generate_sample_decision(
    character_id: str,
    decision_type: str,
    success: bool,
    quality: str = "good"
) -> Dict[str, Any]:
    """Generate a sample decision record for testing"""
    return {
        "decision_id": f"dec_{character_id}_{decision_type}_{success}",
        "character_id": character_id,
        "session_id": "test_session",
        "timestamp": "2024-01-01T12:00:00",
        "situation_context": {
            "game_state": {
                "location": "Test location",
                "turn": 1,
                "combat_active": decision_type == "combat_action"
            },
            "character_state": {
                "hp": 45 if success else 35,
                "max_hp": 50
            },
            "perception_data": {
                "nearby_enemies": [{"id": "goblin_1"}] if decision_type == "combat_action" else []
            }
        },
        "decision_data": {
            "decision_type": decision_type,
            "action": f"test_action_{decision_type}",
            "reasoning": f"Test reasoning for {decision_type}",
            "confidence": 0.8 if success else 0.6,
            "source": "bot"
        },
        "outcome_data": {
            "success": success,
            "immediate": "Test immediate result",
            "quality_analysis": {"quality_score": 0.8 if success else 0.5}
        },
        "success": success,
        "quality_label": quality,
        "training_eligible": 1
    }


# ============================================================================
# Tests
# ============================================================================

async def test_training_data_collection():
    """Test 1: Training data collection"""
    print("\n" + "=" * 70)
    print("TEST 1: Training Data Collection")
    print("=" * 70)

    if not TRAINING_DATA_AVAILABLE:
        print("SKIP: TrainingDataCollector not available")
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        collector = TrainingDataCollector(str(db_path))

        # Start a session
        session_id = collector.start_session(
            session_notes="Test session for Phase 7"
        )
        print(f"  Started session: {session_id}")

        # Log multiple decisions
        character_id = "test_character"

        for i in range(10):
            decision = {
                "decision_type": "combat_action" if i % 2 == 0 else "exploration",
                "action": f"test_action_{i}",
                "reasoning": f"Test reasoning {i}",
                "confidence": 0.7 + (i * 0.02),
                "source": "bot"
            }

            situation = {
                "game_state": {"location": f"Location {i}", "turn": i},
                "character_state": {"hp": 50 - i, "max_hp": 50}
            }

            decision_id = collector.log_decision(
                character_id=character_id,
                situation_context=situation,
                decision=decision
            )
            print(f"  Logged decision {i+1}: {decision_id}")

        # Update outcomes
        decisions = collector.get_decisions_for_character(character_id)
        print(f"  Retrieved {len(decisions)} decisions")

        for decision in decisions[:5]:
            collector.update_outcome(
                decision["decision_id"],
                {"immediate": "Success!"},
                success=True
            )
            collector.update_quality_label(
                decision["decision_id"],
                "good"
            )

        # Get statistics
        stats = collector.get_statistics(character_id=character_id)
        print(f"  Statistics: {stats['total_decisions']} decisions")
        print(f"  Success rate: {stats['success_rate']:.1%}")

        # End session
        summary = collector.end_session()
        print(f"  Session ended")

        assert stats['total_decisions'] == 10
        assert collector.current_session_id is None

        print("  PASSED")
        return collector, character_id


async def test_outcome_tracking():
    """Test 2: Outcome tracking"""
    print("\n" + "=" * 70)
    print("TEST 2: Outcome Tracking")
    print("=" * 70)

    if not OUTCOME_TRACKER_AVAILABLE:
        print("SKIP: OutcomeTracker not available")
        return None

    tracker = OutcomeTracker()

    # Track immediate outcome
    outcome = tracker.track_immediate_outcome(
        decision_id="test_dec_1",
        description="Successfully attacked goblin",
        success=True,
        context={"decision_type": "combat_action"}
    )

    print(f"  Tracked immediate outcome: {outcome.decision_id}")
    print(f"  Reward count: {len(outcome.rewards)}")

    # Track delayed outcome
    tracker.track_delayed_outcome(
        decision_id="test_dec_1",
        description="Goblin was defeated later",
        success=True,
        context={},
        outcome_type=OutcomeType.SHORT_TERM
    )

    # Get aggregate reward
    aggregate = tracker.get_aggregate_reward("test_dec_1")
    print(f"  Aggregate reward: {aggregate.total_reward:.2f}")

    # Analyze quality
    quality = tracker.analyze_decision_quality("test_dec_1")
    print(f"  Quality score: {quality['quality_score']:.2f}")

    assert aggregate.total_reward > 0
    print("  PASSED")
    return tracker


async def test_reflection_pipeline():
    """Test 3: Reflection pipeline"""
    print("\n" + "=" * 70)
    print("TEST 3: Reflection Pipeline")
    print("=" * 70)

    if not REFLECTION_PIPELINE_AVAILABLE:
        print("SKIP: ReflectionPipeline not available")
        return None

    pipeline = ReflectionPipeline()

    # Test decision
    decision_data = {
        "decision_id": "test_dec",
        "decision_type": "combat_action",
        "action": "attack goblin",
        "reasoning": "Protect party from threat",
        "confidence": 0.85,
        "source": "bot"
    }

    outcome_data = {
        "success": True,
        "immediate": "Hit for 15 damage",
        "reward_signals": [
            {"domain": "combat", "value": 0.8, "confidence": 0.9}
        ],
        "quality_analysis": {"quality_score": 0.75}
    }

    context = {
        "character_id": "test_char",
        "situation_context": {
            "game_state": {"turn": 5, "location": "Cave"},
            "character_state": {"hp": 35, "max_hp": 50}
        }
    }

    # Reflect on decision
    result = await pipeline.reflect_on_decision(
        decision_data, outcome_data, context
    )

    print(f"  Quality label: {result.quality_label.value}")
    print(f"  Quality score: {result.quality_score:.2f}")
    print(f"  Teaching value: {result.teaching_value:.2f}")

    assert result.quality_label in ReflectionQuality.__members__.values()
    assert 0 <= result.quality_score <= 1

    print("  PASSED")
    return pipeline


async def test_data_curation():
    """Test 4: Data curation pipeline"""
    print("\n" + "=" * 70)
    print("TEST 4: Data Curation Pipeline")
    print("=" * 70)

    if not DATA_CURATION_AVAILABLE:
        print("SKIP: DataCurationPipeline not available")
        return None

    # Generate sample decisions
    decisions = []
    for i in range(20):
        decisions.append(generate_sample_decision(
            "test_char",
            "combat_action" if i % 2 == 0 else "exploration",
            success=i % 3 != 0,  # 2/3 success rate
            quality="good" if i % 3 != 0 else "poor"
        ))

    # Add some teaching moments
    for i in range(3):
        decisions.append(generate_sample_decision(
            "test_char",
            "social",
            success=False,
            quality="teaching_moment"
        ))

    # Create curation pipeline
    config = CurationConfig(
        min_confidence=0.3,
        min_quality_score=0.4,
        deduplication_enabled=False,  # Skip for faster test
        balance_success_failure=True
    )

    pipeline = DataCurationPipeline(config)

    # Run curation
    with tempfile.TemporaryDirectory() as tmpdir:
        report = pipeline.curate(
            decisions=decisions,
            character_id="test_char",
            output_dir=tmpdir
        )

    print(f"  Input: {report.input_count} decisions")
    print(f"  After filtering: {report.filtered_count}")
    print(f"  After deduplication: {report.deduplicated_count}")
    print(f"  After balancing: {report.balanced_count}")
    print(f"  Final: {report.final_count} decisions")
    print(f"  Train/Val/Test: {report.train_count}/{report.val_count}/{report.test_count}")

    assert report.input_count == 23
    assert report.final_count > 0
    assert report.train_count + report.val_count + report.test_count == report.final_count

    print("  PASSED")
    return pipeline


async def test_qlora_training():
    """Test 5: QLoRA training infrastructure"""
    print("\n" + "=" * 70)
    print("TEST 5: QLoRA Training Infrastructure")
    print("=" * 70)

    if not QLORA_TRAINING_AVAILABLE:
        print("SKIP: QLoRATrainer not available")
        return None

    # Create sample training data
    with tempfile.TemporaryDirectory() as tmpdir:
        train_path = Path(tmpdir) / "train.jsonl"
        with open(train_path, 'w') as f:
            for i in range(10):
                f.write(json.dumps({
                    "instruction": "What combat action should I take?",
                    "input": f"Location: Cave {i}\nHP: 35/50",
                    "output": f"Action: Attack\nReasoning: Defend party"
                }) + '\n')

        # Progress tracking
        progress_updates = []

        def progress_callback(progress):
            progress_updates.append(progress.to_dict())

        # Create trainer (will use mock if no GPU)
        config = TrainingConfig(
            character_id="test_char",
            output_dir=str(tmpdir),
            num_train_epochs=1
        )

        trainer = get_trainer(config, progress_callback)

        # Run training
        result = trainer.train(
            training_data_path=str(train_path),
            character_id="test_char"
        )

        print(f"  Success: {result.success}")
        print(f"  Final train loss: {result.final_train_loss:.3f}")
        print(f"  Training time: {result.training_time_seconds:.1f}s")

        assert result.success

        # Check progress updates
        if progress_updates:
            states = [p['state'] for p in progress_updates]
            print(f"  States: {set(states)}")
            assert 'dreaming' in states or 'training' in states

    print("  PASSED")
    return trainer


async def test_learning_aware_consolidation():
    """Test 6: Learning-aware consolidation"""
    print("\n" + "=" * 70)
    print("TEST 6: Learning-Aware Consolidation")
    print("=" * 70)

    if not ADVANCED_CONSOLIDATION_AVAILABLE or not MEMORY_SYSTEM_AVAILABLE:
        print("SKIP: Advanced consolidation or memory system not available")
        return None

    # Create memory engine
    memory_engine = MemoryConsolidationEngine("test_char")

    # Create training data collector with sample data
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        collector = TrainingDataCollector(str(db_path))

        # Add sample decisions
        for i in range(15):
            decision = {
                "decision_type": "combat_action" if i % 2 == 0 else "exploration",
                "action": f"action_{i}",
                "reasoning": f"reasoning_{i}",
                "confidence": 0.7
            }

            situation = {
                "game_state": {"location": "test", "turn": i},
                "character_state": {"hp": 50 - i, "max_hp": 50}
            }

            decision_id = collector.log_decision(
                character_id="test_char",
                situation_context=situation,
                decision=decision
            )

            collector.update_outcome(
                decision_id,
                {"immediate": "result"},
                success=i % 3 != 0
            )

        # Create learning-aware consolidation
        consolidation = LearningAwareConsolidation(
            character_id="test_char",
            training_data_collector=collector
        )

        # Run consolidation
        result = await consolidation.consolidate_recent_decisions(memory_engine)

        print(f"  Consolidation triggered: {result['triggered']}")
        print(f"  Decisions processed: {result.get('decisions_processed', 0)}")
        print(f"  Semantic created: {result.get('semantic_created', 0)}")

        # Get summary
        summary = consolidation.get_consolidation_summary()
        print(f"  Total consolidations: {summary.get('total_consolidations', 0)}")

        assert result['triggered']

    print("  PASSED")
    return consolidation


async def test_dream_cycle_coordinator():
    """Test 7: Dream cycle coordinator"""
    print("\n" + "=" * 70)
    print("TEST 7: Dream Cycle Coordinator")
    print("=" * 70)

    if not ADVANCED_CONSOLIDATION_AVAILABLE:
        print("SKIP: DreamCycleCoordinator not available")
        return None

    # Create coordinator
    coordinator = DreamCycleCoordinator(
        character_id="test_char",
        min_decisions_for_training=10,
        min_teaching_moments=3
    )

    # Check initial state
    print(f"  Initial state: {coordinator.get_state().value}")
    assert coordinator.get_state() == CharacterState.ACTIVE

    # Check if should trigger (not enough data)
    should_trigger, reason = coordinator.should_trigger_dream_cycle()
    print(f"  Should trigger: {should_trigger}")
    print(f"  Reason: {reason}")
    assert not should_trigger  # No training data collector

    # Test state transitions
    assert coordinator.transition_to(CharacterState.DREAMING)
    print(f"  State after first transition: {coordinator.get_state().value}")

    assert coordinator.transition_to(CharacterState.TRAINING)
    print(f"  State after second transition: {coordinator.get_state().value}")

    assert coordinator.transition_to(CharacterState.AWAKENING)
    print(f"  State after third transition: {coordinator.get_state().value}")

    assert coordinator.transition_to(CharacterState.ACTIVE)
    print(f"  Final state: {coordinator.get_state().value}")

    # Check state history
    history = coordinator.get_state_history()
    print(f"  State transitions: {len(history)}")

    # Test invalid transition
    assert not coordinator.transition_to(CharacterState.ERROR)  # Can't skip to ERROR
    print("  Invalid transition correctly blocked")

    print("  PASSED")
    return coordinator


async def test_qlora_export():
    """Test 8: QLoRA export from training data collector"""
    print("\n" + "=" * 70)
    print("TEST 8: QLoRA Export")
    print("=" * 70)

    if not TRAINING_DATA_AVAILABLE:
        print("SKIP: TrainingDataCollector not available")
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        collector = TrainingDataCollector(str(db_path))

        # Add sample decisions
        character_id = "test_char"
        for i in range(10):
            decision = {
                "decision_type": "combat_action",
                "action": f"attack_{i}",
                "reasoning": f"reasoning_{i}",
                "confidence": 0.7 + (i * 0.02)
            }

            situation = {
                "game_state": {"location": "cave", "turn": i},
                "character_state": {"hp": 50 - i, "max_hp": 50}
            }

            decision_id = collector.log_decision(
                character_id=character_id,
                situation_context=situation,
                decision=decision
            )

            collector.update_outcome(
                decision_id,
                {"immediate": "hit", "quality_analysis": {"quality_score": 0.7}},
                success=i % 2 == 0
            )

        # Export for QLoRA
        export_path = Path(tmpdir) / "qlora_export.jsonl"
        stats = collector.export_for_qlora(
            character_id=character_id,
            output_path=str(export_path),
            format="jsonl"
        )

        print(f"  Total decisions: {stats['total_decisions']}")
        print(f"  Filtered decisions: {stats['filtered_decisions']}")
        print(f"  Exported records: {stats['exported_records']}")
        print(f"  Output path: {stats['output_path']}")

        # Verify file exists and has content
        assert export_path.exists()
        with open(export_path, 'r') as f:
            lines = f.readlines()
            print(f"  Lines in export: {len(lines)}")
            assert len(lines) > 0

            # Verify format
            first_record = json.loads(lines[0])
            assert "instruction" in first_record
            assert "input" in first_record
            assert "output" in first_record
            print(f"  Sample record keys: {list(first_record.keys())}")

        # Export for consolidation
        consolidation_path = Path(tmpdir) / "consolidation.json"
        cons_stats = collector.export_for_consolidation(
            character_id=character_id,
            output_path=str(consolidation_path)
        )

        print(f"  Consolidation groups: {cons_stats['consolidation_groups']}")

    print("  PASSED")


# ============================================================================
# Main Test Runner
# ============================================================================

async def run_all_tests():
    """Run all Phase 7 integration tests"""
    print("\n" + "=" * 70)
    print("PHASE 7 LEARNING PIPELINE - INTEGRATION TEST SUITE")
    print("=" * 70)

    tests = [
        ("Training Data Collection", test_training_data_collection),
        ("Outcome Tracking", test_outcome_tracking),
        ("Reflection Pipeline", test_reflection_pipeline),
        ("Data Curation", test_data_curation),
        ("QLoRA Training", test_qlora_training),
        ("Learning-Aware Consolidation", test_learning_aware_consolidation),
        ("Dream Cycle Coordinator", test_dream_cycle_coordinator),
        ("QLoRA Export", test_qlora_export),
    ]

    passed = 0
    failed = 0
    skipped = 0

    for name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            print(f"\n  FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Total:  {passed + failed}")
    print("=" * 70)

    if failed == 0:
        print("\n  ALL TESTS PASSED!")
    else:
        print(f"\n  {failed} TESTS FAILED")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
