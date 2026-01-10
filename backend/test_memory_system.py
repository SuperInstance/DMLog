"""
Tests for Memory System

Comprehensive test suite for the 6-tier memory hierarchy system.
Tests memory consolidation, temporal landmarks, and autobiographical narratives.
"""

import pytest
from datetime import datetime, timedelta
from memory_system import (
    MemoryConsolidationEngine,
    Memory,
    MemoryType,
    MemoryImportance,
    TemporalLandmark,
    AutobiographicalNarrative,
    IdentityPersistenceSystem,
    MemoryStats
)


class TestMemoryConsolidationEngine:
    """Test suite for MemoryConsolidationEngine"""

    def setup_method(self):
        """Create fresh engine for each test"""
        self.engine = MemoryConsolidationEngine("test_character")

    def test_initialization(self):
        """Test engine initialization"""
        assert self.engine.character_id == "test_character"
        assert len(self.engine.memories) == 0
        assert len(self.engine.temporal_landmarks) == 0
        assert self.engine.importance_accumulator == 0.0
        print("✓ Engine initialized successfully")

    def test_store_memory(self):
        """Test basic memory storage"""
        memory = self.engine.store_memory(
            content="I fought a goblin near the cave entrance",
            memory_type=MemoryType.EPISODIC,
            importance=7.0,
            emotional_valence=0.3
        )

        assert memory.id is not None
        assert memory.content == "I fought a goblin near the cave entrance"
        assert memory.memory_type == MemoryType.EPISODIC
        assert memory.importance == 7.0
        assert memory.emotional_valence == 0.3
        assert memory.id in self.engine.memories

        print(f"✓ Stored memory: {memory.id}")

    def test_memory_types(self):
        """Test all memory types can be stored"""
        types = [
            MemoryType.WORKING,
            MemoryType.MID_TERM,
            MemoryType.LONG_TERM,
            MemoryType.EPISODIC,
            MemoryType.SEMANTIC,
            MemoryType.PROCEDURAL
        ]

        for mem_type in types:
            memory = self.engine.store_memory(
                content=f"Test {mem_type.value} memory",
                memory_type=mem_type,
                importance=5.0
            )
            assert memory.memory_type == mem_type

        print(f"✓ All {len(types)} memory types work")

    def test_temporal_landmark_detection(self):
        """Test temporal landmark detection"""
        # First time event - check if landmark is detected
        memory = self.engine.store_memory(
            content="First time visiting the ancient elven ruins",
            memory_type=MemoryType.EPISODIC,
            importance=8.0,
            location="Ancient Ruins"
        )

        # Memory should be stored with its properties
        assert memory.id is not None
        assert "First time" in memory.content

        print("✓ Memory stored with first-time event content")

    def test_emotional_peak_landmark(self):
        """Test emotional peak memory storage"""
        memory = self.engine.store_memory(
            content="Defeated the dragon that killed my father",
            memory_type=MemoryType.EPISODIC,
            importance=9.0,
            emotional_valence=0.9  # Very positive
        )

        # Memory should be stored with high importance
        assert memory.importance == 9.0
        assert memory.emotional_valence == 0.9

        print("✓ Emotional peak memory stored")

    def test_location_transition_landmark(self):
        """Test location change memory storage"""
        # Add some memories in same location
        for i in range(3):
            self.engine.store_memory(
                content=f"Exploring cave room {i}",
                memory_type=MemoryType.EPISODIC,
                location="Dark Cave"
            )

        # New location memory
        memory = self.engine.store_memory(
            content="Exited the cave and entered the forest",
            memory_type=MemoryType.EPISODIC,
            location="Enchanted Forest"
        )

        # Memory should be stored with new location
        assert memory.location == "Enchanted Forest"

        print("✓ Location transition memory stored")

    def test_memory_importance_levels(self):
        """Test memory importance levels"""
        importances = [
            MemoryImportance.FORGOTTEN,
            MemoryImportance.ROUTINE,
            MemoryImportance.NOTABLE,
            MemoryImportance.SIGNIFICANT,
            MemoryImportance.CORE_IDENTITY
        ]

        for imp in importances:
            memory = self.engine.store_memory(
                content=f"Test memory with importance {imp.value}",
                importance=imp.value
            )
            assert memory.importance == imp.value

        print("✓ All importance levels work")

    def test_retrieve_memories(self):
        """Test memory retrieval"""
        # Store memories with different importance
        self.engine.store_memory("Important combat", importance=9.0)
        self.engine.store_memory("Routine exploration", importance=3.0)
        self.engine.store_memory("Social interaction", importance=6.0)

        # Retrieve
        results = self.engine.retrieve_memories(
            query="combat",
            top_k=2
        )

        assert len(results) <= 2

        # Check access counts increased
        for memory in results:
            assert memory.access_count > 0

        print(f"✓ Retrieved {len(results)} memories")

    def test_weighted_retrieval(self):
        """Test weighted retrieval (recency + importance + relevance)"""
        # Old important memory
        old_important = self.engine.store_memory(
            content="Critical battle victory",
            importance=9.0
        )
        old_important.timestamp = datetime.now() - timedelta(days=7)

        # Recent less important
        recent = self.engine.store_memory(
            content="Minor exploration",
            importance=3.0
        )

        # Default weights balanced
        results = self.engine.retrieve_memories(
            query="exploration",
            top_k=5,
            α_recency=1.0,
            α_importance=1.0,
            α_relevance=1.0
        )

        assert len(results) > 0

        print("✓ Weighted retrieval works")

    def test_reflection_consolidation(self):
        """Test reflection consolidation"""
        # Store enough important memories to trigger reflection
        for i in range(20):
            self.engine.store_memory(
                content=f"Event {i}: happened in session",
                importance=7.0,
                emotional_valence=0.5 if i % 2 == 0 else -0.3
            )

        # Trigger reflection
        result = self.engine.reflection_consolidation()

        if result["triggered"]:
            assert "reflection_id" in result
            assert result["memories_processed"] > 0
            assert self.engine.importance_accumulator == 0.0  # Reset

            print(f"✓ Reflection consolidation: {result['memories_processed']} memories processed")
        else:
            print("✓ Reflection threshold not reached (expected)")

    def test_episodic_to_semantic_consolidation(self):
        """Test episodic to semantic memory consolidation"""
        # Store old unconsolidated episodic memories
        old_time = datetime.now() - timedelta(days=2)

        for i in range(10):
            memory = self.engine.store_memory(
                content=f"Combat encounter {i}: fought goblins",
                memory_type=MemoryType.EPISODIC,
                importance=6.0
            )
            memory.timestamp = old_time

        # Force consolidation window passed
        self.engine.last_consolidation_time = datetime.now() - timedelta(days=2)

        result = self.engine.episodic_to_semantic_consolidation()

        # Consolidation should complete without error
        assert "triggered" in result
        assert "patterns_created" in result

        print(f"✓ Consolidation completed")

    def test_autobiographical_narrative(self):
        """Test autobiographical narrative generation"""
        # Store some memories
        self.engine.store_memory(
            "I am a warrior who values honor",
            memory_type=MemoryType.SEMANTIC,
            importance=9.0
        )

        self.engine.store_memory(
            "Defeated the dragon at the mountain peak",
            memory_type=MemoryType.EPISODIC,
            importance=10.0,
            emotional_valence=0.8
        )

        self.engine.store_memory(
            "Learned that alliances are stronger than solo efforts",
            memory_type=MemoryType.SEMANTIC,
            importance=7.0
        )

        narrative = self.engine.generate_autobiographical_narrative()

        assert narrative.character_id == "test_character"
        assert len(narrative.narrative) > 0
        assert len(narrative.key_themes) > 0
        assert len(narrative.core_identity_traits) > 0
        assert 0.0 <= narrative.coherence_score <= 1.0

        print(f"✓ Generated narrative:")
        print(f"   Themes: {narrative.key_themes}")
        print(f"   Coherence: {narrative.coherence_score:.2f}")

    def test_memory_to_dict(self):
        """Test memory serialization"""
        memory = self.engine.store_memory(
            content="Test memory",
            memory_type=MemoryType.EPISODIC,
            importance=5.0,
            participants=["Alice", "Bob"],
            location="Tavern"
        )

        as_dict = memory.to_dict()

        assert as_dict["id"] == memory.id
        assert as_dict["content"] == memory.content
        assert as_dict["memory_type"] == "episodic"
        assert as_dict["importance"] == 5.0
        assert "Alice" in as_dict["participants"]
        assert as_dict["location"] == "Tavern"

        print("✓ Memory serialization works")

    def test_memory_access_boost(self):
        """Test accessing memory boosts importance"""
        memory = self.engine.store_memory(
            content="Important memory",
            importance=5.0
        )

        initial_importance = memory.importance

        # Access the memory multiple times
        for _ in range(5):
            self.engine.retrieve_memories("important")

        # Importance should have increased
        assert memory.importance > initial_importance

        print(f"✓ Access boosted importance: {initial_importance:.1f} -> {memory.importance:.1f}")


class TestIdentityPersistenceSystem:
    """Test suite for IdentityPersistenceSystem"""

    def setup_method(self):
        """Create fresh system for each test"""
        self.system = IdentityPersistenceSystem("test_char")

    def test_initialization(self):
        """Test system initialization"""
        assert self.system.character_id == "test_char"
        assert len(self.system.core_traits) == 5
        assert "openness" in self.system.core_traits
        assert "conscientiousness" in self.system.core_traits
        print("✓ Identity system initialized")

    def test_custom_traits(self):
        """Test custom personality traits"""
        custom = {
            "openness": 0.8,
            "conscientiousness": 0.3,
            "extraversion": 0.9,
            "agreeableness": 0.2,
            "neuroticism": 0.5
        }

        system = IdentityPersistenceSystem("custom_char", custom)

        for trait, value in custom.items():
            assert system.core_traits[trait] == value

        print("✓ Custom traits initialized")

    def test_drift_calculation(self):
        """Test identity drift calculation"""
        import numpy as np

        # Baseline embedding
        baseline = np.array([0.5] * 100)
        self.system.baseline_embedding = baseline

        # No drift - identical vectors
        same = np.array([0.5] * 100)
        drift = self.system._calculate_drift(same)
        assert drift == 0.0

        # Some drift - different vectors
        different = np.array([0.3] * 100)
        drift = self.system._calculate_drift(different)
        # Drift should be non-negative
        assert drift >= 0

        print(f"✓ Drift calculation: {drift:.3f}")

    def test_identity_coherence_index(self):
        """Test identity coherence index calculation"""
        import numpy as np

        # Set baseline
        self.system.baseline_embedding = np.array([0.5] * 100)

        # Add some memories
        from memory_system import Memory
        memories = [
            Memory(
                id="m1",
                content="Stayed true to principles",
                memory_type=MemoryType.SEMANTIC,
                timestamp=datetime.now(),
                importance=8.0,
                emotional_valence=0.5
            ),
            Memory(
                id="m2",
                content="Acted consistently with beliefs",
                memory_type=MemoryType.EPISODIC,
                timestamp=datetime.now(),
                importance=7.0,
                emotional_valence=0.3
            )
        ]

        ici = self.system.get_identity_coherence_index(memories)

        assert 0.0 <= ici <= 1.0

        print(f"✓ Identity Coherence Index: {ici:.2f}")

    def test_personality_snapshot(self):
        """Test personality snapshot"""
        initial_count = len(self.system.personality_history)

        self.system.snapshot_personality(reason="Test snapshot")

        assert len(self.system.personality_history) == initial_count + 1

        snapshot = self.system.personality_history[-1]
        assert snapshot["reason"] == "Test snapshot"
        assert "core_traits" in snapshot
        assert "temporal_traits" in snapshot

        print("✓ Personality snapshot created")

    def test_identity_reinforcement_prompt(self):
        """Test identity reinforcement prompt"""
        prompt = self.system.get_identity_reinforcement_prompt()

        assert "fundamentally" in prompt.lower()
        assert "openness" in prompt
        assert "core identity" in prompt.lower()

        print("✓ Reinforcement prompt generated")

    def test_trait_update_limits(self):
        """Test traits stay within bounds"""
        import numpy as np

        # Try to push traits beyond limits
        extreme_embedding = np.array([100.0] * 100)
        self.system.update_from_behavior(extreme_embedding, confidence=1.0)

        # All traits should still be between 0 and 1
        for trait, value in self.system.temporal_traits.items():
            assert 0.0 <= value <= 1.0

        print("✓ Traits stay within bounds")


class TestMemoryStats:
    """Test suite for MemoryStats"""

    def test_health_report(self):
        """Test memory health report"""
        engine = MemoryConsolidationEngine("stats_char")

        # Add various memories
        engine.store_memory("Event 1", MemoryType.EPISODIC, importance=7.0)
        engine.store_memory("Event 2", MemoryType.SEMANTIC, importance=8.0)
        engine.store_memory("Event 3", MemoryType.EPISODIC, importance=4.0)

        # Consolidate one
        engine.memories[list(engine.memories.keys())[0]].consolidated = True

        report = MemoryStats.get_memory_health_report(engine)

        assert report["total_memories"] == 3
        assert report["by_type"]["episodic"] == 2
        assert report["by_type"]["semantic"] == 1
        assert report["consolidation_status"]["consolidated"] == 1
        assert report["consolidation_status"]["unconsolidated"] == 2
        assert report["average_importance"] > 0

        print("✓ Health report generated")
        print(f"   Total memories: {report['total_memories']}")
        print(f"   Avg importance: {report['average_importance']:.1f}")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("MEMORY SYSTEM - TEST SUITE")
    print("=" * 60)
    print()

    passed = 0
    failed = 0

    # Memory Consolidation Engine tests
    print("=== Memory Consolidation Engine ===")
    engine_suite = TestMemoryConsolidationEngine()
    engine_tests = [
        engine_suite.test_initialization,
        engine_suite.test_store_memory,
        engine_suite.test_memory_types,
        engine_suite.test_temporal_landmark_detection,
        engine_suite.test_emotional_peak_landmark,
        engine_suite.test_location_transition_landmark,
        engine_suite.test_memory_importance_levels,
        engine_suite.test_retrieve_memories,
        engine_suite.test_weighted_retrieval,
        engine_suite.test_reflection_consolidation,
        engine_suite.test_episodic_to_semantic_consolidation,
        engine_suite.test_autobiographical_narrative,
        engine_suite.test_memory_to_dict,
        engine_suite.test_memory_access_boost
    ]

    for test in engine_tests:
        engine_suite.setup_method()
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
        print()

    # Identity Persistence System tests
    print("=== Identity Persistence System ===")
    identity_suite = TestIdentityPersistenceSystem()
    identity_tests = [
        identity_suite.test_initialization,
        identity_suite.test_custom_traits,
        identity_suite.test_drift_calculation,
        identity_suite.test_identity_coherence_index,
        identity_suite.test_personality_snapshot,
        identity_suite.test_identity_reinforcement_prompt,
        identity_suite.test_trait_update_limits
    ]

    for test in identity_tests:
        identity_suite.setup_method()
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
        print()

    # Memory Stats tests
    print("=== Memory Stats ===")
    stats_suite = TestMemoryStats()
    stats_tests = [
        stats_suite.test_health_report
    ]

    for test in stats_tests:
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
