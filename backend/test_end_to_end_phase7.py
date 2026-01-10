"""
End-to-End Integration Test - Phase 7 Task 7.4
================================================
Tests the complete Phase 7 learning pipeline in a realistic gameplay scenario.

This test simulates:
1. Character gameplay session with multiple decisions
2. Decision collection and outcome tracking
3. Reflection analysis
4. Data curation and export
5. QLoRA training (mock or real if GPU available)
6. Memory consolidation
7. Character dashboard verification

Run with: python test_end_to_end_phase7.py
"""

import asyncio
import json
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

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
    from qlora_training import get_trainer, TrainingConfig, CharacterState
    QLORA_TRAINING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: QLoRATrainer not available: {e}")
    QLORA_TRAINING_AVAILABLE = False

try:
    from advanced_consolidation import (
        LearningAwareConsolidation,
        DreamCycleCoordinator
    )
    from qlora_training import CharacterState  # Import CharacterState for type
    ADVANCED_CONSOLIDATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Advanced consolidation not available: {e}")
    ADVANCED_CONSOLIDATION_AVAILABLE = False
    CharacterState = None  # Fallback

try:
    from session_manager import SessionManager
    SESSION_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: SessionManager not available: {e}")
    SESSION_MANAGER_AVAILABLE = False


# ============================================================================
# Test Scenario - "The Cave Encounter"
# ============================================================================

CAVE_SCENARIO = {
    "name": "The Cave Encounter",
    "description": "A tactical combat scenario testing decision-making under pressure",
    "setup": {
        "location": "Dark Cave Entrance",
        "characters": ["thorin", "elara"],
        "enemies": ["goblin_scout", "goblin_warrior"],
        "environment": {"lighting": "dim", "terrain": "rocky"}
    }
}


# ============================================================================
# Test Utilities
# ============================================================================

class TestLogger:
    """Colored output for test results"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def header(self, text: str):
        print(f"\n{'=' * 70}")
        print(f"  {text}")
        print(f"{'=' * 70}\n")

    def section(self, text: str):
        print(f"\n--- {text} ---")

    def pass_(self, msg: str):
        print(f"  [PASS] {msg}")
        self.passed += 1

    def fail(self, msg: str):
        print(f"  [FAIL] {msg}")
        self.failed += 1

    def warn(self, msg: str):
        print(f"  [WARN] {msg}")
        self.warnings += 1

    def info(self, msg: str):
        print(f"  [INFO] {msg}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'=' * 70}")
        print(f"  TEST SUMMARY")
        print(f"{'=' * 70}")
        print(f"  Passed:  {self.passed}")
        print(f"  Failed:  {self.failed}")
        print(f"  Warnings: {self.warnings}")
        print(f"  Total:   {total}")
        if self.failed == 0:
            print(f"\n  ALL TESTS PASSED!")
        else:
            print(f"\n  {self.failed} TESTS FAILED")
        print(f"{'=' * 70}\n")
        return self.failed == 0


log = TestLogger()


# ============================================================================
# Test Steps
# ============================================================================

class EndToEndTest:
    """End-to-end integration test for Phase 7"""

    def __init__(self):
        self.tmpdir = None
        self.collector = None
        self.session_manager = None
        self.results = {}

    async def setup(self):
        """Set up test environment"""
        log.header("PHASE 7 END-TO-END INTEGRATION TEST")

        self.tmpdir = tempfile.mkdtemp(prefix="dmlog_e2e_")
        log.info(f"Test directory: {self.tmpdir}")

        # Initialize training data collector
        if TRAINING_DATA_AVAILABLE:
            db_path = Path(self.tmpdir) / "decisions.db"
            self.collector = TrainingDataCollector(str(db_path))
            log.pass_("TrainingDataCollector initialized")

            # Initialize session manager
            if SESSION_MANAGER_AVAILABLE:
                self.session_manager = SessionManager()
                log.pass_("SessionManager initialized")
        else:
            log.fail("TrainingDataCollector not available - cannot continue")
            return False

        return True

    async def test_gameplay_session(self):
        """
        Test 1: Simulate a gameplay session with multiple decisions

        Scenario: Two characters (Thorin the dwarf fighter, Elara the elven ranger)
        encounter goblins at a cave entrance. They must make tactical decisions.
        """
        log.section("Test 1: Gameplay Session Simulation")

        if not TRAINING_DATA_AVAILABLE:
            log.fail("TrainingDataCollector not available")
            return False

        # Start session
        session_id = self.collector.start_session(
            session_notes="Cave encounter with goblins",
            character_ids=["thorin", "elara"],
            tags=["combat", "cave", "goblins"]
        )
        log.info(f"Started session: {session_id}")

        # Simulate gameplay turns
        turns = [
            {
                "character": "thorin",
                "situation": {
                    "game_state": {
                        "location": "Cave entrance",
                        "turn": 1,
                        "combat_active": True
                    },
                    "character_state": {"hp": 45, "max_hp": 50},
                    "perception_data": {
                        "nearby_enemies": [{"id": "goblin_scout", "distance": 30}]
                    }
                },
                "decision": {
                    "decision_type": "combat_action",
                    "action": "Charge and attack with axe",
                    "reasoning": "Close distance quickly before goblin can alert others",
                    "confidence": 0.85,
                    "source": "bot"
                }
            },
            {
                "character": "elara",
                "situation": {
                    "game_state": {
                        "location": "Cave entrance",
                        "turn": 2,
                        "combat_active": True
                    },
                    "character_state": {"hp": 38, "max_hp": 42},
                    "perception_data": {
                        "nearby_enemies": [{"id": "goblin_scout", "distance": 20}]
                    }
                },
                "decision": {
                    "decision_type": "combat_action",
                    "action": "Shoot arrow at goblin scout",
                    "reasoning": "Support Thorin's charge with ranged attack",
                    "confidence": 0.90,
                    "source": "bot"
                }
            },
            {
                "character": "thorin",
                "situation": {
                    "game_state": {
                        "location": "Inside cave",
                        "turn": 3,
                        "combat_active": True
                    },
                    "character_state": {"hp": 42, "max_hp": 50},
                    "perception_data": {
                        "nearby_enemies": [
                            {"id": "goblin_scout", "distance": 5},
                            {"id": "goblin_warrior", "distance": 15}
                        ]
                    }
                },
                "decision": {
                    "decision_type": "combat_action",
                    "action": "Attack goblin warrior",
                    "reasoning": "Threaten the more dangerous foe",
                    "confidence": 0.75,
                    "source": "bot"
                }
            },
            {
                "character": "elara",
                "situation": {
                    "game_state": {
                        "location": "Cave entrance",
                        "turn": 4,
                        "combat_active": True
                    },
                    "character_state": {"hp": 35, "max_hp": 42},
                    "perception_data": {
                        "nearby_enemies": [{"id": "goblin_scout", "distance": 25}]
                    }
                },
                "decision": {
                    "decision_type": "exploration",
                    "action": "Move to flank position",
                    "reasoning": "Get better angle for next shot",
                    "confidence": 0.70,
                    "source": "brain"
                }
            },
            {
                "character": "thorin",
                "situation": {
                    "game_state": {
                        "location": "Inside cave",
                        "turn": 5,
                        "combat_active": True
                    },
                    "character_state": {"hp": 35, "max_hp": 50},
                    "perception_data": {
                        "nearby_enemies": [
                            {"id": "goblin_scout", "distance": 10},
                            {"id": "goblin_warrior", "distance": 5}
                        ]
                    }
                },
                "decision": {
                    "decision_type": "combat_action",
                    "action": "Raise shield and defend",
                    "reasoning": "Protect against two attackers",
                    "confidence": 0.95,
                    "source": "bot"
                }
            },
        ]

        decision_ids = []

        # Log decisions
        for turn in turns:
            decision_id = self.collector.log_decision(
                character_id=turn["character"],
                situation_context=turn["situation"],
                decision=turn["decision"],
                session_id=session_id
            )
            if decision_id:
                decision_ids.append((decision_id, turn["character"]))
                log.info(f"Logged {turn['character']} decision: {turn['decision']['action']}")
            else:
                log.fail(f"Failed to log decision for {turn['character']}")

        # Simulate outcomes
        outcomes = [
            (decision_ids[0][0], {
                "immediate": "Hit goblin scout for 12 damage",
                "success": True
            }),
            (decision_ids[1][0], {
                "immediate": "Arrow hits, 8 damage",
                "success": True
            }),
            (decision_ids[2][0], {
                "immediate": "Attack misses, counter-attack for 10 damage",
                "success": False
            }),
            (decision_ids[3][0], {
                "immediate": "Successfully flanked, +2 to next attack",
                "success": True
            }),
            (decision_ids[4][0], {
                "immediate": "Blocked both attacks",
                "success": True
            }),
        ]

        for decision_id, outcome in outcomes:
            self.collector.update_outcome(
                decision_id,
                outcome,
                success=outcome["success"]
            )

        # End session
        session_summary = self.collector.end_session()
        log.info(f"Session ended: {session_summary['total_decisions']} decisions")

        # Verify statistics
        stats = self.collector.get_statistics()
        log.info(f"Statistics: {stats['total_decisions']} decisions, "
                f"{stats['success_rate']:.1%} success rate")

        self.results['decision_ids'] = [d[0] for d in decision_ids]
        self.results['session_id'] = session_id

        # Check results
        if len(decision_ids) == 5:
            log.pass_("All 5 decisions logged successfully")
        else:
            log.fail_(f"Expected 5 decisions, got {len(decision_ids)}")

        if stats['total_decisions'] == 5:
            log.pass_("Statistics correct")
        else:
            log.fail_(f"Expected 5 total decisions, got {stats['total_decisions']}")

        return len(decision_ids) == 5

    async def test_outcome_tracking(self):
        """Test 2: Outcome tracking with reward signals"""
        log.section("Test 2: Outcome Tracking")

        if not OUTCOME_TRACKER_AVAILABLE:
            log.warn("OutcomeTracker not available, skipping")
            return True

        tracker = OutcomeTracker()

        # Track outcomes from our session
        for decision_id, character in [(self.results['decision_ids'][0], 'thorin'),
                                        (self.results['decision_ids'][2], 'thorin')]:
            outcome = tracker.track_immediate_outcome(
                decision_id=decision_id,
                description="Combat outcome",
                success=character == 'thorin',
                context={"decision_type": "combat_action"}
            )
            log.info(f"Tracked outcome for {decision_id}")

        # Get aggregate reward
        aggregate = tracker.get_aggregate_reward(self.results['decision_ids'][0])
        log.info(f"Aggregate reward: {aggregate:.2f}")

        if aggregate > 0:
            log.pass_("Reward calculation working")
        else:
            log.fail_("Reward calculation failed")

        return aggregate > 0

    async def test_reflection_analysis(self):
        """Test 3: Reflection pipeline analysis"""
        log.section("Test 3: Reflection Analysis")

        if not REFLECTION_PIPELINE_AVAILABLE:
            log.warn("ReflectionPipeline not available, skipping")
            return True

        pipeline = ReflectionPipeline()

        # Analyze one of Thorin's decisions
        thorin_decisions = self.collector.get_decisions_for_character("thorin")

        if not thorin_decisions:
            log.fail_("No decisions found for Thorin")
            return False

        decision = thorin_decisions[0]

        result = await pipeline.reflect_on_decision(
            decision_data=decision['decision_data'],
            outcome_data=decision['outcome_data'],
            context={
                "character_id": "thorin",
                "situation_context": decision['situation_context']
            }
        )

        log.info(f"Reflection quality: {result.quality_label.value}")
        log.info(f"Quality score: {result.quality_score:.2f}")
        log.info(f"Teaching value: {result.teaching_value:.2f}")

        # Update quality label in database
        self.collector.update_quality_label(
            decision['decision_id'],
            result.quality_label.value,
            f"Teaching value: {result.teaching_value:.2f}"
        )

        if 0 <= result.quality_score <= 1:
            log.pass_("Quality score in valid range")
        else:
            log.fail_(f"Quality score out of range: {result.quality_score}")

        self.results['reflection_result'] = result

        return 0 <= result.quality_score <= 1

    async def test_data_curation(self):
        """Test 4: Data curation and export"""
        log.section("Test 4: Data Curation and Export")

        if not DATA_CURATION_AVAILABLE:
            log.warn("DataCurationPipeline not available, skipping")
            return True

        # Get all decisions
        thorin_decisions = self.collector.get_decisions_for_character("thorin")
        elara_decisions = self.collector.get_decisions_for_character("elara")

        all_decisions = thorin_decisions + elara_decisions

        log.info(f"Curating {len(all_decisions)} decisions")

        # Create curation pipeline
        config = CurationConfig(
            min_confidence=0.3,
            min_quality_score=0.4,
            deduplication_enabled=False,  # Skip for test speed
            balance_success_failure=True
        )

        pipeline = DataCurationPipeline(config)

        # Run curation
        output_dir = Path(self.tmpdir) / "curated"
        report = pipeline.curate(
            decisions=all_decisions,
            character_id="thorin",
            output_dir=str(output_dir)
        )

        log.info(f"Curation report:")
        log.info(f"  Input: {report.input_count}")
        log.info(f"  Filtered: {report.filtered_count}")
        log.info(f"  Final: {report.final_count}")
        log.info(f"  Train/Val/Test: {report.train_count}/{report.val_count}/{report.test_count}")

        self.results['curation_report'] = report

        # Verify outputs exist
        train_file = output_dir / "train.jsonl"
        val_file = output_dir / "val.jsonl"
        test_file = output_dir / "test.jsonl"

        files_exist = train_file.exists() and val_file.exists() and test_file.exists()

        if files_exist:
            log.pass_("All output files created")
        else:
            log.fail_("Some output files missing")

        return files_exist

    async def test_qlora_export(self):
        """Test 5: QLoRA format export"""
        log.section("Test 5: QLoRA Format Export")

        if not TRAINING_DATA_AVAILABLE:
            log.warn("TrainingDataCollector not available, skipping")
            return True

        # Export for QLoRA training
        export_path = Path(self.tmpdir) / "qlora_train.jsonl"

        stats = self.collector.export_for_qlora(
            character_id="thorin",
            output_path=str(export_path),
            format="jsonl"
        )

        log.info(f"Export statistics:")
        log.info(f"  Total decisions: {stats['total_decisions']}")
        log.info(f"  Filtered: {stats['filtered_decisions']}")
        log.info(f"  Exported: {stats['exported_records']}")

        # Verify file format
        if export_path.exists():
            with open(export_path, 'r') as f:
                first_line = f.readline()
                record = json.loads(first_line)

                has_instruction = "instruction" in record
                has_input = "input" in record
                has_output = "output" in record

                if has_instruction and has_input and has_output:
                    log.pass_("QLoRA format correct")
                else:
                    log.fail_("QLoRA format incorrect")

                return has_instruction and has_input and has_output
        else:
            log.fail_("Export file not created")
            return False

    async def test_training_simulation(self):
        """Test 6: QLoRA training (simulation)"""
        log.section("Test 6: QLoRA Training Simulation")

        if not QLORA_TRAINING_AVAILABLE:
            log.warn("QLoRATrainer not available, skipping")
            return True

        # Create sample training data
        train_path = Path(self.tmpdir) / "train.jsonl"

        if not train_path.exists():
            # Create minimal test data
            with open(train_path, 'w') as f:
                for i in range(10):
                    f.write(json.dumps({
                        "instruction": "What combat action should I take?",
                        "input": f"Location: Cave, Turn: {i}\nHP: 35/50",
                        "output": f"Action: Attack\nReasoning: Defend party"
                    }) + '\n')

        # Progress tracking
        progress_updates = []

        def progress_callback(progress):
            progress_updates.append(progress.to_dict())

        # Create trainer (force mock for faster testing)
        config = TrainingConfig(
            character_id="thorin",
            output_dir=self.tmpdir,
            num_train_epochs=1
        )

        trainer = get_trainer(config, progress_callback, force_mock=True)

        # Run training
        result = trainer.train(
            training_data_path=str(train_path),
            character_id="thorin"
        )

        log.info(f"Training result:")
        log.info(f"  Success: {result.success}")
        log.info(f"  Final loss: {result.final_train_loss:.3f}")
        log.info(f"  Training time: {result.training_time_seconds:.1f}s")

        self.results['training_result'] = result

        if result.success:
            log.pass_("Training completed successfully")
        else:
            log.fail_(f"Training failed: {result.error_message}")

        # Check progress updates
        states = [p['state'] for p in progress_updates]
        if 'dreaming' in states and 'training' in states:
            log.pass_("Progress tracking working")
        else:
            log.warn_("Progress tracking incomplete")

        return result.success

    async def test_memory_consolidation(self):
        """Test 7: Memory consolidation integration"""
        log.section("Test 7: Memory Consolidation Integration")

        if not ADVANCED_CONSOLIDATION_AVAILABLE:
            log.warn("Advanced consolidation not available, skipping")
            return True

        # Create dream cycle coordinator
        coordinator = DreamCycleCoordinator(
            character_id="thorin",
            min_decisions_for_training=5,
            min_teaching_moments=1
        )

        # Check state transitions
        log.info(f"Initial state: {coordinator.get_state().value}")

        coordinator.transition_to(CharacterState.DREAMING)
        coordinator.transition_to(CharacterState.TRAINING)
        coordinator.transition_to(CharacterState.AWAKENING)

        final_state = coordinator.get_state()
        log.info(f"Final state: {final_state.value}")

        if final_state == CharacterState.ACTIVE:
            coordinator.transition_to(CharacterState.ACTIVE)

        if final_state == CharacterState.AWAKENING:
            log.pass_("State transitions working")
        else:
            log.fail_(f"Unexpected final state: {final_state}")

        return final_state == CharacterState.AWAKENING

    async def test_character_dashboard(self):
        """Test 8: Character Dashboard"""
        log.section("Test 8: Character Dashboard Data")

        # Get statistics for dashboard display
        stats = self.collector.get_statistics(character_id="thorin")

        log.info(f"Thorin's statistics:")
        log.info(f"  Total decisions: {stats['total_decisions']}")
        log.info(f"  Success rate: {stats['success_rate']:.1%}")
        log.info(f"  By type: {stats['by_type']}")
        log.info(f"  By source: {stats['by_source']}")

        self.results['dashboard_stats'] = stats

        if stats['total_decisions'] > 0:
            log.pass_("Dashboard data available")
        else:
            log.fail_("No dashboard data")

        return stats['total_decisions'] > 0

    async def test_hyperparameter_hints(self):
        """Test 9: Hyperparameter hints generation"""
        log.section("Test 9: Hyperparameter Hints")

        try:
            from hyperparameter_hints import get_hyperparameter_hints_from_db
        except ImportError:
            log.warn("hyperparameter_hints not available, skipping")
            return True

        hints = get_hyperparameter_hints_from_db(
            character_id="thorin",
            db_path=str(Path(self.tmpdir) / "decisions.db")
        )

        if hints:
            log.info(f"Character class: {hints.character_class}")
            log.info(f"Confidence: {hints.confidence:.2f}")
            log.info(f"Recommended lora_r: {hints.lora_r}")
            log.info(f"Recommended learning_rate: {hints.learning_rate}")

            self.results['hyperparameter_hints'] = hints

            log.pass_("Hyperparameter hints generated")
            return True
        else:
            log.fail_("Failed to generate hyperparameter hints")
            return False

    async def generate_report(self):
        """Generate final test report"""
        log.section("Generating Test Report")

        report = {
            "test_name": "Phase 7 End-to-End Integration Test",
            "timestamp": datetime.now().isoformat(),
            "scenario": CAVE_SCENARIO,
            "results": {
                "decisions_logged": len(self.results.get('decision_ids', [])),
                "curation_report": self.results.get('curation_report', {}).to_dict()
                if self.results.get('curation_report') else None,
                "training_result": self.results.get('training_result', {}).to_dict()
                if isinstance(self.results.get('training_result'), object) else self.results.get('training_result'),
                "dashboard_stats": self.results.get('dashboard_stats')
            },
            "components_tested": {
                "training_data_collector": TRAINING_DATA_AVAILABLE,
                "outcome_tracker": OUTCOME_TRACKER_AVAILABLE,
                "reflection_pipeline": REFLECTION_PIPELINE_AVAILABLE,
                "data_curation": DATA_CURATION_AVAILABLE,
                "qlora_training": QLORA_TRAINING_AVAILABLE,
                "advanced_consolidation": ADVANCED_CONSOLIDATION_AVAILABLE,
                "session_manager": SESSION_MANAGER_AVAILABLE
            }
        }

        # Save report
        report_path = Path(self.tmpdir) / "test_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        log.info(f"Test report saved to: {report_path}")

        # Print summary
        print("\n" + "=" * 70)
        print("  TEST RESULTS SUMMARY")
        print("=" * 70)
        print(f"\n  Scenario: {CAVE_SCENARIO['name']}")
        print(f"  Decisions Logged: {report['results']['decisions_logged']}")
        print(f"\n  Components Available:")
        for component, available in report['components_tested'].items():
            status = "OK" if available else "SKIP"
            print(f"    {component}: {status}")

        return report

    async def run_all(self):
        """Run all tests"""
        if not await self.setup():
            return False

        await self.test_gameplay_session()
        await self.test_outcome_tracking()
        await self.test_reflection_analysis()
        await self.test_data_curation()
        await self.test_qlora_export()
        await self.test_training_simulation()
        await self.test_memory_consolidation()
        await self.test_character_dashboard()
        await self.test_hyperparameter_hints()

        await self.generate_report()

        return log.summary()


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Main test runner"""
    test = EndToEndTest()
    success = await test.run_all()

    # Cleanup
    import shutil
    if test.tmpdir:
        log.info(f"\nTest data preserved at: {test.tmpdir}")
        log.info("To clean up: rm -rf " + test.tmpdir)

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
