"""
DM Automation System (Phase 6)

Enhanced digital twin for the Dungeon Master with automated responses, NPC management,
story generation, and encounter design. Integrates with escalation engine and chat system.

Key Features:
- DM digital twin with personality
- Automated response generation
- Context-aware suggestions
- Story beat tracking
- NPC management and dialogue
- Encounter balancing
- Rule adjudication
- Integration with chat system
"""

import time
import asyncio
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DMMode(Enum):
    """DM automation modes"""
    MANUAL = "manual"           # Human DM only
    ASSISTED = "assisted"       # AI suggestions, human approval
    AUTOMATED = "automated"     # AI handles routine, human for critical
    FULL_AUTO = "full_auto"     # AI handles everything


class DMTaskType(Enum):
    """Types of DM tasks"""
    NARRATION = "narration"           # Scene descriptions
    NPC_DIALOGUE = "npc_dialogue"     # NPC speech
    COMBAT = "combat"                 # Combat management
    EXPLORATION = "exploration"       # Location descriptions
    PUZZLE = "puzzle"                 # Puzzle/riddle management
    SOCIAL = "social"                 # Social encounters
    LOOT = "loot"                     # Treasure distribution
    RULES = "rules"                   # Rule adjudication
    STORY = "story"                   # Story progression


class StoryBeat(Enum):
    """Story progression beats"""
    INTRODUCTION = "introduction"
    CALL_TO_ACTION = "call_to_action"
    RISING_ACTION = "rising_action"
    COMPLICATION = "complication"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    DENOUEMENT = "denouement"


@dataclass
class DMPersonality:
    """DM personality configuration"""
    # Descriptive style
    description_detail: float = 0.7    # 0=sparse, 1=very detailed
    combat_pacing: float = 0.6         # 0=slow, 1=fast
    
    # Tone
    humor_level: float = 0.5           # 0=serious, 1=comedic
    darkness_level: float = 0.5        # 0=lighthearted, 1=dark
    epic_scale: float = 0.6            # 0=grounded, 1=epic
    
    # Challenge
    difficulty: float = 0.6            # 0=easy, 1=deadly
    forgiveness: float = 0.5           # 0=harsh, 1=forgiving
    
    # Storytelling
    plot_focus: str = "balanced"       # "combat", "roleplay", "exploration", "balanced"
    improvisation: float = 0.7         # 0=strict to plan, 1=fully improvised
    player_agency: float = 0.8         # 0=railroaded, 1=total freedom


@dataclass
class StoryContext:
    """Current story context"""
    campaign_name: str
    session_number: int
    current_beat: StoryBeat
    
    # Location
    current_location: str
    location_type: str  # "dungeon", "city", "wilderness", "social"
    
    # Tension
    tension_level: float = 0.5         # 0=relaxed, 1=intense
    pacing: float = 0.5                # 0=slow, 1=fast
    
    # Plot threads
    active_plot_threads: List[str] = field(default_factory=list)
    completed_objectives: List[str] = field(default_factory=list)
    pending_revelations: List[str] = field(default_factory=list)
    
    # Recent events
    recent_events: List[str] = field(default_factory=list)
    last_major_event: Optional[str] = None


@dataclass
class DMResponse:
    """DM response to a situation"""
    response_text: str
    task_type: DMTaskType
    confidence: float
    
    # Alternatives
    alternatives: List[str] = field(default_factory=list)
    
    # Actions
    requires_roll: bool = False
    roll_dc: Optional[int] = None
    roll_type: Optional[str] = None
    
    # NPCs involved
    npc_speakers: List[str] = field(default_factory=list)
    
    # Story impact
    advances_plot: bool = False
    changes_tension: float = 0.0
    
    # Metadata
    generation_time_ms: float = 0.0
    source: str = "auto"  # "auto", "suggested", "manual"


class DMDigitalTwin:
    """
    DM Digital Twin
    
    AI assistant for the Dungeon Master. Can generate responses, suggest
    actions, manage NPCs, and automate routine DM tasks while maintaining
    the DM's style and preferences.
    """
    
    def __init__(
        self,
        personality: Optional[DMPersonality] = None,
        mode: DMMode = DMMode.ASSISTED
    ):
        """
        Initialize DM digital twin
        
        Args:
            personality: DM personality configuration
            mode: Automation mode
        """
        self.personality = personality or DMPersonality()
        self.mode = mode
        
        # Story context
        self.story_context: Optional[StoryContext] = None
        
        # Response history
        self.response_history: List[DMResponse] = []
        
        # Task handlers (would connect to LLM in real implementation)
        self.task_handlers: Dict[DMTaskType, callable] = {
            DMTaskType.NARRATION: self._generate_narration,
            DMTaskType.NPC_DIALOGUE: self._generate_npc_dialogue,
            DMTaskType.COMBAT: self._handle_combat,
            DMTaskType.EXPLORATION: self._generate_exploration,
            DMTaskType.RULES: self._adjudicate_rules,
        }
        
        # Templates for common responses
        self._load_response_templates()
        
        logger.info(f"DMDigitalTwin initialized in {mode.value} mode")
    
    def _load_response_templates(self) -> None:
        """Load response templates for common situations"""
        self.templates = {
            "combat_start": [
                "Roll for initiative! {enemy_description}",
                "The {enemy_type} spots you and readies for battle! Everyone roll initiative.",
                "Combat begins! {enemy_description} Initiative, please!"
            ],
            "combat_hit": [
                "Your {weapon} strikes true, dealing {damage} damage!",
                "A solid hit! {damage} points of damage to the {target}.",
                "You connect! The {target} takes {damage} damage."
            ],
            "combat_miss": [
                "Your attack goes wide, missing the {target}.",
                "The {target} dodges your strike!",
                "You swing, but the {target} is too quick!"
            ],
            "combat_kill": [
                "The {target} falls! {damage} damage was the final blow.",
                "Your strike fells the {target}!",
                "The {target} collapses, defeated."
            ],
            "exploration_enter": [
                "You enter {location}. {description}",
                "The party arrives at {location}. {description}",
                "You find yourself in {location}. {description}"
            ],
            "exploration_search": [
                "Searching {location}, you find: {findings}",
                "Your search reveals: {findings}",
                "You discover: {findings}"
            ],
            "npc_greeting": [
                "\"{greeting}\" says {npc_name}.",
                "{npc_name} greets you: \"{greeting}\"",
                "\"{greeting}\" {npc_name} says with a {emotion}."
            ],
            "npc_hostile": [
                "\"{threat}\" snarls {npc_name}.",
                "{npc_name} threatens: \"{threat}\"",
                "With a hostile glare, {npc_name} says \"{threat}\""
            ],
            "success": [
                "Success! {result}",
                "You succeed! {result}",
                "Well done! {result}"
            ],
            "failure": [
                "Unfortunately, you fail. {consequence}",
                "That doesn't work. {consequence}",
                "No luck. {consequence}"
            ],
            "skill_check": [
                "Make a {skill} check, DC {dc}.",
                "Roll {skill}, DC {dc}.",
                "{skill} check, DC {dc} please."
            ]
        }
    
    def set_story_context(self, context: StoryContext) -> None:
        """Set current story context"""
        self.story_context = context
        logger.info(
            f"Story context set: {context.campaign_name} "
            f"Session {context.session_number}, {context.current_beat.value}"
        )
    
    async def generate_response(
        self,
        task_type: DMTaskType,
        situation: str,
        context: Optional[Dict[str, Any]] = None
    ) -> DMResponse:
        """
        Generate DM response to a situation
        
        Args:
            task_type: Type of DM task
            situation: Description of the situation
            context: Additional context
            
        Returns:
            DMResponse with generated content
        """
        start_time = time.time()
        
        context = context or {}
        
        # Check if we should auto-handle this task
        if not self._should_auto_handle(task_type):
            # Return placeholder for human DM
            return DMResponse(
                response_text="[Awaiting DM input]",
                task_type=task_type,
                confidence=0.0,
                source="manual"
            )
        
        # Get appropriate handler
        handler = self.task_handlers.get(
            task_type,
            self._generate_generic
        )
        
        # Generate response
        response = await handler(situation, context)
        
        # Add metadata
        response.generation_time_ms = (time.time() - start_time) * 1000
        
        # Store in history
        self.response_history.append(response)
        
        # Update story context if needed
        if response.advances_plot and self.story_context:
            self._update_story_context(response)
        
        logger.debug(
            f"Generated {task_type.value} response: "
            f"{response.confidence:.2f} confidence, "
            f"{response.generation_time_ms:.1f}ms"
        )
        
        return response
    
    def _should_auto_handle(self, task_type: DMTaskType) -> bool:
        """Determine if task should be auto-handled based on mode"""
        if self.mode == DMMode.MANUAL:
            return False
        elif self.mode == DMMode.FULL_AUTO:
            return True
        elif self.mode == DMMode.AUTOMATED:
            # Automate routine tasks, manual for story-critical
            routine_tasks = {
                DMTaskType.COMBAT,
                DMTaskType.EXPLORATION,
                DMTaskType.LOOT,
                DMTaskType.RULES
            }
            return task_type in routine_tasks
        else:  # ASSISTED
            # Generate suggestions for everything
            return True
    
    async def _generate_narration(
        self,
        situation: str,
        context: Dict[str, Any]
    ) -> DMResponse:
        """Generate narrative description"""
        
        detail_level = self.personality.description_detail
        
        if detail_level > 0.7:
            style = "detailed"
        elif detail_level > 0.4:
            style = "moderate"
        else:
            style = "brief"
        
        # Generate based on style
        if style == "detailed":
            response_text = (
                f"The scene unfolds before you in vivid detail: {situation}. "
                f"You notice the subtle play of light and shadow, "
                f"the ambient sounds, and the palpable atmosphere."
            )
        elif style == "moderate":
            response_text = f"You see: {situation}."
        else:
            response_text = situation
        
        return DMResponse(
            response_text=response_text,
            task_type=DMTaskType.NARRATION,
            confidence=0.85,
            source="auto"
        )
    
    async def _generate_npc_dialogue(
        self,
        situation: str,
        context: Dict[str, Any]
    ) -> DMResponse:
        """Generate NPC dialogue"""
        
        npc_name = context.get("npc_name", "NPC")
        npc_personality = context.get("npc_personality", "neutral")
        
        # Template-based generation
        if npc_personality == "hostile":
            template = random.choice(self.templates["npc_hostile"])
            threats = [
                "Leave now, or face the consequences!",
                "You dare enter my domain?",
                "I've killed better than you."
            ]
            threat = random.choice(threats)
            response_text = template.format(npc_name=npc_name, threat=threat)
        else:
            template = random.choice(self.templates["npc_greeting"])
            greetings = {
                "friendly": "Well met, travelers!",
                "neutral": "Hello.",
                "fearful": "P-please, don't hurt me!",
                "cheerful": "Wonderful to see you!"
            }
            emotions = {
                "friendly": "warm smile",
                "neutral": "nod",
                "fearful": "trembling voice",
                "cheerful": "bright grin"
            }
            
            greeting = greetings.get(npc_personality, "Hello.")
            emotion = emotions.get(npc_personality, "neutral expression")
            
            response_text = template.format(
                npc_name=npc_name,
                greeting=greeting,
                emotion=emotion
            )
        
        return DMResponse(
            response_text=response_text,
            task_type=DMTaskType.NPC_DIALOGUE,
            confidence=0.75,
            npc_speakers=[npc_name],
            source="auto"
        )
    
    async def _handle_combat(
        self,
        situation: str,
        context: Dict[str, Any]
    ) -> DMResponse:
        """Handle combat situation"""
        
        action = context.get("action", "attack")
        target = context.get("target", "enemy")
        result = context.get("result", "hit")
        damage = context.get("damage", 0)
        weapon = context.get("weapon", "weapon")
        
        if action == "start":
            template = random.choice(self.templates["combat_start"])
            enemy_type = context.get("enemy_type", "enemy")
            enemy_count = context.get("enemy_count", 1)
            
            if enemy_count == 1:
                enemy_desc = f"A {enemy_type} appears!"
            else:
                enemy_desc = f"{enemy_count} {enemy_type}s appear!"
            
            response_text = template.format(
                enemy_description=enemy_desc,
                enemy_type=enemy_type
            )
            changes_tension = 0.2
            
        elif result == "hit":
            template = random.choice(self.templates["combat_hit"])
            response_text = template.format(
                weapon=weapon,
                damage=damage,
                target=target
            )
            changes_tension = 0.0
            
        elif result == "kill":
            template = random.choice(self.templates["combat_kill"])
            response_text = template.format(
                target=target,
                damage=damage
            )
            changes_tension = -0.1
            
        else:  # miss
            template = random.choice(self.templates["combat_miss"])
            response_text = template.format(target=target)
            changes_tension = 0.05
        
        return DMResponse(
            response_text=response_text,
            task_type=DMTaskType.COMBAT,
            confidence=0.9,
            changes_tension=changes_tension,
            source="auto"
        )
    
    async def _generate_exploration(
        self,
        situation: str,
        context: Dict[str, Any]
    ) -> DMResponse:
        """Generate exploration description"""
        
        action = context.get("action", "enter")
        location = context.get("location", "the area")
        features = context.get("features", [])
        
        if action == "search":
            template = random.choice(self.templates["exploration_search"])
            findings = context.get("findings", "nothing of interest")
            response_text = template.format(
                location=location,
                findings=findings
            )
        else:  # enter
            template = random.choice(self.templates["exploration_enter"])
            
            if features:
                description = f"You notice: {', '.join(features)}."
            else:
                description = "The area is unremarkable."
            
            response_text = template.format(
                location=location,
                description=description
            )
        
        return DMResponse(
            response_text=response_text,
            task_type=DMTaskType.EXPLORATION,
            confidence=0.8,
            source="auto"
        )
    
    async def _adjudicate_rules(
        self,
        situation: str,
        context: Dict[str, Any]
    ) -> DMResponse:
        """Adjudicate rules question"""
        
        # In real implementation, would reference rules database
        rule_type = context.get("rule_type", "general")
        
        if rule_type == "skill_check":
            template = random.choice(self.templates["skill_check"])
            skill = context.get("skill", "ability")
            dc = context.get("dc", 15)
            
            response_text = template.format(skill=skill, dc=dc)
            requires_roll = True
            roll_dc = dc
            roll_type = skill
        else:
            response_text = f"Based on the rules: {situation}"
            requires_roll = False
            roll_dc = None
            roll_type = None
        
        return DMResponse(
            response_text=response_text,
            task_type=DMTaskType.RULES,
            confidence=0.7,
            requires_roll=requires_roll,
            roll_dc=roll_dc,
            roll_type=roll_type,
            source="auto"
        )
    
    async def _generate_generic(
        self,
        situation: str,
        context: Dict[str, Any]
    ) -> DMResponse:
        """Generic response generation"""
        
        return DMResponse(
            response_text=f"DM responds: {situation}",
            task_type=DMTaskType.NARRATION,
            confidence=0.6,
            source="auto"
        )
    
    def _update_story_context(self, response: DMResponse) -> None:
        """Update story context based on response"""
        if not self.story_context:
            return
        
        # Add to recent events
        self.story_context.recent_events.append(response.response_text)
        if len(self.story_context.recent_events) > 10:
            self.story_context.recent_events.pop(0)
        
        # Update tension
        self.story_context.tension_level += response.changes_tension
        self.story_context.tension_level = max(
            0.0,
            min(1.0, self.story_context.tension_level)
        )
    
    def suggest_next_action(self) -> List[str]:
        """Suggest potential next actions/events"""
        if not self.story_context:
            return ["Continue the adventure"]
        
        suggestions = []
        
        # Based on current beat
        if self.story_context.current_beat == StoryBeat.INTRODUCTION:
            suggestions.append("Introduce the main conflict")
            suggestions.append("Present a call to action")
        elif self.story_context.current_beat == StoryBeat.RISING_ACTION:
            suggestions.append("Add a complication")
            suggestions.append("Introduce a new character")
            suggestions.append("Reveal a clue")
        elif self.story_context.current_beat == StoryBeat.CLIMAX:
            suggestions.append("Trigger the final confrontation")
            suggestions.append("Reveal a major secret")
        
        # Based on tension
        if self.story_context.tension_level < 0.3:
            suggestions.append("Increase tension with a challenge")
            suggestions.append("Introduce a time pressure")
        elif self.story_context.tension_level > 0.8:
            suggestions.append("Provide a breather moment")
            suggestions.append("Resolve a minor conflict")
        
        # Based on plot threads
        if self.story_context.pending_revelations:
            suggestions.append(f"Reveal: {self.story_context.pending_revelations[0]}")
        
        return suggestions[:3]  # Top 3 suggestions
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get DM automation statistics"""
        if not self.response_history:
            return {"total_responses": 0}
        
        total = len(self.response_history)
        by_type = {}
        by_source = {"auto": 0, "suggested": 0, "manual": 0}
        
        avg_confidence = sum(r.confidence for r in self.response_history) / total
        avg_time = sum(r.generation_time_ms for r in self.response_history) / total
        
        for response in self.response_history:
            task_type = response.task_type.value
            by_type[task_type] = by_type.get(task_type, 0) + 1
            by_source[response.source] += 1
        
        return {
            "total_responses": total,
            "by_type": by_type,
            "by_source": by_source,
            "avg_confidence": avg_confidence,
            "avg_time_ms": avg_time,
            "automation_rate": by_source["auto"] / total if total > 0 else 0
        }


# Test code
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.DEBUG)
    
    async def test_dm_automation():
        print("Testing DM Automation System (Phase 6)...\n")
        
        # Test 1: Create DM with personality
        print("=== Test 1: DM Initialization ===")
        personality = DMPersonality(
            description_detail=0.8,
            humor_level=0.6,
            difficulty=0.7,
            improvisation=0.8
        )
        
        dm = DMDigitalTwin(
            personality=personality,
            mode=DMMode.AUTOMATED
        )
        
        print(f"DM created in {dm.mode.value} mode")
        print(f"Description detail: {personality.description_detail}")
        print()
        
        # Test 2: Set story context
        print("=== Test 2: Story Context ===")
        context = StoryContext(
            campaign_name="The Lost Mines",
            session_number=3,
            current_beat=StoryBeat.RISING_ACTION,
            current_location="Goblin Cave",
            location_type="dungeon",
            tension_level=0.6,
            active_plot_threads=["Find the missing miners", "Defeat goblin boss"],
            pending_revelations=["The goblins work for a dark cult"],
            recent_events=["Party entered cave", "Encountered goblin scouts"]
        )
        
        dm.set_story_context(context)
        print(f"Context: {context.campaign_name} - {context.current_location}")
        print(f"Tension: {context.tension_level}")
        print()
        
        # Test 3: Generate narration
        print("=== Test 3: Narration ===")
        response = await dm.generate_response(
            task_type=DMTaskType.NARRATION,
            situation="The cave walls glisten with moisture",
            context={}
        )
        print(f"Response: {response.response_text}")
        print(f"Confidence: {response.confidence:.2f}")
        print(f"Time: {response.generation_time_ms:.1f}ms")
        print()
        
        # Test 4: NPC dialogue
        print("=== Test 4: NPC Dialogue ===")
        response = await dm.generate_response(
            task_type=DMTaskType.NPC_DIALOGUE,
            situation="NPC greets party",
            context={
                "npc_name": "Gundren",
                "npc_personality": "friendly"
            }
        )
        print(f"Response: {response.response_text}")
        print(f"NPCs: {response.npc_speakers}")
        print()
        
        response = await dm.generate_response(
            task_type=DMTaskType.NPC_DIALOGUE,
            situation="Hostile NPC threatens",
            context={
                "npc_name": "Goblin Boss",
                "npc_personality": "hostile"
            }
        )
        print(f"Hostile: {response.response_text}")
        print()
        
        # Test 5: Combat
        print("=== Test 5: Combat Management ===")
        response = await dm.generate_response(
            task_type=DMTaskType.COMBAT,
            situation="Combat starts",
            context={
                "action": "start",
                "enemy_type": "goblin",
                "enemy_count": 3
            }
        )
        print(f"Start: {response.response_text}")
        print()
        
        response = await dm.generate_response(
            task_type=DMTaskType.COMBAT,
            situation="Attack hits",
            context={
                "action": "attack",
                "result": "hit",
                "damage": 12,
                "weapon": "longsword",
                "target": "goblin"
            }
        )
        print(f"Hit: {response.response_text}")
        print()
        
        response = await dm.generate_response(
            task_type=DMTaskType.COMBAT,
            situation="Enemy defeated",
            context={
                "action": "attack",
                "result": "kill",
                "damage": 8,
                "target": "goblin"
            }
        )
        print(f"Kill: {response.response_text}")
        print()
        
        # Test 6: Exploration
        print("=== Test 6: Exploration ===")
        response = await dm.generate_response(
            task_type=DMTaskType.EXPLORATION,
            situation="Enter new room",
            context={
                "action": "enter",
                "location": "a large chamber",
                "features": ["ancient pillars", "a glowing altar", "two exits"]
            }
        )
        print(f"Enter: {response.response_text}")
        print()
        
        response = await dm.generate_response(
            task_type=DMTaskType.EXPLORATION,
            situation="Search room",
            context={
                "action": "search",
                "location": "the altar",
                "findings": "a silver key and 50 gold pieces"
            }
        )
        print(f"Search: {response.response_text}")
        print()
        
        # Test 7: Rules
        print("=== Test 7: Rules Adjudication ===")
        response = await dm.generate_response(
            task_type=DMTaskType.RULES,
            situation="Skill check needed",
            context={
                "rule_type": "skill_check",
                "skill": "Perception",
                "dc": 15
            }
        )
        print(f"Response: {response.response_text}")
        print(f"Requires roll: {response.requires_roll}")
        print(f"DC: {response.roll_dc}")
        print()
        
        # Test 8: Suggestions
        print("=== Test 8: Next Action Suggestions ===")
        suggestions = dm.suggest_next_action()
        print("Suggested next actions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
        print()
        
        # Test 9: Statistics
        print("=== Test 9: Statistics ===")
        stats = dm.get_statistics()
        print(f"Total responses: {stats['total_responses']}")
        print(f"By type: {stats['by_type']}")
        print(f"Automation rate: {stats['automation_rate']:.2%}")
        print()
        
        print("✅ All DM automation tests completed!")
    
    asyncio.run(test_dm_automation())
