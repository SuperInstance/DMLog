"""
NPC Manager (Phase 6)

Enhanced NPC management system for tracking and automating non-player characters.
Integrates with DM automation and chat systems.

Key Features:
- NPC personality and behavior tracking
- Automated dialogue generation
- Relationship tracking with PCs
- NPC goals and motivations
- Faction affiliations
- Memory of past interactions
"""

import time
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NPCType(Enum):
    """Types of NPCs"""
    ALLY = "ally"               # Friendly, helpful
    NEUTRAL = "neutral"         # Indifferent
    ENEMY = "enemy"             # Hostile
    MERCHANT = "merchant"       # Trader
    QUEST_GIVER = "quest_giver" # Provides quests
    INFORMANT = "informant"     # Provides information
    BOSS = "boss"               # Major antagonist
    MINION = "minion"           # Minor enemy


class NPCMood(Enum):
    """Current mood/attitude"""
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    SUSPICIOUS = "suspicious"
    HOSTILE = "hostile"
    FEARFUL = "fearful"
    ANGRY = "angry"
    HELPFUL = "helpful"
    INDIFFERENT = "indifferent"


@dataclass
class NPCPersonality:
    """NPC personality traits"""
    # Big Five traits (0-1)
    openness: float = 0.5           # Creative vs practical
    conscientiousness: float = 0.5  # Organized vs spontaneous
    extraversion: float = 0.5       # Outgoing vs reserved
    agreeableness: float = 0.5      # Cooperative vs competitive
    neuroticism: float = 0.5        # Anxious vs confident
    
    # Speech patterns
    verbosity: float = 0.5          # Talkative vs brief
    formality: float = 0.5          # Formal vs casual
    honesty: float = 0.5            # Truthful vs deceptive
    
    # Motivations
    primary_motivation: str = "survival"
    secondary_motivations: List[str] = field(default_factory=list)


@dataclass
class NPCRelationship:
    """Relationship with a specific character"""
    character_id: str
    trust_level: float = 0.5
    affection: float = 0.5
    respect: float = 0.5
    
    interactions: int = 0
    last_interaction: Optional[float] = None
    memorable_events: List[str] = field(default_factory=list)


@dataclass
class NPC:
    """Non-player character"""
    npc_id: str
    name: str
    npc_type: NPCType
    
    race: str = "human"
    profession: str = "commoner"
    faction: Optional[str] = None
    
    personality: NPCPersonality = field(default_factory=NPCPersonality)
    current_mood: NPCMood = NPCMood.NEUTRAL
    
    level: int = 1
    hp: int = 10
    max_hp: int = 10
    
    is_alive: bool = True
    location: str = "unknown"
    
    short_term_goals: List[str] = field(default_factory=list)
    long_term_goals: List[str] = field(default_factory=list)
    
    knows_about: Set[str] = field(default_factory=set)
    secrets: Set[str] = field(default_factory=set)
    
    relationships: Dict[str, NPCRelationship] = field(default_factory=dict)
    
    common_phrases: List[str] = field(default_factory=list)
    
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


class NPCManager:
    """NPC Manager - Tracks all NPCs and their behaviors"""
    
    def __init__(self):
        self.npcs: Dict[str, NPC] = {}
        self.faction_relationships: Dict[Tuple[str, str], float] = {}
        self.stats = {"total_npcs": 0, "interactions": 0, "dialogue_generated": 0}
        logger.info("NPCManager initialized")
    
    def create_npc(self, npc_id: str, name: str, npc_type: NPCType, **kwargs) -> NPC:
        npc = NPC(npc_id=npc_id, name=name, npc_type=npc_type, **kwargs)
        self.npcs[npc_id] = npc
        self.stats["total_npcs"] += 1
        logger.info(f"Created NPC: {name} ({npc_type.value})")
        return npc
    
    def get_npc(self, npc_id: str) -> Optional[NPC]:
        return self.npcs.get(npc_id)
    
    def get_npcs_by_type(self, npc_type: NPCType) -> List[NPC]:
        return [npc for npc in self.npcs.values() if npc.npc_type == npc_type]
    
    def get_npcs_in_location(self, location: str) -> List[NPC]:
        return [npc for npc in self.npcs.values() if npc.location == location and npc.is_alive]
    
    def update_relationship(self, npc_id: str, character_id: str,
                           trust_delta: float = 0.0, affection_delta: float = 0.0,
                           respect_delta: float = 0.0, event: Optional[str] = None) -> None:
        npc = self.get_npc(npc_id)
        if not npc:
            return
        
        if character_id not in npc.relationships:
            npc.relationships[character_id] = NPCRelationship(character_id=character_id)
        
        rel = npc.relationships[character_id]
        rel.trust_level = max(0.0, min(1.0, rel.trust_level + trust_delta))
        rel.affection = max(0.0, min(1.0, rel.affection + affection_delta))
        rel.respect = max(0.0, min(1.0, rel.respect + respect_delta))
        rel.interactions += 1
        rel.last_interaction = time.time()
        
        if event:
            rel.memorable_events.append(event)
        
        self._update_mood(npc, character_id)
    
    def _update_mood(self, npc: NPC, character_id: str) -> None:
        if character_id not in npc.relationships:
            return
        
        rel = npc.relationships[character_id]
        sentiment = (rel.trust_level + rel.affection + rel.respect) / 3.0
        
        if sentiment >= 0.8:
            npc.current_mood = NPCMood.FRIENDLY
        elif sentiment >= 0.6:
            npc.current_mood = NPCMood.HELPFUL
        elif sentiment >= 0.4:
            npc.current_mood = NPCMood.NEUTRAL
        elif sentiment >= 0.2:
            npc.current_mood = NPCMood.SUSPICIOUS
        else:
            npc.current_mood = NPCMood.HOSTILE
    
    def generate_greeting(self, npc_id: str, character_id: str) -> str:
        npc = self.get_npc(npc_id)
        if not npc:
            return "..."
        
        rel = npc.relationships.get(character_id)
        first_meeting = rel is None or rel.interactions == 0
        
        if first_meeting:
            greetings = {
                NPCMood.FRIENDLY: f"Well met! I'm {npc.name}.",
                NPCMood.NEUTRAL: f"Hello. I am {npc.name}.",
                NPCMood.SUSPICIOUS: "Who are you?",
                NPCMood.HOSTILE: "What do you want?",
                NPCMood.HELPFUL: "Greetings! How can I help?",
            }
        else:
            greetings = {
                NPCMood.FRIENDLY: "Ah, good to see you again!",
                NPCMood.NEUTRAL: "Hello again.",
                NPCMood.SUSPICIOUS: "You again. What is it this time?",
                NPCMood.HOSTILE: "I thought I told you to leave.",
                NPCMood.HELPFUL: "Welcome back! How can I assist you?",
                NPCMood.FEARFUL: "P-please, I don't want trouble...",
                NPCMood.ANGRY: "You have some nerve showing your face here.",
            }
        
        self.stats["dialogue_generated"] += 1
        return greetings.get(npc.current_mood, "Hello.")
    
    def can_provide_information(self, npc_id: str, topic: str, character_id: str) -> Tuple[bool, Optional[str]]:
        npc = self.get_npc(npc_id)
        if not npc:
            return False, "NPC not found"
        
        if topic not in npc.knows_about:
            return False, f"{npc.name} doesn't know about that."
        
        if topic in npc.secrets:
            rel = npc.relationships.get(character_id)
            if not rel or rel.trust_level < 0.7:
                return False, f"{npc.name} doesn't trust you enough."
        
        if npc.current_mood == NPCMood.HOSTILE:
            return False, f"{npc.name} refuses to talk."
        
        return True, None
    
    def add_knowledge(self, npc_id: str, topic: str, is_secret: bool = False) -> None:
        npc = self.get_npc(npc_id)
        if npc:
            npc.knows_about.add(topic)
            if is_secret:
                npc.secrets.add(topic)
    
    def get_available_quests(self, npc_id: str, character_id: str) -> List[str]:
        npc = self.get_npc(npc_id)
        if not npc or npc.npc_type != NPCType.QUEST_GIVER:
            return []
        return [f"Help with: {goal}" for goal in npc.short_term_goals]
    
    def get_statistics(self) -> Dict[str, Any]:
        alive = sum(1 for npc in self.npcs.values() if npc.is_alive)
        by_type = {}
        for npc in self.npcs.values():
            by_type[npc.npc_type.value] = by_type.get(npc.npc_type.value, 0) + 1
        
        return {**self.stats, "alive_npcs": alive, "dead_npcs": self.stats["total_npcs"] - alive, "by_type": by_type}


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print("Testing NPC Manager...\n")
    
    manager = NPCManager()
    
    print("=== Test 1: Create NPCs ===")
    innkeeper = manager.create_npc("inn1", "Tobias", NPCType.MERCHANT, location="Inn")
    sage = manager.create_npc("sage1", "Elminster", NPCType.QUEST_GIVER, location="Tower")
    sage.short_term_goals = ["Find artifact", "Defeat cult"]
    sage.knows_about = {"magic", "cult", "prophecy"}
    sage.secrets = {"prophecy"}
    print(f"Created {manager.stats['total_npcs']} NPCs\n")
    
    print("=== Test 2: Greetings ===")
    print(f"Innkeeper: {manager.generate_greeting('inn1', 'player1')}")
    manager.update_relationship("inn1", "player1", trust_delta=0.2)
    print(f"Innkeeper again: {manager.generate_greeting('inn1', 'player1')}\n")
    
    print("=== Test 3: Relationships ===")
    manager.update_relationship("sage1", "player1", trust_delta=0.3, respect_delta=0.2)
    rel = sage.relationships["player1"]
    print(f"Trust: {rel.trust_level:.2f}, Mood: {sage.current_mood.value}\n")
    
    print("=== Test 4: Knowledge ===")
    can, reason = manager.can_provide_information("sage1", "prophecy", "player1")
    print(f"Can share secret (trust={rel.trust_level:.2f}): {can}")
    if not can: print(f"  {reason}")
    manager.update_relationship("sage1", "player1", trust_delta=0.5)
    can, _ = manager.can_provide_information("sage1", "prophecy", "player1")
    print(f"After trust increase: {can}\n")
    
    print("=== Test 5: Quests ===")
    quests = manager.get_available_quests("sage1", "player1")
    print(f"Quests: {quests}\n")
    
    print("=== Test 6: Statistics ===")
    print(f"Stats: {manager.get_statistics()}\n")
    
    print("✅ All tests completed!")
