"""
Training Data Collector

Captures gameplay decisions for character learning and improvement.
Integrates with escalation engine to log decisions, context, and outcomes.

Phase 7.1.1 - Decision Logger
Phase 7.1.2 - Enhanced with Outcome Tracker integration
Phase 7.1.3 - Enhanced with Session Manager integration
"""

import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Import outcome tracker for Phase 7.1.2
try:
    from outcome_tracker import OutcomeTracker, OutcomeType
    OUTCOME_TRACKER_AVAILABLE = True
except ImportError:
    OUTCOME_TRACKER_AVAILABLE = False
    logger.warning("OutcomeTracker not available - advanced outcome analysis disabled")

# Import session manager for Phase 7.1.3
try:
    from session_manager import SessionManager
    SESSION_MANAGER_AVAILABLE = True
except ImportError:
    SESSION_MANAGER_AVAILABLE = False
    logger.warning("SessionManager not available - enhanced session tracking disabled")


@dataclass
class CharacterDataSettings:
    """Privacy and data collection settings per character"""
    character_id: str
    enabled: bool = True
    collect_bot_decisions: bool = True
    collect_brain_decisions: bool = True
    collect_human_overrides: bool = True
    retention_days: int = 30
    training_eligible: bool = True
    
    def should_log_decision(self, decision_source: str) -> bool:
        """Check if this decision should be logged"""
        if not self.enabled:
            return False
        
        if decision_source == 'bot' and not self.collect_bot_decisions:
            return False
        if decision_source == 'brain' and not self.collect_brain_decisions:
            return False
        if decision_source == 'human' and not self.collect_human_overrides:
            return False
        
        return True


class TrainingDataCollector:
    """
    Collects gameplay decisions for training character models.
    
    Features:
    - Logs decisions with full context
    - Tracks outcomes and success metrics
    - Respects privacy settings
    - Efficient querying and export
    - Automatic data cleanup
    """
    
    def __init__(self, db_path: str = "data/decisions.db"):
        """
        Initialize the training data collector
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.current_session_id: Optional[str] = None
        
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Load character settings
        self.character_settings: Dict[str, CharacterDataSettings] = {}
        self._load_character_settings()
        
        # Initialize outcome tracker (Phase 7.1.2)
        self.outcome_tracker = None
        if OUTCOME_TRACKER_AVAILABLE:
            try:
                self.outcome_tracker = OutcomeTracker()
                logger.info("Outcome tracking enabled with reward signals")
            except Exception as e:
                logger.warning(f"Failed to initialize outcome tracker: {e}")
        
        # Initialize session manager (Phase 7.1.3)
        self.session_manager = None
        if SESSION_MANAGER_AVAILABLE:
            try:
                self.session_manager = SessionManager()
                logger.info("Enhanced session management enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize session manager: {e}")
        
        logger.info(f"TrainingDataCollector initialized: {db_path}")
    
    def _init_database(self) -> None:
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Decisions table - main storage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                decision_id TEXT PRIMARY KEY,
                character_id TEXT NOT NULL,
                session_id TEXT,
                timestamp TEXT NOT NULL,
                
                -- Situation context (JSON)
                situation_context TEXT NOT NULL,
                
                -- Decision details (JSON)
                decision_data TEXT NOT NULL,
                
                -- Outcome (JSON, filled in later)
                outcome_data TEXT,
                outcome_timestamp TEXT,
                
                -- Meta
                training_eligible INTEGER DEFAULT 1,
                quality_label TEXT,  -- 'good', 'acceptable', 'bad', 'teaching_moment'
                reflection_notes TEXT,
                
                -- Indexes for queries
                decision_type TEXT,
                decision_source TEXT,
                success INTEGER,
                
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                start_timestamp TEXT NOT NULL,
                end_timestamp TEXT,
                character_ids TEXT,  -- JSON array
                total_decisions INTEGER DEFAULT 0,
                session_notes TEXT
            )
        """)
        
        # Character settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_settings (
                character_id TEXT PRIMARY KEY,
                enabled INTEGER DEFAULT 1,
                collect_bot_decisions INTEGER DEFAULT 1,
                collect_brain_decisions INTEGER DEFAULT 1,
                collect_human_overrides INTEGER DEFAULT 1,
                retention_days INTEGER DEFAULT 30,
                training_eligible INTEGER DEFAULT 1,
                updated_timestamp TEXT NOT NULL
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_character_id 
            ON decisions(character_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_id 
            ON decisions(session_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON decisions(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_decision_source 
            ON decisions(decision_source)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_training_eligible 
            ON decisions(training_eligible)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quality_label 
            ON decisions(quality_label)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("Database initialized successfully")
    
    def _load_character_settings(self) -> None:
        """Load character settings from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM character_settings")
        rows = cursor.fetchall()
        
        for row in rows:
            settings = CharacterDataSettings(
                character_id=row[0],
                enabled=bool(row[1]),
                collect_bot_decisions=bool(row[2]),
                collect_brain_decisions=bool(row[3]),
                collect_human_overrides=bool(row[4]),
                retention_days=row[5],
                training_eligible=bool(row[6])
            )
            self.character_settings[row[0]] = settings
        
        conn.close()
        
        logger.info(f"Loaded settings for {len(self.character_settings)} characters")
    
    def get_character_settings(
        self,
        character_id: str
    ) -> CharacterDataSettings:
        """
        Get settings for a character, creating defaults if needed
        
        Args:
            character_id: Character ID
            
        Returns:
            CharacterDataSettings for this character
        """
        if character_id not in self.character_settings:
            # Create default settings
            settings = CharacterDataSettings(character_id=character_id)
            self.character_settings[character_id] = settings
            self._save_character_settings(settings)
        
        return self.character_settings[character_id]
    
    def update_character_settings(
        self,
        settings: CharacterDataSettings
    ) -> None:
        """
        Update settings for a character
        
        Args:
            settings: New settings to save
        """
        self.character_settings[settings.character_id] = settings
        self._save_character_settings(settings)
        logger.info(f"Updated settings for {settings.character_id}")
    
    def _save_character_settings(
        self,
        settings: CharacterDataSettings
    ) -> None:
        """Save character settings to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO character_settings 
            (character_id, enabled, collect_bot_decisions, collect_brain_decisions,
             collect_human_overrides, retention_days, training_eligible, updated_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            settings.character_id,
            int(settings.enabled),
            int(settings.collect_bot_decisions),
            int(settings.collect_brain_decisions),
            int(settings.collect_human_overrides),
            settings.retention_days,
            int(settings.training_eligible),
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def start_session(
        self,
        session_id: Optional[str] = None,
        session_notes: str = "",
        character_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Start a new gameplay session (Phase 7.1.3 enhanced)
        
        Args:
            session_id: Optional custom session ID
            session_notes: Optional notes about the session
            character_ids: Characters participating in session
            tags: Session tags for categorization
            
        Returns:
            Session ID
        """
        if session_id is None:
            session_id = f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        self.current_session_id = session_id
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sessions 
            (session_id, start_timestamp, character_ids, session_notes)
            VALUES (?, ?, ?, ?)
        """, (
            session_id,
            datetime.utcnow().isoformat(),
            json.dumps(character_ids or []),
            session_notes
        ))
        
        conn.commit()
        conn.close()
        
        # Start session in session manager (Phase 7.1.3)
        if self.session_manager:
            try:
                self.session_manager.start_session(
                    session_id=session_id,
                    character_ids=character_ids,
                    notes=session_notes,
                    tags=tags
                )
            except Exception as e:
                logger.warning(f"Failed to start session in manager: {e}")
        
        logger.info(f"Started session: {session_id}")
        return session_id
    
    def end_session(self) -> Optional[Dict[str, Any]]:
        """
        End the current session (Phase 7.1.3 enhanced)
        
        Returns:
            Session summary if session manager available
        """
        if not self.current_session_id:
            logger.warning("No active session to end")
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update session end time and decision count
        cursor.execute("""
            UPDATE sessions
            SET end_timestamp = ?,
                total_decisions = (
                    SELECT COUNT(*) FROM decisions 
                    WHERE session_id = ?
                )
            WHERE session_id = ?
        """, (
            datetime.utcnow().isoformat(),
            self.current_session_id,
            self.current_session_id
        ))
        
        conn.commit()
        conn.close()
        
        # End session in session manager (Phase 7.1.3)
        session_summary = None
        if self.session_manager:
            try:
                final_metrics = self.session_manager.end_session(self.current_session_id)
                if final_metrics:
                    session_summary = {
                        "session_id": final_metrics.session_id,
                        "duration_seconds": final_metrics.session_duration_seconds,
                        "total_decisions": final_metrics.total_decisions,
                        "success_rate": final_metrics.total_successes / max(1, final_metrics.total_decisions),
                        "total_reward": final_metrics.total_session_reward,
                        "characters_improved": final_metrics.characters_improved,
                        "avg_growth_score": final_metrics.avg_growth_score,
                        "teaching_moments": final_metrics.teaching_moments
                    }
            except Exception as e:
                logger.warning(f"Failed to end session in manager: {e}")
        
        logger.info(f"Ended session: {self.current_session_id}")
        session_id = self.current_session_id
        self.current_session_id = None
        
        return session_summary
    
    def log_decision(
        self,
        character_id: str,
        situation_context: Dict[str, Any],
        decision: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Log a gameplay decision (Phase 7.1.3 enhanced)
        
        Args:
            character_id: Character making the decision
            situation_context: Game state and context
            decision: Decision details (action, reasoning, confidence, etc.)
            session_id: Optional session ID (uses current if not specified)
            
        Returns:
            decision_id if logged, None if rejected by settings
        """
        # Check privacy settings
        settings = self.get_character_settings(character_id)
        decision_source = decision.get('source', 'bot')
        
        if not settings.should_log_decision(decision_source):
            logger.debug(f"Decision not logged due to privacy settings: {character_id}")
            return None
        
        # Generate decision ID
        decision_id = f"dec_{uuid.uuid4().hex}"
        
        # Use current session or provided session
        session = session_id or self.current_session_id
        
        # Extract key fields for indexing
        decision_type = decision.get('decision_type', 'unknown')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO decisions
            (decision_id, character_id, session_id, timestamp,
             situation_context, decision_data, decision_type, decision_source,
             training_eligible)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision_id,
            character_id,
            session,
            datetime.utcnow().isoformat(),
            json.dumps(situation_context),
            json.dumps(decision),
            decision_type,
            decision_source,
            int(settings.training_eligible)
        ))
        
        conn.commit()
        conn.close()
        
        # Notify session manager (Phase 7.1.3)
        if self.session_manager and session:
            try:
                self.session_manager.record_decision(
                    session_id=session,
                    character_id=character_id,
                    decision_data=decision,
                    outcome_data=None  # Will be added when outcome is recorded
                )
            except Exception as e:
                logger.warning(f"Failed to record decision in session manager: {e}")
        
        logger.debug(f"Logged decision: {decision_id} for {character_id}")
        return decision_id
    
    def update_outcome(
        self,
        decision_id: str,
        outcome: Dict[str, Any],
        success: bool
    ) -> None:
        """
        Update a decision with its outcome (Phase 7.1.2-7.1.3 enhanced)
        
        Args:
            decision_id: ID of the decision
            outcome: Outcome details
            success: Whether the decision was successful
        """
        # Get the decision context for reward calculation
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT situation_context, decision_data, character_id, session_id
            FROM decisions 
            WHERE decision_id = ?
        """, (decision_id,))
        
        row = cursor.fetchone()
        
        if not row:
            logger.warning(f"Decision not found for outcome update: {decision_id}")
            conn.close()
            return
        
        situation_context = json.loads(row[0])
        decision_data = json.loads(row[1])
        character_id = row[2]
        session_id = row[3]
        
        # Enhanced outcome with reward signals (Phase 7.1.2)
        enhanced_outcome = dict(outcome)
        
        if self.outcome_tracker:
            try:
                # Determine outcome type
                outcome_type = outcome.get("outcome_type", "immediate")
                
                # Build context for reward calculation
                reward_context = {
                    "decision_type": decision_data.get("decision_type", "unknown"),
                    "situation": situation_context,
                    "decision": decision_data
                }
                
                # Track outcome with reward signals
                if outcome_type == "immediate":
                    outcome_record = self.outcome_tracker.track_immediate_outcome(
                        decision_id=decision_id,
                        description=outcome.get("immediate", str(outcome)),
                        success=success,
                        context=reward_context
                    )
                else:
                    outcome_record = self.outcome_tracker.track_delayed_outcome(
                        decision_id=decision_id,
                        description=outcome.get("delayed", outcome.get("immediate", str(outcome))),
                        success=success,
                        context=reward_context,
                        outcome_type=OutcomeType.SHORT_TERM if outcome_type == "short_term" else OutcomeType.LONG_TERM,
                        related_decisions=outcome.get("related_decisions", [])
                    )
                
                # Add reward signals to outcome
                enhanced_outcome["reward_signals"] = [r.to_dict() for r in outcome_record.rewards]
                enhanced_outcome["aggregate_reward"] = self.outcome_tracker.get_aggregate_reward(decision_id)
                
                # Add quality analysis
                quality = self.outcome_tracker.analyze_decision_quality(decision_id)
                enhanced_outcome["quality_analysis"] = quality
                
            except Exception as e:
                logger.warning(f"Failed to calculate reward signals: {e}")
        
        # Update database
        cursor.execute("""
            UPDATE decisions
            SET outcome_data = ?,
                outcome_timestamp = ?,
                success = ?
            WHERE decision_id = ?
        """, (
            json.dumps(enhanced_outcome),
            datetime.utcnow().isoformat(),
            int(success),
            decision_id
        ))
        
        conn.commit()
        conn.close()
        
        # Notify session manager (Phase 7.1.3)
        if self.session_manager and session_id:
            try:
                # The session manager needs the full outcome data
                self.session_manager.record_decision(
                    session_id=session_id,
                    character_id=character_id,
                    decision_data=decision_data,
                    outcome_data=enhanced_outcome
                )
            except Exception as e:
                logger.warning(f"Failed to update session manager with outcome: {e}")
        
        if cursor.rowcount == 0:
            logger.warning(f"Decision not found for outcome update: {decision_id}")
        else:
            logger.debug(f"Updated outcome for decision: {decision_id} (enhanced={self.outcome_tracker is not None})")

    
    def update_quality_label(
        self,
        decision_id: str,
        quality_label: str,
        reflection_notes: str = ""
    ) -> None:
        """
        Update decision quality label (from reflection pipeline)
        
        Args:
            decision_id: ID of the decision
            quality_label: Quality label ('good', 'acceptable', 'bad', 'teaching_moment')
            reflection_notes: Optional notes from reflection analysis
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE decisions
            SET quality_label = ?,
                reflection_notes = ?
            WHERE decision_id = ?
        """, (quality_label, reflection_notes, decision_id))
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Updated quality label for {decision_id}: {quality_label}")
    
    def get_decisions_for_character(
        self,
        character_id: str,
        session_id: Optional[str] = None,
        limit: Optional[int] = None,
        training_eligible_only: bool = False,
        include_outcomes: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve decisions for a character
        
        Args:
            character_id: Character ID
            session_id: Optional session filter
            limit: Optional limit on number of results
            training_eligible_only: Only return training-eligible decisions
            include_outcomes: Whether to include decisions with outcomes
            
        Returns:
            List of decision records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT * FROM decisions
            WHERE character_id = ?
        """
        params = [character_id]
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        if training_eligible_only:
            query += " AND training_eligible = 1"
        
        if include_outcomes:
            query += " AND outcome_data IS NOT NULL"
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert to dictionaries
        decisions = []
        for row in rows:
            decision = dict(row)
            # Parse JSON fields
            decision['situation_context'] = json.loads(decision['situation_context'])
            decision['decision_data'] = json.loads(decision['decision_data'])
            if decision['outcome_data']:
                decision['outcome_data'] = json.loads(decision['outcome_data'])
            decisions.append(decision)
        
        conn.close()
        
        logger.debug(f"Retrieved {len(decisions)} decisions for {character_id}")
        return decisions
    
    def get_training_eligible_decisions(
        self,
        character_id: str,
        min_quality: Optional[str] = None,
        decision_types: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get decisions suitable for training
        
        Args:
            character_id: Character ID
            min_quality: Minimum quality label ('good', 'acceptable')
            decision_types: Optional filter by decision types
            limit: Optional limit on results
            
        Returns:
            List of training-eligible decisions
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT * FROM decisions
            WHERE character_id = ?
            AND training_eligible = 1
            AND outcome_data IS NOT NULL
        """
        params = [character_id]
        
        if min_quality:
            if min_quality == 'good':
                query += " AND quality_label = 'good'"
            elif min_quality == 'acceptable':
                query += " AND quality_label IN ('good', 'acceptable')"
        
        if decision_types:
            placeholders = ','.join('?' * len(decision_types))
            query += f" AND decision_type IN ({placeholders})"
            params.extend(decision_types)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        decisions = []
        for row in rows:
            decision = dict(row)
            decision['situation_context'] = json.loads(decision['situation_context'])
            decision['decision_data'] = json.loads(decision['decision_data'])
            decision['outcome_data'] = json.loads(decision['outcome_data'])
            decisions.append(decision)
        
        conn.close()
        
        return decisions
    
    def get_statistics(
        self,
        character_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about collected data
        
        Args:
            character_id: Optional character filter
            session_id: Optional session filter
            
        Returns:
            Statistics dictionary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query
        where_clauses = []
        params = []
        
        if character_id:
            where_clauses.append("character_id = ?")
            params.append(character_id)
        
        if session_id:
            where_clauses.append("session_id = ?")
            params.append(session_id)
        
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        
        # Total decisions
        cursor.execute(f"SELECT COUNT(*) FROM decisions {where_sql}", params)
        total_decisions = cursor.fetchone()[0]
        
        # By source
        cursor.execute(f"""
            SELECT decision_source, COUNT(*) 
            FROM decisions {where_sql}
            GROUP BY decision_source
        """, params)
        by_source = dict(cursor.fetchall())
        
        # By type
        cursor.execute(f"""
            SELECT decision_type, COUNT(*) 
            FROM decisions {where_sql}
            GROUP BY decision_type
        """, params)
        by_type = dict(cursor.fetchall())
        
        # Success rate
        cursor.execute(f"""
            SELECT 
                COUNT(CASE WHEN success = 1 THEN 1 END) as successes,
                COUNT(CASE WHEN success = 0 THEN 1 END) as failures,
                COUNT(CASE WHEN success IS NULL THEN 1 END) as pending
            FROM decisions {where_sql}
        """, params)
        success_data = cursor.fetchone()
        
        # Quality labels
        cursor.execute(f"""
            SELECT quality_label, COUNT(*) 
            FROM decisions {where_sql}
            WHERE quality_label IS NOT NULL
            GROUP BY quality_label
        """, params)
        by_quality = dict(cursor.fetchall())
        
        # Training eligible
        cursor.execute(f"""
            SELECT COUNT(*) 
            FROM decisions {where_sql}
            AND training_eligible = 1
            AND outcome_data IS NOT NULL
        """, params)
        training_eligible_count = cursor.fetchone()[0]
        
        conn.close()
        
        stats = {
            "total_decisions": total_decisions,
            "by_source": by_source,
            "by_type": by_type,
            "successes": success_data[0],
            "failures": success_data[1],
            "pending_outcomes": success_data[2],
            "success_rate": success_data[0] / (success_data[0] + success_data[1]) if (success_data[0] + success_data[1]) > 0 else 0,
            "by_quality": by_quality,
            "training_eligible": training_eligible_count
        }
        
        return stats
    
    def cleanup_old_data(
        self,
        character_id: Optional[str] = None
    ) -> int:
        """
        Clean up old data based on retention policies
        
        Args:
            character_id: Optional character to clean up (all if None)
            
        Returns:
            Number of decisions deleted
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        deleted_count = 0
        
        if character_id:
            characters = [character_id]
        else:
            # Get all characters with settings
            cursor.execute("SELECT character_id FROM character_settings")
            characters = [row[0] for row in cursor.fetchall()]
        
        for char_id in characters:
            settings = self.get_character_settings(char_id)
            cutoff_date = datetime.utcnow() - timedelta(days=settings.retention_days)
            
            cursor.execute("""
                DELETE FROM decisions
                WHERE character_id = ?
                AND timestamp < ?
            """, (char_id, cutoff_date.isoformat()))
            
            deleted_count += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"Cleaned up {deleted_count} old decisions")
        return deleted_count
    
    def export_to_json(
        self,
        character_id: str,
        output_path: str,
        include_all: bool = False
    ) -> None:
        """
        Export character data to JSON file

        Args:
            character_id: Character to export
            output_path: Output file path
            include_all: Include non-training-eligible decisions
        """
        if include_all:
            decisions = self.get_decisions_for_character(character_id)
        else:
            decisions = self.get_training_eligible_decisions(character_id)

        export_data = {
            "character_id": character_id,
            "export_timestamp": datetime.utcnow().isoformat(),
            "total_decisions": len(decisions),
            "decisions": decisions,
            "statistics": self.get_statistics(character_id)
        }

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported {len(decisions)} decisions to {output_path}")

    # ========================================================================
    # Phase 7.2.2: QLoRA Training Data Export
    # ========================================================================

    def export_for_qlora(
        self,
        character_id: str,
        output_path: str,
        format: str = "jsonl",
        min_confidence: float = 0.3,
        min_quality: float = 0.4,
        include_teaching_moments: bool = True
    ) -> Dict[str, Any]:
        """
        Export training data in QLoRA-compatible format (Phase 7.2.2)

        Args:
            character_id: Character to export
            output_path: Output file path
            format: Output format ('jsonl' or 'parquet')
            min_confidence: Minimum confidence threshold
            min_quality: Minimum quality score threshold
            include_teaching_moments: Always include teaching moments

        Returns:
            Export statistics
        """
        decisions = self.get_training_eligible_decisions(character_id)

        # Filter by quality
        filtered_decisions = []
        for d in decisions:
            quality_label = d.get('quality_label', 'unknown')
            confidence = d.get('decision_data', {}).get('confidence', 0.0)
            quality_analysis = d.get('outcome_data', {}).get('quality_analysis', {})
            quality_score = quality_analysis.get('quality_score', 0.5)

            # Always include teaching moments
            if quality_label == 'teaching_moment' and include_teaching_moments:
                filtered_decisions.append(d)
                continue

            # Apply filters
            if confidence < min_confidence:
                continue
            if quality_score < min_quality:
                continue

            filtered_decisions.append(d)

        # Convert to QLoRA format
        qlora_records = []
        for d in filtered_decisions:
            record = self._decision_to_qlora_format(d)
            qlora_records.append(record)

        # Write output
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if format == "jsonl":
            with open(output_file, 'w') as f:
                for record in qlora_records:
                    f.write(json.dumps(record) + '\n')
        elif format == "parquet":
            try:
                import pandas as pd
                df = pd.DataFrame(qlora_records)
                df.to_parquet(output_file, index=False)
            except ImportError:
                logger.warning("pandas not available, falling back to jsonl")
                output_file = output_file.with_suffix('.jsonl')
                with open(output_file, 'w') as f:
                    for record in qlora_records:
                        f.write(json.dumps(record) + '\n')

        stats = {
            "character_id": character_id,
            "total_decisions": len(decisions),
            "filtered_decisions": len(filtered_decisions),
            "exported_records": len(qlora_records),
            "output_path": str(output_file),
            "format": format
        }

        logger.info(f"Exported {len(qlora_records)} QLoRA records to {output_file}")
        return stats

    def _decision_to_qlora_format(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a decision to QLoRA training format (Phase 7.2.2)

        Format for instruction tuning:
        {
            "instruction": "What action should I take?",
            "input": "<situation context>",
            "output": "<decision with reasoning>"
        }
        """
        situation = decision.get('situation_context', {})
        decision_data = decision.get('decision_data', {})
        outcome = decision.get('outcome_data', {})

        # Build instruction prompt
        instruction = self._build_instruction_prompt(decision)

        # Build input (context)
        input_text = self._build_input_context(situation, decision_data)

        # Build output (the decision and what happened)
        output_text = self._build_output_text(decision_data, outcome)

        return {
            "instruction": instruction,
            "input": input_text,
            "output": output_text,
            "metadata": {
                "decision_id": decision.get('decision_id'),
                "decision_type": decision_data.get('decision_type', 'unknown'),
                "quality_label": decision.get('quality_label', 'unknown'),
                "success": decision.get('success', False),
                "confidence": decision_data.get('confidence', 0.0)
            }
        }

    def _build_instruction_prompt(self, decision: Dict[str, Any]) -> str:
        """Build the instruction prompt for QLoRA training"""
        decision_type = decision.get('decision_data', {}).get('decision_type', 'action')

        instructions = {
            "combat_action": "What combat action should I take in this situation?",
            "exploration": "How should I proceed with exploration?",
            "social": "How should I respond in this social situation?",
            "skill_check": "What skill check should I attempt?",
            "roleplay": "How should my character respond?",
            "default": "What action should I take?"
        }

        return instructions.get(decision_type, instructions["default"])

    def _build_input_context(self, situation: Dict, decision_data: Dict) -> str:
        """Build the input context from situation data"""
        parts = []

        # Game state
        game_state = situation.get('game_state', {})
        if game_state:
            if 'location' in game_state:
                parts.append(f"Location: {game_state['location']}")
            if 'turn' in game_state:
                parts.append(f"Turn: {game_state['turn']}")
            if game_state.get('combat_active'):
                parts.append("Combat is active")
            if game_state.get('time'):
                parts.append(f"Time: {game_state['time']}")

        # Character state
        char_state = situation.get('character_state', {})
        if char_state:
            hp = char_state.get('hp', 0)
            max_hp = char_state.get('max_hp', hp)
            parts.append(f"HP: {hp}/{max_hp}")

            if char_state.get('status_effects'):
                parts.append(f"Status: {', '.join(char_state['status_effects'])}")

        # Perception data
        perception = situation.get('perception_data', {})
        if perception:
            if 'nearby_enemies' in perception:
                enemies = [e.get('id', 'unknown') for e in perception['nearby_enemies']]
                parts.append(f"Nearby enemies: {', '.join(enemies)}")
            if 'nearby_allies' in perception:
                allies = perception['nearby_allies']
                parts.append(f"Nearby allies: {', '.join(allies)}")

        # Decision context
        if 'stakes' in decision_data:
            parts.append(f"Stakes: {decision_data['stakes']:.1%}")

        return "\n".join(parts) if parts else "No additional context"

    def _build_output_text(self, decision_data: Dict, outcome: Dict) -> str:
        """Build the output text from decision and outcome"""
        parts = []

        action = decision_data.get('action', 'unknown action')
        reasoning = decision_data.get('reasoning', '')
        confidence = decision_data.get('confidence', 0.0)

        parts.append(f"Action: {action}")

        if reasoning:
            parts.append(f"Reasoning: {reasoning}")

        parts.append(f"Confidence: {confidence:.0%}")

        # Add outcome information if available
        if outcome:
            success = outcome.get('success', False)
            immediate = outcome.get('immediate', '')

            if immediate:
                parts.append(f"Result: {immediate}")

            if success:
                parts.append("This action was successful.")
            else:
                parts.append("This action was not successful.")

        return "\n".join(parts)

    def export_for_consolidation(
        self,
        character_id: str,
        output_path: str
    ) -> Dict[str, Any]:
        """
        Export data for memory consolidation (Phase 7 enhanced)

        Converts episodic memories to semantic format for consolidation.

        Args:
            character_id: Character to export
            output_path: Output file path

        Returns:
            Export statistics
        """
        decisions = self.get_training_eligible_decisions(character_id)

        # Group by decision type for consolidation
        by_type = {}
        for d in decisions:
            decision_type = d.get('decision_data', {}).get('decision_type', 'unknown')
            if decision_type not in by_type:
                by_type[decision_type] = []
            by_type[decision_type].append(d)

        # Create consolidation records
        consolidation_data = {
            "character_id": character_id,
            "export_timestamp": datetime.utcnow().isoformat(),
            "episodic_count": len(decisions),
            "consolidation_groups": []
        }

        for decision_type, type_decisions in by_type.items():
            if len(type_decisions) >= 3:  # Only consolidate with 3+ examples
                group = {
                    "decision_type": decision_type,
                    "count": len(type_decisions),
                    "success_count": sum(1 for d in type_decisions if d.get('success')),
                    "patterns": self._extract_patterns(type_decisions)
                }
                consolidation_data["consolidation_groups"].append(group)

        with open(output_path, 'w') as f:
            json.dump(consolidation_data, f, indent=2)

        stats = {
            "character_id": character_id,
            "total_decisions": len(decisions),
            "consolidation_groups": len(consolidation_data["consolidation_groups"]),
            "output_path": str(output_path)
        }

        logger.info(f"Exported consolidation data with {stats['consolidation_groups']} groups")
        return stats

    def _extract_patterns(self, decisions: List[Dict]) -> List[str]:
        """Extract patterns from similar decisions for consolidation"""
        patterns = []

        # Successful actions
        successful = [d for d in decisions if d.get('success')]
        if successful:
            actions = [d.get('decision_data', {}).get('action', '') for d in successful]
            # Find common successful actions
            from collections import Counter
            common = Counter(actions).most_common(3)
            for action, count in common:
                if count >= 2:
                    patterns.append(f"Successful pattern: {action} ({count} times)")

        # Failed actions to avoid
        failed = [d for d in decisions if not d.get('success')]
        if failed:
            actions = [d.get('decision_data', {}).get('action', '') for d in failed]
            from collections import Counter
            common = Counter(actions).most_common(3)
            for action, count in common:
                if count >= 2:
                    patterns.append(f"Failed pattern to avoid: {action} ({count} times)")

        return patterns
    
    def get_session_summary(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Get summary of a gameplay session (Phase 7.1.3 enhanced)
        
        Args:
            session_id: Session ID
            
        Returns:
            Session summary
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get session info
        cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        session_row = cursor.fetchone()
        
        if not session_row:
            return {"error": "Session not found"}
        
        session_info = dict(session_row)
        session_info['character_ids'] = json.loads(session_info['character_ids'])
        
        # Get decision stats
        stats = self.get_statistics(session_id=session_id)
        
        # Add outcome tracker stats (Phase 7.1.2)
        if self.outcome_tracker:
            try:
                outcome_stats = self.outcome_tracker.get_statistics()
                stats["outcome_tracking"] = outcome_stats
            except Exception as e:
                logger.warning(f"Failed to get outcome tracker stats: {e}")
        
        # Add session manager data (Phase 7.1.3)
        if self.session_manager:
            try:
                manager_summary = self.session_manager.get_session_summary(session_id)
                if manager_summary and "error" not in manager_summary:
                    stats["session_manager"] = manager_summary
            except Exception as e:
                logger.warning(f"Failed to get session manager summary: {e}")
        
        conn.close()
        
        return {
            "session_info": session_info,
            "statistics": stats
        }
    
    def get_outcome_tracker_statistics(self) -> Optional[Dict[str, Any]]:
        """
        Get outcome tracker statistics (Phase 7.1.2)
        
        Returns:
            Outcome tracker statistics or None if unavailable
        """
        if not self.outcome_tracker:
            return None
        
        try:
            return self.outcome_tracker.get_statistics()
        except Exception as e:
            logger.warning(f"Failed to get outcome tracker statistics: {e}")
            return None
    
    def get_session_manager_statistics(self) -> Optional[Dict[str, Any]]:
        """
        Get session manager statistics (Phase 7.1.3)
        
        Returns:
            Session manager statistics or None if unavailable
        """
        if not self.session_manager:
            return None
        
        try:
            return self.session_manager.get_statistics()
        except Exception as e:
            logger.warning(f"Failed to get session manager statistics: {e}")
            return None
    
    def get_character_session_history(
        self,
        character_id: str,
        limit: Optional[int] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get session history for a character (Phase 7.1.3)
        
        Args:
            character_id: Character ID
            limit: Optional limit on results
            
        Returns:
            List of session summaries or None if unavailable
        """
        if not self.session_manager:
            return None
        
        try:
            return self.session_manager.get_character_session_history(
                character_id=character_id,
                limit=limit
            )
        except Exception as e:
            logger.warning(f"Failed to get character session history: {e}")
            return None


# Test and demo functionality
async def test_training_data_collector():
    """Test the training data collector"""
    print("Testing TrainingDataCollector...")
    
    # Create collector (in-memory for testing)
    collector = TrainingDataCollector(":memory:")
    
    # Start a session
    session_id = collector.start_session(session_notes="Test session")
    print(f"✓ Started session: {session_id}")
    
    # Test character settings
    settings = collector.get_character_settings("thorin")
    print(f"✓ Loaded settings for thorin: {settings.enabled}")
    
    # Log a decision
    situation_context = {
        "game_state": {
            "turn": 5,
            "combat_active": True,
            "location": "Cave entrance"
        },
        "character_state": {
            "hp": 35,
            "max_hp": 50,
            "position": {"x": 10, "y": 5}
        },
        "perception_data": {
            "nearby_enemies": [{"id": "goblin_1", "distance": 5}]
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
    
    decision_id = collector.log_decision(
        character_id="thorin",
        situation_context=situation_context,
        decision=decision
    )
    print(f"✓ Logged decision: {decision_id}")
    
    # Update outcome
    outcome = {
        "immediate": "Hit for 15 damage",
        "delayed": "Goblin defeated",
        "rewards": {"xp": 50}
    }
    collector.update_outcome(decision_id, outcome, success=True)
    print(f"✓ Updated outcome")
    
    # Update quality label
    collector.update_quality_label(decision_id, "good", "Excellent tactical choice")
    print(f"✓ Updated quality label")
    
    # Get statistics
    stats = collector.get_statistics(character_id="thorin")
    print(f"✓ Statistics: {stats['total_decisions']} decisions")
    
    # Get training data
    training_data = collector.get_training_eligible_decisions("thorin")
    print(f"✓ Training data: {len(training_data)} eligible decisions")
    
    # End session
    collector.end_session()
    print(f"✓ Ended session")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_training_data_collector())
