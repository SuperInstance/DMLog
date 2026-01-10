"""
Session Manager

Enhanced session tracking with character evolution metrics, reward aggregation,
and multi-character coordination.

Phase 7.1.3 - Session Management Enhancement
"""

import time
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SessionPhase(Enum):
    """Phases of a gameplay session"""
    SETUP = "setup"              # Pre-game setup
    ACTIVE = "active"            # Gameplay in progress
    INTERMISSION = "intermission"  # Break/reflection
    COMPLETE = "complete"        # Session ended
    ARCHIVED = "archived"        # Old session


@dataclass
class CharacterSessionStats:
    """Statistics for a character in a session"""
    character_id: str
    decisions_made: int = 0
    success_count: int = 0
    failure_count: int = 0
    
    # Reward aggregates
    total_reward: float = 0.0
    combat_reward: float = 0.0
    social_reward: float = 0.0
    exploration_reward: float = 0.0
    resource_reward: float = 0.0
    strategic_reward: float = 0.0
    
    # Decision sources
    bot_decisions: int = 0
    brain_decisions: int = 0
    human_decisions: int = 0
    
    # Performance metrics
    avg_decision_time_ms: float = 0.0
    avg_confidence: float = 0.0
    
    # Evolution indicators
    growth_score: float = 0.0  # How much character improved
    learning_opportunities: int = 0  # Number of teaching moments
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "character_id": self.character_id,
            "decisions_made": self.decisions_made,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_count / max(1, self.decisions_made),
            "total_reward": self.total_reward,
            "rewards_by_domain": {
                "combat": self.combat_reward,
                "social": self.social_reward,
                "exploration": self.exploration_reward,
                "resource": self.resource_reward,
                "strategic": self.strategic_reward
            },
            "decisions_by_source": {
                "bot": self.bot_decisions,
                "brain": self.brain_decisions,
                "human": self.human_decisions
            },
            "avg_decision_time_ms": self.avg_decision_time_ms,
            "avg_confidence": self.avg_confidence,
            "growth_score": self.growth_score,
            "learning_opportunities": self.learning_opportunities
        }


@dataclass
class SessionMetrics:
    """Aggregated metrics for entire session"""
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    phase: SessionPhase = SessionPhase.SETUP
    
    # Participation
    character_ids: List[str] = field(default_factory=list)
    active_characters: int = 0
    
    # Decision metrics
    total_decisions: int = 0
    total_successes: int = 0
    total_failures: int = 0
    
    # Reward metrics
    total_session_reward: float = 0.0
    avg_reward_per_decision: float = 0.0
    
    # Quality metrics
    avg_decision_quality: float = 0.0
    teaching_moments: int = 0
    
    # Performance
    session_duration_seconds: float = 0.0
    avg_decision_latency_ms: float = 0.0
    
    # Character evolution
    characters_improved: List[str] = field(default_factory=list)
    avg_growth_score: float = 0.0
    
    # Session notes
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "session_id": self.session_id,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "phase": self.phase.value,
            "character_ids": self.character_ids,
            "active_characters": self.active_characters,
            "total_decisions": self.total_decisions,
            "success_rate": self.total_successes / max(1, self.total_decisions),
            "total_session_reward": self.total_session_reward,
            "avg_reward_per_decision": self.avg_reward_per_decision,
            "avg_decision_quality": self.avg_decision_quality,
            "teaching_moments": self.teaching_moments,
            "session_duration_seconds": self.session_duration_seconds,
            "avg_decision_latency_ms": self.avg_decision_latency_ms,
            "characters_improved": self.characters_improved,
            "avg_growth_score": self.avg_growth_score,
            "notes": self.notes,
            "tags": self.tags
        }


class SessionManager:
    """
    Manages gameplay sessions with enhanced tracking.
    
    Features:
    - Character evolution metrics per session
    - Reward aggregation across domains
    - Session quality scoring
    - Multi-character coordination
    - Performance analytics
    - Training opportunity identification
    """
    
    def __init__(self):
        """Initialize session manager"""
        # Active sessions
        self.active_sessions: Dict[str, SessionMetrics] = {}
        
        # Character stats per session
        self.character_stats: Dict[str, Dict[str, CharacterSessionStats]] = {}  # session_id -> char_id -> stats
        
        # Completed sessions history
        self.completed_sessions: List[SessionMetrics] = []
        
        # Performance metrics
        self.metrics = {
            "total_sessions": 0,
            "total_session_time": 0.0,
            "avg_session_duration": 0.0,
            "avg_decisions_per_session": 0.0,
            "avg_session_reward": 0.0,
            "sessions_with_learning": 0
        }
        
        logger.info("SessionManager initialized")
    
    def start_session(
        self,
        session_id: Optional[str] = None,
        character_ids: Optional[List[str]] = None,
        notes: str = "",
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Start a new gameplay session
        
        Args:
            session_id: Optional custom session ID
            character_ids: Characters participating
            notes: Session notes
            tags: Session tags
            
        Returns:
            Session ID
        """
        if session_id is None:
            session_id = f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Create session metrics
        session = SessionMetrics(
            session_id=session_id,
            start_time=time.time(),
            phase=SessionPhase.ACTIVE,
            character_ids=character_ids or [],
            active_characters=len(character_ids or []),
            notes=notes,
            tags=tags or []
        )
        
        self.active_sessions[session_id] = session
        
        # Initialize character stats
        self.character_stats[session_id] = {}
        for char_id in (character_ids or []):
            self.character_stats[session_id][char_id] = CharacterSessionStats(
                character_id=char_id
            )
        
        logger.info(f"Started session: {session_id} with {len(character_ids or [])} characters")
        
        return session_id
    
    def add_character_to_session(
        self,
        session_id: str,
        character_id: str
    ) -> None:
        """
        Add a character to an active session
        
        Args:
            session_id: Session ID
            character_id: Character to add
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Session not found: {session_id}")
            return
        
        session = self.active_sessions[session_id]
        
        if character_id not in session.character_ids:
            session.character_ids.append(character_id)
            session.active_characters += 1
            
            # Initialize stats
            if session_id not in self.character_stats:
                self.character_stats[session_id] = {}
            self.character_stats[session_id][character_id] = CharacterSessionStats(
                character_id=character_id
            )
            
            logger.info(f"Added {character_id} to session {session_id}")
    
    def record_decision(
        self,
        session_id: str,
        character_id: str,
        decision_data: Dict[str, Any],
        outcome_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a decision in the session
        
        Args:
            session_id: Session ID
            character_id: Character making decision
            decision_data: Decision details
            outcome_data: Optional outcome (if immediate)
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Session not found: {session_id}")
            return
        
        session = self.active_sessions[session_id]
        
        # Get or create character stats
        if session_id not in self.character_stats:
            self.character_stats[session_id] = {}
        if character_id not in self.character_stats[session_id]:
            self.character_stats[session_id][character_id] = CharacterSessionStats(
                character_id=character_id
            )
            if character_id not in session.character_ids:
                session.character_ids.append(character_id)
                session.active_characters += 1
        
        char_stats = self.character_stats[session_id][character_id]
        
        # Update decision counts
        char_stats.decisions_made += 1
        session.total_decisions += 1
        
        # Track decision source
        source = decision_data.get('source', 'bot')
        if source == 'bot':
            char_stats.bot_decisions += 1
        elif source == 'brain':
            char_stats.brain_decisions += 1
        elif source == 'human':
            char_stats.human_decisions += 1
        
        # Track decision time
        decision_time = decision_data.get('time_taken_ms', 0)
        if char_stats.decisions_made == 1:
            char_stats.avg_decision_time_ms = decision_time
        else:
            char_stats.avg_decision_time_ms = (
                (char_stats.avg_decision_time_ms * (char_stats.decisions_made - 1) + decision_time) 
                / char_stats.decisions_made
            )
        
        # Track confidence
        confidence = decision_data.get('confidence', 0.5)
        if char_stats.decisions_made == 1:
            char_stats.avg_confidence = confidence
        else:
            char_stats.avg_confidence = (
                (char_stats.avg_confidence * (char_stats.decisions_made - 1) + confidence)
                / char_stats.decisions_made
            )
        
        # Update session latency
        session.avg_decision_latency_ms = (
            (session.avg_decision_latency_ms * (session.total_decisions - 1) + decision_time)
            / session.total_decisions
        )
        
        # Process outcome if available
        if outcome_data:
            self._process_outcome(session_id, character_id, outcome_data)
    
    def _process_outcome(
        self,
        session_id: str,
        character_id: str,
        outcome_data: Dict[str, Any]
    ) -> None:
        """Process outcome data for session tracking"""
        session = self.active_sessions.get(session_id)
        if not session:
            return
        
        char_stats = self.character_stats[session_id].get(character_id)
        if not char_stats:
            return
        
        # Track success/failure
        success = outcome_data.get('success', False)
        if success:
            char_stats.success_count += 1
            session.total_successes += 1
        else:
            char_stats.failure_count += 1
            session.total_failures += 1
        
        # Aggregate rewards
        reward_signals = outcome_data.get('reward_signals', [])
        for signal in reward_signals:
            domain = signal.get('domain', '')
            value = signal.get('value', 0.0)
            confidence = signal.get('confidence', 1.0)
            weighted_value = value * confidence
            
            if domain == 'combat':
                char_stats.combat_reward += weighted_value
            elif domain == 'social':
                char_stats.social_reward += weighted_value
            elif domain == 'exploration':
                char_stats.exploration_reward += weighted_value
            elif domain == 'resource':
                char_stats.resource_reward += weighted_value
            elif domain == 'strategic':
                char_stats.strategic_reward += weighted_value
            
            char_stats.total_reward += weighted_value
        
        # Update session totals
        aggregate_reward = outcome_data.get('aggregate_reward', 0.0)
        session.total_session_reward += aggregate_reward
        session.avg_reward_per_decision = (
            session.total_session_reward / session.total_decisions
        )
        
        # Track quality
        quality_analysis = outcome_data.get('quality_analysis', {})
        quality_score = quality_analysis.get('quality_score', 0.0)
        
        if session.total_decisions == 1:
            session.avg_decision_quality = quality_score
        else:
            session.avg_decision_quality = (
                (session.avg_decision_quality * (session.total_decisions - 1) + quality_score)
                / session.total_decisions
            )
        
        # Track teaching moments (low quality or failure with learning potential)
        if quality_score < 0 or (not success and quality_score < 0.3):
            char_stats.learning_opportunities += 1
            session.teaching_moments += 1
    
    def set_session_phase(
        self,
        session_id: str,
        phase: SessionPhase
    ) -> None:
        """
        Set the current phase of a session
        
        Args:
            session_id: Session ID
            phase: New phase
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Session not found: {session_id}")
            return
        
        session = self.active_sessions[session_id]
        old_phase = session.phase
        session.phase = phase
        
        logger.info(f"Session {session_id} phase: {old_phase.value} → {phase.value}")
    
    def end_session(
        self,
        session_id: str
    ) -> SessionMetrics:
        """
        End a session and calculate final metrics
        
        Args:
            session_id: Session ID
            
        Returns:
            Final session metrics
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Session not found: {session_id}")
            return None
        
        session = self.active_sessions[session_id]
        session.end_time = time.time()
        session.phase = SessionPhase.COMPLETE
        session.session_duration_seconds = session.end_time - session.start_time
        
        # Calculate character growth scores
        self._calculate_character_growth(session_id)
        
        # Identify characters that improved
        session.characters_improved = [
            char_id for char_id, stats in self.character_stats[session_id].items()
            if stats.growth_score > 0.5
        ]
        
        # Calculate average growth
        if self.character_stats[session_id]:
            growth_scores = [
                stats.growth_score 
                for stats in self.character_stats[session_id].values()
            ]
            session.avg_growth_score = sum(growth_scores) / len(growth_scores)
        
        # Move to completed
        self.completed_sessions.append(session)
        del self.active_sessions[session_id]
        
        # Update metrics
        self.metrics["total_sessions"] += 1
        self.metrics["total_session_time"] += session.session_duration_seconds
        self.metrics["avg_session_duration"] = (
            self.metrics["total_session_time"] / self.metrics["total_sessions"]
        )
        self.metrics["avg_decisions_per_session"] = (
            (self.metrics["avg_decisions_per_session"] * (self.metrics["total_sessions"] - 1) 
             + session.total_decisions)
            / self.metrics["total_sessions"]
        )
        self.metrics["avg_session_reward"] = (
            (self.metrics["avg_session_reward"] * (self.metrics["total_sessions"] - 1)
             + session.total_session_reward)
            / self.metrics["total_sessions"]
        )
        if session.teaching_moments > 0:
            self.metrics["sessions_with_learning"] += 1
        
        logger.info(
            f"Ended session {session_id}: "
            f"{session.total_decisions} decisions, "
            f"{session.session_duration_seconds:.0f}s, "
            f"{len(session.characters_improved)} characters improved"
        )
        
        return session
    
    def _calculate_character_growth(self, session_id: str) -> None:
        """Calculate growth score for each character in session"""
        if session_id not in self.character_stats:
            return
        
        for char_id, stats in self.character_stats[session_id].items():
            # Growth based on:
            # 1. Success rate improvement (compared to baseline)
            # 2. Positive reward accumulation
            # 3. Learning opportunities addressed
            
            success_rate = stats.success_count / max(1, stats.decisions_made)
            
            # Baseline is 0.5 (50% success)
            success_factor = (success_rate - 0.5) * 2  # -1 to 1
            
            # Reward factor (normalized)
            reward_factor = min(1.0, stats.total_reward / max(1, stats.decisions_made))
            
            # Learning factor (having opportunities is good for growth)
            learning_factor = min(1.0, stats.learning_opportunities / max(1, stats.decisions_made * 0.3))
            
            # Weighted combination
            growth_score = (
                success_factor * 0.4 +
                reward_factor * 0.4 +
                learning_factor * 0.2
            )
            
            # Clamp to [0, 1]
            stats.growth_score = max(0.0, min(1.0, (growth_score + 1) / 2))
    
    def get_session_summary(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Get comprehensive summary of a session
        
        Args:
            session_id: Session ID
            
        Returns:
            Session summary dictionary
        """
        # Check active sessions first
        session = self.active_sessions.get(session_id)
        
        # Check completed sessions
        if not session:
            session = next(
                (s for s in self.completed_sessions if s.session_id == session_id),
                None
            )
        
        if not session:
            return {"error": "Session not found"}
        
        # Get character stats
        character_summaries = {}
        if session_id in self.character_stats:
            character_summaries = {
                char_id: stats.to_dict()
                for char_id, stats in self.character_stats[session_id].items()
            }
        
        return {
            "session": session.to_dict(),
            "characters": character_summaries,
            "is_active": session_id in self.active_sessions
        }
    
    def get_character_session_history(
        self,
        character_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get session history for a character
        
        Args:
            character_id: Character ID
            limit: Optional limit on results
            
        Returns:
            List of session summaries
        """
        history = []
        
        for session in self.completed_sessions:
            if character_id in session.character_ids:
                # Get character stats for this session
                char_stats = None
                if session.session_id in self.character_stats:
                    char_stats = self.character_stats[session.session_id].get(character_id)
                
                history.append({
                    "session_id": session.session_id,
                    "start_time": datetime.fromtimestamp(session.start_time).isoformat(),
                    "duration_seconds": session.session_duration_seconds,
                    "decisions_made": char_stats.decisions_made if char_stats else 0,
                    "success_rate": char_stats.success_count / max(1, char_stats.decisions_made) if char_stats else 0,
                    "total_reward": char_stats.total_reward if char_stats else 0,
                    "growth_score": char_stats.growth_score if char_stats else 0
                })
        
        # Sort by start time (newest first)
        history.sort(key=lambda x: x['start_time'], reverse=True)
        
        if limit:
            history = history[:limit]
        
        return history
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get session manager statistics"""
        stats = dict(self.metrics)
        
        # Active sessions
        stats["active_sessions"] = len(self.active_sessions)
        stats["completed_sessions"] = len(self.completed_sessions)
        
        # Learning stats
        if self.metrics["total_sessions"] > 0:
            stats["sessions_with_learning_pct"] = (
                self.metrics["sessions_with_learning"] / self.metrics["total_sessions"]
            )
        
        return stats
    
    def identify_training_opportunities(
        self,
        min_quality: float = 0.5,
        min_decisions: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Identify sessions with good training opportunities
        
        Args:
            min_quality: Minimum average quality
            min_decisions: Minimum decisions required
            
        Returns:
            List of session summaries with training potential
        """
        opportunities = []
        
        for session in self.completed_sessions:
            if (session.avg_decision_quality >= min_quality and
                session.total_decisions >= min_decisions and
                session.teaching_moments > 0):
                
                opportunities.append({
                    "session_id": session.session_id,
                    "avg_quality": session.avg_decision_quality,
                    "total_decisions": session.total_decisions,
                    "teaching_moments": session.teaching_moments,
                    "characters_improved": session.characters_improved,
                    "avg_growth": session.avg_growth_score,
                    "total_reward": session.total_session_reward
                })
        
        # Sort by quality and teaching moments
        opportunities.sort(
            key=lambda x: (x['avg_quality'], x['teaching_moments']),
            reverse=True
        )
        
        return opportunities


# Test functionality
async def test_session_manager():
    """Test the session manager"""
    print("Testing SessionManager...")
    
    manager = SessionManager()
    
    # Start session
    session_id = manager.start_session(
        character_ids=["thorin", "elara"],
        notes="Test session",
        tags=["test", "combat"]
    )
    print(f"✓ Started session: {session_id}")
    
    # Record some decisions
    for i in range(5):
        char = "thorin" if i % 2 == 0 else "elara"
        
        decision_data = {
            "source": "bot" if i < 3 else "brain",
            "confidence": 0.7 + (i * 0.05),
            "time_taken_ms": 50.0
        }
        
        outcome_data = {
            "success": i % 3 != 0,
            "reward_signals": [
                {"domain": "combat", "value": 0.5, "confidence": 0.8}
            ],
            "aggregate_reward": 0.5,
            "quality_analysis": {"quality_score": 0.6 if i % 3 != 0 else 0.2}
        }
        
        manager.record_decision(session_id, char, decision_data, outcome_data)
    
    print(f"✓ Recorded 5 decisions")
    
    # Get summary
    summary = manager.get_session_summary(session_id)
    print(f"✓ Session summary:")
    print(f"    Total decisions: {summary['session']['total_decisions']}")
    print(f"    Success rate: {summary['session']['success_rate']:.1%}")
    print(f"    Avg reward: {summary['session']['avg_reward_per_decision']:.3f}")
    
    # End session
    final_session = manager.end_session(session_id)
    print(f"✓ Ended session:")
    print(f"    Duration: {final_session.session_duration_seconds:.1f}s")
    print(f"    Characters improved: {len(final_session.characters_improved)}")
    print(f"    Avg growth: {final_session.avg_growth_score:.3f}")
    
    # Get statistics
    stats = manager.get_statistics()
    print(f"✓ Statistics:")
    print(f"    Total sessions: {stats['total_sessions']}")
    print(f"    Completed: {stats['completed_sessions']}")
    
    print("\n✅ All session manager tests passed!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_session_manager())
