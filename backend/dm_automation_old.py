"""
DM Automation System

Digital twin for the Dungeon Master that can handle routine DM tasks,
generate story content, manage NPCs, and provide suggestions to the human DM.

Key Features:
- DM personality and style modeling
- Auto-response for routine situations
- Story generation and suggestions
- NPC behavior automation
- Encounter design assistance
- Rule adjudication help
- Human-in-the-loop for critical decisions
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import random

logger = logging.getLogger(__name__)


class DMResponseType(Enum):
    """Types of DM responses"""
    NARRATION = "narration"           # Story/scene description
    NPC_DIALOGUE = "npc_dialogue"     # NPC speaking
    RULE_CLARIFICATION = "rule_clarification"  # Rules explanation
    ENCOUNTER = "encounter"           # Combat/encounter intro
    CONSEQUENCE = "consequence"       # Action results
    TRANSITION = "transition"         # Scene changes
    ATMOSPHERE = "atmosphere"         # Mood/environment
    PROMPT = "prompt"                 # Player prompts


class DMAutomationLevel(Enum):
    """How much the DM is automated"""
    MANUAL = "manual"           # Human DM only
    ASSISTED = "assisted"       # Suggestions only
    SEMI_AUTO = "semi_auto"     # Auto routine, human critical
    FULL_AUTO = "full_auto"     # Full automation with oversight


@dataclass
class DMPersonality:
    """DM's personality and style"""
    # Storytelling style
    narrative_style: str = "descriptive"  # "descriptive", "cinematic", "tactical", "humorous"
    pacing_preference: str = "balanced"   # "fast", "balanced", "slow"
    detail_level: float = 0.6            # 0=sparse, 1=very detailed
    
    # Interaction style
    npc_interaction: str = "immersive"   # "immersive", "practical", "theatrical"
    rule_strictness: float = 0.7         # 0=lenient, 1=strict RAW
    player_agency: float = 0.8           # 0=railroaded, 1=open sandbox
    
    # Challenge balance
    combat_difficulty: float = 0.6       # 0=easy, 1=deadly
    puzzle_complexity: float = 0.5       # 0=simple, 1=complex
    social_challenge: float = 0.5        # 0=easy persuasion, 1=hard
    
    # Personality traits
    humor_level: float = 0.4             # 0=serious, 1=comedic
    drama_level: float = 0.6             # 0=low-key, 1=dramatic
    mystery_level: float = 0.5           # 0=straightforward, 1=mysterious


@dataclass
class DMContext:
    """Context for DM decision-making"""
    # Current situation
    situation_type: str  # "combat", "social", "exploration", "rest"
    scene_description: str
    active_characters: List[str]
    
    # Story state
    current_quest: Optional[str] = None
    story_arc: Optional[str] = None
    session_goals: List[str] = field(default_factory=list)
    
    # Recent events
    recent_actions: List[str] = field(default_factory=list)
    recent_rolls: List[Dict[str, Any]] = field(default_factory=list)
    
    # Player state
    party_hp_avg: float = 1.0
    party_resources_avg: float = 1.0
    player_engagement: float = 0.7  # 0=bored, 1=engaged
    
    # Time
    in_game_time: str = "day"
    session_time_remaining: Optional[int] = None  # minutes
    
    # Flags
    is_critical_moment: bool = False
    needs_human_dm: bool = False


@dataclass
class DMResponse:
    """A response from the DM automation"""
    response_id: str
    response_type: DMResponseType
    content: str
    
    # Confidence
    confidence: float = 0.0
    automation_level: DMAutomationLevel = DMAutomationLevel.MANUAL
    
    # Suggestions
    alternative_responses: List[str] = field(default_factory=list)
    suggested_npcs: List[str] = field(default_factory=list)
    suggested_encounters: List[str] = field(default_factory=list)
    
    # Metadata
    requires_human_approval: bool = False
    reasoning: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class DMAutomation:
    """
    DM Automation System
    
    Acts as the DM's digital twin, handling routine tasks and providing
    suggestions for complex situations. Can operate at different automation
    levels based on DM preference and situation criticality.
    """
    
    def __init__(
        self,
        personality: Optional[DMPersonality] = None,
        automation_level: DMAutomationLevel = DMAutomationLevel.SEMI_AUTO
    ):
        """
        Initialize DM automation
        
        Args:
            personality: DM personality configuration
            automation_level: How much to automate
        """
        self.personality = personality or DMPersonality()
        self.automation_level = automation_level
        
        # Story state
        self.story_state = {
            "current_location": "Unknown",
            "active_quests": [],
            "completed_quests": [],
            "known_npcs": {},
            "world_events": [],
            "session_count": 0
        }
        
        # Response history
        self.response_history: List[DMResponse] = []
        
        # Templates
        self.response_templates = self._load_response_templates()
        
        # Statistics
        self.stats = {
            "total_responses": 0,
            "auto_responses": 0,
            "human_overrides": 0,
            "avg_confidence": 0.0
        }
        
        logger.info(f"DMAutomation initialized at {automation_level.value} level")
    
    def _load_response_templates(self) -> Dict[str, List[str]]:
        """Load response templates for different situations"""
        return {
            "combat_start": [
                "Roll for initiative! {enemies} appear before you.",
                "The battle begins as {enemies} {action}!",
                "You hear a war cry as {enemies} charge toward you!",
            ],
            "combat_hit": [
                "Your attack strikes true, dealing {damage} damage!",
                "A devastating blow! You deal {damage} damage to {target}.",
                "Your weapon finds its mark - {damage} damage!",
            ],
            "combat_miss": [
                "Your attack misses as {target} {action}.",
                "The blow goes wide, missing {target} by inches.",
                "{target} deftly avoids your attack.",
            ],
            "npc_greeting": [
                "{npc} looks up and says, \"{greeting}\"",
                "\"{greeting}\" {npc} greets you with a {expression}.",
                "{npc} notices you and {action}, saying \"{greeting}\"",
            ],
            "discovery": [
                "You discover {item}!",
                "Your search reveals {item}.",
                "Something catches your eye: {item}.",
            ],
            "atmosphere": [
                "The air grows {feeling} as you {action}.",
                "You notice {detail} in the {location}.",
                "The atmosphere is {mood}.",
            ]
        }
    
    async def generate_response(
        self,
        context: DMContext,
        response_type: DMResponseType,
        prompt: Optional[str] = None
    ) -> DMResponse:
        """
        Generate a DM response based on context
        
        Args:
            context: Current game context
            response_type: Type of response needed
            prompt: Optional specific prompt
            
        Returns:
            DMResponse with content and metadata
        """
        start_time = time.time()
        
        # Check if we need human DM
        needs_human = self._needs_human_dm(context, response_type)
        
        # Determine response strategy
        if needs_human and self.automation_level != DMAutomationLevel.FULL_AUTO:
            # Generate suggestions only
            response = await self._generate_suggestions(context, response_type, prompt)
            response.requires_human_approval = True
            response.automation_level = DMAutomationLevel.ASSISTED
        
        elif self.automation_level == DMAutomationLevel.MANUAL:
            # No automation, only suggestions
            response = await self._generate_suggestions(context, response_type, prompt)
            response.requires_human_approval = True
            response.automation_level = DMAutomationLevel.MANUAL
        
        else:
            # Generate automated response
            response = await self._generate_automated_response(
                context, response_type, prompt
            )
            response.automation_level = self.automation_level
        
        # Record response
        self.response_history.append(response)
        self.stats["total_responses"] += 1
        
        if not response.requires_human_approval:
            self.stats["auto_responses"] += 1
        
        time_taken = (time.time() - start_time) * 1000
        logger.debug(
            f"Generated {response_type.value} response in {time_taken:.1f}ms "
            f"(confidence={response.confidence:.2f})"
        )
        
        return response
    
    def _needs_human_dm(
        self,
        context: DMContext,
        response_type: DMResponseType
    ) -> bool:
        """Determine if situation requires human DM"""
        
        # Critical moments always need human
        if context.is_critical_moment or context.needs_human_dm:
            return True
        
        # Major story beats need human
        if response_type in [DMResponseType.ENCOUNTER, DMResponseType.CONSEQUENCE]:
            if context.current_quest and "boss" in context.current_quest.lower():
                return True
        
        # Low party resources need human oversight
        if context.party_hp_avg < 0.3 or context.party_resources_avg < 0.2:
            return True
        
        # Low player engagement might need human creativity
        if context.player_engagement < 0.4:
            return True
        
        return False
    
    async def _generate_automated_response(
        self,
        context: DMContext,
        response_type: DMResponseType,
        prompt: Optional[str]
    ) -> DMResponse:
        """Generate an automated DM response"""
        
        # Select appropriate generation method
        if response_type == DMResponseType.NARRATION:
            content, confidence = self._generate_narration(context, prompt)
        
        elif response_type == DMResponseType.NPC_DIALOGUE:
            content, confidence = self._generate_npc_dialogue(context, prompt)
        
        elif response_type == DMResponseType.ENCOUNTER:
            content, confidence = self._generate_encounter(context, prompt)
        
        elif response_type == DMResponseType.CONSEQUENCE:
            content, confidence = self._generate_consequence(context, prompt)
        
        elif response_type == DMResponseType.ATMOSPHERE:
            content, confidence = self._generate_atmosphere(context)
        
        else:
            # Generic response
            content = f"[{response_type.value}] {prompt or 'Something happens...'}"
            confidence = 0.5
        
        # Create response
        response = DMResponse(
            response_id=f"dm_{time.time()}",
            response_type=response_type,
            content=content,
            confidence=confidence,
            reasoning=f"Generated from {response_type.value} template"
        )
        
        # Add alternatives if confidence is low
        if confidence < 0.7:
            response.alternative_responses = await self._generate_alternatives(
                context, response_type, prompt
            )
        
        return response
    
    def _generate_narration(
        self,
        context: DMContext,
        prompt: Optional[str]
    ) -> Tuple[str, float]:
        """Generate narrative description"""
        
        if prompt:
            # Specific narration requested
            base = prompt
            confidence = 0.7
        else:
            # General scene description
            base = f"You find yourselves in {context.scene_description}."
            confidence = 0.6
        
        # Add detail based on DM personality
        if self.personality.detail_level > 0.7:
            details = [
                "The air is thick with anticipation.",
                "Shadows dance on the walls.",
                "You hear distant sounds echoing."
            ]
            base += f" {random.choice(details)}"
            confidence += 0.1
        
        # Add atmosphere if dramatic DM
        if self.personality.drama_level > 0.6:
            base = self._add_dramatic_flair(base)
            confidence += 0.05
        
        return base, min(confidence, 0.95)
    
    def _generate_npc_dialogue(
        self,
        context: DMContext,
        prompt: Optional[str]
    ) -> Tuple[str, float]:
        """Generate NPC dialogue"""
        
        if not prompt:
            return "The NPC looks at you expectantly.", 0.4
        
        # Parse NPC name from prompt
        npc_name = "the NPC"
        if ":" in prompt:
            npc_name, dialogue = prompt.split(":", 1)
            dialogue = dialogue.strip()
        else:
            dialogue = prompt
        
        # Style based on DM personality
        if self.personality.npc_interaction == "theatrical":
            response = f"{npc_name} proclaims dramatically: \"{dialogue}\""
            confidence = 0.75
        elif self.personality.npc_interaction == "immersive":
            response = f"{npc_name} says, \"{dialogue}\""
            confidence = 0.8
        else:  # practical
            response = f"{npc_name}: \"{dialogue}\""
            confidence = 0.85
        
        return response, confidence
    
    def _generate_encounter(
        self,
        context: DMContext,
        prompt: Optional[str]
    ) -> Tuple[str, float]:
        """Generate encounter description"""
        
        if not prompt:
            return "An encounter begins!", 0.3
        
        # Use combat start templates
        templates = self.response_templates.get("combat_start", [])
        template = random.choice(templates)
        
        # Format with context
        content = template.format(
            enemies=prompt,
            action=random.choice(["attack", "advance", "roar menacingly", "charge"])
        )
        
        # Add initiative call if not already there
        if "initiative" not in content.lower():
            content += " Roll for initiative!"
        
        confidence = 0.8
        
        return content, confidence
    
    def _generate_consequence(
        self,
        context: DMContext,
        prompt: Optional[str]
    ) -> Tuple[str, float]:
        """Generate action consequences"""
        
        if not prompt:
            return "The action has an effect.", 0.3
        
        # Check recent actions for context
        if context.recent_rolls:
            last_roll = context.recent_rolls[-1]
            roll_value = last_roll.get("value", 10)
            
            if roll_value >= 20:
                prefix = "Critical success! "
                confidence = 0.85
            elif roll_value >= 15:
                prefix = "Your action succeeds. "
                confidence = 0.9
            elif roll_value >= 10:
                prefix = "You manage to "
                confidence = 0.85
            else:
                prefix = "You attempt to "
                confidence = 0.8
        else:
            prefix = ""
            confidence = 0.6
        
        content = prefix + prompt
        
        return content, confidence
    
    def _generate_atmosphere(
        self,
        context: DMContext
    ) -> Tuple[str, float]:
        """Generate atmospheric description"""
        
        templates = self.response_templates.get("atmosphere", [])
        template = random.choice(templates)
        
        # Context-based details
        feelings = ["tense", "mysterious", "calm", "ominous", "peaceful"]
        moods = ["tense", "relaxed", "charged", "heavy", "light"]
        
        content = template.format(
            feeling=random.choice(feelings),
            mood=random.choice(moods),
            action=random.choice(["proceed", "wait", "look around"]),
            detail=random.choice(["flickering torchlight", "distant sounds", "strange shadows"]),
            location=context.scene_description or "area"
        )
        
        confidence = 0.7
        
        return content, confidence
    
    def _add_dramatic_flair(self, text: str) -> str:
        """Add dramatic elements to text"""
        dramatic_elements = [
            "Suddenly, ",
            "Without warning, ",
            "In that moment, ",
            "To your surprise, "
        ]
        
        if random.random() < self.personality.drama_level:
            return random.choice(dramatic_elements) + text.lower()
        
        return text
    
    async def _generate_suggestions(
        self,
        context: DMContext,
        response_type: DMResponseType,
        prompt: Optional[str]
    ) -> DMResponse:
        """Generate suggestions for human DM"""
        
        # Generate multiple options
        suggestions = []
        
        for i in range(3):
            content, _ = self._generate_narration(context, prompt)
            suggestions.append(content)
        
        # Create response with suggestions
        response = DMResponse(
            response_id=f"dm_suggest_{time.time()}",
            response_type=response_type,
            content=suggestions[0],  # Best suggestion
            confidence=0.5,
            alternative_responses=suggestions[1:],
            reasoning="Generated suggestions for human DM review"
        )
        
        return response
    
    async def _generate_alternatives(
        self,
        context: DMContext,
        response_type: DMResponseType,
        prompt: Optional[str]
    ) -> List[str]:
        """Generate alternative responses"""
        alternatives = []
        
        for _ in range(2):
            if response_type == DMResponseType.NARRATION:
                content, _ = self._generate_narration(context, prompt)
            else:
                content = f"Alternative {response_type.value} response"
            
            alternatives.append(content)
        
        return alternatives
    
    def update_story_state(
        self,
        key: str,
        value: Any
    ) -> None:
        """Update story state tracking"""
        self.story_state[key] = value
        logger.debug(f"Updated story state: {key} = {value}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get DM automation statistics"""
        if self.stats["total_responses"] > 0:
            self.stats["avg_confidence"] = sum(
                r.confidence for r in self.response_history
            ) / len(self.response_history)
            
            self.stats["auto_rate"] = (
                self.stats["auto_responses"] / self.stats["total_responses"]
            )
        
        return self.stats.copy()


# Test code
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    async def test_dm_automation():
        print("Testing DM Automation System...\n")
        
        # Create DM with personality
        print("=== Test 1: Create DM with Personality ===")
        personality = DMPersonality(
            narrative_style="cinematic",
            detail_level=0.8,
            drama_level=0.7,
            humor_level=0.3
        )
        
        dm = DMAutomation(
            personality=personality,
            automation_level=DMAutomationLevel.SEMI_AUTO
        )
        print(f"DM created with {dm.automation_level.value} automation")
        print()
        
        # Test narration
        print("=== Test 2: Generate Narration ===")
        context = DMContext(
            situation_type="exploration",
            scene_description="a dark cavern",
            active_characters=["Thorin", "Elara"],
            player_engagement=0.8
        )
        
        response = await dm.generate_response(
            context=context,
            response_type=DMResponseType.NARRATION,
            prompt="The party enters the cavern"
        )
        
        print(f"Response: {response.content}")
        print(f"Confidence: {response.confidence:.2f}")
        print(f"Requires approval: {response.requires_human_approval}")
        print()
        
        # Test NPC dialogue
        print("=== Test 3: Generate NPC Dialogue ===")
        response = await dm.generate_response(
            context=context,
            response_type=DMResponseType.NPC_DIALOGUE,
            prompt="Guard: Who goes there?"
        )
        
        print(f"Response: {response.content}")
        print(f"Confidence: {response.confidence:.2f}")
        print()
        
        # Test encounter
        print("=== Test 4: Generate Encounter ===")
        combat_context = DMContext(
            situation_type="combat",
            scene_description="forest clearing",
            active_characters=["Thorin", "Elara"],
            party_hp_avg=0.9
        )
        
        response = await dm.generate_response(
            context=combat_context,
            response_type=DMResponseType.ENCOUNTER,
            prompt="three orcs"
        )
        
        print(f"Response: {response.content}")
        print(f"Confidence: {response.confidence:.2f}")
        print()
        
        # Test critical situation (needs human)
        print("=== Test 5: Critical Situation (Human Needed) ===")
        critical_context = DMContext(
            situation_type="combat",
            scene_description="boss chamber",
            active_characters=["Thorin", "Elara"],
            party_hp_avg=0.2,  # Low HP
            is_critical_moment=True
        )
        
        response = await dm.generate_response(
            context=critical_context,
            response_type=DMResponseType.ENCOUNTER,
            prompt="the dragon awakens"
        )
        
        print(f"Response: {response.content}")
        print(f"Requires human: {response.requires_human_approval}")
        print(f"Alternatives: {len(response.alternative_responses)}")
        print()
        
        # Test atmosphere
        print("=== Test 6: Generate Atmosphere ===")
        response = await dm.generate_response(
            context=context,
            response_type=DMResponseType.ATMOSPHERE
        )
        
        print(f"Response: {response.content}")
        print()
        
        # Get statistics
        print("=== Test 7: Statistics ===")
        stats = dm.get_stats()
        print(f"Total responses: {stats['total_responses']}")
        print(f"Auto responses: {stats['auto_responses']}")
        print(f"Average confidence: {stats['avg_confidence']:.2f}")
        print()
        
        print("✅ All DM automation tests completed!")
    
    asyncio.run(test_dm_automation())
