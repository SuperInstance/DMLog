"""
Social Bots (Phase 8)
Specialized bots for social interactions including dialogue, persuasion, deception, and insight.
"""
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from mechanical_bot import MechanicalBot, BotType, BotParameters, BotPerception, BotAction, BotPriority

class SocialTactic(Enum):
    FRIENDLY = "friendly"
    LOGICAL = "logical"
    EMOTIONAL = "emotional"
    AUTHORITATIVE = "authoritative"
    CHARMING = "charming"

@dataclass
class SocialParameters(BotParameters):
    preferred_tactic: SocialTactic = SocialTactic.FRIENDLY
    honesty: float = 0.7
    empathy: float = 0.5
    assertiveness: float = 0.5
    deception_skill: float = 0.5
    insight_skill: float = 0.5
    persuasion_skill: float = 0.5
    intimidation_skill: float = 0.5

class DialogueBot(MechanicalBot):
    def __init__(self, parameters: SocialParameters):
        super().__init__("dialogue", BotType.SOCIAL, parameters)
        self.params = parameters
    
    def perceive(self, perception: BotPerception) -> Dict[str, Any]:
        processed = {"visible_npcs": [], "conversation_partners": []}
        for entity in perception.visible_entities:
            if entity.get("entity_type") in ["npc", "character"]:
                npc_data = {"id": entity.get("id"), "name": entity.get("name", "Unknown"),
                           "distance": entity.get("distance", 999), "attitude": entity.get("attitude", "neutral")}
                processed["visible_npcs"].append(npc_data)
                if npc_data["distance"] < 10:
                    processed["conversation_partners"].append(npc_data)
        return processed
    
    def decide(self, perception: BotPerception, context: Optional[Dict[str, Any]] = None) -> BotAction:
        processed = self.perceive(perception)
        if not processed["conversation_partners"]:
            return BotAction(action_type="wait", confidence=0.9, reasoning="No one nearby", estimated_duration_ms=5)
        
        partner = processed["conversation_partners"][0]
        attitude = partner["attitude"]
        
        if attitude == "hostile":
            action_type = "speak_calmly" if self.params.assertiveness < 0.3 else "speak_firmly"
            action_desc = f"speak calmly to {partner['name']}" if self.params.assertiveness < 0.3 else f"firmly address {partner['name']}"
            confidence = 0.7
        elif attitude == "friendly":
            action_type = "friendly_conversation"
            action_desc = f"engage in friendly conversation with {partner['name']}"
            confidence = 0.85
        else:
            action_type = "greet"
            action_desc = f"greet {partner['name']}"
            confidence = 0.75
        
        return BotAction(action_type=action_type, target=partner['name'], confidence=confidence,
                        reasoning=action_desc, priority=BotPriority.NORMAL, estimated_duration_ms=8)

class PersuasionBot(MechanicalBot):
    def __init__(self, parameters: SocialParameters):
        super().__init__("persuasion", BotType.SOCIAL, parameters)
        self.params = parameters
    
    def perceive(self, perception: BotPerception) -> Dict[str, Any]:
        processed = {"target": None, "relationship_level": 0.5, "stakes": 0.5}
        for entity in perception.visible_entities:
            if entity.get("is_persuasion_target"):
                processed["target"] = entity
                processed["relationship_level"] = entity.get("relationship", 0.5)
                processed["stakes"] = entity.get("request_stakes", 0.5)
                break
        return processed
    
    def decide(self, perception: BotPerception, context: Optional[Dict[str, Any]] = None) -> BotAction:
        processed = self.perceive(perception)
        context = context or {}
        
        if not processed["target"]:
            return BotAction(action_type="wait", confidence=0.5, reasoning="No target", estimated_duration_ms=5)
        
        target_name = processed["target"].get("name", "target")
        request = context.get("request", "help")
        tactic = self.params.preferred_tactic
        
        if tactic == SocialTactic.LOGICAL:
            action_type = "persuade_logical"
            action_desc = f"logically explain why {target_name} should {request}"
            base_confidence = self.params.persuasion_skill * 0.7
        elif tactic == SocialTactic.EMOTIONAL:
            action_type = "persuade_emotional"
            action_desc = f"appeal to {target_name}'s emotions about {request}"
            base_confidence = self.params.empathy * 0.6 + self.params.persuasion_skill * 0.3
        else:
            action_type = "persuade_friendly"
            action_desc = f"ask {target_name} nicely to {request}"
            base_confidence = processed["relationship_level"] * 0.5 + self.params.persuasion_skill * 0.4
        
        confidence = base_confidence * (0.5 + processed["relationship_level"] * 0.5) * (1.0 - processed["stakes"] * 0.3)
        return BotAction(action_type=action_type, target=target_name, confidence=min(0.95, confidence),
                        reasoning=action_desc, priority=BotPriority.NORMAL, estimated_duration_ms=12,
                        parameters={"tactic": tactic.value, "request": request})

class InsightBot(MechanicalBot):
    def __init__(self, parameters: SocialParameters):
        super().__init__("insight", BotType.SOCIAL, parameters)
        self.params = parameters
    
    def perceive(self, perception: BotPerception) -> Dict[str, Any]:
        processed = {"speakers": []}
        for entity in perception.visible_entities:
            if entity.get("is_speaking"):
                speaker = {"id": entity.get("id"), "name": entity.get("name", "Unknown"),
                          "body_language": entity.get("body_language", "neutral"),
                          "is_evasive": entity.get("is_evasive", False)}
                processed["speakers"].append(speaker)
        return processed
    
    def decide(self, perception: BotPerception, context: Optional[Dict[str, Any]] = None) -> BotAction:
        processed = self.perceive(perception)
        if not processed["speakers"]:
            return BotAction(action_type="observe", confidence=0.8, reasoning="No speakers", estimated_duration_ms=6)
        
        speaker = processed["speakers"][0]
        suspicion_score = 0.0
        if speaker["body_language"] == "nervous": suspicion_score += 0.3
        if speaker["is_evasive"]: suspicion_score += 0.4
        
        adjusted_score = suspicion_score * self.params.insight_skill
        
        if adjusted_score > 0.7:
            action_type = "assess_lying"
            assessment = f"{speaker['name']} appears to be lying"
            confidence = self.params.insight_skill * 0.8
        elif adjusted_score > 0.4:
            action_type = "assess_nervous"
            assessment = f"{speaker['name']} seems nervous"
            confidence = self.params.insight_skill * 0.6
        else:
            action_type = "assess_truthful"
            assessment = f"{speaker['name']} appears truthful"
            confidence = self.params.insight_skill * 0.7
        
        return BotAction(action_type=action_type, target=speaker['name'], confidence=confidence,
                        reasoning=assessment, priority=BotPriority.NORMAL, estimated_duration_ms=10,
                        parameters={"suspicion_score": adjusted_score})

if __name__ == "__main__":
    print("Testing Social Bots...\n")
    params = SocialParameters(preferred_tactic=SocialTactic.FRIENDLY, empathy=0.8,
                             assertiveness=0.5, persuasion_skill=0.7, insight_skill=0.8)
    
    dialogue_bot = DialogueBot(params)
    perception = BotPerception(visible_entities=[{"id": "npc1", "name": "Innkeeper", "entity_type": "npc",
                                                  "distance": 5, "attitude": "friendly"}])
    action = dialogue_bot.decide(perception)
    print(f"=== Dialogue Bot ===\nAction: {action.reasoning}\nConfidence: {action.confidence:.2f}\n")
    
    persuasion_bot = PersuasionBot(params)
    perception = BotPerception(visible_entities=[{"id": "m1", "name": "Merchant", "entity_type": "npc",
                                                  "is_persuasion_target": True, "relationship": 0.6}])
    action = persuasion_bot.decide(perception, {"request": "lower price"})
    print(f"=== Persuasion Bot ===\nAction: {action.reasoning}\nConfidence: {action.confidence:.2f}\n")
    
    insight_bot = InsightBot(params)
    perception = BotPerception(visible_entities=[{"id": "s1", "name": "Suspect", "is_speaking": True,
                                                  "body_language": "nervous", "is_evasive": True}])
    action = insight_bot.decide(perception)
    print(f"=== Insight Bot ===\nAssessment: {action.reasoning}\nConfidence: {action.confidence:.2f}\n")
    
    print("✅ All tests completed!")
