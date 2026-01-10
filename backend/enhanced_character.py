"""
AI Society D&D - Enhanced Character System
===========================================
Integrates temporal consciousness, personal vector DBs, and D&D mechanics.
Each character has:
- Personal vector database (subjective truth/memory)
- Memory consolidation system
- Character laptop (journal, tools, private work)
- D&D stats and mechanics
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import random
import hashlib
import numpy as np

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic


# ============================================================================
# D&D CHARACTER STATS
# ============================================================================

@dataclass
class DnDStats:
    """Standard D&D 5e ability scores"""
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    
    # Derived stats
    armor_class: int = 10
    hit_points: int = 10
    max_hit_points: int = 10
    speed: int = 30  # feet per round
    
    # Resources
    action_points: int = 1  # Actions per turn
    bonus_action_available: bool = True
    reaction_available: bool = True
    
    def get_modifier(self, ability: str) -> int:
        """Calculate ability modifier (D&D formula: (score - 10) // 2)"""
        score = getattr(self, ability.lower())
        return (score - 10) // 2
    
    def roll_ability_check(self, ability: str, dice_roller) -> Tuple[int, int, int]:
        """Roll d20 + modifier. Returns (total, d20_roll, modifier)"""
        modifier = self.get_modifier(ability)
        d20_roll = dice_roller.roll(20)
        total = d20_roll + modifier
        return (total, d20_roll, modifier)
    
    def roll_saving_throw(self, ability: str, dice_roller) -> Tuple[int, int, int]:
        """Same as ability check for now (proficiencies would add bonuses)"""
        return self.roll_ability_check(ability, dice_roller)
    
    def take_damage(self, amount: int) -> bool:
        """Take damage, return True if still alive"""
        self.hit_points = max(0, self.hit_points - amount)
        return self.hit_points > 0
    
    def heal(self, amount: int):
        """Restore hit points"""
        self.hit_points = min(self.max_hit_points, self.hit_points + amount)
    
    def reset_turn_resources(self):
        """Reset resources at start of turn"""
        self.action_points = 1
        self.bonus_action_available = True
        # Reaction resets at start of YOUR turn


@dataclass
class CharacterClass:
    """D&D character class"""
    name: str  # "Fighter", "Wizard", "Rogue", etc.
    level: int = 1
    hit_die: int = 8  # d8 for most classes
    proficiency_bonus: int = 2  # +2 at level 1-4
    
    # Class features
    features: List[str] = field(default_factory=list)
    spells_known: List[str] = field(default_factory=list)
    spell_slots: Dict[int, int] = field(default_factory=dict)  # {level: slots}
    
    def level_up(self):
        """Increase level and update proficiency bonus"""
        self.level += 1
        # Proficiency bonus increases at levels 5, 9, 13, 17
        self.proficiency_bonus = 2 + ((self.level - 1) // 4)


@dataclass
class Inventory:
    """Character's inventory and equipment"""
    gold: int = 0
    
    # Equipped items
    weapon: Optional[str] = None
    armor: Optional[str] = None
    shield: Optional[str] = None
    
    # Carried items
    items: List[Dict[str, Any]] = field(default_factory=list)
    
    # Capacity
    max_weight: int = 150  # pounds
    current_weight: float = 0.0
    
    def add_item(self, name: str, quantity: int = 1, weight: float = 0.0):
        """Add item to inventory"""
        self.items.append({
            "name": name,
            "quantity": quantity,
            "weight": weight
        })
        self.current_weight += weight * quantity
    
    def remove_item(self, name: str, quantity: int = 1) -> bool:
        """Remove item from inventory"""
        for item in self.items:
            if item["name"] == name:
                if item["quantity"] >= quantity:
                    item["quantity"] -= quantity
                    self.current_weight -= item["weight"] * quantity
                    if item["quantity"] == 0:
                        self.items.remove(item)
                    return True
        return False


# ============================================================================
# CHARACTER LAPTOP (Personal Computing Environment)
# ============================================================================

@dataclass
class CharacterLaptop:
    """
    The character's personal "laptop" - their notebook and tools.
    Contains:
    - Journal entries (personal reflections)
    - Documents (notes, letters, maps)
    - Tools (dice roller, calculator, etc.)
    - Private LLM access (for thinking/planning)
    """
    owner_id: str
    
    # Journal entries (chronological)
    journal_entries: List[Dict[str, Any]] = field(default_factory=list)
    
    # Documents and notes
    documents: List[Dict[str, Any]] = field(default_factory=list)
    
    # Images and sketches
    images: List[Dict[str, Any]] = field(default_factory=list)
    
    # Private conversation history with LLM
    private_conversations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Tools available
    tools: List[str] = field(default_factory=lambda: [
        "dice_roller",
        "calculator", 
        "rule_lookup",
        "private_llm_query"
    ])
    
    # Preferences
    dm_can_see_private_calls: bool = False  # DM oversight toggle
    
    def add_journal_entry(self, content: str, tags: List[str] = None):
        """Add a journal entry"""
        entry = {
            "id": hashlib.md5(f"{self.owner_id}{datetime.now().isoformat()}".encode()).hexdigest()[:12],
            "timestamp": datetime.now().isoformat(),
            "content": content,
            "tags": tags or [],
            "type": "journal"
        }
        self.journal_entries.append(entry)
        return entry
    
    def add_document(self, title: str, content: str, doc_type: str = "note"):
        """Add a document"""
        doc = {
            "id": hashlib.md5(f"{title}{datetime.now().isoformat()}".encode()).hexdigest()[:12],
            "title": title,
            "content": content,
            "type": doc_type,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self.documents.append(doc)
        return doc
    
    async def private_llm_query(self, query: str, model: str = "gpt-4o-mini") -> str:
        """
        Make a private call to an LLM for thinking/planning.
        DM can see this if dm_can_see_private_calls is True.
        """
        conversation = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "visible_to_dm": self.dm_can_see_private_calls
        }
        
        # Call LLM
        try:
            llm = ChatOpenAI(model=model, temperature=0.7)
            messages = [
                SystemMessage(content=f"You are the inner thoughts of character {self.owner_id}. Help them think through their situation."),
                HumanMessage(content=query)
            ]
            response = await llm.ainvoke(messages)
            conversation["response"] = response.content
        except Exception as e:
            conversation["response"] = f"Error: {str(e)}"
        
        self.private_conversations.append(conversation)
        return conversation["response"]
    
    def get_recent_journal_entries(self, n: int = 10) -> List[Dict]:
        """Get most recent journal entries"""
        return self.journal_entries[-n:]


# ============================================================================
# ENHANCED CHARACTER WITH TEMPORAL CONSCIOUSNESS
# ============================================================================

class EnhancedCharacter:
    """
    Complete character with:
    - D&D stats and mechanics
    - Personal vector database (memory)
    - Memory consolidation system
    - Character laptop
    - Cultural learning capabilities
    """
    
    def __init__(
        self,
        character_id: str,
        name: str,
        race: str,
        character_class: CharacterClass,
        personality_traits: List[str],
        backstory: str,
        vector_db_url: str = "http://localhost:6333",
        use_local_vector_db: bool = True
    ):
        # Identity
        self.character_id = character_id
        self.name = name
        self.race = race
        self.character_class = character_class
        self.personality_traits = personality_traits
        self.backstory = backstory
        
        # D&D Stats
        self.stats = DnDStats()
        self.inventory = Inventory()
        
        # Laptop (personal computing)
        self.laptop = CharacterLaptop(owner_id=character_id)
        
        # Memory & Consciousness (from memory_system.py)
        from memory_system import MemoryConsolidationEngine, IdentityPersistenceSystem
        from vector_memory import QdrantMemoryStore, MemoryVector
        
        self.memory_engine = MemoryConsolidationEngine(character_id)
        self.identity_system = IdentityPersistenceSystem(character_id)
        
        # Personal vector database
        if use_local_vector_db:
            self.vector_store = QdrantMemoryStore(
                character_id=character_id,
                qdrant_url=vector_db_url
            )
        else:
            # Will use fallback in-memory storage
            self.vector_store = None
        
        # Cultural learning (skills learned from others)
        self.learned_skills: Dict[str, Any] = {}
        
        # Game state
        self.current_location: str = "Unknown"
        self.current_quest: Optional[str] = None
        self.conditions: List[str] = []  # "poisoned", "blessed", etc.
        
        # Relationships with other characters
        self.relationships: Dict[str, float] = {}  # character_id -> affinity (-1 to 1)
        
    def get_full_context(self, include_recent_memories: int = 5) -> str:
        """
        Generate full character context for LLM prompts.
        Includes: backstory, personality, stats, recent memories, current state.
        """
        context_parts = [
            f"=== {self.name} the {self.race} {self.character_class.name} ===",
            f"\nPersonality: {', '.join(self.personality_traits)}",
            f"\nBackstory: {self.backstory}",
            f"\n--- Stats ---",
            f"Level {self.character_class.level}",
            f"HP: {self.stats.hit_points}/{self.stats.max_hit_points}",
            f"AC: {self.stats.armor_class}",
            f"STR: {self.stats.strength} ({self.stats.get_modifier('strength'):+d})",
            f"DEX: {self.stats.dexterity} ({self.stats.get_modifier('dexterity'):+d})",
            f"CON: {self.stats.constitution} ({self.stats.get_modifier('constitution'):+d})",
            f"INT: {self.stats.intelligence} ({self.stats.get_modifier('intelligence'):+d})",
            f"WIS: {self.stats.wisdom} ({self.stats.get_modifier('wisdom'):+d})",
            f"CHA: {self.stats.charisma} ({self.stats.get_modifier('charisma'):+d})",
        ]
        
        # Add inventory
        if self.inventory.weapon:
            context_parts.append(f"\nWeapon: {self.inventory.weapon}")
        if self.inventory.armor:
            context_parts.append(f"Armor: {self.inventory.armor}")
        
        # Add conditions
        if self.conditions:
            context_parts.append(f"\nConditions: {', '.join(self.conditions)}")
        
        # Add recent memories
        recent_memories = list(self.memory_engine.memories.values())[-include_recent_memories:]
        if recent_memories:
            context_parts.append("\n--- Recent Memories ---")
            for mem in recent_memories:
                context_parts.append(f"- {mem.content}")
        
        # Add current quest
        if self.current_quest:
            context_parts.append(f"\n--- Current Quest ---\n{self.current_quest}")
        
        return "\n".join(context_parts)
    
    async def make_decision(
        self,
        situation: str,
        available_actions: List[str] = None,
        use_memories: bool = True,
        model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """
        Make a decision in the game using:
        1. Current situation
        2. Relevant memories from vector DB
        3. Character context
        4. Small LLM for reasoning
        
        Returns: {
            "action": "what the character does",
            "reasoning": "why they chose this",
            "confidence": 0.0-1.0
        }
        """
        # Retrieve relevant memories
        relevant_memories = []
        if use_memories and self.vector_store:
            memory_results = self.vector_store.retrieve_memories(
                query=situation,
                top_k=5,
                α_recency=1.0,
                α_importance=1.5,
                α_relevance=2.0
            )
            relevant_memories = [m.content for m in memory_results]
        
        # Build prompt
        prompt_parts = [
            self.get_full_context(),
            "\n=== Current Situation ===",
            situation
        ]
        
        if relevant_memories:
            prompt_parts.append("\n=== Relevant Memories ===")
            for i, mem in enumerate(relevant_memories, 1):
                prompt_parts.append(f"{i}. {mem}")
        
        if available_actions:
            prompt_parts.append("\n=== Available Actions ===")
            for i, action in enumerate(available_actions, 1):
                prompt_parts.append(f"{i}. {action}")
        
        prompt_parts.append("\nWhat do you do? Respond in character, describing your action and your reasoning.")
        
        full_prompt = "\n".join(prompt_parts)
        
        # Call LLM
        try:
            llm = ChatOpenAI(model=model, temperature=0.8)
            messages = [
                SystemMessage(content=f"You are {self.name}, a {self.race} {self.character_class.name}. Stay in character and make decisions based on your personality and experiences."),
                HumanMessage(content=full_prompt)
            ]
            response = await llm.ainvoke(messages)
            
            return {
                "action": response.content,
                "reasoning": "Based on memories and personality",
                "confidence": 0.8,
                "memories_used": len(relevant_memories)
            }
        except Exception as e:
            return {
                "action": "I hesitate, unsure what to do.",
                "reasoning": f"Error: {str(e)}",
                "confidence": 0.0,
                "memories_used": 0
            }
    
    def store_game_memory(
        self,
        event_description: str,
        importance: float = 5.0,
        emotional_valence: float = 0.0,
        participants: List[str] = None
    ):
        """
        Store a memory from the game session.
        This will be consolidated and stored in vector DB.
        """
        from memory_system import MemoryType
        from vector_memory import MemoryVector
        
        # Store in memory consolidation engine
        memory = self.memory_engine.store_memory(
            content=event_description,
            memory_type=MemoryType.EPISODIC,
            importance=importance,
            emotional_valence=emotional_valence,
            participants=participants or [],
            location=self.current_location
        )
        
        # Also store in vector DB for retrieval
        if self.vector_store:
            memory_vector = MemoryVector(
                id=memory.id,
                content=memory.content,
                character_id=self.character_id,
                timestamp=memory.timestamp.isoformat(),
                memory_type=memory.memory_type.value,
                importance=memory.importance,
                emotional_valence=memory.emotional_valence,
                participants=memory.participants,
                location=memory.location,
                is_temporal_landmark=memory.is_temporal_landmark
            )
            self.vector_store.store_memory(memory_vector)
        
        # Also add to journal
        self.laptop.add_journal_entry(
            content=event_description,
            tags=["game_session", self.current_location]
        )
        
        return memory
    
    async def consolidate_memories(self):
        """
        Run memory consolidation (should happen after game sessions).
        Converts episodic memories to semantic knowledge.
        """
        # Check if consolidation is needed
        if self.memory_engine.importance_accumulator > self.memory_engine.REFLECTION_THRESHOLD:
            semantic_memories = self.memory_engine.consolidate_to_semantic()
            
            # Store semantic memories in vector DB
            if self.vector_store and semantic_memories:
                from vector_memory import MemoryVector
                for sem_mem in semantic_memories:
                    vec = MemoryVector(
                        id=sem_mem.id,
                        content=sem_mem.content,
                        character_id=self.character_id,
                        timestamp=sem_mem.timestamp.isoformat(),
                        memory_type=sem_mem.memory_type.value,
                        importance=sem_mem.importance,
                        consolidated=True
                    )
                    self.vector_store.store_memory(vec)
            
            return len(semantic_memories)
        return 0
    
    def get_character_sheet(self) -> Dict[str, Any]:
        """Get full character sheet for display or saving"""
        return {
            "character_id": self.character_id,
            "name": self.name,
            "race": self.race,
            "class": {
                "name": self.character_class.name,
                "level": self.character_class.level,
                "proficiency_bonus": self.character_class.proficiency_bonus
            },
            "personality": self.personality_traits,
            "backstory": self.backstory,
            "stats": asdict(self.stats),
            "inventory": asdict(self.inventory),
            "current_location": self.current_location,
            "current_quest": self.current_quest,
            "conditions": self.conditions,
            "memory_count": len(self.memory_engine.memories),
            "journal_entries": len(self.laptop.journal_entries)
        }


# ============================================================================
# DICE ROLLER (Mechanical Tool)
# ============================================================================

class DiceRoller:
    """D&D dice roller with history tracking"""
    
    def __init__(self):
        self.roll_history: List[Dict] = []
    
    def roll(self, sides: int, count: int = 1, modifier: int = 0) -> int:
        """Roll dice. Returns total."""
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls) + modifier
        
        # Track history
        self.roll_history.append({
            "timestamp": datetime.now().isoformat(),
            "dice": f"{count}d{sides}",
            "modifier": modifier,
            "rolls": rolls,
            "total": total
        })
        
        return total
    
    def roll_with_advantage(self, sides: int = 20) -> Tuple[int, List[int]]:
        """Roll twice, take higher (D&D advantage)"""
        roll1 = random.randint(1, sides)
        roll2 = random.randint(1, sides)
        result = max(roll1, roll2)
        
        self.roll_history.append({
            "timestamp": datetime.now().isoformat(),
            "type": "advantage",
            "rolls": [roll1, roll2],
            "result": result
        })
        
        return result, [roll1, roll2]
    
    def roll_with_disadvantage(self, sides: int = 20) -> Tuple[int, List[int]]:
        """Roll twice, take lower (D&D disadvantage)"""
        roll1 = random.randint(1, sides)
        roll2 = random.randint(1, sides)
        result = min(roll1, roll2)
        
        self.roll_history.append({
            "timestamp": datetime.now().isoformat(),
            "type": "disadvantage",
            "rolls": [roll1, roll2],
            "result": result
        })
        
        return result, [roll1, roll2]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_sample_character() -> EnhancedCharacter:
    """Create a sample character for testing"""
    char_class = CharacterClass(
        name="Fighter",
        level=1,
        hit_die=10,
        features=["Fighting Style", "Second Wind"]
    )
    
    character = EnhancedCharacter(
        character_id="char_001",
        name="Thorin Ironforge",
        race="Dwarf",
        character_class=char_class,
        personality_traits=["Brave", "Stubborn", "Loyal to friends"],
        backstory="A dwarf fighter seeking revenge for his clan's destroyed mine."
    )
    
    # Set stats
    character.stats.strength = 16
    character.stats.constitution = 14
    character.stats.dexterity = 12
    character.stats.hit_points = 12
    character.stats.max_hit_points = 12
    character.stats.armor_class = 16
    
    # Set equipment
    character.inventory.weapon = "Battleaxe"
    character.inventory.armor = "Chain Mail"
    character.inventory.gold = 15
    
    return character
