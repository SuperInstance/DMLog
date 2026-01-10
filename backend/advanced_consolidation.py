"""
AI Society D&D - Advanced Memory Consolidation
===============================================
Enhanced consolidation algorithms beyond the basic system.

Improvements:
- Cluster-based consolidation (group similar memories)
- Adaptive consolidation triggers (learns when to consolidate)
- Quality-aware consolidation (preserves important details)
- Incremental consolidation (don't wait for full batch)
- Cross-memory inference (derive new knowledge from patterns)

Phase 7 Enhanced:
- Integration with training data collector
- Decision-based consolidation triggers
- Learning-aware consolidation prioritization
"""

from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
import hashlib
import logging

logger = logging.getLogger(__name__)

# Import training data collector for Phase 7 integration
try:
    from training_data_collector import TrainingDataCollector
    TRAINING_DATA_AVAILABLE = True
except ImportError:
    TRAINING_DATA_AVAILABLE = False
    logger.warning("TrainingDataCollector not available - decision consolidation disabled")


# ============================================================================
# ADVANCED CONSOLIDATION STRATEGIES
# ============================================================================

class ConsolidationStrategy:
    """Base class for consolidation strategies"""
    
    def should_consolidate(self, memory_engine) -> bool:
        """Determine if consolidation should happen"""
        raise NotImplementedError
    
    def select_memories(self, memory_engine) -> List:
        """Select memories to consolidate"""
        raise NotImplementedError
    
    def consolidate(self, memories: List) -> List:
        """Perform consolidation"""
        raise NotImplementedError


class ClusterBasedConsolidation(ConsolidationStrategy):
    """
    Consolidate memories by clustering similar ones.
    
    Example:
    - "Fought goblin near river"
    - "Defeated goblin by bridge"
    - "Killed goblin at water crossing"
    → "Encounters with goblins near water are common"
    """
    
    def __init__(self, min_cluster_size: int = 3):
        self.min_cluster_size = min_cluster_size
        self.vectorizer = TfidfVectorizer(max_features=100)
    
    def should_consolidate(self, memory_engine) -> bool:
        """Consolidate when we have enough unconsolidated memories"""
        unconsolidated = [
            m for m in memory_engine.memories.values()
            if not m.consolidated
        ]
        return len(unconsolidated) >= self.min_cluster_size * 3
    
    def select_memories(self, memory_engine) -> List:
        """Select all unconsolidated episodic memories"""
        return [
            m for m in memory_engine.memories.values()
            if not m.consolidated and m.memory_type.value == "episodic"
        ]
    
    def consolidate(self, memories: List) -> List:
        """Cluster and consolidate memories"""
        if len(memories) < self.min_cluster_size:
            return []
        
        # Extract text
        texts = [m.content for m in memories]
        
        try:
            # Vectorize
            vectors = self.vectorizer.fit_transform(texts).toarray()
            
            # Cluster
            clustering = DBSCAN(eps=0.5, min_samples=self.min_cluster_size)
            labels = clustering.fit_predict(vectors)
            
            # Create consolidated memories from clusters
            consolidated = []
            for label in set(labels):
                if label == -1:  # Noise
                    continue
                
                cluster_memories = [m for i, m in enumerate(memories) if labels[i] == label]
                if len(cluster_memories) >= self.min_cluster_size:
                    # Create consolidated memory
                    consolidated_memory = self._merge_memories(cluster_memories)
                    consolidated.append(consolidated_memory)
            
            return consolidated
        
        except Exception as e:
            print(f"Clustering error: {e}")
            return []
    
    def _merge_memories(self, memories: List) -> Any:
        """Merge cluster of memories into semantic memory"""
        from memory_system import Memory, MemoryType
        
        # Extract common themes
        all_words = []
        for m in memories:
            all_words.extend(m.content.lower().split())
        
        word_freq = defaultdict(int)
        for word in all_words:
            if len(word) > 3:  # Skip short words
                word_freq[word] += 1
        
        # Find common words
        common_themes = [
            word for word, freq in sorted(word_freq.items(), key=lambda x: -x[1])[:5]
        ]
        
        # Create consolidated content
        content = f"Pattern identified: {', '.join(common_themes)}. "
        content += f"Based on {len(memories)} similar experiences."
        
        # Average importance
        avg_importance = np.mean([m.importance for m in memories])
        
        # Create new memory
        memory_id = hashlib.md5(
            f"{memories[0].id}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        return Memory(
            id=memory_id,
            content=content,
            memory_type=MemoryType.SEMANTIC,
            timestamp=datetime.now(),
            importance=avg_importance,
            consolidated=True,
            consolidation_source_ids=[m.id for m in memories]
        )


class AdaptiveConsolidation(ConsolidationStrategy):
    """
    Learns optimal consolidation timing.
    
    Tracks:
    - When consolidation helps retrieval
    - When consolidation loses important details
    - Optimal batch sizes
    """
    
    def __init__(self):
        self.consolidation_history: List[Dict] = []
        self.retrieval_quality_before: Dict[str, float] = {}
        self.retrieval_quality_after: Dict[str, float] = {}
        
        # Learned parameters
        self.optimal_batch_size = 20
        self.optimal_interval_hours = 24
        self.last_consolidation: Optional[datetime] = None
    
    def should_consolidate(self, memory_engine) -> bool:
        """Consolidate based on learned timing"""
        if self.last_consolidation is None:
            # First time
            return len(memory_engine.memories) >= self.optimal_batch_size
        
        hours_since = (datetime.now() - self.last_consolidation).total_seconds() / 3600
        
        # Check if enough time has passed
        if hours_since < self.optimal_interval_hours:
            return False
        
        # Check if enough new memories
        unconsolidated = [m for m in memory_engine.memories.values() if not m.consolidated]
        return len(unconsolidated) >= self.optimal_batch_size
    
    def select_memories(self, memory_engine) -> List:
        """Select batch of optimal size"""
        unconsolidated = [
            m for m in memory_engine.memories.values()
            if not m.consolidated and m.memory_type.value == "episodic"
        ]
        
        # Sort by importance (consolidate less important first)
        unconsolidated.sort(key=lambda m: m.importance)
        
        return unconsolidated[:self.optimal_batch_size]
    
    def consolidate(self, memories: List) -> List:
        """Consolidate and track quality"""
        # Record before state
        self.retrieval_quality_before[datetime.now().isoformat()] = self._assess_retrieval_quality(memories)
        
        # Perform consolidation (use cluster-based)
        cluster_strategy = ClusterBasedConsolidation()
        consolidated = cluster_strategy.consolidate(memories)
        
        # Record after state
        self.retrieval_quality_after[datetime.now().isoformat()] = self._assess_retrieval_quality(consolidated)
        
        # Update learned parameters
        self._update_parameters()
        
        self.last_consolidation = datetime.now()
        
        return consolidated
    
    def _assess_retrieval_quality(self, memories: List) -> float:
        """Assess how easily memories can be retrieved"""
        if not memories:
            return 0.0
        
        # Simple heuristic: importance * recency
        scores = []
        for m in memories:
            age_hours = (datetime.now() - m.timestamp).total_seconds() / 3600
            recency_factor = 0.995 ** age_hours
            score = m.importance * recency_factor
            scores.append(score)
        
        return np.mean(scores)
    
    def _update_parameters(self):
        """Learn from consolidation history"""
        if len(self.consolidation_history) < 5:
            return  # Not enough data
        
        # Analyze if quality improved
        improvements = []
        for before_time, before_quality in self.retrieval_quality_before.items():
            if before_time in self.retrieval_quality_after:
                after_quality = self.retrieval_quality_after[before_time]
                improvement = after_quality - before_quality
                improvements.append(improvement)
        
        if improvements:
            avg_improvement = np.mean(improvements)
            
            # If consolidation helps, consolidate more often
            if avg_improvement > 0:
                self.optimal_interval_hours = max(12, self.optimal_interval_hours * 0.9)
            else:
                # If it hurts, consolidate less often
                self.optimal_interval_hours = min(72, self.optimal_interval_hours * 1.1)


class IncrementalConsolidation(ConsolidationStrategy):
    """
    Consolidate continuously in small batches.
    
    Don't wait for big batch - process memories as they come.
    """
    
    def __init__(self, batch_size: int = 5):
        self.batch_size = batch_size
        self.last_processed_index = 0
    
    def should_consolidate(self, memory_engine) -> bool:
        """Always ready to consolidate if we have a small batch"""
        unconsolidated = [m for m in memory_engine.memories.values() if not m.consolidated]
        return len(unconsolidated) >= self.batch_size
    
    def select_memories(self, memory_engine) -> List:
        """Select next batch"""
        unconsolidated = [
            m for m in memory_engine.memories.values()
            if not m.consolidated and m.memory_type.value == "episodic"
        ]
        
        # Sort by timestamp (oldest first)
        unconsolidated.sort(key=lambda m: m.timestamp)
        
        return unconsolidated[:self.batch_size]
    
    def consolidate(self, memories: List) -> List:
        """Quick consolidation of small batch"""
        if len(memories) < 2:
            return []
        
        # Group by similarity (simple keyword matching)
        groups = self._group_by_keywords(memories)
        
        consolidated = []
        for group in groups:
            if len(group) >= 2:
                merged = self._quick_merge(group)
                consolidated.append(merged)
        
        return consolidated
    
    def _group_by_keywords(self, memories: List) -> List[List]:
        """Group memories by shared keywords"""
        groups = []
        used = set()
        
        for i, m1 in enumerate(memories):
            if i in used:
                continue
            
            group = [m1]
            words1 = set(m1.content.lower().split())
            
            for j, m2 in enumerate(memories[i+1:], i+1):
                if j in used:
                    continue
                
                words2 = set(m2.content.lower().split())
                overlap = len(words1 & words2) / len(words1 | words2)
                
                if overlap > 0.3:  # 30% word overlap
                    group.append(m2)
                    used.add(j)
            
            used.add(i)
            groups.append(group)
        
        return groups
    
    def _quick_merge(self, memories: List) -> Any:
        """Quick merge of similar memories"""
        from memory_system import Memory, MemoryType
        
        # Simple: take most important memory's content
        memories.sort(key=lambda m: m.importance, reverse=True)
        base = memories[0]
        
        content = f"Learned: {base.content} (from {len(memories)} experiences)"
        
        memory_id = hashlib.md5(
            f"{base.id}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        return Memory(
            id=memory_id,
            content=content,
            memory_type=MemoryType.SEMANTIC,
            timestamp=datetime.now(),
            importance=base.importance,
            consolidated=True,
            consolidation_source_ids=[m.id for m in memories]
        )


# ============================================================================
# CONSOLIDATION MANAGER
# ============================================================================

class AdvancedConsolidationManager:
    """
    Manages multiple consolidation strategies.
    Selects best strategy based on situation.
    """
    
    def __init__(self):
        self.strategies = {
            "cluster": ClusterBasedConsolidation(),
            "adaptive": AdaptiveConsolidation(),
            "incremental": IncrementalConsolidation()
        }
        
        self.default_strategy = "incremental"
        self.consolidation_log: List[Dict] = []
    
    async def consolidate(
        self,
        memory_engine,
        strategy_name: Optional[str] = None
    ) -> Tuple[int, List]:
        """
        Run consolidation with specified or best strategy.
        
        Returns: (num_consolidated, new_semantic_memories)
        """
        strategy_name = strategy_name or self.default_strategy
        strategy = self.strategies.get(strategy_name)
        
        if not strategy:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        # Check if should consolidate
        if not strategy.should_consolidate(memory_engine):
            return 0, []
        
        # Select memories
        memories_to_consolidate = strategy.select_memories(memory_engine)
        
        if not memories_to_consolidate:
            return 0, []
        
        # Consolidate
        new_semantic = strategy.consolidate(memories_to_consolidate)
        
        # Mark originals as consolidated
        for m in memories_to_consolidate:
            m.consolidated = True
        
        # Add new semantic memories
        for sem in new_semantic:
            memory_engine.memories[sem.id] = sem
        
        # Log
        self.consolidation_log.append({
            "timestamp": datetime.now().isoformat(),
            "strategy": strategy_name,
            "input_count": len(memories_to_consolidate),
            "output_count": len(new_semantic)
        })
        
        return len(memories_to_consolidate), new_semantic
    
    def get_consolidation_stats(self) -> Dict[str, Any]:
        """Get consolidation statistics"""
        if not self.consolidation_log:
            return {"message": "No consolidations yet"}
        
        total_consolidated = sum(e["input_count"] for e in self.consolidation_log)
        total_semantic = sum(e["output_count"] for e in self.consolidation_log)
        
        compression_ratio = total_consolidated / total_semantic if total_semantic > 0 else 0
        
        strategy_usage = defaultdict(int)
        for entry in self.consolidation_log:
            strategy_usage[entry["strategy"]] += 1
        
        return {
            "total_consolidations": len(self.consolidation_log),
            "total_memories_consolidated": total_consolidated,
            "total_semantic_created": total_semantic,
            "compression_ratio": compression_ratio,
            "strategy_usage": dict(strategy_usage)
        }


# ============================================================================
# CROSS-MEMORY INFERENCE
# ============================================================================

class MemoryInference:
    """
    Derive new knowledge by finding patterns across memories.
    
    Example:
    Memory 1: "Orcs attack at night"
    Memory 2: "Heard orcs during dark hours"  
    Memory 3: "Orc raid happened after sunset"
    → Inference: "Orcs prefer nighttime attacks"
    """
    
    @staticmethod
    def infer_patterns(memories: List) -> List:
        """Find patterns and create inferred memories"""
        from memory_system import Memory, MemoryType
        
        inferences = []
        
        # Group by actor/subject
        actor_actions = defaultdict(list)
        for m in memories:
            words = m.content.lower().split()
            # Simple heuristic: first noun is often the actor
            for word in words:
                if len(word) > 3 and word not in ['with', 'from', 'that']:
                    actor_actions[word].append(m)
                    break
        
        # Find actors with multiple memories
        for actor, actor_memories in actor_actions.items():
            if len(actor_memories) >= 3:
                # Find common themes
                all_text = " ".join([m.content.lower() for m in actor_memories])
                
                # Simple pattern: actor + common words
                words = all_text.split()
                word_freq = defaultdict(int)
                for w in words:
                    if len(w) > 3:
                        word_freq[w] += 1
                
                common_words = [
                    w for w, freq in word_freq.items()
                    if freq >= 2 and w != actor
                ][:3]
                
                if common_words:
                    inference_text = f"Pattern: {actor} often {', '.join(common_words)}"

                    memory_id = hashlib.md5(
                        f"inference_{actor}{datetime.now().isoformat()}".encode()
                    ).hexdigest()[:16]

                    inferred = Memory(
                        id=memory_id,
                        content=inference_text,
                        memory_type=MemoryType.SEMANTIC,
                        timestamp=datetime.now(),
                        importance=7.0,  # Inferences are important
                        consolidated=True,
                        consolidation_source_ids=[m.id for m in actor_memories]
                    )
                    inferences.append(inferred)

        return inferences


# ============================================================================
# PHASE 7: LEARNING-AWARE CONSOLIDATION
# ============================================================================

class LearningAwareConsolidation:
    """
    Consolidates episodic decisions into semantic knowledge for learning.

    This bridges the gap between:
    - Raw gameplay decisions (logged by TrainingDataCollector)
    - Semantic memories (used by MemoryConsolidationEngine)
    - Training data (used by QLoRA trainer)

    Phase 7.2.2 - Enhanced consolidation for learning pipeline
    """

    def __init__(
        self,
        character_id: str,
        training_data_collector: Optional[TrainingDataCollector] = None
    ):
        """
        Initialize learning-aware consolidation

        Args:
            character_id: Character ID
            training_data_collector: Optional training data collector instance
        """
        self.character_id = character_id
        self.training_collector = training_data_collector
        self.consolidation_history: List[Dict] = []

        # Consolidation thresholds
        self.min_decisions_for_consolidation = 10
        self.consolidation_interval_hours = 24
        self.last_consolidation: Optional[datetime] = None

    async def consolidate_recent_decisions(
        self,
        memory_engine
    ) -> Dict[str, Any]:
        """
        Consolidate recent decisions from training data into semantic memories

        Args:
            memory_engine: MemoryConsolidationEngine instance

        Returns:
            Consolidation report
        """
        if not self.training_collector:
            logger.warning("No training data collector - cannot consolidate decisions")
            return {"triggered": False, "reason": "No training data collector"}

        # Check if enough time has passed
        if self.last_consolidation:
            hours_since = (datetime.now() - self.last_consolidation).total_seconds() / 3600
            if hours_since < self.consolidation_interval_hours:
                return {
                    "triggered": False,
                    "reason": f"Too soon ({hours_since:.1f}h < {self.consolidation_interval_hours}h)"
                }

        # Get recent decisions from training data
        decisions = self.training_collector.get_training_eligible_decisions(
            character_id=self.character_id,
            limit=100
        )

        if len(decisions) < self.min_decisions_for_consolidation:
            return {
                "triggered": False,
                "reason": f"Insufficient decisions ({len(decisions)} < {self.min_decisions_for_consolidation})"
            }

        logger.info(f"Consolidating {len(decisions)} decisions for {self.character_id}")

        # Group by decision type
        by_type = self._group_by_decision_type(decisions)

        semantic_memories_created = []

        # Consolidate each type group
        for decision_type, type_decisions in by_type.items():
            if len(type_decisions) >= 3:  # Need at least 3 examples
                semantic_memory = self._consolidate_decision_group(
                    decision_type, type_decisions, memory_engine
                )
                if semantic_memory:
                    semantic_memories_created.append(semantic_memory)

        # Record consolidation
        self.last_consolidation = datetime.now()
        self.consolidation_history.append({
            "timestamp": datetime.now().isoformat(),
            "decisions_processed": len(decisions),
            "semantic_created": len(semantic_memories_created)
        })

        logger.info(f"Created {len(semantic_memories_created)} semantic memories")

        return {
            "triggered": True,
            "decisions_processed": len(decisions),
            "semantic_created": len(semantic_memories_created),
            "by_type": {k: len(v) for k, v in by_type.items()}
        }

    def _group_by_decision_type(self, decisions: List[Dict]) -> Dict[str, List[Dict]]:
        """Group decisions by type for consolidation"""
        by_type = defaultdict(list)

        for d in decisions:
            decision_type = d.get('decision_data', {}).get('decision_type', 'unknown')
            by_type[decision_type].append(d)

        return dict(by_type)

    def _consolidate_decision_group(
        self,
        decision_type: str,
        decisions: List[Dict],
        memory_engine
    ) -> Optional[Any]:
        """
        Consolidate a group of similar decisions into semantic memory

        Args:
            decision_type: Type of decision
            decisions: List of decisions of this type
            memory_engine: Memory engine to store semantic memory

        Returns:
            Created Memory object or None
        """
        from memory_system import Memory, MemoryType

        # Analyze success patterns
        successful = [d for d in decisions if d.get('success')]
        failed = [d for d in decisions if not d.get('success')]

        # Extract successful patterns
        successful_patterns = self._extract_success_patterns(successful)

        # Extract failure patterns
        failure_patterns = self._extract_failure_patterns(failed)

        # Build semantic memory content
        content_parts = []

        if successful_patterns:
            content_parts.append(f"I have learned from {len(successful)} successful {decision_type} decisions:")
            for pattern in successful_patterns[:3]:
                content_parts.append(f"  - {pattern}")

        if failure_patterns:
            content_parts.append(f"\nI have learned from {len(failed)} failed {decision_type} decisions:")
            for pattern in failure_patterns[:3]:
                content_parts.append(f"  - {pattern}")

        if not content_parts:
            return None

        content = "\n".join(content_parts)

        # Calculate importance based on decision count and success rate
        success_rate = len(successful) / len(decisions) if decisions else 0.5
        importance = 5.0 + (len(decisions) * 0.1) + abs(success_rate - 0.5) * 2
        importance = min(importance, 10.0)

        # Create semantic memory
        memory_id = hashlib.md5(
            f"consolidation_{self.character_id}_{decision_type}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        memory = Memory(
            id=memory_id,
            content=content,
            memory_type=MemoryType.SEMANTIC,
            timestamp=datetime.now(),
            importance=importance,
            consolidated=True,
            consolidation_source_ids=[d.get('decision_id') for d in decisions]
        )

        # Store in memory engine
        memory_engine.memories[memory_id] = memory

        return memory

    def _extract_success_patterns(self, successful_decisions: List[Dict]) -> List[str]:
        """Extract patterns from successful decisions"""
        patterns = []

        # Get common actions
        actions = []
        for d in successful_decisions:
            action = d.get('decision_data', {}).get('action', '')
            if action:
                actions.append(action)

        # Find most common successful actions
        from collections import Counter
        common_actions = Counter(actions).most_common(5)

        for action, count in common_actions:
            if count >= 2:
                # Get reasoning for this action
                reasonings = []
                for d in successful_decisions:
                    if d.get('decision_data', {}).get('action') == action:
                        reasoning = d.get('decision_data', {}).get('reasoning', '')
                        if reasoning:
                            reasonings.append(reasoning)

                if reasonings:
                    # Build pattern description
                    pattern = f"When I {action}, it tends to work"
                    if len(reasonings) >= 2:
                        pattern += " (reasons include: "
                        pattern += ", ".join(reasonings[:2])
                        pattern += ")"
                    patterns.append(pattern)

        return patterns

    def _extract_failure_patterns(self, failed_decisions: List[Dict]) -> List[str]:
        """Extract patterns from failed decisions"""
        patterns = []

        if not failed_decisions:
            return patterns

        # Get common actions that failed
        actions = []
        for d in failed_decisions:
            action = d.get('decision_data', {}).get('action', '')
            if action:
                actions.append(action)

        from collections import Counter
        common_actions = Counter(actions).most_common(5)

        for action, count in common_actions:
            if count >= 2:
                pattern = f"I should be careful when I {action} (failed {count} times)"
                patterns.append(pattern)

        return patterns

    def get_consolidation_summary(self) -> Dict[str, Any]:
        """Get summary of consolidation history"""
        if not self.consolidation_history:
            return {"message": "No consolidations yet"}

        total_decisions = sum(e["decisions_processed"] for e in self.consolidation_history)
        total_semantic = sum(e["semantic_created"] for e in self.consolidation_history)

        return {
            "total_consolidations": len(self.consolidation_history),
            "total_decisions_processed": total_decisions,
            "total_semantic_created": total_semantic,
            "last_consolidation": self.last_consolidation.isoformat() if self.last_consolidation else None,
            "compression_ratio": total_decisions / total_semantic if total_semantic > 0 else 0
        }


class DreamCycleCoordinator:
    """
    Coordinates the dream cycle for character learning.

    The dream cycle is the Phase 7 learning process:
    1. ACTIVE - Character plays, decisions logged
    2. DREAMING - Session ends, prepare for training
    3. TRAINING - QLoRA fine-tuning
    4. AWAKENING - Load new model weights
    5. ACTIVE - Character returns improved

    Phase 7.3 - Dream cycle orchestration
    """

    def __init__(
        self,
        character_id: str,
        training_data_collector: Optional[TrainingDataCollector] = None,
        min_decisions_for_training: int = 100,
        min_teaching_moments: int = 10
    ):
        """
        Initialize dream cycle coordinator

        Args:
            character_id: Character ID
            training_data_collector: Training data collector instance
            min_decisions_for_training: Minimum decisions before training
            min_teaching_moments: Minimum teaching moments before training
        """
        self.character_id = character_id
        self.training_collector = training_data_collector
        self.min_decisions = min_decisions_for_training
        self.min_teaching_moments = min_teaching_moments

        self.state = CharacterState.ACTIVE
        self.state_history: List[Dict] = []

    def should_trigger_dream_cycle(self) -> Tuple[bool, str]:
        """
        Check if dream cycle should be triggered

        Returns:
            (should_trigger, reason)
        """
        if not self.training_collector:
            return False, "No training data collector"

        stats = self.training_collector.get_statistics(
            character_id=self.character_id
        )

        total_decisions = stats.get("total_decisions", 0)
        teaching_moments = stats.get("by_quality", {}).get("teaching_moment", 0)

        if total_decisions >= self.min_decisions:
            return True, f"Reached {total_decisions} decisions (threshold: {self.min_decisions})"

        if teaching_moments >= self.min_teaching_moments:
            return True, f"Reached {teaching_moments} teaching moments (threshold: {self.min_teaching_moments})"

        return False, f"Not enough data: {total_decisions}/{self.min_decisions} decisions, {teaching_moments}/{self.min_teaching_moments} teaching moments"

    def transition_to(self, new_state: CharacterState) -> bool:
        """
        Transition to a new state

        Args:
            new_state: New state to transition to

        Returns:
            True if transition allowed, False otherwise
        """
        # Define allowed transitions
        allowed_transitions = {
            CharacterState.ACTIVE: [CharacterState.DREAMING],
            CharacterState.DREAMING: [CharacterState.TRAINING, CharacterState.ACTIVE],
            CharacterState.TRAINING: [CharacterState.AWAKENING, CharacterState.ERROR],
            CharacterState.AWAKENING: [CharacterState.ACTIVE],
            CharacterState.ERROR: [CharacterState.ACTIVE]
        }

        if new_state not in allowed_transitions.get(self.state, []):
            logger.warning(f"Invalid state transition: {self.state} -> {new_state}")
            return False

        logger.info(f"Character {self.character_id}: {self.state} -> {new_state}")

        # Record transition
        self.state_history.append({
            "from": self.state.value,
            "to": new_state.value,
            "timestamp": datetime.now().isoformat()
        })

        self.state = new_state
        return True

    def get_state(self) -> CharacterState:
        """Get current character state"""
        return self.state

    def get_state_history(self) -> List[Dict]:
        """Get state transition history"""
        return self.state_history.copy()


# Import CharacterState from qlora_training if available
try:
    from qlora_training import CharacterState as QLoRACharacterState
    CharacterState = QLoRACharacterState
except ImportError:
    # Define locally if not available
    from enum import Enum

    class CharacterState(Enum):
        """States during learning cycle"""
        ACTIVE = "active"
        DREAMING = "dreaming"
        TRAINING = "training"
        AWAKENING = "awakening"
        ERROR = "error"
