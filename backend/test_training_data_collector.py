"""
Tests for Training Data Collector (Phase 7.1.1)

Comprehensive test suite for the decision logging system.
"""

import pytest
import asyncio
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta

from training_data_collector import (
    TrainingDataCollector,
    CharacterDataSettings
)


class TestTrainingDataCollector:
    """Test suite for TrainingDataCollector"""
    
    def setup_method(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.collector = TrainingDataCollector(self.db_path)
    
    def teardown_method(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_initialization(self):
        """Test collector initialization"""
        assert self.collector is not None
        assert os.path.exists(self.db_path)
        print("✓ Collector initialized successfully")
    
    def test_character_settings_default(self):
        """Test default character settings"""
        settings = self.collector.get_character_settings("thorin")
        
        assert settings.character_id == "thorin"
        assert settings.enabled == True
        assert settings.collect_bot_decisions == True
        assert settings.collect_brain_decisions == True
        assert settings.retention_days == 30
        
        print("✓ Default character settings work")
    
    def test_character_settings_update(self):
        """Test updating character settings"""
        settings = self.collector.get_character_settings("thorin")
        settings.collect_bot_decisions = False
        settings.retention_days = 60
        
        self.collector.update_character_settings(settings)
        
        # Reload and verify
        settings2 = self.collector.get_character_settings("thorin")
        assert settings2.collect_bot_decisions == False
        assert settings2.retention_days == 60
        
        print("✓ Character settings update works")
    
    def test_privacy_filtering(self):
        """Test privacy-based decision filtering"""
        # Disable bot decisions
        settings = self.collector.get_character_settings("thorin")
        settings.collect_bot_decisions = False
        self.collector.update_character_settings(settings)
        
        # Try to log bot decision
        decision_id = self.collector.log_decision(
            character_id="thorin",
            situation_context={"test": "data"},
            decision={"source": "bot", "action": "attack"}
        )
        
        # Should be rejected
        assert decision_id is None
        
        # Brain decisions should still work
        decision_id2 = self.collector.log_decision(
            character_id="thorin",
            situation_context={"test": "data"},
            decision={"source": "brain", "action": "think"}
        )
        
        assert decision_id2 is not None
        
        print("✓ Privacy filtering works correctly")
    
    def test_session_management(self):
        """Test session start/end"""
        session_id = self.collector.start_session(session_notes="Test session")
        
        assert session_id is not None
        assert self.collector.current_session_id == session_id
        
        # Log some decisions
        for i in range(3):
            self.collector.log_decision(
                character_id="thorin",
                situation_context={"turn": i},
                decision={"action": f"action_{i}", "source": "bot"}
            )
        
        # End session
        self.collector.end_session()
        assert self.collector.current_session_id is None
        
        # Check session summary
        summary = self.collector.get_session_summary(session_id)
        assert summary['statistics']['total_decisions'] == 3
        
        print("✓ Session management works")
    
    def test_decision_logging(self):
        """Test basic decision logging"""
        situation_context = {
            "game_state": {
                "turn": 5,
                "combat_active": True
            },
            "character_state": {
                "hp": 35,
                "max_hp": 50
            }
        }
        
        decision = {
            "decision_type": "combat_action",
            "action": "attack",
            "target": "goblin_1",
            "reasoning": "Protect party",
            "confidence": 0.85,
            "source": "bot"
        }
        
        decision_id = self.collector.log_decision(
            character_id="thorin",
            situation_context=situation_context,
            decision=decision
        )
        
        assert decision_id is not None
        assert decision_id.startswith("dec_")
        
        # Retrieve decision
        decisions = self.collector.get_decisions_for_character("thorin", limit=1)
        assert len(decisions) == 1
        assert decisions[0]['decision_id'] == decision_id
        assert decisions[0]['decision_data']['action'] == "attack"
        
        print("✓ Decision logging works")
    
    def test_outcome_tracking(self):
        """Test outcome updates"""
        decision_id = self.collector.log_decision(
            character_id="thorin",
            situation_context={"turn": 1},
            decision={"action": "attack", "source": "bot"}
        )
        
        # Update outcome
        outcome = {
            "immediate": "Hit for 15 damage",
            "delayed": "Enemy defeated",
            "rewards": {"xp": 50}
        }
        
        self.collector.update_outcome(decision_id, outcome, success=True)
        
        # Retrieve and verify
        decisions = self.collector.get_decisions_for_character("thorin")
        assert len(decisions) == 1
        assert decisions[0]['success'] == 1
        assert decisions[0]['outcome_data']['immediate'] == "Hit for 15 damage"
        
        print("✓ Outcome tracking works")
    
    def test_quality_labeling(self):
        """Test quality label updates"""
        decision_id = self.collector.log_decision(
            character_id="thorin",
            situation_context={"turn": 1},
            decision={"action": "negotiate", "source": "brain"}
        )
        
        self.collector.update_quality_label(
            decision_id,
            quality_label="good",
            reflection_notes="Excellent diplomatic choice"
        )
        
        decisions = self.collector.get_decisions_for_character("thorin")
        assert decisions[0]['quality_label'] == "good"
        assert "diplomatic" in decisions[0]['reflection_notes']
        
        print("✓ Quality labeling works")
    
    def test_training_eligible_filtering(self):
        """Test filtering for training-eligible decisions"""
        # Log several decisions with different qualities
        decisions_data = [
            ("attack", "good", True),
            ("defend", "acceptable", True),
            ("flee", "bad", True),
            ("wait", None, False)  # No outcome
        ]
        
        for action, quality, has_outcome in decisions_data:
            decision_id = self.collector.log_decision(
                character_id="thorin",
                situation_context={"turn": 1},
                decision={"action": action, "source": "bot"}
            )
            
            if has_outcome:
                self.collector.update_outcome(decision_id, {}, success=True)
            
            if quality:
                self.collector.update_quality_label(decision_id, quality)
        
        # Get training eligible (should have outcomes)
        training_data = self.collector.get_training_eligible_decisions("thorin")
        assert len(training_data) == 3  # Only those with outcomes
        
        # Get only "good" quality
        good_data = self.collector.get_training_eligible_decisions(
            "thorin",
            min_quality="good"
        )
        assert len(good_data) == 1
        assert good_data[0]['decision_data']['action'] == "attack"
        
        print("✓ Training data filtering works")
    
    def test_statistics(self):
        """Test statistics generation"""
        # Log diverse decisions
        for i in range(5):
            source = "bot" if i % 2 == 0 else "brain"
            decision_id = self.collector.log_decision(
                character_id="thorin",
                situation_context={"turn": i},
                decision={
                    "action": f"action_{i}",
                    "source": source,
                    "decision_type": "combat_action" if i < 3 else "social"
                }
            )
            
            # Add outcomes
            self.collector.update_outcome(
                decision_id,
                {"result": "test"},
                success=(i % 3 != 0)  # 2 successes, 1 failure, pattern
            )
        
        stats = self.collector.get_statistics(character_id="thorin")
        
        assert stats['total_decisions'] == 5
        assert stats['by_source']['bot'] == 3
        assert stats['by_source']['brain'] == 2
        assert stats['by_type']['combat_action'] == 3
        assert stats['by_type']['social'] == 2
        assert stats['successes'] == 3
        assert stats['failures'] == 2
        assert 0.5 < stats['success_rate'] < 0.7
        
        print("✓ Statistics generation works")
    
    def test_data_cleanup(self):
        """Test old data cleanup"""
        # Log decision with old timestamp
        settings = self.collector.get_character_settings("thorin")
        settings.retention_days = 7
        self.collector.update_character_settings(settings)
        
        # Insert old decision directly
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        old_date = (datetime.utcnow() - timedelta(days=10)).isoformat()
        cursor.execute("""
            INSERT INTO decisions
            (decision_id, character_id, timestamp, situation_context, decision_data,
             decision_type, decision_source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "old_dec",
            "thorin",
            old_date,
            "{}",
            "{}",
            "test",
            "bot"
        ))
        
        conn.commit()
        conn.close()
        
        # Log recent decision
        self.collector.log_decision(
            character_id="thorin",
            situation_context={},
            decision={"source": "bot"}
        )
        
        # Cleanup
        deleted = self.collector.cleanup_old_data("thorin")
        assert deleted == 1
        
        # Verify only recent remains
        decisions = self.collector.get_decisions_for_character("thorin")
        assert len(decisions) == 1
        
        print("✓ Data cleanup works")
    
    def test_export_to_json(self):
        """Test JSON export"""
        # Log some decisions
        for i in range(3):
            decision_id = self.collector.log_decision(
                character_id="thorin",
                situation_context={"turn": i},
                decision={"action": f"action_{i}", "source": "bot"}
            )
            self.collector.update_outcome(decision_id, {}, success=True)
        
        # Export
        output_path = tempfile.mktemp(suffix='.json')
        self.collector.export_to_json("thorin", output_path)
        
        # Verify
        assert os.path.exists(output_path)
        
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        assert data['character_id'] == "thorin"
        assert data['total_decisions'] == 3
        assert len(data['decisions']) == 3
        
        os.unlink(output_path)
        
        print("✓ JSON export works")
    
    def test_concurrent_characters(self):
        """Test logging for multiple characters"""
        characters = ["thorin", "elara", "gandor"]
        
        for char in characters:
            for i in range(2):
                self.collector.log_decision(
                    character_id=char,
                    situation_context={"turn": i},
                    decision={"action": "test", "source": "bot"}
                )
        
        # Verify each character has 2 decisions
        for char in characters:
            decisions = self.collector.get_decisions_for_character(char)
            assert len(decisions) == 2
        
        # Verify total
        stats = self.collector.get_statistics()
        assert stats['total_decisions'] == 6
        
        print("✓ Multi-character logging works")
    
    def test_query_performance(self):
        """Test performance with many decisions"""
        import time
        
        # Insert 100 decisions
        for i in range(100):
            self.collector.log_decision(
                character_id="thorin",
                situation_context={"turn": i},
                decision={"action": f"action_{i}", "source": "bot"}
            )
        
        # Time a query
        start = time.time()
        decisions = self.collector.get_decisions_for_character("thorin", limit=10)
        query_time = (time.time() - start) * 1000
        
        assert len(decisions) == 10
        assert query_time < 100  # Should be < 100ms
        
        print(f"✓ Query performance: {query_time:.2f}ms for 100 decisions")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("TRAINING DATA COLLECTOR - TEST SUITE")
    print("=" * 60)
    print()
    
    test_suite = TestTrainingDataCollector()
    
    tests = [
        test_suite.test_initialization,
        test_suite.test_character_settings_default,
        test_suite.test_character_settings_update,
        test_suite.test_privacy_filtering,
        test_suite.test_session_management,
        test_suite.test_decision_logging,
        test_suite.test_outcome_tracking,
        test_suite.test_quality_labeling,
        test_suite.test_training_eligible_filtering,
        test_suite.test_statistics,
        test_suite.test_data_cleanup,
        test_suite.test_export_to_json,
        test_suite.test_concurrent_characters,
        test_suite.test_query_performance
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
        finally:
            test_suite.teardown_method()
        print()
    
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
