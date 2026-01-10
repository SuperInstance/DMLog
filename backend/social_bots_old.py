"""
Social Bots

Specialized bots for social interactions including dialogue, persuasion,
deception, and relationship management.

Key Features:
- Dialogue selection bot
- Persuasion bot
- Deception detection bot
- Relationship tracking bot
- Emotion expression bot
- Small talk bot
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


class SocialApproach(Enum):
    """Social interaction approaches"""
    FRIENDLY = "friendly"
    FORMAL = "formal"
    CASUAL = "casual"
    FLATTERING = "flattering"
    INTIMIDATING = "intimidating"
    DECEPTIVE = "deceptive"


@dataclass
class SocialParameters(BotParameters):
    """Extended parameters for social bots"""
    # Social preferences
    preferred_approach: SocialApproach = SocialApproach.FRIENDLY
    formality_level: float = 0.5      # 0=casual, 1=very formal
    verbosity: float = 0.5            # 0=terse, 1=verbose
    
    # Interaction style
    charm: float = 0.5                # 0=blunt, 1=charming
    empathy: float = 0.5              # 0=insensitive, 1=empathetic
    wit: float = 0.5                  # 0=serious, 1=witty
    
    # Strategic
    manipulation_willing: float = 0.2  # 0=honest, 1=manipulative
    flattery_level: float = 0.3       # 0=none, 1=excessive
    
    # Relationships
    relationship_value: float = 0.7   # How much they value relationships


class DialogueSelectionBot(MechanicalBot):
    """
    Bot for selecting appropriate dialogue options
    
    Analyzes conversation context and NPC state to choose the best
    dialogue approach.
    """
    
    def __init__(self, parameters: SocialParameters):
        super().__init__("dialogue_selection", BotType.SOCIAL, parameters)
        self.params = parameters
    
    def perceive(self, perception: BotPerception) -> Dict[str, Any]:
        """Extract social-relevant information"""
        
        # Get NPC state
        npcs = [e for e in perception.visible_entities if e.get("entity_type") == "npc"]
        
        processed = {
            "npcs": npcs,
            "relationships": {},
            "moods": {},
            "context": perception.self_status.get("conversation_context", ""),
        }
        
        # Extract relationship data
        for npc in npcs:
            npc_id = npc.get("id")
            processed["relationships"][npc_id] = {
                "trust": npc.get("trust", 0.5),
                "respect": npc.get("respect", 0.5),
                "fear": npc.get("fear", 0.0)
            }
            processed["moods"][npc_id] = npc.get("mood", "neutral")
        
        return processed
    
    def decide(self, perception_data: Dict[str, Any]) -> BotAction:
        """Choose dialogue approach"""
        
        if not perception_data["npcs"]:
            return self._no_npc_action()
        
        npc = perception_data["npcs"][0]
        npc_id = npc.get("id")
        rel = perception_data["relationships"].get(npc_id, {})
        mood = perception_data["moods"].get(npc_id, "neutral")
        
        # Determine best approach based on relationship and mood
        approaches = []
        
        # Friendly approach if good relationship
        if rel.get("trust", 0) > 0.6:
            approaches.append(("friendly", 0.8))
        
        # Formal if low trust
        if rel.get("trust", 0) < 0.4:
            approaches.append(("formal", 0.7))
        
        # Flattering if they have high ego
        if npc.get("personality", {}).get("ego", 0.5) > 0.7:
            approaches.append(("flattering", 0.6))
        
        # Intimidating if they're fearful
        if rel.get("fear", 0) > 0.5:
            approaches.append(("intimidating", 0.7))
        
        # Default to character preference
        if not approaches:
            approaches.append((self.params.preferred_approach.value, 0.5))
        
        # Select best approach
        best_approach, confidence = max(approaches, key=lambda x: x[1])
        
        # Apply personality adjustments
        confidence *= (1.0 - self.params.imperfection_rate)
        
        # Add hesitation
        if random.random() < self.params.hesitation_rate:
            delay = random.randint(100, 500)
        else:
            delay = 0
        
        return BotAction(
            action_type=f"use_{best_approach}_approach",
            confidence=confidence,
            priority=BotPriority.NORMAL,
            estimated_duration_ms=delay,
            reasoning=f"Best approach for {mood} NPC with trust={rel.get('trust', 0):.2f}"
        )
    
    def _no_npc_action(self) -> BotAction:
        """Action when no NPC present"""
        return BotAction(
            action_type="wait",
            confidence=0.9,
            priority=BotPriority.LOW,
            reasoning="No NPC to interact with"
        )


class PersuasionBot(MechanicalBot):
    """
    Bot for persuasion attempts
    
    Determines when and how to persuade NPCs based on goals,
    relationships, and personality.
    """
    
    def __init__(self, parameters: SocialParameters):
        super().__init__("persuasion", BotType.SOCIAL, parameters)
        self.params = parameters
    
    def perceive(self, perception: BotPerception) -> Dict[str, Any]:
        """Extract persuasion-relevant information"""
        
        npcs = [e for e in perception.visible_entities if e.get("entity_type") == "npc"]
        
        processed = {
            "target_npc": npcs[0] if npcs else None,
            "goal": perception.self_status.get("current_goal", ""),
            "relationship": {},
            "npc_personality": {}
        }
        
        if processed["target_npc"]:
            npc = processed["target_npc"]
            npc_id = npc.get("id")
            
            processed["relationship"] = {
                "trust": npc.get("trust", 0.5),
                "respect": npc.get("respect", 0.5),
                "affection": npc.get("affection", 0.0)
            }
            
            processed["npc_personality"] = npc.get("personality", {})
        
        return processed
    
    def decide(self, perception_data: Dict[str, Any]) -> BotAction:
        """Decide on persuasion strategy"""
        
        if not perception_data["target_npc"]:
            return self._no_target_action()
        
        rel = perception_data["relationship"]
        personality = perception_data["npc_personality"]
        goal = perception_data["goal"]
        
        # Calculate persuasion likelihood
        base_chance = 0.5
        
        # Relationship bonuses
        base_chance += rel.get("trust", 0) * 0.3
        base_chance += rel.get("respect", 0) * 0.2
        
        # Personality factors
        if personality.get("agreeableness", 0.5) > 0.7:
            base_chance += 0.2
        
        if personality.get("intelligence", 0.5) > 0.7:
            base_chance -= 0.1  # Smarter NPCs harder to persuade
        
        # Character charm
        base_chance += self.params.charm * 0.2
        
        # Determine strategy
        strategies = []
        
        # Logical argument (works on intelligent NPCs)
        if personality.get("intelligence", 0.5) > 0.6:
            strategies.append(("logical_argument", base_chance + 0.1))
        
        # Emotional appeal (works on empathetic NPCs)
        if personality.get("agreeableness", 0.5) > 0.6:
            strategies.append(("emotional_appeal", base_chance + 0.15))
        
        # Flattery (works on vain NPCs)
        if personality.get("ego", 0.5) > 0.7:
            strategies.append(("flattery", base_chance + 0.2))
        
        # Mutual benefit
        strategies.append(("mutual_benefit", base_chance + 0.05))
        
        # Select best strategy
        best_strategy, success_chance = max(strategies, key=lambda x: x[1])
        
        # Confidence is the success chance
        confidence = min(success_chance, 0.95)
        
        return BotAction(
            action_type=f"persuade_with_{best_strategy}",
            confidence=confidence,
            priority=BotPriority.NORMAL,
            reasoning=f"Best strategy: {best_strategy} ({confidence:.0%} success chance)"
        )
    
    def _no_target_action(self) -> BotAction:
        """Action when no target"""
        return BotAction(
            action_type="wait",
            confidence=0.9,
            priority=BotPriority.LOW,
            reasoning="No persuasion target"
        )


class EmotionExpressionBot(MechanicalBot):
    """
    Bot for expressing appropriate emotions
    
    Determines emotional responses based on situation and character personality.
    """
    
    def __init__(self, parameters: SocialParameters):
        super().__init__("emotion_expression", BotType.SOCIAL, parameters)
        self.params = parameters
    
    def perceive(self, perception: BotPerception) -> Dict[str, Any]:
        """Extract emotion-relevant information"""
        
        recent_events = perception.self_status.get("recent_events", [])
        current_mood = perception.self_status.get("mood", "neutral")
        
        processed = {
            "recent_events": recent_events,
            "current_mood": current_mood,
            "hp_ratio": perception.self_status.get("hp_ratio", 1.0),
            "stress_level": perception.self_status.get("stress", 0.0),
            "relationship_changes": perception.self_status.get("relationship_changes", [])
        }
        
        return processed
    
    def decide(self, perception_data: Dict[str, Any]) -> BotAction:
        """Choose emotional expression"""
        
        # Determine appropriate emotion
        emotions = []
        
        # HP-based emotions
        hp = perception_data["hp_ratio"]
        if hp < 0.3:
            emotions.append(("fear", 0.8))
            emotions.append(("desperation", 0.7))
        elif hp < 0.6:
            emotions.append(("concern", 0.6))
        
        # Event-based emotions
        recent_events = perception_data["recent_events"]
        
        for event in recent_events:
            if "victory" in event.lower():
                emotions.append(("joy", 0.8))
            elif "betrayal" in event.lower():
                emotions.append(("anger", 0.9))
            elif "loss" in event.lower():
                emotions.append(("sadness", 0.8))
            elif "discovery" in event.lower():
                emotions.append(("excitement", 0.7))
        
        # Relationship-based emotions
        rel_changes = perception_data["relationship_changes"]
        for change in rel_changes:
            if change.get("delta", 0) > 0.2:
                emotions.append(("gratitude", 0.7))
            elif change.get("delta", 0) < -0.2:
                emotions.append(("disappointment", 0.7))
        
        # Stress-based emotions
        stress = perception_data["stress_level"]
        if stress > 0.7:
            emotions.append(("anxiety", 0.8))
        
        # Default emotion
        if not emotions:
            emotions.append(("calm", 0.6))
        
        # Select most intense emotion
        emotion, confidence = max(emotions, key=lambda x: x[1])
        
        # Modify by empathy (how much emotion to show)
        expression_intensity = self.params.empathy * confidence
        
        return BotAction(
            action_type=f"express_{emotion}",
            confidence=expression_intensity,
            priority=BotPriority.NORMAL,
            reasoning=f"Emotional state: {emotion}"
        )


class RelationshipTrackerBot(MechanicalBot):
    """
    Bot for tracking and maintaining relationships
    
    Monitors relationship changes and suggests relationship-building actions.
    """
    
    def __init__(self, parameters: SocialParameters):
        super().__init__("relationship_tracker", BotType.SOCIAL, parameters)
        self.params = parameters
        self.relationship_history: Dict[str, List[float]] = {}
    
    def perceive(self, perception: BotPerception) -> Dict[str, Any]:
        """Extract relationship information"""
        
        npcs = [e for e in perception.visible_entities if e.get("entity_type") == "npc"]
        
        processed = {
            "relationships": {},
            "opportunities": []
        }
        
        for npc in npcs:
            npc_id = npc.get("id")
            trust = npc.get("trust", 0.5)
            respect = npc.get("respect", 0.5)
            
            processed["relationships"][npc_id] = {
                "trust": trust,
                "respect": respect,
                "affection": npc.get("affection", 0.0)
            }
            
            # Track history
            if npc_id not in self.relationship_history:
                self.relationship_history[npc_id] = []
            self.relationship_history[npc_id].append(trust)
            
            # Identify opportunities
            if trust < 0.4 and trust > 0.2:  # Can improve
                processed["opportunities"].append({
                    "npc_id": npc_id,
                    "type": "improve_trust",
                    "priority": 0.7
                })
            
            if respect < 0.5:
                processed["opportunities"].append({
                    "npc_id": npc_id,
                    "type": "earn_respect",
                    "priority": 0.6
                })
        
        return processed
    
    def decide(self, perception_data: Dict[str, Any]) -> BotAction:
        """Decide on relationship action"""
        
        opportunities = perception_data["opportunities"]
        
        if not opportunities:
            return BotAction(
                action_type="maintain_relationships",
                confidence=0.7,
                priority=BotPriority.LOW,
                reasoning="No immediate relationship opportunities"
            )
        
        # Select highest priority opportunity
        best_opp = max(opportunities, key=lambda x: x["priority"])
        
        # Determine action based on opportunity type
        if best_opp["type"] == "improve_trust":
            action = "be_honest_and_helpful"
            confidence = 0.75
        elif best_opp["type"] == "earn_respect":
            action = "demonstrate_competence"
            confidence = 0.7
        else:
            action = "engage_positively"
            confidence = 0.65
        
        # Weight by character's valuation of relationships
        confidence *= self.params.relationship_value
        
        return BotAction(
            action_type=action,
            confidence=confidence,
            priority=BotPriority.NORMAL,
            reasoning=f"Opportunity: {best_opp['type']} with {best_opp['npc_id']}"
        )


# Test code
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    print("Testing Social Bots...\n")
    
    # Create social parameters
    params = SocialParameters(
        preferred_approach=SocialApproach.FRIENDLY,
        charm=0.7,
        empathy=0.8,
        relationship_value=0.9
    )
    
    # Test dialogue selection bot
    print("=== Test 1: Dialogue Selection Bot ===")
    dialogue_bot = DialogueSelectionBot(params)
    
    perception = BotPerception(
        visible_entities=[{
            "id": "merchant1",
            "entity_type": "npc",
            "trust": 0.7,
            "respect": 0.6,
            "mood": "friendly",
            "personality": {"ego": 0.5}
        }]
    )
    
    action = dialogue_bot.execute(perception)
    print(f"Action: {action.action.action_type}")
    print(f"Confidence: {action.confidence:.2f}")
    print(f"Reasoning: {action.action.reasoning}")
    print()
    
    # Test persuasion bot
    print("=== Test 2: Persuasion Bot ===")
    persuasion_bot = PersuasionBot(params)
    
    perception.self_status = {"current_goal": "get_discount"}
    action = persuasion_bot.execute(perception)
    print(f"Action: {action.action.action_type}")
    print(f"Confidence: {action.confidence:.2f}")
    print(f"Reasoning: {action.action.reasoning}")
    print()
    
    # Test emotion expression bot
    print("=== Test 3: Emotion Expression Bot ===")
    emotion_bot = EmotionExpressionBot(params)
    
    perception.self_status = {
        "hp_ratio": 0.3,
        "recent_events": ["victory over dragon"],
        "mood": "excited",
        "stress": 0.4
    }
    
    action = emotion_bot.execute(perception)
    print(f"Action: {action.action.action_type}")
    print(f"Confidence: {action.confidence:.2f}")
    print(f"Reasoning: {action.action.reasoning}")
    print()
    
    # Test relationship tracker bot
    print("=== Test 4: Relationship Tracker Bot ===")
    relationship_bot = RelationshipTrackerBot(params)
    
    perception.visible_entities = [{
        "id": "guard1",
        "entity_type": "npc",
        "trust": 0.3,
        "respect": 0.4,
        "affection": 0.0
    }]
    
    action = relationship_bot.execute(perception)
    print(f"Action: {action.action.action_type}")
    print(f"Confidence: {action.confidence:.2f}")
    print(f"Reasoning: {action.action.reasoning}")
    print()
    
    print("✅ All social bot tests completed!")
