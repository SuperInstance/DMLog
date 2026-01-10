"""
Perception Batching Engine

Efficiently processes perception for multiple characters in a single pass.
Reduces redundant computation and enables real-time gameplay with 4-6 characters.

Key Features:
- Batch visual perception (line of sight, visibility)
- Batch audio perception (range-based hearing)
- Batch status perception (buffs, debuffs, conditions)
- Spatial indexing for fast queries
- Delta updates (only changed data)
- Attention system (what matters to each character)
"""

import time
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import math
import logging

logger = logging.getLogger(__name__)


class PerceptionType(Enum):
    """Types of perception"""
    VISUAL = "visual"
    AUDIO = "audio"
    STATUS = "status"
    SOCIAL = "social"
    TERRAIN = "terrain"


@dataclass
class Entity:
    """Any entity that can be perceived"""
    entity_id: str
    entity_type: str  # "character", "npc", "object", "terrain"
    position: Tuple[float, float]
    
    # Visual properties
    visible: bool = True
    size: str = "medium"  # "tiny", "small", "medium", "large", "huge"
    description: str = ""
    
    # Audio properties
    noise_level: float = 0.0  # 0=silent, 1=very loud
    
    # Status
    hp: Optional[int] = None
    max_hp: Optional[int] = None
    conditions: List[str] = field(default_factory=list)
    
    # Social
    attitude: str = "neutral"  # "hostile", "neutral", "friendly"
    relationship_tags: List[str] = field(default_factory=list)
    
    # Metadata
    last_updated: float = field(default_factory=time.time)


@dataclass
class PerceptionResult:
    """Perception result for a single character"""
    character_id: str
    
    # Visual perception
    visible_entities: List[Entity] = field(default_factory=list)
    visible_terrain: List[str] = field(default_factory=list)
    
    # Audio perception
    audible_entities: List[Entity] = field(default_factory=list)
    audible_sounds: List[str] = field(default_factory=list)
    
    # Status perception
    allies: List[Entity] = field(default_factory=list)
    enemies: List[Entity] = field(default_factory=list)
    neutrals: List[Entity] = field(default_factory=list)
    
    # Social perception
    relationships: Dict[str, str] = field(default_factory=dict)
    mood_indicators: List[str] = field(default_factory=list)
    
    # Changes since last perception
    new_entities: List[str] = field(default_factory=list)
    departed_entities: List[str] = field(default_factory=list)
    changed_entities: List[str] = field(default_factory=list)
    
    # Metadata
    perception_time_ms: float = 0.0
    is_delta: bool = False


class SpatialIndex:
    """
    Spatial index for fast proximity queries
    
    Simple grid-based index for O(1) average case proximity lookups.
    """
    
    def __init__(self, cell_size: float = 50.0):
        """
        Initialize spatial index
        
        Args:
            cell_size: Size of grid cells
        """
        self.cell_size = cell_size
        self.grid: Dict[Tuple[int, int], List[Entity]] = {}
        self.entity_cells: Dict[str, Tuple[int, int]] = {}
    
    def _get_cell(self, position: Tuple[float, float]) -> Tuple[int, int]:
        """Get grid cell for position"""
        return (
            int(position[0] // self.cell_size),
            int(position[1] // self.cell_size)
        )
    
    def add_entity(self, entity: Entity) -> None:
        """Add entity to index"""
        cell = self._get_cell(entity.position)
        
        # Add to grid
        if cell not in self.grid:
            self.grid[cell] = []
        self.grid[cell].append(entity)
        
        # Track entity's cell
        self.entity_cells[entity.entity_id] = cell
    
    def remove_entity(self, entity_id: str) -> None:
        """Remove entity from index"""
        if entity_id in self.entity_cells:
            cell = self.entity_cells[entity_id]
            if cell in self.grid:
                self.grid[cell] = [e for e in self.grid[cell] if e.entity_id != entity_id]
            del self.entity_cells[entity_id]
    
    def update_entity(self, entity: Entity) -> None:
        """Update entity position"""
        self.remove_entity(entity.entity_id)
        self.add_entity(entity)
    
    def query_radius(
        self,
        position: Tuple[float, float],
        radius: float
    ) -> List[Entity]:
        """
        Query entities within radius
        
        Args:
            position: Center position
            radius: Search radius
            
        Returns:
            List of entities within radius
        """
        # Get all cells that might contain entities in radius
        cell_radius = int(math.ceil(radius / self.cell_size))
        center_cell = self._get_cell(position)
        
        entities = []
        
        for dx in range(-cell_radius, cell_radius + 1):
            for dy in range(-cell_radius, cell_radius + 1):
                cell = (center_cell[0] + dx, center_cell[1] + dy)
                if cell in self.grid:
                    # Check each entity in cell
                    for entity in self.grid[cell]:
                        distance = self._distance(position, entity.position)
                        if distance <= radius:
                            entities.append(entity)
        
        return entities
    
    def _distance(
        self,
        pos1: Tuple[float, float],
        pos2: Tuple[float, float]
    ) -> float:
        """Calculate distance between positions"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def clear(self) -> None:
        """Clear all entities from index"""
        self.grid.clear()
        self.entity_cells.clear()


class PerceptionBatchEngine:
    """
    Batch perception processing engine
    
    Efficiently processes perception for multiple characters simultaneously,
    using spatial indexing and caching to minimize redundant computation.
    """
    
    def __init__(self):
        """Initialize perception engine"""
        self.spatial_index = SpatialIndex(cell_size=50.0)
        self.entities: Dict[str, Entity] = {}
        
        # Previous perception for delta updates
        self.previous_perceptions: Dict[str, PerceptionResult] = {}
        
        # Perception ranges (configurable)
        self.visual_range = 60.0
        self.audio_range = 100.0
        self.status_range = 60.0  # Can see allies/enemies status
        
        # Metrics
        self.metrics = {
            "total_batches": 0,
            "total_characters": 0,
            "avg_batch_time_ms": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        logger.info("PerceptionBatchEngine initialized")
    
    def register_entity(self, entity: Entity) -> None:
        """
        Register an entity in the world
        
        Args:
            entity: Entity to register
        """
        self.entities[entity.entity_id] = entity
        self.spatial_index.add_entity(entity)
        entity.last_updated = time.time()
    
    def unregister_entity(self, entity_id: str) -> None:
        """
        Unregister an entity
        
        Args:
            entity_id: Entity to remove
        """
        if entity_id in self.entities:
            self.spatial_index.remove_entity(entity_id)
            del self.entities[entity_id]
    
    def update_entity(self, entity: Entity) -> None:
        """
        Update an entity's state
        
        Args:
            entity: Updated entity
        """
        if entity.entity_id in self.entities:
            # Update position in spatial index if changed
            old_pos = self.entities[entity.entity_id].position
            if old_pos != entity.position:
                self.spatial_index.update_entity(entity)
            
            # Update entity
            self.entities[entity.entity_id] = entity
            entity.last_updated = time.time()
    
    def batch_perceive(
        self,
        character_ids: List[str],
        use_delta: bool = True
    ) -> Dict[str, PerceptionResult]:
        """
        Process perception for multiple characters in one batch
        
        Args:
            character_ids: Characters to process perception for
            use_delta: Use delta updates if possible
            
        Returns:
            Dict mapping character_id to perception result
        """
        start_time = time.time()
        results = {}
        
        for char_id in character_ids:
            if char_id not in self.entities:
                logger.warning(f"Character not registered: {char_id}")
                continue
            
            character = self.entities[char_id]
            
            # Decide if we can use delta update
            can_use_delta = (
                use_delta and
                char_id in self.previous_perceptions and
                self._is_recent(char_id)
            )
            
            if can_use_delta:
                result = self._delta_perceive(character)
                self.metrics["cache_hits"] += 1
            else:
                result = self._full_perceive(character)
                self.metrics["cache_misses"] += 1
            
            # Calculate perception time
            result.perception_time_ms = (time.time() - start_time) * 1000
            
            results[char_id] = result
            self.previous_perceptions[char_id] = result
        
        # Update metrics
        self._update_metrics(len(character_ids), time.time() - start_time)
        
        return results
    
    def _full_perceive(self, character: Entity) -> PerceptionResult:
        """
        Perform full perception (compute everything)
        
        Args:
            character: Character perceiving
            
        Returns:
            Complete perception result
        """
        result = PerceptionResult(
            character_id=character.entity_id,
            is_delta=False
        )
        
        # Visual perception
        visible = self._perceive_visual(character)
        result.visible_entities = visible
        
        # Audio perception
        audible = self._perceive_audio(character)
        result.audible_entities = audible
        result.audible_sounds = [f"Sound from {e.entity_id}" for e in audible if e.noise_level > 0.3]
        
        # Status perception (categorize entities)
        for entity in visible:
            if entity.entity_id == character.entity_id:
                continue
            
            if entity.attitude == "friendly":
                result.allies.append(entity)
            elif entity.attitude == "hostile":
                result.enemies.append(entity)
            else:
                result.neutrals.append(entity)
        
        # Social perception
        result.relationships = self._perceive_relationships(character, visible)
        
        return result
    
    def _delta_perceive(self, character: Entity) -> PerceptionResult:
        """
        Perform delta perception (only changes since last time)
        
        Args:
            character: Character perceiving
            
        Returns:
            Perception result with deltas
        """
        # Get previous perception
        prev = self.previous_perceptions[character.entity_id]
        
        # Start with previous as base
        result = PerceptionResult(
            character_id=character.entity_id,
            is_delta=True,
            visible_entities=prev.visible_entities.copy(),
            audible_entities=prev.audible_entities.copy(),
            allies=prev.allies.copy(),
            enemies=prev.enemies.copy(),
            neutrals=prev.neutrals.copy(),
            relationships=prev.relationships.copy()
        )
        
        # Detect changes
        prev_visible_ids = {e.entity_id for e in prev.visible_entities}
        curr_visible = self._perceive_visual(character)
        curr_visible_ids = {e.entity_id for e in curr_visible}
        
        # New entities
        result.new_entities = list(curr_visible_ids - prev_visible_ids)
        
        # Departed entities
        result.departed_entities = list(prev_visible_ids - curr_visible_ids)
        
        # Changed entities (moved, status changed, etc.)
        for entity in curr_visible:
            if entity.entity_id in prev_visible_ids:
                prev_entity = next(e for e in prev.visible_entities if e.entity_id == entity.entity_id)
                if self._has_changed(prev_entity, entity):
                    result.changed_entities.append(entity.entity_id)
        
        # Update with current perception
        result.visible_entities = curr_visible
        
        # Recategorize if needed
        if result.new_entities or result.changed_entities:
            result.allies = []
            result.enemies = []
            result.neutrals = []
            
            for entity in curr_visible:
                if entity.entity_id == character.entity_id:
                    continue
                
                if entity.attitude == "friendly":
                    result.allies.append(entity)
                elif entity.attitude == "hostile":
                    result.enemies.append(entity)
                else:
                    result.neutrals.append(entity)
        
        return result
    
    def _perceive_visual(self, character: Entity) -> List[Entity]:
        """
        Perceive visible entities
        
        Args:
            character: Perceiving character
            
        Returns:
            List of visible entities
        """
        # Query spatial index
        nearby = self.spatial_index.query_radius(
            character.position,
            self.visual_range
        )
        
        # Filter by visibility
        visible = []
        for entity in nearby:
            if not entity.visible:
                continue
            
            # Check line of sight (simplified - would integrate with terrain)
            if self._has_line_of_sight(character.position, entity.position):
                visible.append(entity)
        
        return visible
    
    def _perceive_audio(self, character: Entity) -> List[Entity]:
        """
        Perceive audible entities
        
        Args:
            character: Perceiving character
            
        Returns:
            List of audible entities
        """
        nearby = self.spatial_index.query_radius(
            character.position,
            self.audio_range
        )
        
        # Filter by noise level
        audible = [e for e in nearby if e.noise_level > 0.1]
        
        return audible
    
    def _perceive_relationships(
        self,
        character: Entity,
        visible_entities: List[Entity]
    ) -> Dict[str, str]:
        """
        Perceive social relationships
        
        Args:
            character: Perceiving character
            visible_entities: Visible entities
            
        Returns:
            Dict mapping entity_id to relationship status
        """
        relationships = {}
        
        for entity in visible_entities:
            if entity.entity_id == character.entity_id:
                continue
            
            # Simplified relationship detection
            if "friend" in entity.relationship_tags:
                relationships[entity.entity_id] = "friendly"
            elif "enemy" in entity.relationship_tags:
                relationships[entity.entity_id] = "hostile"
            else:
                relationships[entity.entity_id] = entity.attitude
        
        return relationships
    
    def _has_line_of_sight(
        self,
        pos1: Tuple[float, float],
        pos2: Tuple[float, float]
    ) -> bool:
        """
        Check if there's line of sight between positions
        
        Args:
            pos1: First position
            pos2: Second position
            
        Returns:
            True if line of sight exists
        """
        # Simplified - would check for terrain obstacles
        return True
    
    def _has_changed(self, prev: Entity, curr: Entity) -> bool:
        """Check if entity has changed significantly"""
        return (
            prev.position != curr.position or
            prev.hp != curr.hp or
            prev.conditions != curr.conditions or
            prev.attitude != curr.attitude
        )
    
    def _is_recent(self, character_id: str, max_age_ms: float = 500.0) -> bool:
        """Check if previous perception is recent enough for delta"""
        if character_id not in self.previous_perceptions:
            return False
        
        prev = self.previous_perceptions[character_id]
        age_ms = (time.time() - self.entities[character_id].last_updated) * 1000
        
        return age_ms < max_age_ms
    
    def _update_metrics(self, num_characters: int, batch_time: float) -> None:
        """Update engine metrics"""
        total = self.metrics["total_batches"]
        
        self.metrics["total_batches"] += 1
        self.metrics["total_characters"] += num_characters
        
        batch_time_ms = batch_time * 1000
        self.metrics["avg_batch_time_ms"] = (
            (self.metrics["avg_batch_time_ms"] * total + batch_time_ms) / (total + 1)
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get engine metrics"""
        metrics = self.metrics.copy()
        
        if metrics["total_batches"] > 0:
            metrics["avg_characters_per_batch"] = (
                metrics["total_characters"] / metrics["total_batches"]
            )
        else:
            metrics["avg_characters_per_batch"] = 0
        
        total_queries = metrics["cache_hits"] + metrics["cache_misses"]
        if total_queries > 0:
            metrics["cache_hit_rate"] = metrics["cache_hits"] / total_queries
        else:
            metrics["cache_hit_rate"] = 0.0
        
        return metrics
    
    def clear(self) -> None:
        """Clear all entities and caches"""
        self.entities.clear()
        self.spatial_index.clear()
        self.previous_perceptions.clear()


# Test perception engine
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*50)
    print("PERCEPTION BATCHING ENGINE TEST")
    print("="*50)
    
    # Create engine
    engine = PerceptionBatchEngine()
    
    # Register test entities
    print("\nRegistering entities...")
    
    # Player characters
    thorin = Entity(
        entity_id="thorin",
        entity_type="character",
        position=(0, 0),
        attitude="friendly",
        hp=40, max_hp=50
    )
    
    elara = Entity(
        entity_id="elara",
        entity_type="character",
        position=(10, 5),
        attitude="friendly",
        hp=35, max_hp=40
    )
    
    # Enemies
    orc1 = Entity(
        entity_id="orc_1",
        entity_type="npc",
        position=(25, 10),
        attitude="hostile",
        hp=30, max_hp=50,
        noise_level=0.6
    )
    
    goblin1 = Entity(
        entity_id="goblin_1",
        entity_type="npc",
        position=(30, 8),
        attitude="hostile",
        hp=10, max_hp=15
    )
    
    # Neutral
    merchant = Entity(
        entity_id="merchant",
        entity_type="npc",
        position=(50, 50),
        attitude="neutral",
        noise_level=0.3
    )
    
    for entity in [thorin, elara, orc1, goblin1, merchant]:
        engine.register_entity(entity)
    
    print(f"Registered {len(engine.entities)} entities")
    
    # Test 1: Batch perception
    print(f"\n{'-'*50}")
    print("TEST 1: Batch Perception")
    print(f"{'-'*50}")
    
    results = engine.batch_perceive(["thorin", "elara"], use_delta=False)
    
    for char_id, result in results.items():
        print(f"\n{char_id.upper()}:")
        print(f"  Visible entities: {len(result.visible_entities)}")
        print(f"  - Allies: {[e.entity_id for e in result.allies]}")
        print(f"  - Enemies: {[e.entity_id for e in result.enemies]}")
        print(f"  - Neutrals: {[e.entity_id for e in result.neutrals]}")
        print(f"  Audible entities: {len(result.audible_entities)}")
        print(f"  Perception time: {result.perception_time_ms:.2f}ms")
        print(f"  Is delta: {result.is_delta}")
    
    # Test 2: Delta updates
    print(f"\n{'-'*50}")
    print("TEST 2: Delta Updates")
    print(f"{'-'*50}")
    
    # Move an orc
    orc1.position = (20, 10)
    engine.update_entity(orc1)
    
    # Add a new enemy
    orc2 = Entity(
        entity_id="orc_2",
        entity_type="npc",
        position=(28, 12),
        attitude="hostile",
        hp=45, max_hp=50
    )
    engine.register_entity(orc2)
    
    # Batch perceive with delta
    results = engine.batch_perceive(["thorin", "elara"], use_delta=True)
    
    for char_id, result in results.items():
        print(f"\n{char_id.upper()}:")
        print(f"  Is delta: {result.is_delta}")
        if result.new_entities:
            print(f"  New entities: {result.new_entities}")
        if result.changed_entities:
            print(f"  Changed entities: {result.changed_entities}")
        print(f"  Perception time: {result.perception_time_ms:.2f}ms")
    
    # Test 3: Performance benchmark
    print(f"\n{'-'*50}")
    print("TEST 3: Performance Benchmark")
    print(f"{'-'*50}")
    
    # Run 100 batches
    for i in range(100):
        engine.batch_perceive(["thorin", "elara"], use_delta=True)
    
    metrics = engine.get_metrics()
    print(f"\nMetrics after 100 batches:")
    print(f"  Total batches: {metrics['total_batches']}")
    print(f"  Avg batch time: {metrics['avg_batch_time_ms']:.2f}ms")
    print(f"  Avg chars/batch: {metrics['avg_characters_per_batch']:.1f}")
    print(f"  Cache hit rate: {metrics['cache_hit_rate']:.2%}")
    
    print("\nPerception engine test complete!")
