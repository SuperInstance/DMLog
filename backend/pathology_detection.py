"""
AI Society D&D - Pathology Detection & Monitoring
==================================================
Detects and prevents cognitive pathologies in AI characters:

1. Memory Drift: Character forgets who they are
2. Identity Fragmentation: Personality becomes inconsistent
3. Memory Bloat: Too many irrelevant memories
4. Cultural Homogenization: All characters become similar
5. Decision Paralysis: Can't make choices due to conflicting memories
6. Temporal Confusion: Can't distinguish past from present

Implements real-time monitoring, alerts, and interventions.
"""

from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
from collections import defaultdict, Counter
import statistics


# ============================================================================
# PATHOLOGY TYPES
# ============================================================================

class PathologyType(Enum):
    """Types of cognitive pathologies"""
    MEMORY_DRIFT = "memory_drift"                  # Character drifting from core identity
    IDENTITY_FRAGMENTATION = "identity_fragmentation"  # Inconsistent personality
    MEMORY_BLOAT = "memory_bloat"                  # Too many low-importance memories
    CULTURAL_HOMOGENIZATION = "cultural_homogenization"  # Losing uniqueness
    DECISION_PARALYSIS = "decision_paralysis"      # Can't decide due to conflicts
    TEMPORAL_CONFUSION = "temporal_confusion"      # Can't track time properly
    REPETITION_SYNDROME = "repetition_syndrome"    # Repeating same actions
    CONTEXT_COLLAPSE = "context_collapse"          # Forgetting recent events


class PathologySeverity(Enum):
    """Severity levels for pathologies"""
    HEALTHY = 0      # No issues
    MINOR = 1        # Watch but don't intervene
    MODERATE = 2     # Consider intervention
    SEVERE = 3       # Intervention recommended
    CRITICAL = 4     # Immediate intervention required


@dataclass
class PathologyAlert:
    """Alert for detected pathology"""
    pathology_type: PathologyType
    severity: PathologySeverity
    character_id: str
    detected_at: datetime
    
    # Diagnostic data
    score: float
    threshold: float
    evidence: List[str] = field(default_factory=list)
    
    # Recommended interventions
    interventions: List[str] = field(default_factory=list)
    
    # Status
    acknowledged: bool = False
    resolved: bool = False


# ============================================================================
# PATHOLOGY DETECTORS
# ============================================================================

class MemoryDriftDetector:
    """
    Detects when character is drifting from their core identity.
    
    Signals:
    - Core traits changing significantly
    - Behaving inconsistently with backstory
    - Recent memories contradict established patterns
    """
    
    THRESHOLDS = {
        PathologySeverity.MINOR: 0.10,
        PathologySeverity.MODERATE: 0.15,
        PathologySeverity.SEVERE: 0.25,
        PathologySeverity.CRITICAL: 0.35
    }
    
    @staticmethod
    def detect(character) -> Optional[PathologyAlert]:
        """Detect memory drift in character"""
        
        # Get identity coherence index
        identity_system = character.identity_system
        drift_score = identity_system.get_drift_score()
        
        # Check if drifting
        severity = PathologySeverity.HEALTHY
        for sev, threshold in MemoryDriftDetector.THRESHOLDS.items():
            if drift_score >= threshold:
                severity = sev
        
        if severity == PathologySeverity.HEALTHY:
            return None
        
        # Gather evidence
        evidence = []
        
        # Compare core vs temporal traits
        for trait in identity_system.core_traits:
            core_val = identity_system.core_traits[trait]
            temporal_val = identity_system.temporal_traits[trait]
            diff = abs(core_val - temporal_val)
            if diff > 0.2:
                evidence.append(
                    f"{trait}: core={core_val:.2f}, current={temporal_val:.2f} (diff: {diff:.2f})"
                )
        
        # Recommend interventions
        interventions = []
        if severity >= PathologySeverity.MODERATE:
            interventions.append("Reinforce core identity in system prompt")
            interventions.append("Review and prune conflicting memories")
        if severity >= PathologySeverity.SEVERE:
            interventions.append("Restore from personality snapshot")
            interventions.append("Increase weight of core identity traits")
        
        return PathologyAlert(
            pathology_type=PathologyType.MEMORY_DRIFT,
            severity=severity,
            character_id=character.character_id,
            detected_at=datetime.now(),
            score=drift_score,
            threshold=MemoryDriftDetector.THRESHOLDS[severity],
            evidence=evidence,
            interventions=interventions
        )


class IdentityFragmentationDetector:
    """
    Detects when character's personality becomes inconsistent.
    
    Signals:
    - Contradictory decisions
    - Personality trait variance over time
    - Inconsistent responses to similar situations
    """
    
    THRESHOLDS = {
        PathologySeverity.MINOR: 0.60,
        PathologySeverity.MODERATE: 0.50,
        PathologySeverity.SEVERE: 0.40,
        PathologySeverity.CRITICAL: 0.30
    }
    
    @staticmethod
    def detect(character, recent_decisions: List[Dict] = None) -> Optional[PathologyAlert]:
        """Detect identity fragmentation"""
        
        # Get identity coherence
        ici = character.identity_system.get_identity_coherence_index(
            list(character.memory_engine.memories.values()),
            window_days=30
        )
        
        # Check coherence
        severity = PathologySeverity.HEALTHY
        for sev, threshold in IdentityFragmentationDetector.THRESHOLDS.items():
            if ici <= threshold:
                severity = sev
        
        if severity == PathologySeverity.HEALTHY:
            return None
        
        # Gather evidence
        evidence = [
            f"Identity Coherence Index: {ici:.2f} (threshold: {IdentityFragmentationDetector.THRESHOLDS[severity]:.2f})"
        ]
        
        # Check for contradictory memories
        if recent_decisions:
            decisions_text = [d.get('action', '') for d in recent_decisions[-10:]]
            # Simple contradiction detection (would use embeddings in production)
            if any('not' in d1 and d1.replace('not', '') in d2 
                   for d1 in decisions_text for d2 in decisions_text if d1 != d2):
                evidence.append("Detected contradictory decisions in recent history")
        
        # Recommend interventions
        interventions = [
            "Review character's core personality traits",
            "Consolidate conflicting memories",
            "Add personality reinforcement to prompts"
        ]
        
        if severity >= PathologySeverity.SEVERE:
            interventions.append("Consider character therapy session")
            interventions.append("Rebuild autobiographical narrative")
        
        return PathologyAlert(
            pathology_type=PathologyType.IDENTITY_FRAGMENTATION,
            severity=severity,
            character_id=character.character_id,
            detected_at=datetime.now(),
            score=1.0 - ici,  # Invert so higher = worse
            threshold=1.0 - IdentityFragmentationDetector.THRESHOLDS[severity],
            evidence=evidence,
            interventions=interventions
        )


class MemoryBloatDetector:
    """
    Detects when character has too many low-importance memories.
    
    Signals:
    - High percentage of importance < 3.0
    - Memory count growing faster than consolidation
    - Retrieval quality degrading
    """
    
    MAX_MEMORIES = 1000
    LOW_IMPORTANCE_THRESHOLD = 3.0
    LOW_IMPORTANCE_RATIO_WARNING = 0.40
    
    @staticmethod
    def detect(character) -> Optional[PathologyAlert]:
        """Detect memory bloat"""
        
        memories = list(character.memory_engine.memories.values())
        total_memories = len(memories)
        
        if total_memories == 0:
            return None
        
        # Calculate metrics
        low_importance_count = sum(
            1 for m in memories if m.importance < MemoryBloatDetector.LOW_IMPORTANCE_THRESHOLD
        )
        low_importance_ratio = low_importance_count / total_memories
        
        # Check bloat
        severity = PathologySeverity.HEALTHY
        
        if total_memories > MemoryBloatDetector.MAX_MEMORIES * 1.5:
            severity = PathologySeverity.CRITICAL
        elif total_memories > MemoryBloatDetector.MAX_MEMORIES:
            severity = PathologySeverity.SEVERE
        elif low_importance_ratio > 0.60:
            severity = PathologySeverity.MODERATE
        elif low_importance_ratio > MemoryBloatDetector.LOW_IMPORTANCE_RATIO_WARNING:
            severity = PathologySeverity.MINOR
        
        if severity == PathologySeverity.HEALTHY:
            return None
        
        # Gather evidence
        evidence = [
            f"Total memories: {total_memories} (max recommended: {MemoryBloatDetector.MAX_MEMORIES})",
            f"Low importance ratio: {low_importance_ratio:.1%}"
        ]
        
        # Recommend interventions
        interventions = [
            "Run memory consolidation cycle",
            "Archive or prune low-importance memories",
            "Increase consolidation frequency"
        ]
        
        if severity >= PathologySeverity.SEVERE:
            interventions.append("Emergency memory cleanup required")
            interventions.append("Consider resetting to semantic memories only")
        
        return PathologyAlert(
            pathology_type=PathologyType.MEMORY_BLOAT,
            severity=severity,
            character_id=character.character_id,
            detected_at=datetime.now(),
            score=low_importance_ratio,
            threshold=MemoryBloatDetector.LOW_IMPORTANCE_RATIO_WARNING,
            evidence=evidence,
            interventions=interventions
        )


class RepetitionSyndromeDetector:
    """
    Detects when character keeps repeating same actions.
    
    Signals:
    - Same action taken multiple times in short period
    - Decision space collapsing
    - Low variance in behavior
    """
    
    REPETITION_THRESHOLD = 3  # Same action 3+ times in 10 actions
    
    @staticmethod
    def detect(character, recent_actions: List[str] = None) -> Optional[PathologyAlert]:
        """Detect repetition syndrome"""
        
        if not recent_actions or len(recent_actions) < 10:
            return None
        
        # Check last 10 actions
        last_10 = recent_actions[-10:]
        action_counts = Counter(last_10)
        max_repetition = max(action_counts.values())
        most_repeated = action_counts.most_common(1)[0]
        
        severity = PathologySeverity.HEALTHY
        if max_repetition >= 5:
            severity = PathologySeverity.CRITICAL
        elif max_repetition >= 4:
            severity = PathologySeverity.SEVERE
        elif max_repetition >= RepetitionSyndromeDetector.REPETITION_THRESHOLD:
            severity = PathologySeverity.MODERATE
        
        if severity == PathologySeverity.HEALTHY:
            return None
        
        evidence = [
            f"Action '{most_repeated[0]}' repeated {most_repeated[1]} times in last 10 actions",
            f"Unique actions in last 10: {len(action_counts)}"
        ]
        
        interventions = [
            "Introduce novelty prompt: 'Try something different'",
            "Increase temperature in decision making",
            "Review and diversify available actions"
        ]
        
        return PathologyAlert(
            pathology_type=PathologyType.REPETITION_SYNDROME,
            severity=severity,
            character_id=character.character_id,
            detected_at=datetime.now(),
            score=max_repetition / 10.0,
            threshold=RepetitionSyndromeDetector.REPETITION_THRESHOLD / 10.0,
            evidence=evidence,
            interventions=interventions
        )


# ============================================================================
# PATHOLOGY MONITOR
# ============================================================================

class PathologyMonitor:
    """
    Central monitoring system for character cognitive health.
    Runs all detectors and manages alerts.
    """
    
    def __init__(self):
        self.detectors = [
            MemoryDriftDetector,
            IdentityFragmentationDetector,
            MemoryBloatDetector,
            RepetitionSyndromeDetector
        ]
        
        # Alert tracking
        self.active_alerts: Dict[str, List[PathologyAlert]] = defaultdict(list)
        self.alert_history: List[PathologyAlert] = []
        
        # Monitoring frequency
        self.check_frequency = {
            PathologyType.MEMORY_DRIFT: 10,  # Every 10 actions
            PathologyType.IDENTITY_FRAGMENTATION: 20,
            PathologyType.MEMORY_BLOAT: 50,
            PathologyType.REPETITION_SYNDROME: 5
        }
        
        # Action counters
        self.action_counters: Dict[str, int] = defaultdict(int)
    
    def check_character_health(
        self,
        character,
        recent_actions: List[str] = None,
        recent_decisions: List[Dict] = None,
        force_check: bool = False
    ) -> List[PathologyAlert]:
        """
        Run health check on character.
        
        Returns list of active pathology alerts.
        """
        char_id = character.character_id
        self.action_counters[char_id] += 1
        
        alerts = []
        
        for detector in self.detectors:
            # Check if it's time to run this detector
            if not force_check:
                pathology_type = detector.__name__.replace('Detector', '').upper()
                if pathology_type in [p.value for p in PathologyType]:
                    pt = PathologyType(pathology_type.lower())
                    if self.action_counters[char_id] % self.check_frequency.get(pt, 10) != 0:
                        continue
            
            # Run detector
            try:
                if detector == RepetitionSyndromeDetector:
                    alert = detector.detect(character, recent_actions)
                elif detector == IdentityFragmentationDetector:
                    alert = detector.detect(character, recent_decisions)
                else:
                    alert = detector.detect(character)
                
                if alert:
                    alerts.append(alert)
                    self.active_alerts[char_id].append(alert)
                    self.alert_history.append(alert)
            
            except Exception as e:
                print(f"Error running {detector.__name__}: {e}")
        
        return alerts
    
    def get_character_health_report(self, character_id: str) -> Dict[str, Any]:
        """Get comprehensive health report for character"""
        
        active = self.active_alerts.get(character_id, [])
        unresolved = [a for a in active if not a.resolved]
        
        # Severity breakdown
        severity_counts = Counter(a.severity for a in unresolved)
        
        # Pathology breakdown
        pathology_counts = Counter(a.pathology_type for a in unresolved)
        
        # Overall health score (0-100)
        health_score = 100.0
        for alert in unresolved:
            if alert.severity == PathologySeverity.CRITICAL:
                health_score -= 30
            elif alert.severity == PathologySeverity.SEVERE:
                health_score -= 20
            elif alert.severity == PathologySeverity.MODERATE:
                health_score -= 10
            elif alert.severity == PathologySeverity.MINOR:
                health_score -= 5
        
        health_score = max(0, health_score)
        
        # Health status
        if health_score >= 90:
            status = "EXCELLENT"
        elif health_score >= 70:
            status = "GOOD"
        elif health_score >= 50:
            status = "FAIR"
        elif health_score >= 30:
            status = "POOR"
        else:
            status = "CRITICAL"
        
        return {
            "character_id": character_id,
            "health_score": health_score,
            "status": status,
            "active_alerts": len(unresolved),
            "by_severity": {k.name: v for k, v in severity_counts.items()},
            "by_pathology": {k.name: v for k, v in pathology_counts.items()},
            "alerts": [
                {
                    "type": a.pathology_type.name,
                    "severity": a.severity.name,
                    "detected": a.detected_at.isoformat(),
                    "score": a.score,
                    "evidence": a.evidence[:3],  # First 3 pieces of evidence
                    "interventions": a.interventions
                }
                for a in unresolved
            ]
        }
    
    def resolve_alert(self, character_id: str, alert_index: int):
        """Mark an alert as resolved"""
        if character_id in self.active_alerts:
            if 0 <= alert_index < len(self.active_alerts[character_id]):
                self.active_alerts[character_id][alert_index].resolved = True
    
    def get_global_health_stats(self) -> Dict[str, Any]:
        """Get statistics across all characters"""
        
        all_active = []
        for alerts in self.active_alerts.values():
            all_active.extend([a for a in alerts if not a.resolved])
        
        if not all_active:
            return {
                "total_characters": len(self.active_alerts),
                "total_alerts": 0,
                "average_health": 100.0,
                "message": "All characters healthy!"
            }
        
        # Calculate stats
        severity_counts = Counter(a.severity for a in all_active)
        pathology_counts = Counter(a.pathology_type for a in all_active)
        
        # Average health
        health_scores = []
        for char_id in self.active_alerts:
            report = self.get_character_health_report(char_id)
            health_scores.append(report['health_score'])
        
        avg_health = statistics.mean(health_scores) if health_scores else 100.0
        
        return {
            "total_characters": len(self.active_alerts),
            "total_alerts": len(all_active),
            "average_health": avg_health,
            "by_severity": {k.name: v for k, v in severity_counts.items()},
            "by_pathology": {k.name: v for k, v in pathology_counts.items()},
            "characters_at_risk": len([s for s in health_scores if s < 70])
        }


# ============================================================================
# INTERVENTION SYSTEM
# ============================================================================

class InterventionSystem:
    """
    Executes interventions to resolve pathologies.
    """
    
    @staticmethod
    async def apply_intervention(
        character,
        alert: PathologyAlert
    ) -> Dict[str, Any]:
        """Apply intervention for pathology"""
        
        results = {
            "character_id": character.character_id,
            "pathology": alert.pathology_type.name,
            "severity": alert.severity.name,
            "interventions_applied": [],
            "success": False
        }
        
        if alert.pathology_type == PathologyType.MEMORY_DRIFT:
            # Reinforce core identity
            if alert.severity >= PathologySeverity.MODERATE:
                # Snapshot current state
                character.identity_system.snapshot_personality(
                    reason=f"Pre-intervention for memory drift (severity: {alert.severity.name})"
                )
                
                # Adjust temporal traits back toward core
                for trait in character.identity_system.temporal_traits:
                    core_val = character.identity_system.core_traits[trait]
                    temp_val = character.identity_system.temporal_traits[trait]
                    # Move 30% back toward core
                    character.identity_system.temporal_traits[trait] = (
                        temp_val * 0.7 + core_val * 0.3
                    )
                
                results["interventions_applied"].append("Adjusted temporal traits toward core")
                results["success"] = True
        
        elif alert.pathology_type == PathologyType.MEMORY_BLOAT:
            # Run consolidation
            if alert.severity >= PathologySeverity.MODERATE:
                consolidated = await character.consolidate_memories()
                results["interventions_applied"].append(
                    f"Consolidated {consolidated} memories"
                )
                results["success"] = True
        
        elif alert.pathology_type == PathologyType.IDENTITY_FRAGMENTATION:
            # Rebuild autobiographical narrative
            if alert.severity >= PathologySeverity.SEVERE:
                narrative = character.memory_engine.generate_autobiographical_narrative()
                if narrative:
                    character.memory_engine.autobiographical_narratives.append(narrative)
                    results["interventions_applied"].append("Generated new autobiographical narrative")
                    results["success"] = True
        
        return results
