"""
NPC Manager

Manages non-player characters with automated behaviors, dialogue trees,
and personality-driven interactions.

Key Features:
- NPC personality and motivations
- Automated dialogue generation
- Behavior trees for NPC actions
- Relationship tracking
- Quest giving and progression
- Dynamic NPC reactions
"""

import time
import random
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NPCType(Enum):
    """Types of NPCs"""
    QUEST_GIVER = "quest_giver"
    MERCHANT = "merchant"
    GUARD = "guard"
    COMMONER = "commoner"
    ALLY = "ally"
    ENEMY = "enemy"
    NEUTRAL = "neutral"
    BOSS = "boss"


class NPCMood(Enum):
    """NPC emotional states"""
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    SUSPICIOUS = "suspicious"
    HOSTILE = "hostile"
    FEARFUL = "fearful"
    EXCITED = "excited"
    DEPRESSED = "depressed"


class DialogueIntent(Enum):
    """Intent of NPC dialogue"""
    GREETING = "greeting"
    QUEST_OFFER = "quest_offer"
    INFORMATION = "information"
    TRADE = "trade"
    THREAT = "threat"
    PLEA = "plea"
    FAREWELL = "farewell"
    SMALL_TALK = "small_talk"


@dataclass
class NPCPersonality:
    """NPC personality traits"""
    # Big 5 personality
    openness: float = 0.5           # 0=conventional, 1=curious
    conscientiousness: float = 0.5  # 0=careless, 1=organized
    extraversion: float = 0.5       # 0=reserved, 1=outgoing
    agreeableness: float = 0.5      # 0=competitive, 1=cooperative
    neuroticism: float = 0.5        # 0=confident, 1=nervous
    
    # Additional traits
    honesty: float = 0.7            # 0=deceitful, 1=honest
    bravery: float = 0.5            # 0=cowardly, 1=brave
    intelligence: float = 0.5       # 0=simple, 1=clever
    greed: float = 0.3              # 0=generous, 1=greedy


@dataclass
class NPCKnowledge:
    """What an NPC knows"""
    known_facts: Set[str] = field(default_factory=set)
    rumors: Set[str] = field(default_factory=set)
    secrets: Set[str] = field(default_factory=set)
    quest_info: Dict[str, str] = field(default_factory=dict)
    locations_known: Set[str] = field(default_factory=set)


@dataclass
class NPCRelationship:
    """NPC's relationship with a character"""
    character_id: str
    trust: float = 0.5        # 0=distrust, 1=complete trust
    respect: float = 0.5      # 0=contempt, 1=admiration
    fear: float = 0.0         # 0=not afraid, 1=terrified
    affection: float = 0.0    # 0=none, 1=love
    
    # History
    interactions: int = 0
    last_interaction: Optional[float] = None
    shared_quests: List[str] = field(default_factory=list)


@dataclass
class DialogueOption:
    """A dialogue choice"""
    text: str
    intent: DialogueIntent
    requires_check: Optional[str] = None  # "persuasion", "intimidation", etc.
    dc: int = 10
    leads_to: Optional[str] = None  # Next dialogue node
    consequence: Optional[str] = None


@dataclass
class DialogueNode:
    """A node in dialogue tree"""
    node_id: str
    npc_text: str
    mood: NPCMood
    options: List[DialogueOption] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)


class NPC:
    """
    Non-Player Character
    
    An NPC with personality, knowledge, relationships, and automated behaviors.
    """
    
    def __init__(
        self,
        npc_id: str,
        name: str,
        npc_type: NPCType,
        personality: Optional[NPCPersonality] = None,
        description: str = ""
    ):
        """
        Initialize NPC
        
        Args:
            npc_id: Unique identifier
            name: NPC name
            npc_type: Type of NPC
            personality: Personality traits
            description: Physical description
        """
        self.npc_id = npc_id
        self.name = name
        self.npc_type = npc_type
        self.personality = personality or NPCPersonality()
        self.description = description
        
        # State
        self.current_mood = NPCMood.NEUTRAL
        self.current_location = "unknown"
        self.is_alive = True
        self.is_hostile = npc_type == NPCType.ENEMY
        
        # Knowledge
        self.knowledge = NPCKnowledge()
        
        # Relationships
        self.relationships: Dict[str, NPCRelationship] = {}
        
        # Dialogue
        self.dialogue_tree: Dict[str, DialogueNode] = {}
        self.current_dialogue_node: Optional[str] = None
        
        # Quests
        self.quests_available: List[str] = []
        self.quests_given: List[str] = []
        
        # Statistics
        self.interaction_count = 0
        self.last_interaction_time: Optional[float] = None
        
        logger.info(f"Created NPC: {name} ({npc_type.value})")
    
    def get_relationship(self, character_id: str) -> NPCRelationship:
        """Get or create relationship with a character"""
        if character_id not in self.relationships:
            self.relationships[character_id] = NPCRelationship(
                character_id=character_id
            )
        return self.relationships[character_id]
    
    def update_relationship(
        self,
        character_id: str,
        trust_delta: float = 0.0,
        respect_delta: float = 0.0,
        fear_delta: float = 0.0
    ) -> None:
        """Update relationship values"""
        rel = self.get_relationship(character_id)
        
        rel.trust = max(0.0, min(1.0, rel.trust + trust_delta))
        rel.respect = max(0.0, min(1.0, rel.respect + respect_delta))
        rel.fear = max(0.0, min(1.0, rel.fear + fear_delta))
        rel.interactions += 1
        rel.last_interaction = time.time()
        
        logger.debug(
            f"{self.name} relationship with {character_id}: "
            f"trust={rel.trust:.2f}, respect={rel.respect:.2f}"
        )
    
    def generate_greeting(self, character_id: str) -> str:
        """Generate context-appropriate greeting"""
        rel = self.get_relationship(character_id)
        
        # Base greeting on relationship
        if rel.trust > 0.7:
            greetings = [
                f"Ah, my friend! Good to see you again.",
                f"Welcome back! Always a pleasure.",
                f"There you are! I was hoping you'd stop by."
            ]
        elif rel.fear > 0.7:
            greetings = [
                f"P-please, I meant no harm...",
                f"What do you want from me?",
                f"I'll do whatever you ask, just don't hurt me!"
            ]
        elif rel.trust < 0.3:
            greetings = [
                f"What do you want?",
                f"I don't have time for this.",
                f"Make it quick."
            ]
        else:
            greetings = [
                f"Hello there.",
                f"Can I help you?",
                f"Greetings, traveler."
            ]
        
        return random.choice(greetings)
    
    def generate_response(
        self,
        character_id: str,
        player_input: str,
        intent: DialogueIntent = DialogueIntent.SMALL_TALK
    ) -> str:
        """Generate response to player input"""
        
        rel = self.get_relationship(character_id)
        
        # Quest-related responses
        if intent == DialogueIntent.QUEST_OFFER and self.quests_available:
            return self._generate_quest_offer()
        
        # Information requests
        if intent == DialogueIntent.INFORMATION:
            return self._generate_information_response(player_input, rel)
        
        # Trade
        if intent == DialogueIntent.TRADE and self.npc_type == NPCType.MERCHANT:
            return "I have some fine wares. What interests you?"
        
        # Small talk
        return self._generate_small_talk(rel)
    
    def _generate_quest_offer(self) -> str:
        """Generate quest offering dialogue"""
        if not self.quests_available:
            return "I have no tasks for you at the moment."
        
        quest_id = self.quests_available[0]
        
        if self.personality.agreeableness > 0.6:
            return f"I could really use your help with something. Would you be willing to assist me?"
        elif self.personality.greed > 0.7:
            return f"I have a job for you, if you're interested. There's coin in it, of course."
        else:
            return f"I need someone capable to handle a matter. Interested?"
    
    def _generate_information_response(
        self,
        query: str,
        relationship: NPCRelationship
    ) -> str:
        """Generate response to information request"""
        
        # Check if NPC is willing to share
        if relationship.trust < 0.3:
            return "I don't know anything about that."
        
        # Check knowledge
        query_lower = query.lower()
        
        for fact in self.knowledge.known_facts:
            if any(word in fact.lower() for word in query_lower.split()):
                return f"I know that {fact}"
        
        for rumor in self.knowledge.rumors:
            if any(word in rumor.lower() for word in query_lower.split()):
                return f"I've heard rumors that {rumor}"
        
        # Doesn't know
        responses = [
            "I'm afraid I don't know much about that.",
            "That's not something I'm familiar with.",
            "You might want to ask someone else about that."
        ]
        
        return random.choice(responses)
    
    def _generate_small_talk(self, relationship: NPCRelationship) -> str:
        """Generate casual conversation"""
        
        if self.current_mood == NPCMood.FRIENDLY:
            responses = [
                "Things have been going well, thank you for asking.",
                "Can't complain! How about yourself?",
                "Busy as always, but managing."
            ]
        elif self.current_mood == NPCMood.DEPRESSED:
            responses = [
                "Times are tough, I'm afraid.",
                "Not much to be cheerful about these days.",
                "I've seen better days."
            ]
        elif self.current_mood == NPCMood.EXCITED:
            responses = [
                "Have you heard the news? It's wonderful!",
                "These are exciting times!",
                "I can barely contain my enthusiasm!"
            ]
        else:
            responses = [
                "Things are as they are.",
                "Nothing much to report.",
                "Just another day."
            ]
        
        return random.choice(responses)
    
    def set_dialogue_tree(self, dialogue_tree: Dict[str, DialogueNode]) -> None:
        """Set the dialogue tree for this NPC"""
        self.dialogue_tree = dialogue_tree
        self.current_dialogue_node = "start" if "start" in dialogue_tree else None
    
    def get_current_dialogue(self) -> Optional[DialogueNode]:
        """Get current dialogue node"""
        if self.current_dialogue_node and self.current_dialogue_node in self.dialogue_tree:
            return self.dialogue_tree[self.current_dialogue_node]
        return None
    
    def advance_dialogue(self, option_index: int) -> bool:
        """Advance to next dialogue node based on choice"""
        current = self.get_current_dialogue()
        if not current or option_index >= len(current.options):
            return False
        
        option = current.options[option_index]
        if option.leads_to:
            self.current_dialogue_node = option.leads_to
            return True
        
        return False
    
    def determine_behavior(self, context: Dict[str, Any]) -> str:
        """Determine NPC behavior based on type and context"""
        
        # Hostile NPCs attack
        if self.is_hostile:
            return "attack"
        
        # Type-specific behaviors
        if self.npc_type == NPCType.GUARD:
            if context.get("intrusion"):
                return "challenge"
            return "patrol"
        
        elif self.npc_type == NPCType.MERCHANT:
            return "offer_wares"
        
        elif self.npc_type == NPCType.QUEST_GIVER:
            if self.quests_available:
                return "offer_quest"
            return "chat"
        
        else:
            # Default behavior based on mood
            if self.current_mood == NPCMood.FRIENDLY:
                return "chat"
            elif self.current_mood == NPCMood.FEARFUL:
                return "flee"
            else:
                return "idle"


class NPCManager:
    """
    NPC Management System
    
    Manages all NPCs in the game world, handles their behaviors,
    and coordinates interactions.
    """
    
    def __init__(self):
        """Initialize NPC manager"""
        self.npcs: Dict[str, NPC] = {}
        self.npcs_by_location: Dict[str, Set[str]] = {}
        
        # Templates
        self.dialogue_templates = self._load_dialogue_templates()
        
        # Statistics
        self.stats = {
            "total_npcs": 0,
            "total_interactions": 0,
            "quests_given": 0
        }
        
        logger.info("NPCManager initialized")
    
    def _load_dialogue_templates(self) -> Dict[str, Any]:
        """Load dialogue templates"""
        return {
            "guard": {
                "greeting": "Halt! State your business.",
                "challenge": "You don't belong here. Leave now!",
                "approved": "You may pass."
            },
            "merchant": {
                "greeting": "Welcome! Take a look at my wares.",
                "haggle_accept": "Fine, you drive a hard bargain.",
                "haggle_reject": "I can't go that low."
            },
            "quest_giver": {
                "greeting": "Ah, you look like someone who can help.",
                "quest_accept": "Thank you! I knew I could count on you.",
                "quest_complete": "You've done it! Here's your reward."
            }
        }
    
    def create_npc(
        self,
        npc_id: str,
        name: str,
        npc_type: NPCType,
        location: str,
        personality: Optional[NPCPersonality] = None,
        **kwargs
    ) -> NPC:
        """Create a new NPC"""
        
        npc = NPC(
            npc_id=npc_id,
            name=name,
            npc_type=npc_type,
            personality=personality,
            **kwargs
        )
        
        # Register NPC
        self.npcs[npc_id] = npc
        
        # Add to location
        if location not in self.npcs_by_location:
            self.npcs_by_location[location] = set()
        self.npcs_by_location[location].add(npc_id)
        
        npc.current_location = location
        
        self.stats["total_npcs"] += 1
        
        logger.info(f"Created NPC {name} at {location}")
        
        return npc
    
    def get_npc(self, npc_id: str) -> Optional[NPC]:
        """Get NPC by ID"""
        return self.npcs.get(npc_id)
    
    def get_npcs_at_location(self, location: str) -> List[NPC]:
        """Get all NPCs at a location"""
        npc_ids = self.npcs_by_location.get(location, set())
        return [self.npcs[npc_id] for npc_id in npc_ids if npc_id in self.npcs]
    
    def interact(
        self,
        npc_id: str,
        character_id: str,
        interaction_type: str = "talk",
        content: str = ""
    ) -> Optional[str]:
        """Handle interaction with NPC"""
        
        npc = self.get_npc(npc_id)
        if not npc:
            return None
        
        npc.interaction_count += 1
        npc.last_interaction_time = time.time()
        self.stats["total_interactions"] += 1
        
        # Determine intent
        if "quest" in content.lower():
            intent = DialogueIntent.QUEST_OFFER
        elif "buy" in content.lower() or "sell" in content.lower():
            intent = DialogueIntent.TRADE
        elif any(word in content.lower() for word in ["what", "where", "who", "how"]):
            intent = DialogueIntent.INFORMATION
        else:
            intent = DialogueIntent.SMALL_TALK
        
        # Generate response
        if interaction_type == "talk":
            if npc.interaction_count == 1:
                response = npc.generate_greeting(character_id)
            else:
                response = npc.generate_response(character_id, content, intent)
            
            # Update relationship based on interaction
            if "please" in content.lower() or "thank" in content.lower():
                npc.update_relationship(character_id, respect_delta=0.05)
            
            return response
        
        return None
    
    def update_npc_location(self, npc_id: str, new_location: str) -> bool:
        """Move NPC to new location"""
        npc = self.get_npc(npc_id)
        if not npc:
            return False
        
        # Remove from old location
        old_location = npc.current_location
        if old_location in self.npcs_by_location:
            self.npcs_by_location[old_location].discard(npc_id)
        
        # Add to new location
        if new_location not in self.npcs_by_location:
            self.npcs_by_location[new_location] = set()
        self.npcs_by_location[new_location].add(npc_id)
        
        npc.current_location = new_location
        
        logger.debug(f"{npc.name} moved to {new_location}")
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get NPC management statistics"""
        return self.stats.copy()


# Test code
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("Testing NPC Manager...\n")
    
    # Create manager
    print("=== Test 1: Create NPC Manager ===")
    manager = NPCManager()
    print(f"Manager created")
    print()
    
    # Create NPCs
    print("=== Test 2: Create NPCs ===")
    
    # Guard
    guard_personality = NPCPersonality(
        extraversion=0.3,
        agreeableness=0.4,
        bravery=0.8
    )
    guard = manager.create_npc(
        npc_id="guard1",
        name="Guard Ironbeard",
        npc_type=NPCType.GUARD,
        location="town_gate",
        personality=guard_personality,
        description="A stern-looking dwarf in chainmail"
    )
    
    # Merchant
    merchant_personality = NPCPersonality(
        extraversion=0.8,
        agreeableness=0.6,
        greed=0.7
    )
    merchant = manager.create_npc(
        npc_id="merchant1",
        name="Bella the Trader",
        npc_type=NPCType.MERCHANT,
        location="market",
        personality=merchant_personality
    )
    
    # Quest giver
    quest_giver = manager.create_npc(
        npc_id="elder1",
        name="Elder Thorne",
        npc_type=NPCType.QUEST_GIVER,
        location="town_hall",
        description="An elderly human with a worried expression"
    )
    quest_giver.quests_available.append("rescue_child")
    
    print(f"Created {len(manager.npcs)} NPCs")
    print()
    
    # Test interactions
    print("=== Test 3: Guard Interaction ===")
    response = manager.interact(
        npc_id="guard1",
        character_id="player1",
        interaction_type="talk",
        content="Hello"
    )
    print(f"Guard: {response}")
    print()
    
    print("=== Test 4: Merchant Interaction ===")
    response = manager.interact(
        npc_id="merchant1",
        character_id="player1",
        interaction_type="talk",
        content="What do you have for sale?"
    )
    print(f"Merchant: {response}")
    print()
    
    print("=== Test 5: Quest Giver Interaction ===")
    response = manager.interact(
        npc_id="elder1",
        character_id="player1",
        interaction_type="talk",
        content="Do you have any quests?"
    )
    print(f"Elder: {response}")
    print()
    
    # Test relationship building
    print("=== Test 6: Relationship Building ===")
    for i in range(3):
        manager.interact(
            npc_id="guard1",
            character_id="player1",
            interaction_type="talk",
            content="Thank you for your service"
        )
    
    rel = guard.get_relationship("player1")
    print(f"Relationship with guard:")
    print(f"  Trust: {rel.trust:.2f}")
    print(f"  Respect: {rel.respect:.2f}")
    print(f"  Interactions: {rel.interactions}")
    print()
    
    # Test location queries
    print("=== Test 7: Location Queries ===")
    npcs_at_gate = manager.get_npcs_at_location("town_gate")
    print(f"NPCs at town_gate: {[npc.name for npc in npcs_at_gate]}")
    
    npcs_at_market = manager.get_npcs_at_location("market")
    print(f"NPCs at market: {[npc.name for npc in npcs_at_market]}")
    print()
    
    # Test statistics
    print("=== Test 8: Statistics ===")
    stats = manager.get_stats()
    print(f"Stats: {stats}")
    print()
    
    print("✅ All NPC manager tests completed!")
