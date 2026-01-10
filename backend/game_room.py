"""
AI Society D&D - Game Room & Dungeon Master System
===================================================
Implements:
- D&D game sessions (rooms where characters play)
- Dungeon Master system with master vector DB
- Game state management
- Session transcripts and world lore
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import json
import asyncio


# ============================================================================
# GAME SESSION STATE
# ============================================================================

class SessionPhase(Enum):
    """Phases of a game session"""
    SETUP = "setup"                    # Characters joining, setting up
    INTRODUCTION = "introduction"      # DM introduces the scene
    EXPLORATION = "exploration"        # Free-form roleplay and exploration
    COMBAT = "combat"                  # Combat encounter
    SOCIAL = "social"                  # Social interaction, dialogue
    REST = "rest"                      # Short or long rest
    CONCLUSION = "conclusion"          # Wrapping up the session
    ENDED = "ended"                    # Session complete


@dataclass
class GameState:
    """Current state of the game world"""
    session_id: str
    campaign_name: str
    session_number: int
    
    # Location and environment
    current_location: str = "Unknown"
    location_description: str = ""
    time_of_day: str = "midday"
    weather: str = "clear"
    
    # Active elements
    active_npcs: List[str] = field(default_factory=list)
    active_threats: List[str] = field(default_factory=list)
    environmental_features: List[str] = field(default_factory=list)
    
    # Quest tracking
    active_quests: List[Dict[str, Any]] = field(default_factory=list)
    completed_quests: List[Dict[str, Any]] = field(default_factory=list)
    
    # Session state
    phase: SessionPhase = SessionPhase.SETUP
    round_number: int = 0
    
    # Metadata
    started_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


# ============================================================================
# GAME ROOM (D&D SESSION)
# ============================================================================

class DnDGameRoom:
    """
    A game room where a D&D session happens.
    Manages:
    - Characters in the session
    - Game state and progression
    - Transcript recording
    - Combat encounters
    """
    
    def __init__(
        self,
        room_id: str,
        campaign_name: str,
        session_number: int,
        dm_id: str
    ):
        self.room_id = room_id
        self.campaign_name = campaign_name
        self.session_number = session_number
        self.dm_id = dm_id
        
        # Game state
        self.game_state = GameState(
            session_id=room_id,
            campaign_name=campaign_name,
            session_number=session_number
        )
        
        # Characters in this session
        self.characters: Dict[str, Any] = {}  # character_id -> EnhancedCharacter
        
        # Transcript (all events in chronological order)
        self.transcript: List[Dict[str, Any]] = []
        
        # Combat tracker
        self.active_combat: Optional[Any] = None  # CombatEncounter if in combat
        
        # NPCs controlled by DM
        self.npcs: Dict[str, Dict] = {}
        
    def add_character(self, character):
        """Add a character to the game session"""
        self.characters[character.character_id] = character
        
        # Update character's location
        character.current_location = self.game_state.current_location
        
        # Log to transcript
        self._add_to_transcript(
            event_type="character_joined",
            actor=character.name,
            description=f"{character.name} has joined the session."
        )
    
    def add_npc(self, npc_id: str, npc_data: Dict):
        """Add an NPC to the session"""
        self.npcs[npc_id] = npc_data
        self.game_state.active_npcs.append(npc_id)
        
        self._add_to_transcript(
            event_type="npc_introduced",
            actor="DM",
            description=f"NPC {npc_data['name']} has been introduced."
        )
    
    def _add_to_transcript(
        self,
        event_type: str,
        actor: str,
        description: str,
        metadata: Dict = None
    ):
        """Add event to transcript"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "actor": actor,
            "description": description,
            "phase": self.game_state.phase.value,
            "round": self.game_state.round_number,
            "location": self.game_state.current_location,
            "metadata": metadata or {}
        }
        self.transcript.append(event)
        self.game_state.last_updated = datetime.now()
    
    async def dm_narrate(self, narration: str):
        """DM narrates something"""
        self._add_to_transcript(
            event_type="dm_narration",
            actor="DM",
            description=narration
        )
        
        return {
            "type": "narration",
            "text": narration,
            "timestamp": datetime.now().isoformat()
        }
    
    async def character_action(
        self,
        character_id: str,
        action_description: str,
        action_type: str = "roleplay"
    ):
        """Character performs an action"""
        if character_id not in self.characters:
            return {"error": "Character not in session"}
        
        character = self.characters[character_id]
        
        self._add_to_transcript(
            event_type="character_action",
            actor=character.name,
            description=action_description,
            metadata={"action_type": action_type}
        )
        
        # Store as memory for character
        character.store_game_memory(
            event_description=f"I {action_description}",
            importance=5.0
        )
        
        return {
            "type": "action",
            "character": character.name,
            "action": action_description,
            "timestamp": datetime.now().isoformat()
        }
    
    async def start_combat(self, enemies: List[Dict]):
        """Begin a combat encounter"""
        from game_mechanics import CombatEncounter
        
        # Create combat encounter
        combat_id = f"{self.room_id}_combat_{len(self.transcript)}"
        self.active_combat = CombatEncounter(
            encounter_id=combat_id,
            description=f"Combat in {self.game_state.current_location}"
        )
        
        # Add player characters
        for char_id, char in self.characters.items():
            self.active_combat.add_participant(char_id, char.name, is_npc=False)
            # Roll initiative
            init = self.active_combat.roll_initiative(
                char_id,
                char.stats.get_modifier('dexterity')
            )
            self._add_to_transcript(
                event_type="initiative_roll",
                actor=char.name,
                description=f"{char.name} rolled {init} for initiative"
            )
        
        # Add enemies
        for i, enemy in enumerate(enemies):
            enemy_id = f"enemy_{i}"
            enemy_name = enemy.get('name', f'Enemy {i+1}')
            self.active_combat.add_participant(enemy_id, enemy_name, is_npc=True)
            init = self.active_combat.roll_initiative(enemy_id, enemy.get('dex_mod', 0))
            self._add_to_transcript(
                event_type="initiative_roll",
                actor=enemy_name,
                description=f"{enemy_name} rolled {init} for initiative"
            )
        
        # Start combat
        result = self.active_combat.start_combat()
        self.game_state.phase = SessionPhase.COMBAT
        
        self._add_to_transcript(
            event_type="combat_started",
            actor="DM",
            description="Combat has begun!",
            metadata=result
        )
        
        return result
    
    async def combat_action(
        self,
        attacker_id: str,
        action_type: str,
        target_id: str = None,
        **kwargs
    ):
        """Perform combat action"""
        if not self.active_combat:
            return {"error": "No active combat"}
        
        if action_type == "attack":
            result = self.active_combat.perform_attack(
                attacker_id=attacker_id,
                target_id=target_id,
                weapon=kwargs.get('weapon', 'weapon'),
                attack_bonus=kwargs.get('attack_bonus', 0),
                damage_dice=kwargs.get('damage_dice', '1d8'),
                damage_bonus=kwargs.get('damage_bonus', 0)
            )
            
            self._add_to_transcript(
                event_type="combat_action",
                actor=self.active_combat.participants[attacker_id].name,
                description=result['message'],
                metadata=result
            )
            
            return result
        
        return {"error": "Unknown action type"}
    
    async def end_combat(self):
        """End the current combat"""
        if not self.active_combat:
            return {"error": "No active combat"}
        
        result = self.active_combat.end_combat()
        
        self._add_to_transcript(
            event_type="combat_ended",
            actor="DM",
            description=result['message'],
            metadata=result
        )
        
        # Store combat memories for all characters
        for char_id, char in self.characters.items():
            combat_summary = f"Completed combat encounter in {self.game_state.current_location}. "
            combat_summary += f"Lasted {result['rounds']} rounds."
            
            char.store_game_memory(
                event_description=combat_summary,
                importance=7.0,
                emotional_valence=0.5 if result.get('winner') == 'players' else -0.5
            )
        
        self.active_combat = None
        self.game_state.phase = SessionPhase.EXPLORATION
        
        return result
    
    def get_transcript(self) -> List[Dict]:
        """Get full session transcript"""
        return self.transcript
    
    def get_recent_events(self, n: int = 10) -> List[Dict]:
        """Get recent events from transcript"""
        return self.transcript[-n:]
    
    async def end_session(self):
        """End the game session"""
        self.game_state.phase = SessionPhase.ENDED
        
        # Consolidate memories for all characters
        consolidation_results = {}
        for char_id, char in self.characters.items():
            count = await char.consolidate_memories()
            consolidation_results[char.name] = count
        
        self._add_to_transcript(
            event_type="session_ended",
            actor="DM",
            description="Session has ended.",
            metadata={
                "duration_minutes": (datetime.now() - self.game_state.started_at).seconds // 60,
                "total_events": len(self.transcript),
                "memories_consolidated": consolidation_results
            }
        )
        
        return {
            "session_id": self.room_id,
            "duration_minutes": (datetime.now() - self.game_state.started_at).seconds // 60,
            "total_events": len(self.transcript),
            "memories_consolidated": consolidation_results
        }


# ============================================================================
# DUNGEON MASTER SYSTEM
# ============================================================================

class DungeonMaster:
    """
    The Dungeon Master system.
    
    Has access to:
    - Master vector database (world lore, campaign history)
    - All game transcripts
    - Character oversight (can see private calls if enabled)
    - NPC control
    - World state management
    """
    
    def __init__(
        self,
        dm_id: str,
        campaign_name: str,
        vector_db_url: str = "http://localhost:6333"
    ):
        self.dm_id = dm_id
        self.campaign_name = campaign_name
        
        # Master vector database (world lore + campaign history)
        from vector_memory import QdrantMemoryStore, MemoryVector
        self.master_db = QdrantMemoryStore(
            character_id=f"dm_{campaign_name}",
            qdrant_url=vector_db_url,
            collection_name_prefix="dm_master_db_"
        )
        
        # Campaign state
        self.world_lore: Dict[str, Any] = {}
        self.campaign_timeline: List[Dict] = []
        self.npc_profiles: Dict[str, Dict] = {}
        
        # Active sessions
        self.active_sessions: Dict[str, DnDGameRoom] = {}
        
        # Session history
        self.completed_sessions: List[Dict] = []
    
    def add_world_lore(self, lore_entry: str, category: str = "general"):
        """Add canonical world lore to master DB"""
        from vector_memory import MemoryVector
        
        lore_id = f"lore_{len(self.world_lore)}"
        
        # Store in memory
        if category not in self.world_lore:
            self.world_lore[category] = []
        self.world_lore[category].append({
            "id": lore_id,
            "content": lore_entry,
            "added_at": datetime.now().isoformat()
        })
        
        # Store in vector DB for retrieval
        memory_vec = MemoryVector(
            id=lore_id,
            content=lore_entry,
            character_id=self.dm_id,
            timestamp=datetime.now().isoformat(),
            memory_type="semantic",
            importance=8.0,
            consolidated=True
        )
        self.master_db.store_memory(memory_vec)
    
    def query_world_lore(self, query: str, top_k: int = 5) -> List[str]:
        """Query the master DB for relevant world lore"""
        results = self.master_db.retrieve_memories(
            query=query,
            top_k=top_k,
            α_recency=0.5,
            α_importance=2.0,
            α_relevance=2.0
        )
        
        return [r.content for r in results]
    
    def add_npc(self, npc_id: str, npc_data: Dict):
        """Add an NPC profile"""
        npc_data['created_at'] = datetime.now().isoformat()
        self.npc_profiles[npc_id] = npc_data
        
        # Store in master DB
        from vector_memory import MemoryVector
        npc_description = f"NPC {npc_data['name']}: {npc_data.get('description', '')}"
        
        memory_vec = MemoryVector(
            id=f"npc_{npc_id}",
            content=npc_description,
            character_id=self.dm_id,
            timestamp=datetime.now().isoformat(),
            memory_type="semantic",
            importance=6.0
        )
        self.master_db.store_memory(memory_vec)
    
    def create_session(self, session_number: int) -> DnDGameRoom:
        """Create a new game session"""
        session_id = f"{self.campaign_name}_session_{session_number}"
        
        room = DnDGameRoom(
            room_id=session_id,
            campaign_name=self.campaign_name,
            session_number=session_number,
            dm_id=self.dm_id
        )
        
        self.active_sessions[session_id] = room
        
        return room
    
    async def end_session(self, session_id: str):
        """End a session and archive it"""
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        room = self.active_sessions[session_id]
        result = await room.end_session()
        
        # Archive transcript to master DB
        transcript_summary = self._summarize_transcript(room.transcript)
        
        from vector_memory import MemoryVector
        memory_vec = MemoryVector(
            id=f"session_{session_id}",
            content=transcript_summary,
            character_id=self.dm_id,
            timestamp=datetime.now().isoformat(),
            memory_type="episodic",
            importance=9.0,
            is_temporal_landmark=True,
            landmark_type="session"
        )
        self.master_db.store_memory(memory_vec)
        
        # Move to completed
        self.completed_sessions.append({
            "session_id": session_id,
            "session_number": room.session_number,
            "completed_at": datetime.now().isoformat(),
            "transcript_length": len(room.transcript),
            "result": result
        })
        
        del self.active_sessions[session_id]
        
        return result
    
    def _summarize_transcript(self, transcript: List[Dict]) -> str:
        """Create a summary of the session transcript"""
        # Simple summary - would use LLM for better summarization
        events_by_type = {}
        for event in transcript:
            event_type = event['event_type']
            if event_type not in events_by_type:
                events_by_type[event_type] = []
            events_by_type[event_type].append(event)
        
        summary_parts = [
            f"Session completed with {len(transcript)} total events.",
        ]
        
        # Key events
        if 'combat_started' in events_by_type:
            summary_parts.append(f"Engaged in {len(events_by_type['combat_started'])} combat encounters.")
        
        if 'character_action' in events_by_type:
            summary_parts.append(f"Characters took {len(events_by_type['character_action'])} actions.")
        
        return " ".join(summary_parts)
    
    def query_campaign_history(self, query: str) -> Dict[str, Any]:
        """
        Query the master DB for campaign history.
        Useful for maintaining consistency and recalling past events.
        """
        results = self.master_db.retrieve_memories(
            query=query,
            top_k=10,
            α_recency=1.0,
            α_importance=1.5,
            α_relevance=2.0
        )
        
        relevant_events = []
        relevant_lore = []
        
        for result in results:
            if result.memory_type == "episodic":
                relevant_events.append(result.content)
            elif result.memory_type == "semantic":
                relevant_lore.append(result.content)
        
        return {
            "query": query,
            "relevant_events": relevant_events,
            "relevant_lore": relevant_lore,
            "total_results": len(results)
        }
    
    def get_campaign_stats(self) -> Dict[str, Any]:
        """Get overall campaign statistics"""
        return {
            "campaign_name": self.campaign_name,
            "total_sessions": len(self.completed_sessions),
            "active_sessions": len(self.active_sessions),
            "world_lore_entries": sum(len(entries) for entries in self.world_lore.values()),
            "npc_count": len(self.npc_profiles),
            "timeline_events": len(self.campaign_timeline)
        }


# ============================================================================
# SESSION MANAGER
# ============================================================================

class SessionManager:
    """Manages multiple campaigns and sessions"""
    
    def __init__(self):
        self.campaigns: Dict[str, DungeonMaster] = {}
        self.characters: Dict[str, Any] = {}  # All characters across campaigns
    
    def create_campaign(
        self,
        campaign_name: str,
        dm_id: str,
        vector_db_url: str = "http://localhost:6333"
    ) -> DungeonMaster:
        """Create a new campaign"""
        dm = DungeonMaster(
            dm_id=dm_id,
            campaign_name=campaign_name,
            vector_db_url=vector_db_url
        )
        
        self.campaigns[campaign_name] = dm
        return dm
    
    def get_campaign(self, campaign_name: str) -> Optional[DungeonMaster]:
        """Get a campaign"""
        return self.campaigns.get(campaign_name)
    
    def register_character(self, character):
        """Register a character that can join sessions"""
        self.characters[character.character_id] = character
    
    def get_character(self, character_id: str):
        """Get a character"""
        return self.characters.get(character_id)
