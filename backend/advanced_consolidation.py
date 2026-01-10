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
"""

from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
import hashlib


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
