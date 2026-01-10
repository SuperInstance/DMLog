"""
AI Society D&D - Metrics Dashboard & Monitoring
================================================
Comprehensive monitoring and analytics for:
- Character cognitive health
- Memory system performance
- Cultural transmission metrics
- Game session analytics
- Model routing efficiency
- System performance

Provides real-time dashboards and historical analytics.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
import json


# ============================================================================
# METRIC TYPES
# ============================================================================

@dataclass
class Metric:
    """Single metric reading"""
    name: str
    value: float
    timestamp: datetime
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """Time series of metric values"""
    name: str
    values: List[Tuple[datetime, float]] = field(default_factory=list)
    unit: str = ""
    
    def add(self, value: float, timestamp: Optional[datetime] = None):
        """Add value to series"""
        timestamp = timestamp or datetime.now()
        self.values.append((timestamp, value))
    
    def get_latest(self) -> Optional[float]:
        """Get most recent value"""
        return self.values[-1][1] if self.values else None
    
    def get_average(self, window_minutes: int = 60) -> Optional[float]:
        """Get average over time window"""
        if not self.values:
            return None
        
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        recent = [v for t, v in self.values if t >= cutoff]
        
        return statistics.mean(recent) if recent else None
    
    def get_trend(self) -> str:
        """Get trend direction"""
        if len(self.values) < 2:
            return "STABLE"
        
        recent_10 = self.values[-10:]
        if len(recent_10) < 2:
            return "STABLE"
        
        first_avg = statistics.mean([v for _, v in recent_10[:len(recent_10)//2]])
        last_avg = statistics.mean([v for _, v in recent_10[len(recent_10)//2:]])
        
        change = (last_avg - first_avg) / first_avg if first_avg != 0 else 0
        
        if abs(change) < 0.05:
            return "STABLE"
        elif change > 0:
            return "INCREASING"
        else:
            return "DECREASING"


# ============================================================================
# METRICS COLLECTOR
# ============================================================================

class MetricsCollector:
    """
    Collects and stores metrics from all system components.
    """
    
    def __init__(self):
        self.series: Dict[str, MetricSeries] = {}
        self.recent_events: deque = deque(maxlen=1000)
        
        # Aggregated stats
        self.session_stats: Dict[str, Dict] = defaultdict(dict)
        self.character_stats: Dict[str, Dict] = defaultdict(dict)
    
    def record(self, metric_name: str, value: float, unit: str = "", tags: Dict = None):
        """Record a metric"""
        if metric_name not in self.series:
            self.series[metric_name] = MetricSeries(name=metric_name, unit=unit)
        
        self.series[metric_name].add(value)
        
        # Log event
        self.recent_events.append({
            "type": "metric",
            "name": metric_name,
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "tags": tags or {}
        })
    
    def get_series(self, metric_name: str) -> Optional[MetricSeries]:
        """Get metric time series"""
        return self.series.get(metric_name)
    
    def get_all_metrics(self) -> Dict[str, Dict]:
        """Get current values for all metrics"""
        return {
            name: {
                "current": series.get_latest(),
                "average_1h": series.get_average(60),
                "trend": series.get_trend(),
                "unit": series.unit
            }
            for name, series in self.series.items()
        }


# ============================================================================
# CHARACTER METRICS
# ============================================================================

class CharacterMetrics:
    """Metrics specific to character cognitive health"""
    
    @staticmethod
    def collect(character, collector: MetricsCollector):
        """Collect character metrics"""
        char_id = character.character_id
        
        # Memory metrics
        total_memories = len(character.memory_engine.memories)
        collector.record(f"character.{char_id}.memory_count", total_memories)
        
        if total_memories > 0:
            avg_importance = statistics.mean(
                m.importance for m in character.memory_engine.memories.values()
            )
            collector.record(f"character.{char_id}.avg_memory_importance", avg_importance)
            
            # Memory type distribution
            episodic_count = sum(
                1 for m in character.memory_engine.memories.values()
                if m.memory_type.value == "episodic"
            )
            semantic_count = sum(
                1 for m in character.memory_engine.memories.values()
                if m.memory_type.value == "semantic"
            )
            
            collector.record(f"character.{char_id}.episodic_memories", episodic_count)
            collector.record(f"character.{char_id}.semantic_memories", semantic_count)
        
        # Identity metrics
        ici = character.identity_system.get_identity_coherence_index(
            list(character.memory_engine.memories.values()),
            window_days=30
        )
        collector.record(f"character.{char_id}.identity_coherence", ici)
        
        drift = character.identity_system.get_drift_score()
        collector.record(f"character.{char_id}.identity_drift", drift)
        
        # Journal metrics
        journal_entries = len(character.laptop.journal_entries)
        collector.record(f"character.{char_id}.journal_entries", journal_entries)


# ============================================================================
# SESSION METRICS
# ============================================================================

class SessionMetrics:
    """Metrics for game sessions"""
    
    @staticmethod
    def collect(session, collector: MetricsCollector):
        """Collect session metrics"""
        session_id = session.room_id
        
        # Basic stats
        collector.record(f"session.{session_id}.transcript_length", len(session.transcript))
        collector.record(f"session.{session_id}.character_count", len(session.characters))
        
        # Event breakdown
        event_types = defaultdict(int)
        for event in session.transcript:
            event_types[event['event_type']] += 1
        
        for event_type, count in event_types.items():
            collector.record(f"session.{session_id}.events.{event_type}", count)
        
        # Combat metrics
        if session.active_combat:
            collector.record(f"session.{session_id}.combat_active", 1)
            collector.record(f"session.{session_id}.combat_round", 
                           session.active_combat.round_number)


# ============================================================================
# SYSTEM METRICS
# ============================================================================

class SystemMetrics:
    """Overall system performance metrics"""
    
    @staticmethod
    def collect(session_manager, collector: MetricsCollector):
        """Collect system-wide metrics"""
        
        # Campaign metrics
        total_campaigns = len(session_manager.campaigns)
        collector.record("system.campaigns.total", total_campaigns)
        
        # Character metrics
        total_characters = len(session_manager.characters)
        collector.record("system.characters.total", total_characters)
        
        # Session metrics
        active_sessions = sum(
            len(dm.active_sessions) 
            for dm in session_manager.campaigns.values()
        )
        collector.record("system.sessions.active", active_sessions)
        
        completed_sessions = sum(
            len(dm.completed_sessions)
            for dm in session_manager.campaigns.values()
        )
        collector.record("system.sessions.completed", completed_sessions)


# ============================================================================
# DASHBOARD
# ============================================================================

class MetricsDashboard:
    """
    Main dashboard for viewing system metrics.
    """
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
    
    def get_overview(self) -> Dict[str, Any]:
        """Get high-level overview"""
        metrics = self.collector.get_all_metrics()
        
        # System overview
        system_metrics = {
            k.replace("system.", ""): v 
            for k, v in metrics.items() 
            if k.startswith("system.")
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system": system_metrics,
            "health_status": "HEALTHY",  # Would check thresholds
            "active_alerts": 0  # Would integrate with pathology monitor
        }
    
    def get_character_dashboard(self, character_id: str) -> Dict[str, Any]:
        """Get detailed dashboard for a character"""
        prefix = f"character.{character_id}."
        metrics = {
            k.replace(prefix, ""): v 
            for k, v in self.collector.get_all_metrics().items()
            if k.startswith(prefix)
        }
        
        # Health assessment
        ici = metrics.get("identity_coherence", {}).get("current", 0.7)
        drift = metrics.get("identity_drift", {}).get("current", 0.0)
        
        health_score = 100.0
        if ici < 0.5:
            health_score -= 30
        if drift > 0.2:
            health_score -= 20
        
        return {
            "character_id": character_id,
            "health_score": health_score,
            "metrics": metrics,
            "trends": {
                name: series.get_trend()
                for name, series in self.collector.series.items()
                if name.startswith(prefix)
            }
        }
    
    def get_session_dashboard(self, session_id: str) -> Dict[str, Any]:
        """Get dashboard for a game session"""
        prefix = f"session.{session_id}."
        metrics = {
            k.replace(prefix, ""): v 
            for k, v in self.collector.get_all_metrics().items()
            if k.startswith(prefix)
        }
        
        return {
            "session_id": session_id,
            "metrics": metrics,
            "events": [e for e in self.collector.recent_events if session_id in str(e)]
        }
    
    def get_cultural_dashboard(self, cultural_engine) -> Dict[str, Any]:
        """Get cultural transmission metrics"""
        status = cultural_engine.get_cultural_status()
        
        return {
            "total_skills": status["total_skills_created"],
            "total_adoptions": status["total_skills_adopted"],
            "cultural_landmarks": status["cultural_landmarks"],
            "teaching_events": status["teaching_events"],
            "avg_adoption_per_skill": status["average_adoption_per_skill"]
        }
    
    def export_dashboard(self, format: str = "json") -> str:
        """Export dashboard data"""
        if format == "json":
            return json.dumps(
                {
                    "overview": self.get_overview(),
                    "timestamp": datetime.now().isoformat()
                },
                indent=2
            )
        return ""


# ============================================================================
# ALERTING SYSTEM
# ============================================================================

@dataclass
class Alert:
    """System alert"""
    alert_id: str
    level: str  # INFO, WARNING, CRITICAL
    title: str
    message: str
    timestamp: datetime
    source: str
    resolved: bool = False


class AlertManager:
    """Manages system alerts"""
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.alerts: List[Alert] = []
        
        # Alert rules
        self.rules = [
            {
                "metric": "identity_coherence",
                "threshold": 0.5,
                "comparison": "<",
                "level": "WARNING",
                "message": "Identity coherence below healthy threshold"
            },
            {
                "metric": "identity_drift",
                "threshold": 0.25,
                "comparison": ">",
                "level": "WARNING",
                "message": "Character experiencing significant identity drift"
            },
            {
                "metric": "memory_count",
                "threshold": 1000,
                "comparison": ">",
                "level": "INFO",
                "message": "Memory count high, consider consolidation"
            }
        ]
    
    def check_alerts(self):
        """Check for alert conditions"""
        for rule in self.rules:
            metric_name = rule["metric"]
            
            # Check all instances of this metric (all characters, sessions, etc.)
            for series_name, series in self.collector.series.items():
                if metric_name in series_name:
                    value = series.get_latest()
                    if value is None:
                        continue
                    
                    # Check condition
                    triggered = False
                    if rule["comparison"] == "<" and value < rule["threshold"]:
                        triggered = True
                    elif rule["comparison"] == ">" and value > rule["threshold"]:
                        triggered = True
                    
                    if triggered:
                        # Create alert
                        alert = Alert(
                            alert_id=f"alert_{len(self.alerts)}",
                            level=rule["level"],
                            title=f"{metric_name} threshold exceeded",
                            message=f"{rule['message']} (value: {value:.2f}, threshold: {rule['threshold']})",
                            timestamp=datetime.now(),
                            source=series_name
                        )
                        self.alerts.append(alert)
    
    def get_active_alerts(self) -> List[Alert]:
        """Get unresolved alerts"""
        return [a for a in self.alerts if not a.resolved]
    
    def resolve_alert(self, alert_id: str):
        """Mark alert as resolved"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                break


# ============================================================================
# PERFORMANCE ANALYZER
# ============================================================================

class PerformanceAnalyzer:
    """Analyze system performance and provide recommendations"""
    
    @staticmethod
    def analyze_memory_performance(character) -> Dict[str, Any]:
        """Analyze character memory system performance"""
        memories = list(character.memory_engine.memories.values())
        
        if not memories:
            return {"status": "NO_DATA"}
        
        # Memory distribution
        type_counts = defaultdict(int)
        for m in memories:
            type_counts[m.memory_type.value] += 1
        
        # Importance distribution
        importance_scores = [m.importance for m in memories]
        avg_importance = statistics.mean(importance_scores)
        
        # Consolidation ratio
        consolidated_count = sum(1 for m in memories if m.consolidated)
        consolidation_ratio = consolidated_count / len(memories)
        
        # Recommendations
        recommendations = []
        if avg_importance < 4.0:
            recommendations.append("Consider pruning low-importance memories")
        if consolidation_ratio < 0.3 and len(memories) > 50:
            recommendations.append("Run memory consolidation to improve semantic knowledge")
        if type_counts.get("episodic", 0) > type_counts.get("semantic", 0) * 3:
            recommendations.append("High episodic/semantic ratio - consolidation needed")
        
        return {
            "total_memories": len(memories),
            "by_type": dict(type_counts),
            "avg_importance": avg_importance,
            "consolidation_ratio": consolidation_ratio,
            "recommendations": recommendations
        }
    
    @staticmethod
    def analyze_decision_quality(recent_decisions: List[Dict]) -> Dict[str, Any]:
        """Analyze quality of character decisions"""
        if not recent_decisions:
            return {"status": "NO_DATA"}
        
        # Decision time analysis
        times = [d.get("decision_time", 0) for d in recent_decisions if "decision_time" in d]
        avg_time = statistics.mean(times) if times else 0
        
        # Confidence analysis
        confidences = [d.get("confidence", 0) for d in recent_decisions if "confidence" in d]
        avg_confidence = statistics.mean(confidences) if confidences else 0
        
        # Success rate
        successes = sum(1 for d in recent_decisions if d.get("success", False))
        success_rate = successes / len(recent_decisions)
        
        return {
            "avg_decision_time": avg_time,
            "avg_confidence": avg_confidence,
            "success_rate": success_rate,
            "total_decisions": len(recent_decisions)
        }
