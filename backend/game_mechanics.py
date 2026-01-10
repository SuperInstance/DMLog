"""
AI Society D&D - Game Mechanics & Combat System
================================================
Implements D&D 5e rules for:
- Combat rounds (initiative, actions, attacks)
- Skill checks
- Saving throws
- Spell casting
- Environmental interactions
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import random


# ============================================================================
# COMBAT SYSTEM
# ============================================================================

class ActionType(Enum):
    """Types of actions in D&D"""
    ACTION = "action"              # Standard action (attack, cast spell, dash, etc.)
    BONUS_ACTION = "bonus_action"  # Bonus action (second wind, off-hand attack, etc.)
    REACTION = "reaction"          # Reaction (opportunity attack, shield spell, etc.)
    MOVEMENT = "movement"          # Movement
    FREE_ACTION = "free_action"    # Dropping item, shouting, etc.


@dataclass
class CombatAction:
    """A single action taken in combat"""
    actor_id: str
    action_type: ActionType
    description: str
    target_id: Optional[str] = None
    
    # Results
    roll: Optional[int] = None
    success: bool = False
    damage: int = 0
    effects: List[str] = field(default_factory=list)
    
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CombatParticipant:
    """Participant in combat"""
    character_id: str
    name: str
    initiative: int = 0
    is_alive: bool = True
    is_npc: bool = False
    
    # Turn state
    has_taken_action: bool = False
    has_taken_bonus_action: bool = False
    has_taken_reaction: bool = False
    movement_remaining: int = 30  # feet
    
    def reset_turn(self):
        """Reset at start of turn"""
        self.has_taken_action = False
        self.has_taken_bonus_action = False
        # Reaction resets at start of your turn
        self.movement_remaining = 30  # Would come from character stats


class CombatEncounter:
    """
    Manages a single combat encounter.
    Handles turn order, actions, and state tracking.
    """
    
    def __init__(self, encounter_id: str, description: str):
        self.encounter_id = encounter_id
        self.description = description
        
        # Participants
        self.participants: Dict[str, CombatParticipant] = {}
        self.turn_order: List[str] = []  # Ordered by initiative
        
        # Combat state
        self.round_number: int = 0
        self.current_turn_index: int = 0
        self.is_active: bool = False
        
        # History
        self.action_log: List[CombatAction] = []
        
        # Dice roller
        from enhanced_character import DiceRoller
        self.dice = DiceRoller()
    
    def add_participant(self, character_id: str, name: str, is_npc: bool = False):
        """Add character to combat"""
        participant = CombatParticipant(
            character_id=character_id,
            name=name,
            is_npc=is_npc
        )
        self.participants[character_id] = participant
    
    def roll_initiative(self, character_id: str, dex_modifier: int) -> int:
        """Roll initiative for a character"""
        roll = self.dice.roll(20) + dex_modifier
        if character_id in self.participants:
            self.participants[character_id].initiative = roll
        return roll
    
    def start_combat(self):
        """Begin combat, sort by initiative"""
        # Sort participants by initiative (highest first)
        sorted_participants = sorted(
            self.participants.items(),
            key=lambda x: x[1].initiative,
            reverse=True
        )
        self.turn_order = [char_id for char_id, _ in sorted_participants]
        
        self.is_active = True
        self.round_number = 1
        self.current_turn_index = 0
        
        return {
            "message": "Combat begins!",
            "turn_order": [
                {
                    "name": self.participants[cid].name,
                    "initiative": self.participants[cid].initiative
                }
                for cid in self.turn_order
            ]
        }
    
    def get_current_turn(self) -> Optional[CombatParticipant]:
        """Get whose turn it is"""
        if not self.is_active or not self.turn_order:
            return None
        return self.participants[self.turn_order[self.current_turn_index]]
    
    def next_turn(self):
        """Advance to next turn"""
        if not self.is_active:
            return None
        
        # Reset current participant
        current = self.get_current_turn()
        if current:
            current.reset_turn()
        
        # Move to next
        self.current_turn_index += 1
        
        # Check if round is over
        if self.current_turn_index >= len(self.turn_order):
            self.current_turn_index = 0
            self.round_number += 1
            return {
                "message": f"Round {self.round_number} begins!",
                "round": self.round_number
            }
        
        next_participant = self.get_current_turn()
        return {
            "message": f"It's {next_participant.name}'s turn.",
            "current_turn": next_participant.name
        }
    
    def perform_attack(
        self,
        attacker_id: str,
        target_id: str,
        weapon: str,
        attack_bonus: int,
        damage_dice: str = "1d8",
        damage_bonus: int = 0
    ) -> Dict[str, Any]:
        """
        Perform an attack action.
        Returns: {success, attack_roll, damage, message}
        """
        if attacker_id not in self.participants:
            return {"success": False, "message": "Attacker not in combat"}
        if target_id not in self.participants:
            return {"success": False, "message": "Target not in combat"}
        
        attacker = self.participants[attacker_id]
        target = self.participants[target_id]
        
        # Roll attack (d20 + attack bonus)
        attack_roll = self.dice.roll(20) + attack_bonus
        
        # Compare to target AC (would come from character stats)
        target_ac = 13  # Placeholder
        hit = attack_roll >= target_ac
        
        damage = 0
        if hit:
            # Roll damage
            dice_parts = damage_dice.split('d')
            count = int(dice_parts[0])
            sides = int(dice_parts[1])
            damage = self.dice.roll(sides, count, damage_bonus)
        
        # Log action
        action = CombatAction(
            actor_id=attacker_id,
            action_type=ActionType.ACTION,
            description=f"{attacker.name} attacks {target.name} with {weapon}",
            target_id=target_id,
            roll=attack_roll,
            success=hit,
            damage=damage
        )
        self.action_log.append(action)
        
        # Mark action used
        attacker.has_taken_action = True
        
        result = {
            "success": hit,
            "attack_roll": attack_roll,
            "damage": damage,
            "message": f"{attacker.name} {'hits' if hit else 'misses'} {target.name}"
        }
        
        if hit:
            result["message"] += f" for {damage} damage!"
        
        return result
    
    def check_combat_end(self) -> Optional[str]:
        """Check if combat should end. Returns winner side or None."""
        # Simple check: if all NPCs dead or all PCs dead
        npcs_alive = any(p.is_alive and p.is_npc for p in self.participants.values())
        pcs_alive = any(p.is_alive and not p.is_npc for p in self.participants.values())
        
        if not npcs_alive and pcs_alive:
            return "players"
        elif not pcs_alive and npcs_alive:
            return "enemies"
        elif not pcs_alive and not npcs_alive:
            return "draw"
        
        return None
    
    def end_combat(self):
        """End combat"""
        self.is_active = False
        winner = self.check_combat_end()
        
        return {
            "message": "Combat has ended!",
            "winner": winner,
            "rounds": self.round_number,
            "total_actions": len(self.action_log)
        }


# ============================================================================
# SKILL CHECKS & ABILITY CHECKS
# ============================================================================

class SkillCheck:
    """Handle D&D skill checks"""
    
    SKILLS = {
        # Strength
        "athletics": "strength",
        
        # Dexterity
        "acrobatics": "dexterity",
        "sleight_of_hand": "dexterity",
        "stealth": "dexterity",
        
        # Intelligence
        "arcana": "intelligence",
        "history": "intelligence",
        "investigation": "intelligence",
        "nature": "intelligence",
        "religion": "intelligence",
        
        # Wisdom
        "animal_handling": "wisdom",
        "insight": "wisdom",
        "medicine": "wisdom",
        "perception": "wisdom",
        "survival": "wisdom",
        
        # Charisma
        "deception": "charisma",
        "intimidation": "charisma",
        "performance": "charisma",
        "persuasion": "charisma"
    }
    
    @staticmethod
    def make_check(
        skill: str,
        ability_scores: Dict[str, int],
        proficiency_bonus: int = 0,
        is_proficient: bool = False,
        advantage: bool = False,
        disadvantage: bool = False
    ) -> Dict[str, Any]:
        """
        Make a skill check.
        Returns: {total, roll, modifier, success, description}
        """
        from enhanced_character import DiceRoller
        dice = DiceRoller()
        
        # Get ability for this skill
        ability = SkillCheck.SKILLS.get(skill.lower(), "strength")
        ability_score = ability_scores.get(ability, 10)
        ability_modifier = (ability_score - 10) // 2
        
        # Add proficiency if proficient
        total_modifier = ability_modifier
        if is_proficient:
            total_modifier += proficiency_bonus
        
        # Roll d20
        if advantage:
            roll, rolls = dice.roll_with_advantage()
        elif disadvantage:
            roll, rolls = dice.roll_with_disadvantage()
        else:
            roll = dice.roll(20)
            rolls = [roll]
        
        total = roll + total_modifier
        
        return {
            "skill": skill,
            "ability": ability,
            "roll": roll,
            "rolls": rolls,
            "modifier": total_modifier,
            "total": total,
            "advantage": advantage,
            "disadvantage": disadvantage,
            "description": f"{skill.title()} check: {roll} + {total_modifier} = {total}"
        }


# ============================================================================
# SPELL CASTING
# ============================================================================

@dataclass
class Spell:
    """D&D spell"""
    name: str
    level: int  # 0 = cantrip
    school: str  # evocation, abjuration, etc.
    casting_time: str  # "1 action", "1 bonus action", etc.
    range: str  # "60 feet", "Touch", "Self", etc.
    components: List[str]  # ["V", "S", "M"]
    duration: str
    description: str
    
    # Effects
    damage_dice: Optional[str] = None
    damage_type: Optional[str] = None
    save_ability: Optional[str] = None  # "dexterity", "wisdom", etc.
    save_dc: int = 0


class SpellCasting:
    """Handle spell casting mechanics"""
    
    @staticmethod
    def cast_spell(
        spell: Spell,
        caster_id: str,
        target_id: Optional[str],
        spell_attack_bonus: int = 0,
        spell_save_dc: int = 13
    ) -> Dict[str, Any]:
        """
        Cast a spell.
        Returns results dictionary.
        """
        from enhanced_character import DiceRoller
        dice = DiceRoller()
        
        result = {
            "spell": spell.name,
            "caster": caster_id,
            "target": target_id,
            "success": False,
            "damage": 0
        }
        
        # Attack spell (requires attack roll)
        if spell.damage_dice and not spell.save_ability:
            attack_roll = dice.roll(20) + spell_attack_bonus
            # Would check against target AC
            target_ac = 13  # Placeholder
            hit = attack_roll >= target_ac
            
            if hit:
                dice_parts = spell.damage_dice.split('d')
                count = int(dice_parts[0])
                sides = int(dice_parts[1])
                damage = dice.roll(sides, count)
                result["success"] = True
                result["damage"] = damage
                result["attack_roll"] = attack_roll
        
        # Save spell (target makes saving throw)
        elif spell.save_ability:
            # Target would roll saving throw
            save_roll = dice.roll(20)  # + target modifier
            result["save_roll"] = save_roll
            result["success"] = save_roll < spell_save_dc
            
            if result["success"] and spell.damage_dice:
                dice_parts = spell.damage_dice.split('d')
                count = int(dice_parts[0])
                sides = int(dice_parts[1])
                damage = dice.roll(sides, count)
                result["damage"] = damage
        
        return result


# ============================================================================
# ENVIRONMENTAL INTERACTIONS
# ============================================================================

class EnvironmentInteraction:
    """Handle environmental checks and interactions"""
    
    @staticmethod
    def search_room(
        perception_bonus: int,
        investigation_bonus: int,
        dc: int = 15
    ) -> Dict[str, Any]:
        """Search a room for hidden objects"""
        from enhanced_character import DiceRoller
        dice = DiceRoller()
        
        perception_roll = dice.roll(20) + perception_bonus
        investigation_roll = dice.roll(20) + investigation_bonus
        
        found_with_perception = perception_roll >= dc
        found_with_investigation = investigation_roll >= dc
        
        return {
            "perception_check": perception_roll,
            "investigation_check": investigation_roll,
            "found": found_with_perception or found_with_investigation,
            "method": "perception" if found_with_perception else "investigation" if found_with_investigation else None
        }
    
    @staticmethod
    def break_door(
        strength_bonus: int,
        dc: int = 20
    ) -> Dict[str, Any]:
        """Attempt to break down a door"""
        from enhanced_character import DiceRoller
        dice = DiceRoller()
        
        roll = dice.roll(20) + strength_bonus
        success = roll >= dc
        
        return {
            "roll": roll,
            "dc": dc,
            "success": success,
            "message": f"{'Successfully broke' if success else 'Failed to break'} the door (rolled {roll} vs DC {dc})"
        }


# ============================================================================
# GAME MASTER UTILITIES
# ============================================================================

class DMTools:
    """Utility functions for the Dungeon Master"""
    
    @staticmethod
    def generate_encounter(
        party_level: int,
        party_size: int,
        difficulty: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate an encounter appropriate for the party.
        Difficulty: easy, medium, hard, deadly
        """
        # XP thresholds per character level (5e DMG)
        xp_thresholds = {
            1: {"easy": 25, "medium": 50, "hard": 75, "deadly": 100},
            2: {"easy": 50, "medium": 100, "hard": 150, "deadly": 200},
            3: {"easy": 75, "medium": 150, "hard": 225, "deadly": 400},
            # ... would continue for all levels
        }
        
        threshold = xp_thresholds.get(party_level, {}).get(difficulty, 100)
        total_xp = threshold * party_size
        
        return {
            "party_level": party_level,
            "party_size": party_size,
            "difficulty": difficulty,
            "target_xp": total_xp,
            "suggestion": f"Encounter should be worth approximately {total_xp} XP total"
        }
    
    @staticmethod
    def calculate_xp_reward(
        monster_cr: float,
        quantity: int = 1
    ) -> int:
        """Calculate XP reward for defeated monsters"""
        # CR to XP mapping (5e DMG)
        cr_xp = {
            0: 10,
            0.125: 25,
            0.25: 50,
            0.5: 100,
            1: 200,
            2: 450,
            3: 700,
            4: 1100,
            5: 1800,
            # ... would continue
        }
        
        xp_per_monster = cr_xp.get(monster_cr, 100)
        return xp_per_monster * quantity
