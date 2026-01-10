"""
Data Curation Pipeline - Phase 7 Task 7.2.2
==============================================
Prepares training data for QLoRA fine-tuning by:
1. Quality filtering - removing low-quality decisions
2. Deduplication - removing near-duplicate decisions
3. Dataset balancing - balancing success/failure ratios
4. Train/val/test splitting - creating proper splits

This is the critical preprocessing step before model training.
"""

import json
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict
import random

logger = logging.getLogger(__name__)

# Optional: For better deduplication
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence_transformers not available - using basic deduplication")


@dataclass
class CurationConfig:
    """Configuration for data curation pipeline"""
    # Quality filters
    min_confidence: float = 0.3
    min_quality_score: float = 0.4
    always_include_teaching_moments: bool = True

    # Deduplication
    deduplication_enabled: bool = True
    similarity_threshold: float = 0.95  # For embeddings
    text_similarity_threshold: float = 0.85  # For text-based

    # Balancing
    balance_success_failure: bool = True
    target_success_ratio: float = 0.65  # 65% success, 35% failure
    teaching_moment_weight: int = 3  # Teaching moments count 3x

    # Splitting
    train_ratio: float = 0.8
    val_ratio: float = 0.1
    test_ratio: float = 0.1

    # Output
    output_format: str = "jsonl"  # jsonl or parquet
    shuffle_before_split: bool = True
    stratify_by_decision_type: bool = True

    def __post_init__(self):
        """Validate configuration"""
        assert abs(self.train_ratio + self.val_ratio + self.test_ratio - 1.0) < 0.01, \
            "Split ratios must sum to 1.0"
        assert 0 <= self.target_success_ratio <= 1, \
            "target_success_ratio must be between 0 and 1"


@dataclass
class CurationReport:
    """Report from the curation pipeline"""
    input_count: int
    filtered_count: int
    deduplicated_count: int
    balanced_count: int
    final_count: int

    train_count: int = 0
    val_count: int = 0
    test_count: int = 0

    filtering_report: Dict[str, int] = field(default_factory=dict)
    deduplication_report: Dict[str, Any] = field(default_factory=dict)
    balancing_report: Dict[str, Any] = field(default_factory=dict)

    processing_time_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "input_count": self.input_count,
            "filtered_count": self.filtered_count,
            "deduplicated_count": self.deduplicated_count,
            "balanced_count": self.balanced_count,
            "final_count": self.final_count,
            "train_count": self.train_count,
            "val_count": self.val_count,
            "test_count": self.test_count,
            "filtering_report": self.filtering_report,
            "deduplication_report": self.deduplication_report,
            "balancing_report": self.balancing_report,
            "processing_time_seconds": self.processing_time_seconds
        }


class DataCurationPipeline:
    """
    Curates raw decision data into training-ready datasets.

    Pipeline stages:
    1. Quality Filtering - Remove low-quality decisions
    2. Deduplication - Remove near-duplicates
    3. Balancing - Balance success/failure ratios
    4. Splitting - Create train/val/test splits
    """

    def __init__(
        self,
        config: Optional[CurationConfig] = None,
        embedding_model: Optional[str] = "all-MiniLM-L6-v2"
    ):
        """
        Initialize the curation pipeline

        Args:
            config: Curation configuration
            embedding_model: Sentence transformer model for deduplication
        """
        self.config = config or CurationConfig()
        self.embedding_model_name = embedding_model
        self.embedder = None

        # Initialize sentence transformer if available
        if SENTENCE_TRANSFORMERS_AVAILABLE and self.config.deduplication_enabled:
            try:
                self.embedder = SentenceTransformer(embedding_model)
                logger.info(f"Loaded sentence transformer: {embedding_model}")
            except Exception as e:
                logger.warning(f"Failed to load sentence transformer: {e}")

        self.report = CurationReport(
            input_count=0,
            filtered_count=0,
            deduplicated_count=0,
            balanced_count=0,
            final_count=0
        )

    def curate(
        self,
        decisions: List[Dict[str, Any]],
        character_id: str,
        output_dir: str
    ) -> CurationReport:
        """
        Run the full curation pipeline on decisions

        Args:
            decisions: Raw decision records from training_data_collector
            character_id: Character ID for logging
            output_dir: Directory to write curated datasets

        Returns:
            CurationReport with statistics
        """
        start_time = datetime.now()
        logger.info(f"Starting curation for {character_id}: {len(decisions)} decisions")

        self.report.input_count = len(decisions)

        # Stage 1: Quality Filtering
        filtered = self._quality_filter(decisions)
        self.report.filtered_count = len(filtered)
        logger.info(f"After filtering: {len(filtered)} decisions")

        # Stage 2: Deduplication
        if self.config.deduplication_enabled:
            deduplicated = self._deduplicate(filtered)
            self.report.deduplicated_count = len(deduplicated)
            logger.info(f"After deduplication: {len(deduplicated)} decisions")
        else:
            deduplicated = filtered
            self.report.deduplicated_count = len(deduplicated)

        # Stage 3: Balancing
        if self.config.balance_success_failure:
            balanced = self._balance_dataset(deduplicated)
            self.report.balanced_count = len(balanced)
            logger.info(f"After balancing: {len(balanced)} decisions")
        else:
            balanced = deduplicated
            self.report.balanced_count = len(deduplicated)

        # Stage 4: Splitting
        train, val, test = self._split_dataset(balanced)
        self.report.train_count = len(train)
        self.report.val_count = len(val)
        self.report.test_count = len(test)
        self.report.final_count = len(train) + len(val) + len(test)

        # Write outputs
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        self._write_split(train, output_path / "train.jsonl")
        self._write_split(val, output_path / "val.jsonl")
        self._write_split(test, output_path / "test.jsonl")

        # Write metadata
        metadata = {
            "character_id": character_id,
            "curation_timestamp": datetime.now().isoformat(),
            "config": {
                "min_confidence": self.config.min_confidence,
                "min_quality_score": self.config.min_quality_score,
                "target_success_ratio": self.config.target_success_ratio,
                "teaching_moment_weight": self.config.teaching_moment_weight
            },
            "report": self.report.to_dict()
        }
        with open(output_path / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

        self.report.processing_time_seconds = (datetime.now() - start_time).total_seconds()
        logger.info(f"Curation complete: {self.report.final_count} decisions in {self.report.processing_time_seconds:.1f}s")

        return self.report

    def _quality_filter(self, decisions: List[Dict]) -> List[Dict]:
        """
        Stage 1: Quality Filtering

        Removes decisions that:
        - Have confidence < min_confidence
        - Have quality_score < min_quality_score
        - Are missing critical data

        Always keeps:
        - Teaching moments (if configured)
        """
        filtered = []
        filtered_out = defaultdict(int)

        for d in decisions:
            decision_data = d.get('decision_data', {})
            outcome_data = d.get('outcome_data', {})
            quality_label = d.get('quality_label', 'unknown')

            # Always include teaching moments
            if (quality_label == 'teaching_moment' and
                self.config.always_include_teaching_moments):
                filtered.append(d)
                continue

            # Check confidence
            confidence = decision_data.get('confidence', 0.0)
            if confidence < self.config.min_confidence:
                filtered_out['low_confidence'] += 1
                continue

            # Check quality score
            quality_analysis = outcome_data.get('quality_analysis', {})
            quality_score = quality_analysis.get('quality_score', 0.5)
            if quality_score < self.config.min_quality_score:
                filtered_out['low_quality'] += 1
                continue

            # Check required fields
            if not decision_data.get('action'):
                filtered_out['missing_action'] += 1
                continue

            filtered.append(d)

        self.report.filtering_report = dict(filtered_out)
        logger.info(f"Filtered out: {dict(filtered_out)}")

        return filtered

    def _deduplicate(self, decisions: List[Dict]) -> List[Dict]:
        """
        Stage 2: Deduplication

        Removes near-duplicate decisions using:
        - Sentence embeddings (if available)
        - Text-based similarity (fallback)
        """
        if not self.config.deduplication_enabled:
            return decisions

        if self.embedder is not None:
            return self._deduplicate_with_embeddings(decisions)
        else:
            return self._deduplicate_text_based(decisions)

    def _deduplicate_with_embeddings(self, decisions: List[Dict]) -> List[Dict]:
        """
        Deduplicate using sentence transformer embeddings

        Uses cosine similarity to find near-duplicates
        """
        # Extract decision text for embedding
        texts = []
        for d in decisions:
            text = self._get_decision_text(d)
            texts.append(text)

        # Generate embeddings
        logger.info("Generating embeddings for deduplication...")
        embeddings = self.embedder.encode(texts, show_progress_bar=False)

        # Find duplicates using cosine similarity
        kept = []
        removed = []
        used_indices = set()

        for i, emb in enumerate(embeddings):
            if i in used_indices:
                continue

            # Compare with all other decisions
            for j in range(i + 1, len(embeddings)):
                if j in used_indices:
                    continue

                # Cosine similarity
                similarity = np.dot(emb, embeddings[j]) / (
                    np.linalg.norm(emb) * np.linalg.norm(embeddings[j])
                )

                if similarity >= self.config.similarity_threshold:
                    # Found duplicate - keep the higher quality one
                    quality_i = self._get_decision_quality(decisions[i])
                    quality_j = self._get_decision_quality(decisions[j])

                    if quality_i >= quality_j:
                        removed.append(j)
                        used_indices.add(j)
                    else:
                        removed.append(i)
                        used_indices.add(i)
                        break

            if i not in used_indices:
                kept.append(decisions[i])

        self.report.deduplication_report = {
            "method": "sentence_transformers",
            "model": self.embedding_model_name,
            "removed_count": len(removed),
            "kept_count": len(kept)
        }

        logger.info(f"Deduplication: removed {len(removed)} duplicates")

        return kept

    def _deduplicate_text_based(self, decisions: List[Dict]) -> List[Dict]:
        """
        Deduplicate using text-based similarity (Jaccard)

        Fallback when sentence transformers not available
        """
        kept = []
        seen_hashes = defaultdict(list)
        removed = 0

        for i, d in enumerate(decisions):
            text = self._get_decision_text(d)

            # Create simple hash of words
            words = set(text.lower().split())
            word_hash = hashlib.md5(
                " ".join(sorted(words)).encode()
            ).hexdigest()[:16]

            # Check for similar hashes
            is_duplicate = False
            for seen_hash in seen_hashes:
                # Simple Jaccard-like check
                seen_words = set(seen_hashes[seen_hash][0].lower().split())
                intersection = len(words & seen_words)
                union = len(words | seen_words)

                if union > 0 and intersection / union >= self.config.text_similarity_threshold:
                    is_duplicate = True
                    removed += 1
                    break

            if not is_duplicate:
                kept.append(d)
                seen_hashes[word_hash].append(text)

        self.report.deduplication_report = {
            "method": "text_based",
            "removed_count": removed,
            "kept_count": len(kept)
        }

        logger.info(f"Text deduplication: removed {removed} duplicates")

        return kept

    def _balance_dataset(self, decisions: List[Dict]) -> List[Dict]:
        """
        Stage 3: Dataset Balancing

        Balances success/failure ratio to target_success_ratio
        Teaching moments are weighted higher
        """
        # Separate by success and teaching moments
        successful = []
        failed = []
        teaching_moments = []

        for d in decisions:
            quality_label = d.get('quality_label', 'unknown')
            if quality_label == 'teaching_moment':
                teaching_moments.append(d)
            elif d.get('success', False):
                successful.append(d)
            else:
                failed.append(d)

        # Count with weights
        teaching_count = len(teaching_moments) * self.config.teaching_moment_weight
        current_success = len(successful) + teaching_count
        current_failure = len(failed)
        total = current_success + current_failure

        if total == 0:
            return decisions

        current_ratio = current_success / total
        target_ratio = self.config.target_success_ratio

        balanced = []

        # Always include all teaching moments
        balanced.extend(teaching_moments)

        # Balance successful and failed decisions
        if current_ratio > target_ratio:
            # Too many successes - undersample
            needed_success = int(
                (len(failed) * target_ratio) / (1 - target_ratio)
            ) - teaching_count

            needed_success = max(1, needed_success)
            balanced.extend(random.sample(successful, min(needed_success, len(successful))))
            balanced.extend(failed)  # Keep all failures

        elif current_ratio < target_ratio:
            # Too many failures - undersample
            needed_failure = int(
                ((len(successful) + teaching_count) * (1 - target_ratio)) / target_ratio
            )

            needed_failure = max(1, needed_failure)
            balanced.extend(successful)  # Keep all successes
            balanced.extend(random.sample(failed, min(needed_failure, len(failed))))

        else:
            # Already balanced
            balanced.extend(successful)
            balanced.extend(failed)

        self.report.balancing_report = {
            "original_success": len(successful),
            "original_failure": len(failed),
            "teaching_moments": len(teaching_moments),
            "original_ratio": current_ratio,
            "target_ratio": target_ratio,
            "final_success": len([d for d in balanced if d.get('success')]),
            "final_failure": len([d for d in balanced if not d.get('success')]),
            "teaching_moment_weight": self.config.teaching_moment_weight
        }

        # Shuffle balanced dataset
        random.shuffle(balanced)

        return balanced

    def _split_dataset(
        self,
        decisions: List[Dict]
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Stage 4: Train/Val/Test Splitting

        Creates stratified splits by decision type
        """
        if self.config.shuffle_before_split:
            decisions = decisions.copy()
            random.shuffle(decisions)

        if self.config.stratify_by_decision_type:
            return self._stratified_split(decisions)
        else:
            return self._simple_split(decisions)

    def _simple_split(
        self,
        decisions: List[Dict]
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Simple random split"""
        n = len(decisions)
        train_end = int(n * self.config.train_ratio)
        val_end = train_end + int(n * self.config.val_ratio)

        train = decisions[:train_end]
        val = decisions[train_end:val_end]
        test = decisions[val_end:]

        return train, val, test

    def _stratified_split(
        self,
        decisions: List[Dict]
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Stratified split by decision type"""
        # Group by decision type
        by_type = defaultdict(list)
        for d in decisions:
            decision_type = d.get('decision_data', {}).get('decision_type', 'unknown')
            by_type[decision_type].append(d)

        train, val, test = [], [], []

        # Split each type separately
        for decision_type, type_decisions in by_type.items():
            t_type, v_type, te_type = self._simple_split(type_decisions)
            train.extend(t_type)
            val.extend(v_type)
            test.extend(te_type)

        # Shuffle final splits
        random.shuffle(train)
        random.shuffle(val)
        random.shuffle(test)

        return train, val, test

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _get_decision_text(self, decision: Dict) -> str:
        """Extract representative text from decision for deduplication"""
        decision_data = decision.get('decision_data', {})
        situation = decision.get('situation_context', {})

        parts = []

        # Decision type and action
        decision_type = decision_data.get('decision_type', '')
        action = decision_data.get('action', '')
        if decision_type:
            parts.append(decision_type)
        if action:
            parts.append(action)

        # Situation location
        game_state = situation.get('game_state', {})
        location = game_state.get('location', '')
        if location:
            parts.append(location)

        return " ".join(parts)

    def _get_decision_quality(self, decision: Dict) -> float:
        """Get overall quality score for comparison during deduplication"""
        quality_label = decision.get('quality_label', 'acceptable')

        # Quality label to score mapping
        quality_scores = {
            'excellent': 1.0,
            'good': 0.8,
            'acceptable': 0.6,
            'poor': 0.4,
            'bad': 0.2,
            'teaching_moment': 0.9  # High value for learning
        }

        base_score = quality_scores.get(quality_label, 0.5)

        # Factor in confidence
        confidence = decision.get('decision_data', {}).get('confidence', 0.5)
        return base_score * (0.5 + 0.5 * confidence)

    def _write_split(self, decisions: List[Dict], path: Path) -> None:
        """Write a dataset split to file"""
        with open(path, 'w') as f:
            for d in decisions:
                # Convert to QLoRA format
                record = self._decision_to_qlora_format(d)
                f.write(json.dumps(record) + '\n')

        logger.info(f"Wrote {len(decisions)} records to {path}")

    def _decision_to_qlora_format(self, decision: Dict) -> Dict:
        """Convert decision to QLoRA training format"""
        situation = decision.get('situation_context', {})
        decision_data = decision.get('decision_data', {})
        outcome = decision.get('outcome_data', {})

        # Build instruction
        decision_type = decision_data.get('decision_type', 'action')
        instruction_map = {
            "combat_action": "What combat action should I take?",
            "exploration": "How should I proceed with exploration?",
            "social": "How should I respond in this social situation?",
            "skill_check": "What skill check should I attempt?",
        }
        instruction = instruction_map.get(decision_type, "What action should I take?")

        # Build input
        input_parts = []
        game_state = situation.get('game_state', {})
        if game_state.get('location'):
            input_parts.append(f"Location: {game_state['location']}")
        char_state = situation.get('character_state', {})
        if 'hp' in char_state:
            hp = char_state['hp']
            max_hp = char_state.get('max_hp', hp)
            input_parts.append(f"HP: {hp}/{max_hp}")
        input_text = "\n".join(input_parts) if input_parts else "No additional context"

        # Build output
        action = decision_data.get('action', 'unknown action')
        reasoning = decision_data.get('reasoning', '')
        output_text = f"Action: {action}\nReasoning: {reasoning}"

        if outcome:
            success = outcome.get('success', False)
            result = outcome.get('immediate', '')
            if result:
                output_text += f"\nResult: {result}"
            if success:
                output_text += "\nThis action was successful."

        return {
            "instruction": instruction,
            "input": input_text,
            "output": output_text
        }


async def test_data_curation():
    """Test the data curation pipeline"""
    print("\n" + "=" * 60)
    print("Testing DataCurationPipeline")
    print("=" * 60)

    # Create sample decisions
    sample_decisions = [
        {
            "decision_id": "dec_001",
            "character_id": "thorin",
            "decision_data": {
                "decision_type": "combat_action",
                "action": "attack goblin",
                "reasoning": "Protect party",
                "confidence": 0.85
            },
            "situation_context": {
                "game_state": {"location": "Cave entrance", "turn": 5},
                "character_state": {"hp": 35, "max_hp": 50}
            },
            "outcome_data": {
                "success": True,
                "immediate": "Hit for 15 damage",
                "quality_analysis": {"quality_score": 0.75}
            },
            "success": True,
            "quality_label": "good"
        },
        {
            "decision_id": "dec_002",
            "character_id": "thorin",
            "decision_data": {
                "decision_type": "combat_action",
                "action": "attack goblin",  # Duplicate-ish
                "reasoning": "Need to fight",
                "confidence": 0.80
            },
            "situation_context": {
                "game_state": {"location": "Cave entrance", "turn": 6},
                "character_state": {"hp": 30, "max_hp": 50}
            },
            "outcome_data": {
                "success": True,
                "immediate": "Hit for 12 damage",
                "quality_analysis": {"quality_score": 0.70}
            },
            "success": True,
            "quality_label": "good"
        },
        {
            "decision_id": "dec_003",
            "character_id": "thorin",
            "decision_data": {
                "decision_type": "social",
                "action": "negotiate",
                "reasoning": "Avoid conflict",
                "confidence": 0.2  # Low confidence - should be filtered
            },
            "situation_context": {
                "game_state": {"location": "Tavern"},
                "character_state": {"hp": 50, "max_hp": 50}
            },
            "outcome_data": {
                "success": False,
                "immediate": "Negotiation failed",
                "quality_analysis": {"quality_score": 0.3}
            },
            "success": False,
            "quality_label": "poor"
        },
        {
            "decision_id": "dec_004",
            "character_id": "thorin",
            "decision_data": {
                "decision_type": "exploration",
                "action": "search room",
                "reasoning": "Look for treasure",
                "confidence": 0.9
            },
            "situation_context": {
                "game_state": {"location": "Treasure room"},
                "character_state": {"hp": 45, "max_hp": 50}
            },
            "outcome_data": {
                "success": True,
                "immediate": "Found gold",
                "quality_analysis": {"quality_score": 0.85}
            },
            "success": True,
            "quality_label": "excellent"
        },
        {
            "decision_id": "dec_005",
            "character_id": "thorin",
            "decision_data": {
                "decision_type": "combat_action",
                "action": "flee",
                "reasoning": "Too dangerous",
                "confidence": 0.75
            },
            "situation_context": {
                "game_state": {"location": "Dragon's lair"},
                "character_state": {"hp": 5, "max_hp": 50}
            },
            "outcome_data": {
                "success": False,
                "immediate": "Failed to escape",
                "quality_analysis": {"quality_score": 0.5}
            },
            "success": False,
            "quality_label": "teaching_moment"  # Should always be kept
        },
    ]

    # Create pipeline
    config = CurationConfig(
        min_confidence=0.3,
        min_quality_score=0.4,
        deduplication_enabled=True,
        balance_success_failure=True
    )

    pipeline = DataCurationPipeline(config=config)

    # Run curation
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        report = pipeline.curate(
            decisions=sample_decisions,
            character_id="thorin",
            output_dir=tmpdir
        )

    print(f"\nCuration Report:")
    print(f"  Input: {report.input_count} decisions")
    print(f"  After filtering: {report.filtered_count}")
    print(f"  After deduplication: {report.deduplicated_count}")
    print(f"  After balancing: {report.balanced_count}")
    print(f"  Final: {report.final_count} decisions")
    print(f"  Train: {report.train_count}, Val: {report.val_count}, Test: {report.test_count}")

    print(f"\nFiltering report: {report.filtering_report}")
    print(f"Balancing report: {report.balancing_report}")

    # Verify outputs
    assert report.input_count == 5
    assert report.filtered_count <= 5  # Some filtered out
    assert report.train_count + report.val_count + report.test_count == report.final_count

    print("\n✅ Data curation pipeline tests passed!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_data_curation())
