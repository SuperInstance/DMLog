"""
Layer 3 Integration Module

Integrates all Layer 3 components into a cohesive system:
- Local LLM engine
- Character brains
- Mechanical bots
- Perception batching
- Decision coordination

This module demonstrates how everything works together for actual gameplay.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

from local_llm_engine import LocalLLMEngine, ModelTier
from character_brain import CharacterBrain, BrainManager, DecisionContext, DecisionType, BrainConfig
from mechanical_bot import BotSwarm, BotParameters
from combat_bots import CombatTargetingBot, PositionOptimizationBot, ResourceManagementBot, CombatParameters, CombatRole
from perception_batch import PerceptionBatchEngine, Entity, PerceptionResult

logger = logging.getLogger(__name__)


@dataclass
class GameCharacter:
    """Complete character with brain and bots"""
    character_id: str
    name: str
    data: Dict[str, Any]
    brain: CharacterBrain
    bot_swarm: BotSwarm
    entity: Entity


class Layer3IntegratedSystem:
    """
    Integrated Layer 3 system
    
    Coordinates LLM engine, character brains, bot swarms, and perception
    to enable multi-character gameplay with both fast bot decisions and
    intelligent LLM reasoning.
    """
    
    def __init__(
        self,
        models_dir: str = "models",
        vram_budget_mb: int = 5500
    ):
        """
        Initialize integrated system
        
        Args:
            models_dir: Directory containing models
            vram_budget_mb: VRAM budget
        """
        # Core engines
        self.llm_engine = LocalLLMEngine(
            models_dir=models_dir,
            vram_budget_mb=vram_budget_mb
        )
        
        self.brain_manager = BrainManager(self.llm_engine)
        self.perception_engine = PerceptionBatchEngine()
        
        # Characters
        self.characters: Dict[str, GameCharacter] = {}
        
        # Game state
        self.turn_number = 0
        self.in_combat = False
        
        # Metrics
        self.metrics = {
            "total_turns": 0,
            "bot_decisions": 0,
            "brain_decisions": 0,
            "escalations": 0,
            "avg_turn_time_ms": 0.0
        }
        
        logger.info("Layer3IntegratedSystem initialized")
    
    async def start(self) -> None:
        """Start all engines"""
        # Register default models
        self.llm_engine.register_default_models()
        
        # Start LLM engine
        await self.llm_engine.start()
        
        logger.info("Integrated system started")
    
    async def stop(self) -> None:
        """Stop all engines"""
        await self.llm_engine.stop()
        logger.info("Integrated system stopped")
    
    def register_character(
        self,
        character_id: str,
        character_data: Dict[str, Any],
        brain_config: Optional[BrainConfig] = None,
        bot_params: Optional[CombatParameters] = None
    ) -> GameCharacter:
        """
        Register a new character
        
        Args:
            character_id: Unique character ID
            character_data: Character profile
            brain_config: Brain configuration
            bot_params: Bot parameters
            
        Returns:
            Complete game character
        """
        # Create brain
        brain = self.brain_manager.register_brain(
            character_id,
            character_data,
            brain_config
        )
        
        # Create bot swarm
        bot_swarm = BotSwarm(character_id)
        
        # Add combat bots
        params = bot_params or CombatParameters()
        bot_swarm.add_bot(CombatTargetingBot(parameters=params))
        bot_swarm.add_bot(PositionOptimizationBot(parameters=params))
        bot_swarm.add_bot(ResourceManagementBot(parameters=params))
        
        # Create entity for perception
        entity = Entity(
            entity_id=character_id,
            entity_type="character",
            position=character_data.get("position", (0, 0)),
            attitude=character_data.get("attitude", "friendly"),
            hp=character_data.get("hp", 50),
            max_hp=character_data.get("max_hp", 50)
        )
        
        # Register entity in perception engine
        self.perception_engine.register_entity(entity)
        
        # Create complete character
        game_char = GameCharacter(
            character_id=character_id,
            name=character_data.get("name", character_id),
            data=character_data,
            brain=brain,
            bot_swarm=bot_swarm,
            entity=entity
        )
        
        self.characters[character_id] = game_char
        
        logger.info(f"Registered character: {game_char.name}")
        
        return game_char
    
    async def process_turn(
        self,
        active_characters: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process a full game turn for all characters
        
        Args:
            active_characters: Characters to process (None = all)
            
        Returns:
            Turn results with decisions
        """
        start_time = time.time()
        self.turn_number += 1
        
        if active_characters is None:
            active_characters = list(self.characters.keys())
        
        logger.info(f"Processing turn {self.turn_number} for {len(active_characters)} characters")
        
        # Step 1: Batch perception
        perception_results = self.perception_engine.batch_perceive(
            active_characters,
            use_delta=self.turn_number > 1
        )
        
        # Step 2: Process each character's decision
        turn_results = {
            "turn": self.turn_number,
            "characters": {},
            "turn_time_ms": 0.0
        }
        
        for char_id in active_characters:
            char = self.characters[char_id]
            perception = perception_results[char_id]
            
            # Try bot decision first
            char_result = await self._process_character_decision(
                char,
                perception
            )
            
            turn_results["characters"][char_id] = char_result
        
        # Calculate turn time
        turn_time_ms = (time.time() - start_time) * 1000
        turn_results["turn_time_ms"] = turn_time_ms
        
        # Update metrics
        self._update_metrics(turn_results)
        
        logger.info(f"Turn {self.turn_number} complete in {turn_time_ms:.2f}ms")
        
        return turn_results
    
    async def _process_character_decision(
        self,
        character: GameCharacter,
        perception: PerceptionResult
    ) -> Dict[str, Any]:
        """
        Process decision for a single character
        
        Args:
            character: Game character
            perception: Perception result
            
        Returns:
            Character decision result
        """
        result = {
            "name": character.name,
            "decision_source": None,
            "action": None,
            "confidence": 0.0,
            "time_ms": 0.0
        }
        
        # Convert perception to bot perception format
        from mechanical_bot import BotPerception
        
        bot_perception = BotPerception(
            visible_entities=[
                {
                    "id": e.entity_id,
                    "hp": e.hp,
                    "max_hp": e.max_hp,
                    "distance": self._distance(
                        character.entity.position,
                        e.position
                    ),
                    "x": e.position[0],
                    "y": e.position[1]
                }
                for e in perception.visible_entities
            ],
            enemies_status=[
                {
                    "id": e.entity_id,
                    "hp": e.hp,
                    "max_hp": e.max_hp,
                    "distance": self._distance(
                        character.entity.position,
                        e.position
                    ),
                    "x": e.position[0],
                    "y": e.position[1],
                    "level": 1,
                    "ac": 12
                }
                for e in perception.enemies
            ],
            allies_status=[
                {
                    "id": e.entity_id,
                    "hp": e.hp,
                    "max_hp": e.max_hp,
                    "x": e.position[0],
                    "y": e.position[1]
                }
                for e in perception.allies
            ],
            self_status={
                "id": character.character_id,
                "hp": character.entity.hp,
                "max_hp": character.entity.max_hp,
                "x": character.entity.position[0],
                "y": character.entity.position[1],
                "level": character.data.get("level", 1),
                "weapon_range": character.data.get("weapon_range", 5)
            }
        )
        
        # Try bot decisions first (fast)
        if self.in_combat:
            from mechanical_bot import BotType
            bot_decisions = character.bot_swarm.execute_by_type(
                bot_perception,
                BotType.COMBAT
            )
            
            # Get best bot decision
            best_bot = character.bot_swarm.get_best_decision(bot_decisions)
            
            if best_bot and not best_bot.should_escalate:
                # Bot can handle it
                result["decision_source"] = f"bot:{best_bot.bot_name}"
                result["action"] = best_bot.action.action_type
                result["confidence"] = best_bot.confidence
                result["time_ms"] = best_bot.execution_time_ms
                
                self.metrics["bot_decisions"] += 1
                
                return result
            
            # Need to escalate to brain
            self.metrics["escalations"] += 1
        
        # Use brain for decision
        context = DecisionContext(
            decision_type=DecisionType.COMBAT if self.in_combat else DecisionType.SOCIAL,
            situation=self._describe_situation(perception),
            urgency=0.8 if self.in_combat else 0.3,
            stakes=0.6 if self.in_combat else 0.4,
            novelty=0.3,
            recent_events=self._get_recent_events(perception),
            active_goals=character.data.get("goals", [])
        )
        
        brain_decision = await character.brain.make_decision(context)
        
        result["decision_source"] = "brain"
        result["action"] = brain_decision.decision_text
        result["confidence"] = brain_decision.confidence
        result["time_ms"] = brain_decision.time_seconds * 1000
        
        self.metrics["brain_decisions"] += 1
        
        return result
    
    def _describe_situation(self, perception: PerceptionResult) -> str:
        """Create situation description from perception"""
        parts = []
        
        if perception.enemies:
            enemies_desc = ", ".join(e.entity_id for e in perception.enemies[:3])
            parts.append(f"You see enemies: {enemies_desc}")
        
        if perception.allies:
            allies_desc = ", ".join(e.entity_id for e in perception.allies[:3])
            parts.append(f"Your allies: {allies_desc}")
        
        if perception.new_entities:
            parts.append(f"New arrivals: {', '.join(perception.new_entities)}")
        
        return ". ".join(parts) if parts else "The situation is calm."
    
    def _get_recent_events(self, perception: PerceptionResult) -> List[str]:
        """Extract recent events from perception"""
        events = []
        
        if perception.new_entities:
            events.append(f"{len(perception.new_entities)} new entities appeared")
        
        if perception.departed_entities:
            events.append(f"{len(perception.departed_entities)} entities departed")
        
        if perception.changed_entities:
            events.append(f"{len(perception.changed_entities)} entities changed")
        
        return events
    
    def _distance(
        self,
        pos1: tuple[float, float],
        pos2: tuple[float, float]
    ) -> float:
        """Calculate distance"""
        import math
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def _update_metrics(self, turn_results: Dict[str, Any]) -> None:
        """Update system metrics"""
        self.metrics["total_turns"] += 1
        
        total = self.metrics["total_turns"]
        turn_time = turn_results["turn_time_ms"]
        
        self.metrics["avg_turn_time_ms"] = (
            (self.metrics["avg_turn_time_ms"] * (total - 1) + turn_time) / total
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        metrics = self.metrics.copy()
        
        # Add component metrics
        metrics["llm_engine"] = self.llm_engine.get_metrics()
        metrics["brain_manager"] = self.brain_manager.get_all_metrics()
        metrics["perception_engine"] = self.perception_engine.get_metrics()
        
        # Calculate derived metrics
        total_decisions = metrics["bot_decisions"] + metrics["brain_decisions"]
        if total_decisions > 0:
            metrics["bot_usage_rate"] = metrics["bot_decisions"] / total_decisions
            metrics["brain_usage_rate"] = metrics["brain_decisions"] / total_decisions
            metrics["escalation_rate"] = metrics["escalations"] / metrics["bot_decisions"] if metrics["bot_decisions"] > 0 else 0
        
        return metrics


# Example usage / demo
async def demo_integrated_system():
    """Demonstrate the integrated Layer 3 system"""
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*60)
    print("LAYER 3 INTEGRATED SYSTEM DEMO")
    print("="*60)
    
    # Create system
    system = Layer3IntegratedSystem()
    
    try:
        # Start system
        print("\nStarting system...")
        await system.start()
        
        # Register player characters
        print("\nRegistering characters...")
        
        thorin = system.register_character(
            "thorin",
            {
                "name": "Thorin Ironforge",
                "class": "Fighter",
                "level": 3,
                "hp": 40,
                "max_hp": 50,
                "position": (0, 0),
                "attitude": "friendly",
                "weapon_range": 5,
                "goals": ["Protect the party", "Find the treasure"],
                "personality": {
                    "traits": ["brave", "loyal", "stubborn"],
                    "values": ["honor", "clan", "duty"],
                    "speaking_style": "gruff and direct"
                }
            },
            bot_params=CombatParameters(
                aggression=0.7,
                risk_tolerance=0.6,
                formation_preference=CombatRole.TANK
            )
        )
        
        elara = system.register_character(
            "elara",
            {
                "name": "Elara Moonwhisper",
                "class": "Ranger",
                "level": 3,
                "hp": 35,
                "max_hp": 40,
                "position": (10, 5),
                "attitude": "friendly",
                "weapon_range": 60,
                "goals": ["Protect nature", "Support allies"],
                "personality": {
                    "traits": ["calm", "observant", "wise"],
                    "values": ["nature", "balance", "peace"],
                    "speaking_style": "calm and thoughtful"
                }
            },
            bot_params=CombatParameters(
                aggression=0.5,
                risk_tolerance=0.4,
                preferred_range="ranged",
                formation_preference=CombatRole.DAMAGE
            )
        )
        
        # Add enemies
        system.perception_engine.register_entity(Entity(
            entity_id="orc_1",
            entity_type="npc",
            position=(25, 10),
            attitude="hostile",
            hp=30,
            max_hp=50
        ))
        
        system.perception_engine.register_entity(Entity(
            entity_id="goblin_1",
            entity_type="npc",
            position=(28, 8),
            attitude="hostile",
            hp=10,
            max_hp=15
        ))
        
        print(f"Registered {len(system.characters)} characters")
        
        # Start combat
        print("\n" + "-"*60)
        print("COMBAT BEGINS!")
        print("-"*60)
        
        system.in_combat = True
        
        # Process 5 combat turns
        for turn in range(1, 6):
            print(f"\n{'='*60}")
            print(f"TURN {turn}")
            print(f"{'='*60}")
            
            result = await system.process_turn()
            
            # Display results
            print(f"\nTurn time: {result['turn_time_ms']:.2f}ms")
            
            for char_id, char_result in result['characters'].items():
                char = system.characters[char_id]
                print(f"\n{char_result['name']}:")
                print(f"  Source: {char_result['decision_source']}")
                print(f"  Action: {char_result['action']}")
                print(f"  Confidence: {char_result['confidence']:.2f}")
                print(f"  Time: {char_result['time_ms']:.2f}ms")
            
            # Small delay between turns
            await asyncio.sleep(0.1)
        
        # End combat
        system.in_combat = False
        
        # Final metrics
        print(f"\n{'='*60}")
        print("FINAL METRICS")
        print(f"{'='*60}")
        
        metrics = system.get_metrics()
        
        print(f"\nSystem:")
        print(f"  Total turns: {metrics['total_turns']}")
        print(f"  Avg turn time: {metrics['avg_turn_time_ms']:.2f}ms")
        print(f"  Bot decisions: {metrics['bot_decisions']}")
        print(f"  Brain decisions: {metrics['brain_decisions']}")
        print(f"  Escalations: {metrics['escalations']}")
        print(f"  Bot usage: {metrics.get('bot_usage_rate', 0):.1%}")
        print(f"  Brain usage: {metrics.get('brain_usage_rate', 0):.1%}")
        
        print(f"\nLLM Engine:")
        llm_metrics = metrics['llm_engine']
        print(f"  Total requests: {llm_metrics['total_requests']}")
        print(f"  Successful: {llm_metrics['successful_requests']}")
        print(f"  Avg time: {llm_metrics['avg_time_seconds']:.2f}s")
        print(f"  VRAM peak: {llm_metrics['vram_peak_mb']}MB")
        
        print(f"\nPerception Engine:")
        perc_metrics = metrics['perception_engine']
        print(f"  Total batches: {perc_metrics['total_batches']}")
        print(f"  Avg batch time: {perc_metrics['avg_batch_time_ms']:.2f}ms")
        print(f"  Cache hit rate: {perc_metrics.get('cache_hit_rate', 0):.1%}")
        
    finally:
        # Stop system
        print("\nStopping system...")
        await system.stop()
        print("Demo complete!")


if __name__ == "__main__":
    asyncio.run(demo_integrated_system())
