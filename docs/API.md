# DMLog API Documentation

Complete API reference for the DMLog system modules.

## Table of Contents

- [Escalation Engine](#escalation-engine)
- [Memory System](#memory-system)
- [Vector Memory](#vector-memory)
- [Outcome Tracker](#outcome-tracker)
- [Training Data Collector](#training-data-collector)
- [Session Manager](#session-manager)

---

## Escalation Engine

**Module:** `escalation_engine.py`

Intelligent decision routing system that determines when to use Bots (fast, deterministic), Brain (LLM, personality-driven), or Human (critical decisions).

### Classes

#### `EscalationEngine`

Main engine for routing decisions to appropriate sources.

```python
from escalation_engine import EscalationEngine

engine = EscalationEngine(enable_training_data=True)
```

**Constructor Parameters:**
- `enable_training_data` (bool): Enable training data collection. Default: `True`

**Methods:**

##### `route_decision(context: DecisionContext) -> EscalationDecision`

Route a decision to the appropriate source.

**Parameters:**
- `context` (DecisionContext): Decision context including stakes, urgency, situation

**Returns:**
- `EscalationDecision`: Routing decision with source, confidence required, and metadata

**Example:**
```python
context = DecisionContext(
    character_id="warrior_1",
    situation_type="combat",
    situation_description="Goblin attacks with sword",
    stakes=0.7,
    urgency_ms=1000,
    character_hp_ratio=0.8
)

decision = engine.route_decision(context)
# decision.source -> DecisionSource.BOT
```

##### `should_escalate(result: DecisionResult, context: DecisionContext) -> Tuple[bool, Optional[EscalationReason]]`

Determine if a decision should be escalated to next level.

**Parameters:**
- `result` (DecisionResult): The decision that was made
- `context` (DecisionContext): Original decision context

**Returns:**
- `Tuple[bool, Optional[EscalationReason]]`: (should_escalate, reason)

##### `record_decision(result: DecisionResult) -> None`

Record a decision for history and learning.

##### `record_outcome(decision_id: str, success: bool, outcome_details: Optional[Dict]) -> None`

Record the outcome of a decision for learning.

##### `get_character_stats(character_id: str) -> Dict[str, Any]`

Get decision statistics for a character.

**Returns:**
- Dict with keys: `total_decisions`, `bot_decisions`, `brain_decisions`, `human_decisions`, `success_rate`, etc.

##### `get_global_stats() -> Dict[str, Any]`

Get global decision statistics.

#### `DecisionContext`

Context for a decision that needs routing.

**Attributes:**
- `character_id` (str): Character making the decision
- `situation_type` (str): Type of situation (combat, social, exploration, planning)
- `situation_description` (str): Description of the situation
- `stakes` (float): 0-1 importance level
- `urgency_ms` (Optional[int]): Time available for decision
- `character_hp_ratio` (float): Current HP ratio (0-1)
- `available_resources` (Dict[str, int]): Available resources
- `similar_decisions_count` (int): How many times seen similar
- `recent_failures` (int): Recent failed decisions

#### `EscalationDecision`

Result of escalation routing.

**Attributes:**
- `source` (DecisionSource): BOT, BRAIN, HUMAN, or OVERRIDE
- `reason` (Optional[EscalationReason]): Why routed this way
- `confidence_required` (float): Minimum confidence needed
- `time_budget_ms` (Optional[int]): Time allowed for decision
- `allow_fallback` (bool): Whether fallback is allowed
- `metadata` (Dict[str, Any]): Additional routing metadata

#### `DecisionResult`

Result of a routed decision.

**Attributes:**
- `decision_id` (str): Unique decision identifier
- `source` (DecisionSource): Where decision came from
- `action` (str): Action taken
- `confidence` (float): Confidence level (0-1)
- `time_taken_ms` (float): Time to make decision
- `escalated_from` (Optional[DecisionSource]): Previous level if escalated
- `escalation_reason` (Optional[EscalationReason]): Reason for escalation
- `success` (Optional[bool]): Success status (set after outcome)
- `metadata` (Dict[str, Any]): Additional data

#### `EscalationThresholds`

Thresholds for escalation decisions.

**Attributes:**
- `bot_min_confidence` (float): Below this, escalate to brain. Default: 0.7
- `brain_min_confidence` (float): Below this, escalate to human. Default: 0.5
- `high_stakes_threshold` (float): Above this = high stakes. Default: 0.7
- `critical_stakes_threshold` (float): Above this = critical. Default: 0.9
- `urgent_time_ms` (int): Below this = urgent. Default: 500
- `critical_time_ms` (int): Below this = critical. Default: 100
- `novelty_threshold` (float): Above this = novel. Default: 0.6
- `hp_critical_threshold` (float): Below this = critical HP. Default: 0.2

### Enums

#### `DecisionSource`

Where the decision came from:
- `BOT`: Fast, deterministic
- `BRAIN`: LLM, personality-driven
- `HUMAN`: Human decision
- `OVERRIDE`: Emergency override

#### `EscalationReason`

Why a decision was escalated:
- `LOW_CONFIDENCE`: Confidence below threshold
- `HIGH_STAKES`: High importance situation
- `NOVEL_SITUATION`: Unseen situation
- `TIME_CRITICAL`: Very time-sensitive
- `CONFLICTING_BOTS`: Bot disagreement
- `SAFETY_CONCERN`: Critical HP/resources
- `CHARACTER_GROWTH`: Learning opportunity
- `PLAYER_REQUEST`: Player requested

---

## Memory System

**Module:** `memory_system.py`

6-tier memory hierarchy system inspired by neuroscience.

### Classes

#### `MemoryConsolidationEngine`

Main memory system with consolidation and autobiographical narrative.

```python
from memory_system import MemoryConsolidationEngine, MemoryType

engine = MemoryConsolidationEngine(character_id="character_1")
```

**Methods:**

##### `store_memory(content: str, memory_type: MemoryType, importance: float, emotional_valence: float, participants: List[str], location: str) -> Memory`

Store a new memory and update consolidation tracking.

**Parameters:**
- `content` (str): What happened/was learned
- `memory_type` (MemoryType): Type of memory
- `importance` (float): 1-10 importance score
- `emotional_valence` (float): -1 (bad) to +1 (good)
- `participants` (List[str]): Who was involved
- `location` (str): Where it happened

**Returns:**
- `Memory`: The stored memory object

**Example:**
```python
memory = engine.store_memory(
    content="Defeated the dragon at the mountain peak",
    memory_type=MemoryType.EPISODIC,
    importance=9.0,
    emotional_valence=0.8,
    participants=["party", "dragon"],
    location="Mountain Peak"
)
```

##### `retrieve_memories(query: str, top_k: int, α_recency: float, α_importance: float, α_relevance: float) -> List[Memory]`

Weighted retrieval combining recency, importance, and semantic relevance.

**Parameters:**
- `query` (str): Search query
- `top_k` (int): Maximum results to return
- `α_recency` (float): Weight for recency (default 1.0)
- `α_importance` (float): Weight for importance (default 1.0)
- `α_relevance` (float): Weight for semantic relevance (default 1.0)

**Returns:**
- `List[Memory]`: Retrieved memories, ranked by combined score

##### `reflection_consolidation() -> Dict[str, Any]`

Immediate reflection consolidation (insights phase). Triggered when importance accumulator >= threshold.

**Returns:**
- Dict with `triggered`, `reflection_id`, `memories_processed`, `reflection_summary`

##### `episodic_to_semantic_consolidation() -> Dict[str, Any]`

Sleep-like consolidation: Episodic → Semantic (hours/days to weeks).

**Returns:**
- Dict with consolidation results including patterns created

##### `generate_autobiographical_narrative() -> AutobiographicalNarrative`

Generate coherent life story from memories, landmarks, and themes.

**Returns:**
- `AutobiographicalNarrative`: Life story with themes, traits, coherence score

#### `Memory`

Individual memory unit.

**Attributes:**
- `id` (str): Unique identifier
- `content` (str): What happened/was learned
- `memory_type` (MemoryType): Type of memory
- `timestamp` (datetime): When it occurred
- `importance` (float): 1-10 scale
- `emotional_valence` (float): -1 to +1
- `participants` (List[str]): Who was involved
- `location` (str): Where it happened
- `access_count` (int): Times retrieved
- `last_accessed` (Optional[datetime]): Last retrieval time
- `consolidated` (bool): Has moved to semantic
- `is_temporal_landmark` (bool): Is this a landmark memory
- `landmark_type` (Optional[str]): Type of landmark

#### `AutobiographicalNarrative`

Life story constructed from memories.

**Attributes:**
- `character_id` (str): Character this narrative is for
- `narrative` (str): Coherent life story text
- `key_themes` (List[str]): Main themes in memories
- `core_identity_traits` (Dict[str, float]): Personality traits
- `generated_at` (datetime): When narrative was generated
- `memory_ids_used` (List[str]): Memories included
- `coherence_score` (float): 0-1 how coherent is the narrative

#### `IdentityPersistenceSystem`

Maintains consistent identity while allowing growth.

```python
from memory_system import IdentityPersistenceSystem

identity = IdentityPersistenceSystem(
    character_id="char_1",
    core_traits={
        "openness": 0.8,
        "conscientiousness": 0.6,
        "extraversion": 0.5,
        "agreeableness": 0.7,
        "neuroticism": 0.3
    }
)
```

**Methods:**

##### `update_from_behavior(behavior_embedding: np.ndarray, confidence: float)`

Update temporal traits based on observed behavior.

##### `get_identity_coherence_index(recent_memories: List[Memory], window_days: int) -> float`

Calculate Identity Coherence Index (ICI).

**Returns:**
- `float`: >0.7 healthy, 0.4-0.7 monitor, <0.4 intervention

##### `get_identity_reinforcement_prompt() -> str`

Generate prompt to reinforce core identity.

### Enums

#### `MemoryType`

Hierarchical memory tiers:
- `WORKING`: Current attention (LLM context)
- `MID_TERM`: Session buffer (1-6 hours)
- `LONG_TERM`: Consolidated storage (1+ weeks)
- `EPISODIC`: Specific events "what-where-when"
- `SEMANTIC`: Consolidated patterns & facts
- `PROCEDURAL`: Skills & learned behaviors

#### `MemoryImportance`

Importance scoring levels:
- `FORGOTTEN`: 1.0
- `ROUTINE`: 3.0
- `NOTABLE`: 6.0
- `SIGNIFICANT`: 8.0
- `CORE_IDENTITY`: 10.0

---

## Vector Memory

**Module:** `vector_memory.py`

High-performance semantic memory retrieval using Qdrant vector database.

### Classes

#### `QdrantMemoryStore`

Vector memory store using Qdrant.

```python
from vector_memory import QdrantMemoryStore, MemoryVector

store = QdrantMemoryStore(
    character_id="char_1",
    qdrant_url="http://localhost:6333",
    collection_name_prefix="character_memories_"
)
```

**Constructor Parameters:**
- `character_id` (str): Character ID
- `qdrant_url` (str): Qdrant server URL
- `collection_name_prefix` (str): Prefix for collection names

**Methods:**

##### `store_memory(memory_vector: MemoryVector) -> bool`

Store memory with embedding to Qdrant.

**Parameters:**
- `memory_vector` (MemoryVector): Memory to store

**Returns:**
- `bool`: True if successful

##### `retrieve_memories(query: str, top_k: int, filters: Optional[Dict], α_recency: float, α_importance: float, α_relevance: float) -> List[MemoryVector]`

Retrieve memories with weighted scoring.

**Parameters:**
- `query` (str): Search query
- `top_k` (int): Max results
- `filters` (Optional[Dict]): Filters for memory_type, consolidated
- `α_recency` (float): Recency weight (default 1.0)
- `α_importance` (float): Importance weight (default 1.0)
- `α_relevance` (float): Relevance weight (default 1.0)

**Returns:**
- `List[MemoryVector]`: Retrieved memories

##### `get_collection_stats() -> Dict[str, Any]`

Get statistics about this character's memory collection.

#### `MemoryVector`

Memory with embedding and metadata.

**Attributes:**
- `id` (str): Unique identifier
- `content` (str): Memory content
- `embedding` (Optional[List[float]]): Vector embedding
- `character_id` (str): Character this belongs to
- `timestamp` (str): ISO format timestamp
- `memory_type` (str): Type of memory
- `importance` (float): 1-10 importance
- `emotional_valence` (float): -1 to +1
- `participants` (List[str]): Who was involved
- `location` (str): Where it happened
- `consolidated` (bool): Has been consolidated
- `is_temporal_landmark` (bool): Is a landmark
- `landmark_type` (Optional[str]): Landmark type
- `access_count` (int): Times accessed

#### `EmbeddingModel`

Wrapper for embedding generation.

```python
from vector_memory import EmbeddingModel

model = EmbeddingModel(model_name="all-MiniLM-L6-v2")
embedding = model.encode("Text to encode")
```

**Methods:**

##### `encode(text: str) -> Optional[List[float]]`

Generate embedding for text.

---

## Outcome Tracker

**Module:** `outcome_tracker.py`

Tracks decision outcomes with sophisticated reward signals.

### Classes

#### `OutcomeTracker`

Tracks and analyzes decision outcomes with reward signals.

```python
from outcome_tracker import OutcomeTracker, RewardDomain

tracker = OutcomeTracker()
```

**Methods:**

##### `track_immediate_outcome(decision_id: str, description: str, success: bool, context: Dict) -> OutcomeRecord`

Track an immediate outcome (happens right after decision).

**Parameters:**
- `decision_id` (str): ID of the decision
- `description` (str): What happened
- `success` (bool): Whether it succeeded
- `context` (Dict): Decision context for reward calculation

**Returns:**
- `OutcomeRecord`: The recorded outcome

##### `track_delayed_outcome(decision_id: str, description: str, success: bool, context: Dict, outcome_type: OutcomeType, related_decisions: Optional[List[str]]) -> OutcomeRecord`

Track a delayed outcome (happens later).

##### `get_aggregate_reward(decision_id: str, domain: Optional[RewardDomain]) -> float`

Get aggregate reward for a decision.

##### `get_success_rate(decision_type: Optional[str]) -> float`

Get overall success rate.

##### `analyze_decision_quality(decision_id: str) -> Dict[str, Any]`

Analyze the quality of a decision based on its outcomes.

#### `OutcomeRecord`

Record of a decision outcome.

**Attributes:**
- `decision_id` (str): Decision this outcome is for
- `outcome_type` (OutcomeType): IMMEDIATE, SHORT_TERM, or LONG_TERM
- `timestamp` (float): Unix timestamp
- `description` (str): What happened
- `success` (bool): Whether it succeeded
- `rewards` (List[RewardSignal]): Calculated rewards
- `related_decisions` (List[str]): Related decision IDs
- `causal_chain` (List[str]): Causal chain of decisions
- `metadata` (Dict[str, Any]): Additional data

#### `RewardSignal`

Calculated reward signal for an outcome.

**Attributes:**
- `domain` (RewardDomain): COMBAT, SOCIAL, EXPLORATION, RESOURCE, STRATEGIC
- `value` (float): -1.0 to 1.0 reward value
- `confidence` (float): 0.0 to 1.0 confidence in reward
- `components` (Dict[str, float]): Breakdown of reward
- `reasoning` (str): Explanation of reward

### Enums

#### `OutcomeType`

Types of outcomes:
- `IMMEDIATE`: Happens right away
- `SHORT_TERM`: Within same encounter (5-10 turns)
- `LONG_TERM`: Multiple encounters (session-wide)

#### `RewardDomain`

Domains for reward calculation:
- `COMBAT`: Combat-related rewards
- `SOCIAL`: Social interaction rewards
- `EXPLORATION`: Discovery rewards
- `RESOURCE`: Gold, XP, items
- `STRATEGIC`: Long-term positioning

---

## Training Data Collector

**Module:** `training_data_collector.py`

Collects gameplay decisions for training character models.

### Classes

#### `TrainingDataCollector`

Collects gameplay decisions for training.

```python
from training_data_collector import TrainingDataCollector

collector = TrainingDataCollector(db_path="data/decisions.db")
```

**Constructor Parameters:**
- `db_path` (str): Path to SQLite database file

**Methods:**

##### `start_session(session_id: Optional[str], session_notes: str, character_ids: Optional[List[str]], tags: Optional[List[str]]) -> str`

Start a new gameplay session.

**Returns:**
- `str`: Session ID

##### `end_session() -> Optional[Dict[str, Any]]`

End the current session.

**Returns:**
- Optional session summary

##### `log_decision(character_id: str, situation_context: Dict, decision: Dict, session_id: Optional[str]) -> Optional[str]`

Log a gameplay decision.

**Parameters:**
- `character_id` (str): Character making the decision
- `situation_context` (Dict): Game state and context
- `decision` (Dict): Decision details
- `session_id` (Optional[str]): Session ID

**Returns:**
- `str`: Decision ID if logged, None if rejected

##### `update_outcome(decision_id: str, outcome: Dict, success: bool) -> None`

Update a decision with its outcome.

##### `get_decisions_for_character(character_id: str, session_id: Optional[str], limit: Optional[int], training_eligible_only: bool, include_outcomes: bool) -> List[Dict]`

Retrieve decisions for a character.

##### `get_statistics(character_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]`

Get statistics about collected data.

#### `CharacterDataSettings`

Privacy and data collection settings per character.

**Attributes:**
- `character_id` (str): Character ID
- `enabled` (bool): Is collection enabled
- `collect_bot_decisions` (bool): Collect bot decisions
- `collect_brain_decisions` (bool): Collect brain decisions
- `collect_human_overrides` (bool): Collect human decisions
- `retention_days` (int): Days to keep data
- `training_eligible` (bool): Can be used for training

---

## Session Manager

**Module:** `session_manager.py`

Enhanced session management with metrics and growth tracking.

### Classes

#### `SessionManager`

Manages gameplay sessions with character growth tracking.

```python
from session_manager import SessionManager

manager = SessionManager()
```

**Methods:**

##### `start_session(session_id: Optional[str], character_ids: Optional[List[str]], notes: str, tags: Optional[List[str]]) -> str`

Start a new session.

**Returns:**
- `str`: Session ID

##### `end_session(session_id: str) -> SessionMetrics`

End a session and calculate metrics.

**Returns:**
- `SessionMetrics`: Final session metrics

##### `record_decision(session_id: str, character_id: str, decision_data: Dict, outcome_data: Optional[Dict]) -> None`

Record a decision in the session.

##### `get_session_summary(session_id: str) -> Dict[str, Any]`

Get session summary.

##### `get_statistics() -> Dict[str, Any]`

Get session statistics.

#### `SessionMetrics`

Metrics for a completed session.

**Attributes:**
- `session_id` (str): Session identifier
- `total_decisions` (int): Total decisions made
- `total_successes` (int): Successful decisions
- `total_session_reward` (float): Sum of all rewards
- `characters_improved` (int): Characters who improved
- `avg_growth_score` (float): Average growth across characters
- `teaching_moments` (int): Low-quality decisions to learn from
- `session_duration_seconds` (float): Session length

### Enums

#### `SessionPhase`

Phases of a session:
- `ACTIVE`: Currently running
- `INTERMISSION`: Paused
- `COMPLETE`: Finished

---

## Usage Examples

### Complete Decision Flow

```python
from escalation_engine import EscalationEngine, DecisionContext, DecisionResult, DecisionSource
from outcome_tracker import OutcomeTracker

# Initialize systems
escalation = EscalationEngine(enable_training_data=True)
outcome_tracker = OutcomeTracker()

# Create decision context
context = DecisionContext(
    character_id="warrior_1",
    situation_type="combat",
    situation_description="Goblin attacks party",
    stakes=0.7,
    urgency_ms=1000,
    character_hp_ratio=0.8
)

# Route decision
routing = escalation.route_decision(context)

# Make decision (simulated)
result = DecisionResult(
    decision_id="dec_001",
    source=routing.source,
    action="Attack with battleaxe",
    confidence=0.85,
    time_taken_ms=45.0,
    metadata={"character_id": "warrior_1"}
)

# Record decision
escalation.record_decision(result)

# Track outcome
outcome = outcome_tracker.track_immediate_outcome(
    decision_id="dec_001",
    description="Hit goblin for 12 damage, goblin defeated",
    success=True,
    context={"decision_type": "combat_action"}
)

# Record outcome for learning
escalation.record_outcome("dec_001", success=True, outcome_details={
    "immediate": "Hit for 12 damage",
    "delayed": "Goblin defeated"
})
```

### Memory Management

```python
from memory_system import MemoryConsolidationEngine, MemoryType

# Initialize memory system
memory = MemoryConsolidationEngine("character_1")

# Store episodic memory
episodic = memory.store_memory(
    content="Fought goblins near the cave entrance",
    memory_type=MemoryType.EPISODIC,
    importance=7.0,
    emotional_valence=0.3,
    participants=["goblins", "party"],
    location="Cave Entrance"
)

# Retrieve relevant memories
relevant = memory.retrieve_memories(
    query="combat goblins",
    top_k=5,
    α_recency=1.0,
    α_importance=1.5,
    α_relevance=1.0
)

# Trigger consolidation
reflection = memory.reflection_consolidation()

# Generate autobiographical narrative
narrative = memory.generate_autobiographical_narrative()
print(narrative.narrative)
```

### Vector Memory with Qdrant

```python
from vector_memory import QdrantMemoryStore, MemoryVector

# Initialize store
store = QdrantMemoryStore(
    character_id="character_1",
    qdrant_url="http://localhost:6333"
)

# Store memory
memory = MemoryVector(
    id="mem_001",
    content="Defeated the dragon at the mountain peak",
    character_id="character_1",
    timestamp=datetime.now().isoformat(),
    memory_type="episodic",
    importance=9.0,
    emotional_valence=0.8
)

store.store_memory(memory)

# Retrieve with weighted scoring
results = store.retrieve_memories(
    query="dragon combat victory",
    top_k=10,
    α_recency=0.5,
    α_importance=2.0,
    α_relevance=1.0
)
```
