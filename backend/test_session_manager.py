"""
Tests for Session Manager (Phase 7.1.3)

Comprehensive test suite for enhanced session management.
"""

import pytest
from session_manager import (
    SessionManager,
    SessionPhase,
    CharacterSessionStats,
    SessionMetrics
)


class TestSessionManager:
    """Test suite for SessionManager"""
    
    def setup_method(self):
        """Create fresh manager for each test"""
        self.manager = SessionManager()
    
    def test_initialization(self):
        """Test manager initialization"""
        assert self.manager is not None
        assert len(self.manager.active_sessions) == 0
        assert self.manager.metrics["total_sessions"] == 0
        print("✓ Manager initialized successfully")
    
    def test_start_session(self):
        """Test starting a session"""
        session_id = self.manager.start_session(
            character_ids=["thorin", "elara"],
            notes="Test session",
            tags=["test", "combat"]
        )
        
        assert session_id is not None
        assert session_id in self.manager.active_sessions
        
        session = self.manager.active_sessions[session_id]
        assert session.active_characters == 2
        assert "thorin" in session.character_ids
        assert session.phase == SessionPhase.ACTIVE
        
        print(f"✓ Started session: {session_id}")
    
    def test_add_character(self):
        """Test adding character to session"""
        session_id = self.manager.start_session(character_ids=["thorin"])
        
        self.manager.add_character_to_session(session_id, "elara")
        
        session = self.manager.active_sessions[session_id]
        assert "elara" in session.character_ids
        assert session.active_characters == 2
        
        print("✓ Added character to session")
    
    def test_record_decision(self):
        """Test recording decisions"""
        session_id = self.manager.start_session(character_ids=["thorin"])
        
        decision_data = {
            "source": "bot",
            "confidence": 0.85,
            "time_taken_ms": 50.0
        }
        
        self.manager.record_decision(session_id, "thorin", decision_data)
        
        session = self.manager.active_sessions[session_id]
        assert session.total_decisions == 1
        
        char_stats = self.manager.character_stats[session_id]["thorin"]
        assert char_stats.decisions_made == 1
        assert char_stats.bot_decisions == 1
        
        print("✓ Recorded decision")
    
    def test_outcome_processing(self):
        """Test outcome processing with rewards"""
        session_id = self.manager.start_session(character_ids=["thorin"])
        
        decision_data = {
            "source": "brain",
            "confidence": 0.75,
            "time_taken_ms": 300.0
        }
        
        outcome_data = {
            "success": True,
            "reward_signals": [
                {"domain": "combat", "value": 0.7, "confidence": 0.8},
                {"domain": "resource", "value": 0.5, "confidence": 0.9}
            ],
            "aggregate_reward": 0.6,
            "quality_analysis": {"quality_score": 0.65}
        }
        
        self.manager.record_decision(session_id, "thorin", decision_data, outcome_data)
        
        session = self.manager.active_sessions[session_id]
        assert session.total_successes == 1
        assert session.total_session_reward > 0
        
        char_stats = self.manager.character_stats[session_id]["thorin"]
        assert char_stats.success_count == 1
        assert char_stats.combat_reward > 0
        assert char_stats.resource_reward > 0
        
        print(f"✓ Processed outcome with rewards")
        print(f"   Combat reward: {char_stats.combat_reward:.3f}")
        print(f"   Resource reward: {char_stats.resource_reward:.3f}")
    
    def test_multi_character_session(self):
        """Test session with multiple characters"""
        session_id = self.manager.start_session(
            character_ids=["thorin", "elara", "gandor"]
        )
        
        # Each character makes decisions
        for char in ["thorin", "elara", "gandor"]:
            for i in range(3):
                decision_data = {"source": "bot", "time_taken_ms": 50.0}
                outcome_data = {
                    "success": True,
                    "reward_signals": [{"domain": "combat", "value": 0.5, "confidence": 0.8}],
                    "aggregate_reward": 0.5
                }
                self.manager.record_decision(session_id, char, decision_data, outcome_data)
        
        session = self.manager.active_sessions[session_id]
        assert session.total_decisions == 9
        assert session.active_characters == 3
        
        # Check each character stats
        for char in ["thorin", "elara", "gandor"]:
            char_stats = self.manager.character_stats[session_id][char]
            assert char_stats.decisions_made == 3
        
        print("✓ Multi-character session works")
    
    def test_growth_score_calculation(self):
        """Test character growth score calculation"""
        session_id = self.manager.start_session(character_ids=["thorin"])
        
        # Record mostly successful decisions
        for i in range(5):
            decision_data = {"source": "brain", "time_taken_ms": 100.0}
            outcome_data = {
                "success": (i != 1),  # 4/5 success
                "reward_signals": [{"domain": "combat", "value": 0.6, "confidence": 0.8}],
                "aggregate_reward": 0.6,
                "quality_analysis": {"quality_score": 0.5 if i != 1 else 0.1}
            }
            self.manager.record_decision(session_id, "thorin", decision_data, outcome_data)
        
        # End session to calculate growth
        final_session = self.manager.end_session(session_id)
        
        char_stats = self.manager.character_stats[session_id]["thorin"]
        assert char_stats.growth_score > 0.5  # Should show growth
        
        print(f"✓ Growth score: {char_stats.growth_score:.3f}")
    
    def test_teaching_moments(self):
        """Test teaching moment tracking"""
        session_id = self.manager.start_session(character_ids=["elara"])
        
        # Mix of good and bad decisions
        decisions = [
            (True, 0.7),   # Good
            (False, 0.2),  # Bad - teaching moment
            (True, 0.6),   # Good
            (False, -0.1), # Bad - teaching moment
            (True, 0.8)    # Good
        ]
        
        for success, quality in decisions:
            decision_data = {"source": "bot", "time_taken_ms": 50.0}
            outcome_data = {
                "success": success,
                "reward_signals": [{"domain": "social", "value": 0.5, "confidence": 0.8}],
                "aggregate_reward": 0.5,
                "quality_analysis": {"quality_score": quality}
            }
            self.manager.record_decision(session_id, "elara", decision_data, outcome_data)
        
        session = self.manager.active_sessions[session_id]
        assert session.teaching_moments == 2
        
        char_stats = self.manager.character_stats[session_id]["elara"]
        assert char_stats.learning_opportunities == 2
        
        print(f"✓ Tracked {session.teaching_moments} teaching moments")
    
    def test_session_phases(self):
        """Test session phase transitions"""
        session_id = self.manager.start_session()
        
        session = self.manager.active_sessions[session_id]
        assert session.phase == SessionPhase.ACTIVE
        
        self.manager.set_session_phase(session_id, SessionPhase.INTERMISSION)
        assert session.phase == SessionPhase.INTERMISSION
        
        self.manager.set_session_phase(session_id, SessionPhase.ACTIVE)
        assert session.phase == SessionPhase.ACTIVE
        
        print("✓ Session phase transitions work")
    
    def test_end_session(self):
        """Test ending a session"""
        session_id = self.manager.start_session(character_ids=["thorin"])
        
        # Add some decisions
        for i in range(3):
            decision_data = {"source": "bot", "time_taken_ms": 50.0}
            outcome_data = {
                "success": True,
                "reward_signals": [{"domain": "combat", "value": 0.5, "confidence": 0.8}],
                "aggregate_reward": 0.5
            }
            self.manager.record_decision(session_id, "thorin", decision_data, outcome_data)
        
        final_session = self.manager.end_session(session_id)
        
        assert final_session.phase == SessionPhase.COMPLETE
        assert final_session.end_time is not None
        assert final_session.session_duration_seconds > 0
        assert session_id not in self.manager.active_sessions
        assert final_session in self.manager.completed_sessions
        
        print(f"✓ Ended session:")
        print(f"   Duration: {final_session.session_duration_seconds:.1f}s")
        print(f"   Decisions: {final_session.total_decisions}")
    
    def test_session_summary(self):
        """Test getting session summary"""
        session_id = self.manager.start_session(character_ids=["thorin", "elara"])
        
        # Add decisions
        for char in ["thorin", "elara"]:
            decision_data = {"source": "bot", "time_taken_ms": 50.0}
            outcome_data = {
                "success": True,
                "reward_signals": [{"domain": "combat", "value": 0.6, "confidence": 0.8}],
                "aggregate_reward": 0.6
            }
            self.manager.record_decision(session_id, char, decision_data, outcome_data)
        
        summary = self.manager.get_session_summary(session_id)
        
        assert "session" in summary
        assert "characters" in summary
        assert len(summary["characters"]) == 2
        assert "thorin" in summary["characters"]
        assert summary["is_active"] == True
        
        print("✓ Session summary retrieved")
    
    def test_character_session_history(self):
        """Test getting character session history"""
        # Create multiple sessions
        for i in range(3):
            session_id = self.manager.start_session(character_ids=["thorin"])
            
            decision_data = {"source": "bot", "time_taken_ms": 50.0}
            outcome_data = {
                "success": True,
                "reward_signals": [{"domain": "combat", "value": 0.5, "confidence": 0.8}],
                "aggregate_reward": 0.5
            }
            self.manager.record_decision(session_id, "thorin", decision_data, outcome_data)
            
            self.manager.end_session(session_id)
        
        history = self.manager.get_character_session_history("thorin")
        
        assert len(history) == 3
        assert all("session_id" in session for session in history)
        assert all("growth_score" in session for session in history)
        
        print(f"✓ Retrieved history: {len(history)} sessions")
    
    def test_training_opportunities(self):
        """Test identifying training opportunities"""
        # Create session with mixed quality
        session_id = self.manager.start_session(character_ids=["thorin"])
        
        for i in range(15):
            decision_data = {"source": "brain", "time_taken_ms": 200.0}
            outcome_data = {
                "success": (i % 4 != 0),
                "reward_signals": [{"domain": "combat", "value": 0.6, "confidence": 0.8}],
                "aggregate_reward": 0.6,
                "quality_analysis": {"quality_score": 0.6 if i % 4 != 0 else 0.1}
            }
            self.manager.record_decision(session_id, "thorin", decision_data, outcome_data)
        
        self.manager.end_session(session_id)
        
        opportunities = self.manager.identify_training_opportunities(
            min_quality=0.5,
            min_decisions=10
        )
        
        assert len(opportunities) > 0
        assert opportunities[0]["teaching_moments"] > 0
        
        print(f"✓ Found {len(opportunities)} training opportunities")
        print(f"   Best quality: {opportunities[0]['avg_quality']:.3f}")
    
    def test_statistics(self):
        """Test getting statistics"""
        # Create and end a session
        session_id = self.manager.start_session(character_ids=["thorin"])
        
        for i in range(5):
            decision_data = {"source": "bot", "time_taken_ms": 50.0}
            outcome_data = {
                "success": True,
                "reward_signals": [{"domain": "combat", "value": 0.5, "confidence": 0.8}],
                "aggregate_reward": 0.5,
                "quality_analysis": {"quality_score": 0.6}
            }
            self.manager.record_decision(session_id, "thorin", decision_data, outcome_data)
        
        self.manager.end_session(session_id)
        
        stats = self.manager.get_statistics()
        
        assert stats["total_sessions"] == 1
        assert stats["completed_sessions"] == 1
        assert stats["avg_decisions_per_session"] == 5
        assert stats["avg_session_reward"] > 0
        
        print(f"✓ Statistics:")
        print(f"   Total sessions: {stats['total_sessions']}")
        print(f"   Avg decisions: {stats['avg_decisions_per_session']:.1f}")
        print(f"   Avg reward: {stats['avg_session_reward']:.3f}")
    
    def test_performance(self):
        """Test performance with many decisions"""
        import time
        
        session_id = self.manager.start_session(character_ids=["thorin"])
        
        start = time.time()
        for i in range(100):
            decision_data = {"source": "bot", "time_taken_ms": 50.0}
            outcome_data = {
                "success": True,
                "reward_signals": [{"domain": "combat", "value": 0.5, "confidence": 0.8}],
                "aggregate_reward": 0.5,
                "quality_analysis": {"quality_score": 0.6}
            }
            self.manager.record_decision(session_id, "thorin", decision_data, outcome_data)
        elapsed = (time.time() - start) * 1000
        
        avg_time = elapsed / 100
        assert avg_time < 5  # Should be < 5ms per decision
        
        print(f"✓ Performance: {avg_time:.2f}ms per decision (100 decisions in {elapsed:.0f}ms)")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("SESSION MANAGER - TEST SUITE")
    print("=" * 60)
    print()
    
    test_suite = TestSessionManager()
    
    tests = [
        test_suite.test_initialization,
        test_suite.test_start_session,
        test_suite.test_add_character,
        test_suite.test_record_decision,
        test_suite.test_outcome_processing,
        test_suite.test_multi_character_session,
        test_suite.test_growth_score_calculation,
        test_suite.test_teaching_moments,
        test_suite.test_session_phases,
        test_suite.test_end_session,
        test_suite.test_session_summary,
        test_suite.test_character_session_history,
        test_suite.test_training_opportunities,
        test_suite.test_statistics,
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
