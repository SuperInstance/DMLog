"""
Combat Bots

Specialized bots for combat decision-making including targeting, positioning,
resource management, and tactical coordination.

Key Features:
- Smart targeting (threat assessment, focus fire)
- Position optimization (cover, flanking, formation)
- Resource management (HP, spells, items)
- Tactical patterns (combos, opportunity attacks)
- Team coordination
"""

import random
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from mechanical_bot import (
    MechanicalBot, BotType, BotParameters, BotPerception,
    BotAction, BotPriority
)


class CombatRole(Enum):
    """Combat roles for positioning and tactics"""
    TANK = "tank"           # Front line, absorb damage
    DAMAGE = "damage"       # Deal damage, medium positioning
    SUPPORT = "support"     # Back line, heal/buff
    CONTROLLER = "controller"  # Crowd control, medium positioning
    SCOUT = "scout"         # Mobile, flanking


@dataclass
class CombatParameters(BotParameters):
    """Extended parameters for combat bots"""
    # Targeting preferences
    target_priority: str = "threat"  # "threat", "weak", "close", "strong"
    focus_fire: bool = True           # Coordinate with allies
    opportunist: float = 0.5         # Take opportunity attacks
    
    # Positioning
    preferred_range: str = "medium"   # "melee", "medium", "ranged"
    cover_seeking: float = 0.5       # 0=ignore cover, 1=always seek
    formation_preference: CombatRole = CombatRole.DAMAGE
    
    # Resources
    hp_heal_threshold: float = 0.5   # Heal when HP below this
    spell_conservation: float = 0.5  # 0=spam spells, 1=very conservative
    potion_threshold: float = 0.3    # Use potion when HP below this
    
    # Tactics
    combo_seeking: bool = True       # Look for ability combos
    defensive_threshold: float = 0.3 # Go defensive when HP below this


class CombatTargetingBot(MechanicalBot):
    """
    Advanced combat targeting bot
    
    Selects optimal targets based on threat assessment, positioning,
    and tactical considerations.
    """
    
    def __init__(self, parameters: CombatParameters):
        super().__init__("combat_targeting", BotType.COMBAT, parameters)
        self.params = parameters
    
    def perceive(self, perception: BotPerception) -> Dict[str, Any]:
        """Extract combat-relevant information"""
        
        enemies = perception.enemies_status
        allies = perception.allies_status
        self_status = perception.self_status
        
        processed = {
            "enemies": [],
            "allies": allies,
            "self": self_status,
            "threats": [],
            "opportunities": []
        }
        
        # Process each enemy
        for enemy in enemies:
            enemy_data = {
                "id": enemy.get("id"),
                "hp_ratio": enemy.get("hp", 0) / max(enemy.get("max_hp", 1), 1),
                "distance": enemy.get("distance", 999),
                "level": enemy.get("level", 1),
                "armor_class": enemy.get("ac", 10),
                "conditions": enemy.get("conditions", []),
                "is_wounded": enemy.get("hp", 0) < enemy.get("max_hp", 1) * 0.5,
                "is_targeting_me": enemy.get("target") == self_status.get("id"),
                "in_range": self._in_range(enemy, self_status)
            }
            
            # Calculate threat score
            threat = self._calculate_threat(enemy_data, self_status)
            enemy_data["threat_score"] = threat
            
            processed["enemies"].append(enemy_data)
            processed["threats"].append((enemy_data, threat))
        
        # Sort by threat
        processed["threats"].sort(key=lambda x: x[1], reverse=True)
        
        # Identify opportunity targets (low HP, in range)
        for enemy_data in processed["enemies"]:
            if enemy_data["hp_ratio"] < 0.3 and enemy_data["in_range"]:
                processed["opportunities"].append(enemy_data)
        
        return processed
    
    def decide(self, processed_perception: Dict[str, Any]) -> BotAction:
        """Select target and attack"""
        
        enemies = processed_perception["enemies"]
        threats = processed_perception["threats"]
        opportunities = processed_perception["opportunities"]
        self_status = processed_perception["self"]
        
        if not enemies:
            return BotAction(
                action_type="wait",
                confidence=1.0,
                reasoning="No enemies to target"
            )
        
        # Decision logic based on parameters and situation
        target = None
        reasoning = ""
        confidence = 0.7
        
        # 1. Opportunist: finish off weak enemies
        if opportunities and random.random() < self.params.opportunist:
            target = opportunities[0]
            reasoning = "Opportunistic strike on weakened enemy"
            confidence = 0.9
        
        # 2. Defensive: target enemies attacking me
        elif self_status.get("hp", 0) < self_status.get("max_hp", 1) * 0.5:
            for enemy_data in enemies:
                if enemy_data["is_targeting_me"]:
                    target = enemy_data
                    reasoning = "Defending against direct threat"
                    confidence = 0.8
                    break
        
        # 3. Priority-based targeting
        if not target:
            if self.params.target_priority == "threat":
                # Target highest threat
                target = threats[0][0]
                reasoning = f"Targeting highest threat (score={target['threat_score']:.2f})"
                confidence = 0.8 if len(threats) == 1 else 0.6
                
            elif self.params.target_priority == "weak":
                # Target lowest HP
                target = min(enemies, key=lambda e: e["hp_ratio"])
                reasoning = "Targeting weakest enemy"
                confidence = 0.7
                
            elif self.params.target_priority == "close":
                # Target closest
                target = min(enemies, key=lambda e: e["distance"])
                reasoning = "Targeting closest enemy"
                confidence = 0.75
                
            elif self.params.target_priority == "strong":
                # Target highest HP (tank role)
                target = max(enemies, key=lambda e: e["hp_ratio"])
                reasoning = "Targeting strongest enemy (tank role)"
                confidence = 0.6
        
        # Fallback
        if not target:
            target = enemies[0]
            reasoning = "Default target selection"
            confidence = 0.5
        
        # Determine action type
        action_type = "attack"
        action_params = {
            "target_id": target["id"],
            "threat_score": target.get("threat_score", 0.5),
            "distance": target["distance"]
        }
        
        # Check if we should use special ability
        if self._should_use_ability(target, self_status):
            action_type = "special_ability"
            action_params["ability"] = "power_attack"
            reasoning += " (using special ability)"
        
        return BotAction(
            action_type=action_type,
            target=target["id"],
            parameters=action_params,
            confidence=confidence,
            reasoning=reasoning,
            priority=BotPriority.HIGH if target.get("is_targeting_me") else BotPriority.NORMAL
        )
    
    def _calculate_threat(
        self,
        enemy: Dict[str, Any],
        self_status: Dict[str, Any]
    ) -> float:
        """Calculate threat score for enemy"""
        threat = 0.5
        
        # HP ratio (healthy enemies more threatening)
        threat += enemy["hp_ratio"] * 0.2
        
        # Distance (closer = more threat)
        if enemy["distance"] < 5:
            threat += 0.3
        elif enemy["distance"] < 15:
            threat += 0.2
        elif enemy["distance"] < 30:
            threat += 0.1
        
        # Level difference
        self_level = self_status.get("level", 1)
        level_diff = enemy["level"] - self_level
        threat += min(max(level_diff / 10, -0.2), 0.2)
        
        # Targeting me
        if enemy["is_targeting_me"]:
            threat += 0.3
        
        # Conditions (stunned/prone less threatening)
        if "stunned" in enemy["conditions"]:
            threat -= 0.3
        if "prone" in enemy["conditions"]:
            threat -= 0.2
        
        return max(0.0, min(1.0, threat))
    
    def _in_range(
        self,
        enemy: Dict[str, Any],
        self_status: Dict[str, Any]
    ) -> bool:
        """Check if enemy is in attack range"""
        distance = enemy.get("distance", 999)
        weapon_range = self_status.get("weapon_range", 5)
        return distance <= weapon_range
    
    def _should_use_ability(
        self,
        target: Dict[str, Any],
        self_status: Dict[str, Any]
    ) -> bool:
        """Decide if should use special ability instead of basic attack"""
        # Use ability on high-threat, high-HP targets
        if target.get("threat_score", 0) > 0.7 and target["hp_ratio"] > 0.5:
            # Check if we have resources
            if self_status.get("ability_available", False):
                return random.random() < (1.0 - self.params.spell_conservation)
        return False


class PositionOptimizationBot(MechanicalBot):
    """
    Optimizes character positioning in combat
    
    Considers cover, flanking, formation, and range.
    """
    
    def __init__(self, parameters: CombatParameters):
        super().__init__("position_optimization", BotType.COMBAT, parameters)
        self.params = parameters
    
    def perceive(self, perception: BotPerception) -> Dict[str, Any]:
        """Extract positioning information"""
        
        self_status = perception.self_status
        enemies = perception.enemies_status
        allies = perception.allies_status
        terrain = perception.visible_terrain
        
        # Current position
        current_pos = (
            self_status.get("x", 0),
            self_status.get("y", 0)
        )
        
        processed = {
            "current_position": current_pos,
            "enemies": enemies,
            "allies": allies,
            "cover_positions": self._find_cover(terrain, current_pos),
            "flanking_positions": self._find_flanking_positions(enemies, allies, current_pos),
            "formation_position": self._get_formation_position(allies, current_pos),
            "in_danger": self._assess_danger(enemies, current_pos)
        }
        
        return processed
    
    def decide(self, processed_perception: Dict[str, Any]) -> BotAction:
        """Decide on movement"""
        
        current_pos = processed_perception["current_position"]
        enemies = processed_perception["enemies"]
        
        if not enemies:
            return BotAction(
                action_type="hold_position",
                confidence=1.0,
                reasoning="No enemies, holding position"
            )
        
        # Assess if we need to move
        in_danger = processed_perception["in_danger"]
        cover_positions = processed_perception["cover_positions"]
        flanking_positions = processed_perception["flanking_positions"]
        
        # Decision tree
        target_position = None
        reasoning = ""
        confidence = 0.6
        
        # 1. In danger + cover available = move to cover
        if in_danger and cover_positions and random.random() < self.params.cover_seeking:
            target_position = cover_positions[0]
            reasoning = "Moving to cover (under threat)"
            confidence = 0.8
        
        # 2. Opportunistic flanking
        elif flanking_positions and random.random() < self.params.aggression:
            target_position = flanking_positions[0]
            reasoning = "Moving to flanking position"
            confidence = 0.7
        
        # 3. Maintain formation
        elif self.params.formation_preference != CombatRole.SCOUT:
            formation_pos = processed_perception["formation_position"]
            if self._distance(current_pos, formation_pos) > 10:
                target_position = formation_pos
                reasoning = "Returning to formation"
                confidence = 0.6
        
        # 4. Adjust range
        else:
            target_position = self._get_optimal_range_position(
                enemies,
                current_pos,
                self.params.preferred_range
            )
            reasoning = f"Adjusting to {self.params.preferred_range} range"
            confidence = 0.5
        
        # If no movement needed
        if not target_position or target_position == current_pos:
            return BotAction(
                action_type="hold_position",
                confidence=0.9,
                reasoning="Position is optimal"
            )
        
        return BotAction(
            action_type="move",
            parameters={
                "target_position": target_position,
                "urgency": "high" if in_danger else "normal"
            },
            confidence=confidence,
            reasoning=reasoning,
            priority=BotPriority.HIGH if in_danger else BotPriority.NORMAL
        )
    
    def _find_cover(
        self,
        terrain: List[str],
        current_pos: Tuple[float, float]
    ) -> List[Tuple[float, float]]:
        """Find nearby cover positions"""
        # Simplified: would integrate with terrain system
        cover = []
        # Mock implementation
        if "wall" in terrain:
            cover.append((current_pos[0] + 5, current_pos[1]))
        if "boulder" in terrain:
            cover.append((current_pos[0], current_pos[1] + 5))
        return cover
    
    def _find_flanking_positions(
        self,
        enemies: List[Dict],
        allies: List[Dict],
        current_pos: Tuple[float, float]
    ) -> List[Tuple[float, float]]:
        """Find positions that flank enemies"""
        flanking = []
        # Simplified flanking logic
        for enemy in enemies[:1]:  # Focus on primary target
            enemy_pos = (enemy.get("x", 0), enemy.get("y", 0))
            # Position opposite of enemy's facing
            flank_pos = (
                enemy_pos[0] + random.choice([-5, 5]),
                enemy_pos[1] + random.choice([-5, 5])
            )
            flanking.append(flank_pos)
        return flanking
    
    def _get_formation_position(
        self,
        allies: List[Dict],
        current_pos: Tuple[float, float]
    ) -> Tuple[float, float]:
        """Get position based on role in formation"""
        if not allies:
            return current_pos
        
        # Calculate center of party
        center_x = sum(a.get("x", 0) for a in allies) / len(allies)
        center_y = sum(a.get("y", 0) for a in allies) / len(allies)
        
        # Position based on role
        if self.params.formation_preference == CombatRole.TANK:
            # Front line
            return (center_x, center_y - 5)
        elif self.params.formation_preference == CombatRole.SUPPORT:
            # Back line
            return (center_x, center_y + 10)
        else:
            # Middle
            return (center_x, center_y)
    
    def _assess_danger(
        self,
        enemies: List[Dict],
        current_pos: Tuple[float, float]
    ) -> bool:
        """Assess if current position is dangerous"""
        for enemy in enemies:
            enemy_pos = (enemy.get("x", 0), enemy.get("y", 0))
            distance = self._distance(current_pos, enemy_pos)
            if distance < 5 and enemy.get("hp", 0) > 0:
                return True
        return False
    
    def _get_optimal_range_position(
        self,
        enemies: List[Dict],
        current_pos: Tuple[float, float],
        preferred_range: str
    ) -> Tuple[float, float]:
        """Get position for optimal range"""
        if not enemies:
            return current_pos
        
        # Target closest enemy
        closest = min(enemies, key=lambda e: e.get("distance", 999))
        enemy_pos = (closest.get("x", 0), closest.get("y", 0))
        
        # Calculate optimal distance
        if preferred_range == "melee":
            optimal_dist = 5
        elif preferred_range == "ranged":
            optimal_dist = 30
        else:  # medium
            optimal_dist = 15
        
        # Move toward/away from enemy to reach optimal distance
        current_dist = self._distance(current_pos, enemy_pos)
        
        if abs(current_dist - optimal_dist) < 5:
            return current_pos  # Close enough
        
        # Calculate position
        angle = math.atan2(enemy_pos[1] - current_pos[1], enemy_pos[0] - current_pos[0])
        
        if current_dist < optimal_dist:
            # Move away
            new_x = current_pos[0] - math.cos(angle) * 5
            new_y = current_pos[1] - math.sin(angle) * 5
        else:
            # Move closer
            new_x = current_pos[0] + math.cos(angle) * 5
            new_y = current_pos[1] + math.sin(angle) * 5
        
        return (new_x, new_y)
    
    def _distance(
        self,
        pos1: Tuple[float, float],
        pos2: Tuple[float, float]
    ) -> float:
        """Calculate distance between positions"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)


class ResourceManagementBot(MechanicalBot):
    """
    Manages combat resources (HP, spells, items)
    
    Decides when to heal, use potions, conserve spells, etc.
    """
    
    def __init__(self, parameters: CombatParameters):
        super().__init__("resource_management", BotType.COMBAT, parameters)
        self.params = parameters
    
    def perceive(self, perception: BotPerception) -> Dict[str, Any]:
        """Extract resource information"""
        
        self_status = perception.self_status
        
        hp_ratio = self_status.get("hp", 0) / max(self_status.get("max_hp", 1), 1)
        
        processed = {
            "hp_ratio": hp_ratio,
            "spell_slots": self_status.get("spell_slots", {}),
            "potions": self_status.get("potions", 0),
            "abilities_available": self_status.get("abilities_available", []),
            "in_combat": len(perception.enemies_status) > 0,
            "critical_hp": hp_ratio < self.params.potion_threshold,
            "low_hp": hp_ratio < self.params.hp_heal_threshold,
            "defensive_stance_needed": hp_ratio < self.params.defensive_threshold
        }
        
        return processed
    
    def decide(self, processed_perception: Dict[str, Any]) -> BotAction:
        """Decide on resource usage"""
        
        # Priority: critical HP > low HP > defensive stance > resource conservation
        
        # 1. Critical HP - use potion immediately
        if processed_perception["critical_hp"] and processed_perception["potions"] > 0:
            return BotAction(
                action_type="use_potion",
                parameters={"type": "healing"},
                confidence=1.0,
                reasoning="Critical HP, using potion",
                priority=BotPriority.CRITICAL
            )
        
        # 2. Low HP - heal if able
        if processed_perception["low_hp"]:
            # Check for healing ability
            if "heal" in processed_perception["abilities_available"]:
                return BotAction(
                    action_type="use_ability",
                    parameters={"ability": "heal"},
                    confidence=0.9,
                    reasoning="Low HP, using healing ability",
                    priority=BotPriority.HIGH
                )
        
        # 3. Defensive stance if low HP and in combat
        if processed_perception["defensive_stance_needed"] and processed_perception["in_combat"]:
            return BotAction(
                action_type="defensive_stance",
                confidence=0.8,
                reasoning="Low HP, taking defensive stance"
            )
        
        # 4. Resource conservation recommendations
        spell_slots = processed_perception["spell_slots"]
        total_slots = sum(spell_slots.values()) if spell_slots else 0
        
        if total_slots < 3 and processed_perception["in_combat"]:
            # Running low on spell slots
            return BotAction(
                action_type="conserve_resources",
                confidence=0.7,
                reasoning="Low spell slots, conserving resources",
                parameters={"recommendation": "use_basic_attacks"}
            )
        
        # No action needed
        return BotAction(
            action_type="resources_ok",
            confidence=0.9,
            reasoning="Resources healthy"
        )


# Test combat bots
if __name__ == "__main__":
    import logging
    from mechanical_bot import BotSwarm
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*50)
    print("COMBAT BOTS TEST")
    print("="*50)
    
    # Create combat parameters
    params = CombatParameters(
        aggression=0.7,
        risk_tolerance=0.6,
        target_priority="threat",
        focus_fire=True,
        preferred_range="medium",
        formation_preference=CombatRole.DAMAGE
    )
    
    # Create combat bots
    targeting = CombatTargetingBot(parameters=params)
    positioning = PositionOptimizationBot(parameters=params)
    resources = ResourceManagementBot(parameters=params)
    
    # Create perception
    perception = BotPerception(
        enemies_status=[
            {
                "id": "orc_1",
                "hp": 30, "max_hp": 50,
                "distance": 15,
                "level": 3,
                "ac": 14,
                "x": 10, "y": 5,
                "target": "thorin"
            },
            {
                "id": "goblin_1",
                "hp": 5, "max_hp": 15,
                "distance": 10,
                "level": 1,
                "ac": 12,
                "x": 8, "y": 3
            }
        ],
        allies_status=[
            {"id": "elara", "x": 5, "y": 0},
            {"id": "grunk", "x": 15, "y": 0}
        ],
        self_status={
            "id": "thorin",
            "hp": 35, "max_hp": 50,
            "level": 3,
            "x": 0, "y": 0,
            "weapon_range": 5,
            "spell_slots": {1: 3, 2: 2},
            "potions": 2,
            "abilities_available": ["power_attack", "heal"],
            "ability_available": True
        }
    )
    
    # Test targeting
    print("\nTARGETING BOT:")
    decision = targeting.execute(perception)
    print(f"Action: {decision.action.action_type}")
    print(f"Target: {decision.action.target}")
    print(f"Reasoning: {decision.action.reasoning}")
    print(f"Confidence: {decision.confidence:.2f}")
    print(f"Should escalate: {decision.should_escalate}")
    
    # Test positioning
    print("\nPOSITIONING BOT:")
    decision = positioning.execute(perception)
    print(f"Action: {decision.action.action_type}")
    if decision.action.parameters:
        print(f"Parameters: {decision.action.parameters}")
    print(f"Reasoning: {decision.action.reasoning}")
    print(f"Confidence: {decision.confidence:.2f}")
    
    # Test resources
    print("\nRESOURCE MANAGEMENT BOT:")
    decision = resources.execute(perception)
    print(f"Action: {decision.action.action_type}")
    print(f"Reasoning: {decision.action.reasoning}")
    print(f"Confidence: {decision.confidence:.2f}")
    
    # Test with critical HP
    print("\n" + "-"*50)
    print("TEST: Critical HP Situation")
    print("-"*50)
    
    perception.self_status["hp"] = 10  # Critical HP
    decision = resources.execute(perception)
    print(f"Action: {decision.action.action_type}")
    print(f"Reasoning: {decision.action.reasoning}")
    print(f"Priority: {decision.action.priority.name}")
    
    print("\nCombat bots test complete!")
