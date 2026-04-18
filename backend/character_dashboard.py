"""
Character Dashboard UI - Phase 7 Task 7.2.3
=============================================
CLI-based dashboard for visualizing character learning progress,
memory statistics, training data, and consolidation results.

Features:
- Character learning progress visualization
- Memory statistics and health metrics
- Training data quality reports
- Consolidation results display
- Interactive CLI interface

Usage:
    python character_dashboard.py --character-id thorin
    python character_dashboard.py --list-characters
    python character_dashboard.py --character-id thorin --show-training
"""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


# ============================================================================
# ANSI Colors for Terminal UI
# ============================================================================

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def disable():
        """Disable colors"""
        Colors.HEADER = ''
        Colors.OKBLUE = ''
        Colors.OKCYAN = ''
        Colors.OKGREEN = ''
        Colors.WARNING = ''
        Colors.FAIL = ''
        Colors.ENDC = ''
        Colors.BOLD = ''
        Colors.UNDERLINE = ''


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class CharacterSummary:
    """Summary of a character's learning state"""
    character_id: str
    total_decisions: int
    success_rate: float
    total_reward: float
    memory_count: int
    last_session: Optional[str] = None
    growth_score: float = 0.0
    teaching_moments: int = 0


@dataclass
class LearningMetrics:
    """Detailed learning metrics for a character"""
    character_id: str
    decisions_by_type: Dict[str, int]
    decisions_by_source: Dict[str, int]
    success_rate_by_type: Dict[str, float]
    reward_by_domain: Dict[str, float]
    avg_confidence: float
    avg_decision_time_ms: float
    quality_distribution: Dict[str, int]
    session_history: List[Dict]


@dataclass
class MemoryStats:
    """Memory system statistics"""
    total_memories: int
    episodic_count: int
    semantic_count: int
    avg_importance: float
    consolidation_count: int
    memory_growth_trend: List[float]


@dataclass
class TrainingReport:
    """Training data quality report"""
    total_training_eligible: int
    quality_distribution: Dict[str, int]
    avg_quality_score: float
    teaching_moments: int
    recommended_for_training: bool
    data_freshness_days: float


# ============================================================================
# Dashboard Database Queries
# ============================================================================

class DashboardData:
    """Data access layer for the dashboard"""

    def __init__(self, db_path: str = "data/decisions.db"):
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Check if database exists"""
        if not Path(self.db_path).exists():
            logger.warning(f"Database not found: {self.db_path}")

    def _get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def list_characters(self) -> List[str]:
        """Get list of all character IDs"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT character_id FROM decisions ORDER BY character_id")
            characters = [row[0] for row in cursor.fetchall()]
            conn.close()
            return characters
        except Exception as e:
            logger.error(f"Failed to list characters: {e}")
            return []

    def get_character_summary(self, character_id: str) -> Optional[CharacterSummary]:
        """Get summary statistics for a character"""
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Total decisions
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes
                FROM decisions
                WHERE character_id = ?
            """, (character_id,))
            row = cursor.fetchone()

            if not row or row['total'] == 0:
                conn.close()
                return None

            total_decisions = row['total']
            success_rate = row['successes'] / total_decisions if total_decisions > 0 else 0

            # Get aggregate rewards from outcome data
            cursor.execute("""
                SELECT decision_id, outcome_data FROM decisions
                WHERE character_id = ? AND outcome_data IS NOT NULL
            """, (character_id,))
            total_reward = 0.0
            teaching_moments = 0
            for row in cursor.fetchall():
                try:
                    outcome = json.loads(row['outcome_data'])
                    total_reward += outcome.get('aggregate_reward', 0.0)
                    if outcome.get('quality_analysis', {}).get('quality_score', 0.5) < 0:
                        teaching_moments += 1
                except:
                    pass

            # Get last session
            cursor.execute("""
                SELECT session_id FROM decisions
                WHERE character_id = ? AND session_id IS NOT NULL
                ORDER BY timestamp DESC LIMIT 1
            """, (character_id,))
            last_session_row = cursor.fetchone()
            last_session = last_session_row['session_id'] if last_session_row else None

            conn.close()

            return CharacterSummary(
                character_id=character_id,
                total_decisions=total_decisions,
                success_rate=success_rate,
                total_reward=total_reward,
                memory_count=total_decisions,  # Approximation
                last_session=last_session,
                teaching_moments=teaching_moments
            )
        except Exception as e:
            logger.error(f"Failed to get character summary: {e}")
            return None

    def get_learning_metrics(self, character_id: str) -> Optional[LearningMetrics]:
        """Get detailed learning metrics for a character"""
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Decisions by type
            cursor.execute("""
                SELECT decision_type, COUNT(*) as count
                FROM decisions
                WHERE character_id = ?
                GROUP BY decision_type
            """, (character_id,))
            decisions_by_type = {row['decision_type']: row['count'] for row in cursor.fetchall()}

            # Decisions by source
            cursor.execute("""
                SELECT decision_source, COUNT(*) as count
                FROM decisions
                WHERE character_id = ? AND decision_source IS NOT NULL
                GROUP BY decision_source
            """, (character_id,))
            decisions_by_source = {row['decision_source']: row['count'] for row in cursor.fetchall()}

            # Success rate by type
            cursor.execute("""
                SELECT decision_type,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as rate
                FROM decisions
                WHERE character_id = ? AND success IS NOT NULL
                GROUP BY decision_type
            """, (character_id,))
            success_rate_by_type = {row['decision_type']: row['rate'] for row in cursor.fetchall()}

            # Extract rewards by domain
            cursor.execute("""
                SELECT outcome_data FROM decisions
                WHERE character_id = ? AND outcome_data IS NOT NULL
            """, (character_id,))
            reward_by_domain = defaultdict(float)
            total_confidence = 0.0
            confidence_count = 0
            quality_dist = defaultdict(int)

            for row in cursor.fetchall():
                try:
                    outcome = json.loads(row['outcome_data'])
                    for reward in outcome.get('reward_signals', []):
                        domain = reward.get('domain', 'unknown')
                        value = reward.get('value', 0.0) * reward.get('confidence', 1.0)
                        reward_by_domain[domain] += value

                    # Quality distribution
                    quality_score = outcome.get('quality_analysis', {}).get('quality_score', 0.5)
                    if quality_score >= 0.7:
                        quality_dist['good'] += 1
                    elif quality_score >= 0.4:
                        quality_dist['acceptable'] += 1
                    else:
                        quality_dist['poor'] += 1
                except:
                    pass

            # Get average confidence from decision data
            cursor.execute("""
                SELECT decision_data FROM decisions
                WHERE character_id = ?
            """, (character_id,))
            for row in cursor.fetchall():
                try:
                    decision = json.loads(row['decision_data'])
                    conf = decision.get('confidence', 0.0)
                    if conf > 0:
                        total_confidence += conf
                        confidence_count += 1
                except:
                    pass

            avg_confidence = total_confidence / confidence_count if confidence_count > 0 else 0.0

            # Get session history
            cursor.execute("""
                SELECT session_id, COUNT(*) as decisions,
                       MIN(timestamp) as start, MAX(timestamp) as end
                FROM decisions
                WHERE character_id = ? AND session_id IS NOT NULL
                GROUP BY session_id
                ORDER BY start DESC
                LIMIT 10
            """, (character_id,))
            session_history = []
            for row in cursor.fetchall():
                session_history.append({
                    'session_id': row['session_id'],
                    'decisions': row['decisions'],
                    'start': row['start'],
                    'end': row['end']
                })

            conn.close()

            return LearningMetrics(
                character_id=character_id,
                decisions_by_type=decisions_by_type,
                decisions_by_source=decisions_by_source,
                success_rate_by_type=success_rate_by_type,
                reward_by_domain=dict(reward_by_domain),
                avg_confidence=avg_confidence,
                avg_decision_time_ms=0.0,  # Would need to track this
                quality_distribution=dict(quality_dist),
                session_history=session_history
            )
        except Exception as e:
            logger.error(f"Failed to get learning metrics: {e}")
            return None

    def get_training_report(self, character_id: str) -> Optional[TrainingReport]:
        """Get training data quality report"""
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Training eligible decisions
            cursor.execute("""
                SELECT COUNT(*) as count FROM decisions
                WHERE character_id = ? AND training_eligible = 1 AND outcome_data IS NOT NULL
            """, (character_id,))
            total_eligible = cursor.fetchone()['count']

            # Quality distribution
            cursor.execute("""
                SELECT quality_label, COUNT(*) as count
                FROM decisions
                WHERE character_id = ? AND quality_label IS NOT NULL
                GROUP BY quality_label
            """, (character_id,))
            quality_dist = {row['quality_label']: row['count'] for row in cursor.fetchall()}

            # Average quality score
            cursor.execute("""
                SELECT outcome_data FROM decisions
                WHERE character_id = ? AND outcome_data IS NOT NULL
            """, (character_id,))
            total_quality = 0.0
            quality_count = 0
            teaching_moments = 0

            timestamps = []
            for row in cursor.fetchall():
                try:
                    outcome = json.loads(row['outcome_data'])
                    quality = outcome.get('quality_analysis', {}).get('quality_score', 0.5)
                    total_quality += quality
                    quality_count += 1

                    if outcome.get('quality_analysis', {}).get('quality_score', 0.5) < 0:
                        teaching_moments += 1
                except:
                    pass

            avg_quality = total_quality / quality_count if quality_count > 0 else 0.0

            # Data freshness - get average timestamp age
            cursor.execute("""
                SELECT timestamp FROM decisions
                WHERE character_id = ?
                ORDER BY timestamp DESC
            """, (character_id,))
            timestamps_str = [row['timestamp'] for row in cursor.fetchall()]
            if timestamps_str:
                latest = datetime.fromisoformat(timestamps_str[0])
                freshness_days = (datetime.now() - latest).days
            else:
                freshness_days = 0

            conn.close()

            # Recommend for training if enough data
            recommended = total_eligible >= 50 and avg_quality >= 0.5

            return TrainingReport(
                total_training_eligible=total_eligible,
                quality_distribution=quality_dist,
                avg_quality_score=avg_quality,
                teaching_moments=teaching_moments,
                recommended_for_training=recommended,
                data_freshness_days=freshness_days
            )
        except Exception as e:
            logger.error(f"Failed to get training report: {e}")
            return None


# ============================================================================
# Terminal UI Components
# ============================================================================

class TerminalUI:
    """Terminal UI rendering utilities"""

    @staticmethod
    def header(text: str, width: int = 80):
        """Print a centered header"""
        padding = (width - len(text)) // 2
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * width}")
        print(f"{' ' * padding}{text}")
        print(f"{'=' * width}{Colors.ENDC}\n")

    @staticmethod
    def section(title: str):
        """Print a section title"""
        print(f"\n{Colors.BOLD}{Colors.OKCYAN}--- {title} ---{Colors.ENDC}")

    @staticmethod
    def key_value(key: str, value: Any, width: int = 25):
        """Print a key-value pair"""
        value_str = str(value) if value is not None else "N/A"
        print(f"  {key:<{width}}: {Colors.OKBLUE}{value_str}{Colors.ENDC}")

    @staticmethod
    def progress_bar(value: float, max_value: float = 1.0, width: int = 30,
                     label: str = "") -> str:
        """Create a visual progress bar"""
        ratio = min(1.0, max(0.0, value / max_value)) if max_value > 0 else 0
        filled = int(ratio * width)
        bar = "█" * filled + "░" * (width - filled)

        # Color based on value
        if ratio >= 0.7:
            color = Colors.OKGREEN
        elif ratio >= 0.4:
            color = Colors.WARNING
        else:
            color = Colors.FAIL

        return f"{color}{bar}{Colors.ENDC} {ratio:.1%}"

    @staticmethod
    def stat_card(title: str, value: str, subtitle: str = ""):
        """Print a stat card"""
        print(f"  {Colors.BOLD}{title}{Colors.ENDC}")
        print(f"    {Colors.OKGREEN}{value}{Colors.ENDC}")
        if subtitle:
            print(f"    {Colors.WARNING}{subtitle}{Colors.ENDC}")
        print()

    @staticmethod
    def table(headers: List[str], rows: List[List[str]], widths: List[int] = None):
        """Print a formatted table"""
        if widths is None:
            widths = [15] * len(headers)

        # Header
        header_line = "  "
        for i, h in enumerate(headers):
            header_line += f"{Colors.BOLD}{h:<{widths[i]}}{Colors.ENDC}"
        print(header_line)
        print("  " + "-" * sum(widths))

        # Rows
        for row in rows:
            row_line = "  "
            for i, cell in enumerate(row):
                row_line += f"{cell:<{widths[i]}}"
            print(row_line)

    @staticmethod
    def sparkline(values: List[float], width: int = 30) -> str:
        """Create a simple sparkline from values"""
        if not values:
            return "░" * width

        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val if max_val > min_val else 1

        bars = []
        bars_full = "▁▂▃▄▅▆▇█"

        for v in values:
            if range_val == 0:
                idx = 4
            else:
                normalized = (v - min_val) / range_val
                idx = int(normalized * (len(bars_full) - 1))
            bars.append(bars_full[idx])

        # Scale to fit width
        if len(bars) > width:
            step = len(bars) / width
            scaled = [bars[int(i * step)] for i in range(width)]
            return "".join(scaled)
        return "".join(bars)


# ============================================================================
# Character Dashboard
# ============================================================================

class CharacterDashboard:
    """
    Main dashboard class for displaying character learning progress.

    Usage:
        dashboard = CharacterDashboard(db_path="data/decisions.db")
        dashboard.show_character_summary("thorin")
        dashboard.show_learning_metrics("thorin")
        dashboard.show_training_report("thorin")
    """

    def __init__(self, db_path: str = "data/decisions.db"):
        self.data = DashboardData(db_path)
        self.ui = TerminalUI()

    def list_characters(self):
        """List all available characters"""
        characters = self.data.list_characters()

        self.ui.header("Character List")

        if not characters:
            print(f"{Colors.WARNING}No characters found in database.{Colors.ENDC}")
            return

        print(f"Found {len(characters)} character(s):\n")
        for char_id in characters:
            summary = self.data.get_character_summary(char_id)
            if summary:
                print(f"  {Colors.BOLD}{char_id}{Colors.ENDC}")
                print(f"    Decisions: {summary.total_decisions}")
                print(f"    Success Rate: {summary.success_rate:.1%}")
                print(f"    Teaching Moments: {summary.teaching_moments}")
                print()
            else:
                print(f"  {char_id} (no data)")

    def show_character_overview(self, character_id: str):
        """Show comprehensive overview of a character"""
        self.ui.header(f"Character Dashboard: {character_id}")

        summary = self.data.get_character_summary(character_id)

        if not summary:
            print(f"{Colors.FAIL}No data found for character: {character_id}{Colors.ENDC}")
            return

        # Overview section
        self.ui.section("Overview")
        self.ui.key_value("Character ID", summary.character_id)
        self.ui.key_value("Total Decisions", summary.total_decisions)
        self.ui.key_value("Success Rate", f"{summary.success_rate:.1%}")
        self.ui.key_value("Total Reward", f"{summary.total_reward:.2f}")
        self.ui.key_value("Last Session", summary.last_session or "No sessions")

        # Visual success rate
        print(f"\n  Success Rate:")
        print(f"    {self.ui.progress_bar(summary.success_rate)}")

        # Stats cards
        self.ui.section("Key Metrics")
        self.ui.stat_card("Decisions Made", str(summary.total_decisions),
                         f"Teaching moments: {summary.teaching_moments}")
        self.ui.stat_card("Performance", f"{summary.success_rate:.1%}",
                         "Based on all tracked decisions")
        self.ui.stat_card("Learning Score", f"{summary.total_reward:.2f}",
                         "Aggregate reward from all outcomes")

    def show_learning_metrics(self, character_id: str):
        """Show detailed learning metrics"""
        metrics = self.data.get_learning_metrics(character_id)

        if not metrics:
            print(f"{Colors.WARNING}No learning metrics available for {character_id}{Colors.ENDC}")
            return

        self.ui.section("Decision Analysis")

        # Decisions by type
        print(f"\n  {Colors.BOLD}Decisions by Type:{Colors.ENDC}")
        for dtype, count in metrics.decisions_by_type.items():
            print(f"    {dtype:<20} {Colors.OKGREEN}{count:>5}{Colors.ENDC}")

        # Decisions by source
        print(f"\n  {Colors.BOLD}Decisions by Source:{Colors.ENDC}")
        for source, count in metrics.decisions_by_source.items():
            print(f"    {source:<20} {Colors.OKBLUE}{count:>5}{Colors.ENDC}")

        # Success rate by type
        print(f"\n  {Colors.BOLD}Success Rate by Type:{Colors.ENDC}")
        for dtype, rate in metrics.success_rate_by_type.items():
            bar = self.ui.progress_bar(rate)
            print(f"    {dtype:<20} {bar}")

        # Rewards by domain
        if metrics.reward_by_domain:
            print(f"\n  {Colors.BOLD}Rewards by Domain:{Colors.ENDC}")
            for domain, reward in metrics.reward_by_domain.items():
                color = Colors.OKGREEN if reward > 0 else Colors.FAIL
                print(f"    {domain:<20} {color}{reward:>6.2f}{Colors.ENDC}")

        # Quality distribution
        if metrics.quality_distribution:
            print(f"\n  {Colors.BOLD}Quality Distribution:{Colors.ENDC}")
            for quality, count in metrics.quality_distribution.items():
                bar_color = Colors.OKGREEN if quality == 'good' else Colors.WARNING if quality == 'acceptable' else Colors.FAIL
                print(f"    {bar_color}{quality:<12}{Colors.ENDC} {count:>5}")

        # Average confidence
        print(f"\n  {Colors.BOLD}Average Confidence:{Colors.ENDC} {metrics.avg_confidence:.2%}")
        print(f"    {self.ui.progress_bar(metrics.avg_confidence)}")

        # Recent sessions
        if metrics.session_history:
            self.ui.section("Recent Sessions")
            headers = ["Session", "Decisions", "Start"]
            rows = []
            for session in metrics.session_history[:10]:
                rows.append([
                    session['session_id'][:20] + "..." if len(session['session_id']) > 20 else session['session_id'],
                    str(session['decisions']),
                    session['start'][:10]
                ])
            self.ui.table(headers, rows, widths=[25, 10, 12])

    def show_training_report(self, character_id: str):
        """Show training data quality report"""
        report = self.data.get_training_report(character_id)

        if not report:
            print(f"{Colors.WARNING}No training report available for {character_id}{Colors.ENDC}")
            return

        self.ui.section("Training Readiness Report")

        # Training eligibility
        print(f"\n  {Colors.BOLD}Training Data Statistics:{Colors.ENDC}")
        self.ui.key_value("Training Eligible", report.total_training_eligible)
        self.ui.key_value("Average Quality", f"{report.avg_quality_score:.2f}")
        self.ui.key_value("Teaching Moments", report.teaching_moments)
        self.ui.key_value("Data Freshness", f"{report.data_freshness_days:.0f} days ago")

        # Quality distribution
        if report.quality_distribution:
            print(f"\n  {Colors.BOLD}Quality Label Distribution:{Colors.ENDC}")
            for label, count in report.quality_distribution.items():
                color = Colors.OKGREEN if label in ['good', 'excellent'] else Colors.WARNING if label == 'acceptable' else Colors.FAIL
                print(f"    {color}{label:<15}{Colors.ENDC} {count:>5}")

        # Recommendation
        print(f"\n  {Colors.BOLD}Training Recommendation:{Colors.ENDC}")
        if report.recommended_for_training:
            print(f"    {Colors.OKGREEN}READY FOR TRAINING{Colors.ENDC}")
            print(f"    {Colors.OKGREEN}This character has sufficient quality data for QLoRA fine-tuning.{Colors.ENDC}")
        else:
            if report.total_training_eligible < 50:
                print(f"    {Colors.WARNING}NEED MORE DATA{Colors.ENDC}")
                print(f"    {Colors.WARNING}Collect at least {50 - report.total_training_eligible} more training-eligible decisions.{Colors.ENDC}")
            elif report.avg_quality_score < 0.5:
                print(f"    {Colors.WARNING}IMPROVE QUALITY{Colors.ENDC}")
                print(f"    {Colors.WARNING}Average quality score is below threshold. Focus on high-quality decisions.{Colors.ENDC}")

    def show_full_dashboard(self, character_id: str):
        """Show complete dashboard for a character"""
        self.show_character_overview(character_id)
        self.show_learning_metrics(character_id)
        self.show_training_report(character_id)

    def export_report(self, character_id: str, output_path: str):
        """Export dashboard report to JSON"""
        summary = self.data.get_character_summary(character_id)
        metrics = self.data.get_learning_metrics(character_id)
        report = self.data.get_training_report(character_id)

        export_data = {
            "character_id": character_id,
            "generated_at": datetime.now().isoformat(),
            "summary": summary.__dict__ if summary else None,
            "learning_metrics": metrics.__dict__ if metrics else None,
            "training_report": report.__dict__ if report else None
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        print(f"\n{Colors.OKGREEN}Report exported to: {output_path}{Colors.ENDC}")


# ============================================================================
# Hyperparameter Optimization Hints
# ============================================================================

@dataclass
class CharacterClassHints:
    """Hyperparameter hints for a character class"""
    class_name: str
    description: str
    recommended_lora_r: int
    recommended_lora_alpha: int
    recommended_learning_rate: float
    recommended_epochs: int
    recommended_batch_size: int
    target_success_ratio: float
    quality_threshold: float
    reasoning: str


# Character class templates with hyperparameter hints
CHARACTER_CLASS_HINTS = {
    "combat_focused": CharacterClassHints(
        class_name="combat_focused",
        description="Characters focused on combat and tactical decisions",
        recommended_lora_r=16,
        recommended_lora_alpha=32,
        recommended_learning_rate=2e-4,
        recommended_epochs=3,
        recommended_batch_size=4,
        target_success_ratio=0.65,
        quality_threshold=0.5,
        reasoning="Combat decisions benefit from higher rank for tactical complexity"
    ),
    "social_focused": CharacterClassHints(
        class_name="social_focused",
        description="Characters focused on social interactions and dialogue",
        recommended_lora_r=32,
        recommended_lora_alpha=64,
        recommended_learning_rate=1e-4,
        recommended_epochs=4,
        recommended_batch_size=2,
        target_success_ratio=0.6,
        quality_threshold=0.45,
        reasoning="Social interactions require higher capacity for nuance and context"
    ),
    "exploration_focused": CharacterClassHints(
        class_name="exploration_focused",
        description="Characters focused on exploration and discovery",
        recommended_lora_r=16,
        recommended_lora_alpha=32,
        recommended_learning_rate=2e-4,
        recommended_epochs=2,
        recommended_batch_size=4,
        target_success_ratio=0.7,
        quality_threshold=0.5,
        reasoning="Exploration patterns are simpler, faster training"
    ),
    "balanced": CharacterClassHints(
        class_name="balanced",
        description="Characters with mixed decision types",
        recommended_lora_r=24,
        recommended_lora_alpha=48,
        recommended_learning_rate=1.5e-4,
        recommended_epochs=3,
        recommended_batch_size=4,
        target_success_ratio=0.65,
        quality_threshold=0.5,
        reasoning="Balanced characters need medium complexity to handle all scenarios"
    ),
    "high_variance": CharacterClassHints(
        class_name="high_variance",
        description="Characters with inconsistent performance (teaching moments)",
        recommended_lora_r=32,
        recommended_lora_alpha=64,
        recommended_learning_rate=5e-5,
        recommended_epochs=5,
        recommended_batch_size=2,
        target_success_ratio=0.6,
        quality_threshold=0.4,
        reasoning="High variance requires more careful learning with lower rates"
    ),
}


def detect_character_class(metrics: LearningMetrics) -> str:
    """Detect character class based on decision patterns"""
    total_decisions = sum(metrics.decisions_by_type.values())

    if total_decisions == 0:
        return "balanced"

    # Calculate type distribution
    combat_ratio = metrics.decisions_by_type.get('combat_action', 0) / total_decisions
    social_ratio = metrics.decisions_by_type.get('social', 0) / total_decisions
    exploration_ratio = metrics.decisions_by_type.get('exploration', 0) / total_decisions

    # Check for high variance (poor quality ratio)
    poor_quality = metrics.quality_distribution.get('poor', 0)
    total_quality = sum(metrics.quality_distribution.values())
    variance_ratio = poor_quality / total_quality if total_quality > 0 else 0

    if variance_ratio > 0.3:
        return "high_variance"
    elif combat_ratio > 0.5:
        return "combat_focused"
    elif social_ratio > 0.5:
        return "social_focused"
    elif exploration_ratio > 0.5:
        return "exploration_focused"
    else:
        return "balanced"


def show_hyperparameter_hints(character_id: str, db_path: str = "data/decisions.db"):
    """Display hyperparameter optimization hints for a character"""
    data = DashboardData(db_path)
    metrics = data.get_learning_metrics(character_id)

    if not metrics:
        print(f"{Colors.WARNING}No metrics available for {character_id}{Colors.ENDC}")
        return

    # Detect character class
    detected_class = detect_character_class(metrics)
    hints = CHARACTER_CLASS_HINTS[detected_class]

    ui = TerminalUI()
    ui.header(f"Hyperparameter Hints: {character_id}")

    print(f"\n  {Colors.BOLD}Detected Character Class:{Colors.ENDC} {Colors.OKCYAN}{detected_class}{Colors.ENDC}")
    print(f"  {hints.description}")
    print(f"  {Colors.WARNING}{hints.reasoning}{Colors.ENDC}")

    ui.section("Recommended Hyperparameters")

    ui.key_value("LoRA Rank (r)", hints.recommended_lora_r)
    ui.key_value("LoRA Alpha", hints.recommended_lora_alpha)
    ui.key_value("Learning Rate", f"{hints.recommended_learning_rate:.0e}")
    ui.key_value("Epochs", hints.recommended_epochs)
    ui.key_value("Batch Size", hints.recommended_batch_size)
    ui.key_value("Target Success Ratio", hints.target_success_ratio)
    ui.key_value("Quality Threshold", hints.quality_threshold)

    # Export config
    print(f"\n  {Colors.BOLD}Training Config JSON:{Colors.ENDC}")
    config = {
        "character_id": character_id,
        "character_class": detected_class,
        "lora_r": hints.recommended_lora_r,
        "lora_alpha": hints.recommended_lora_alpha,
        "learning_rate": hints.recommended_learning_rate,
        "num_train_epochs": hints.recommended_epochs,
        "per_device_train_batch_size": hints.recommended_batch_size,
        "target_success_ratio": hints.target_success_ratio,
        "min_quality_score": hints.quality_threshold
    }
    print(f"  {Colors.OKGREEN}{json.dumps(config, indent=2)}{Colors.ENDC}")


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="DMLog Character Dashboard - View character learning progress",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list-characters
  %(prog)s --character-id thorin
  %(prog)s --character-id thorin --show-metrics
  %(prog)s --character-id thorin --show-training
  %(prog)s --character-id thorin --export report.json
  %(prog)s --character-id thorin --hyperparameter-hints
        """
    )

    parser.add_argument(
        "--db-path",
        default="data/decisions.db",
        help="Path to the decisions database"
    )

    parser.add_argument(
        "--list-characters",
        action="store_true",
        help="List all available characters"
    )

    parser.add_argument(
        "--character-id",
        type=str,
        help="Character ID to display"
    )

    parser.add_argument(
        "--show-metrics",
        action="store_true",
        help="Show detailed learning metrics"
    )

    parser.add_argument(
        "--show-training",
        action="store_true",
        help="Show training readiness report"
    )

    parser.add_argument(
        "--export",
        type=str,
        metavar="PATH",
        help="Export report to JSON file"
    )

    parser.add_argument(
        "--hyperparameter-hints",
        action="store_true",
        help="Show hyperparameter optimization hints"
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )

    args = parser.parse_args()

    # Disable colors if requested
    if args.no_color or not sys.stdout.isatty():
        Colors.disable()

    # Create dashboard
    dashboard = CharacterDashboard(args.db_path)

    # List characters
    if args.list_characters:
        dashboard.list_characters()
        return

    # Need character ID for other commands
    if not args.character_id:
        parser.print_help()
        print("\nError: --character-id is required (unless using --list-characters)")
        return

    # Hyperparameter hints
    if args.hyperparameter_hints:
        show_hyperparameter_hints(args.character_id, args.db_path)
        return

    # Export report
    if args.export:
        dashboard.export_report(args.character_id, args.export)
        return

    # Show specific sections or full dashboard
    if args.show_metrics:
        dashboard.show_learning_metrics(args.character_id)
    elif args.show_training:
        dashboard.show_training_report(args.character_id)
    else:
        dashboard.show_full_dashboard(args.character_id)


if __name__ == "__main__":
    main()
