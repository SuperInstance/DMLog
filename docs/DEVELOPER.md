# DMLog Developer Guide (Level 2)

**Complete Developer Documentation for the Temporal Consciousness D&D System**

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Environment Setup](#development-environment-setup)
3. [Project Structure](#project-structure)
4. [API Reference](#api-reference)
5. [Module Development](#module-development)
6. [Testing Guide](#testing-guide)
7. [Contributing Guidelines](#contributing-guidelines)
8. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

Before starting development, ensure you have:

- **Python 3.10+** - Required for type hinting and modern features
- **Docker & Docker Compose** - For running Qdrant vector database
- **OpenAI API Key** - For LLM integration (GPT-4)
- **Anthropic API Key** (Optional) - For Claude integration
- **Git** - For version control

### 5-Minute Setup

#### Step 1: Clone and Navigate

```bash
# Clone the repository
git clone https://github.com/ctothed/DMLog.git
cd DMLog/source_code
```

#### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

#### Step 3: Install Dependencies

```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Install development dependencies
pip install pytest pytest-cov black flake8 mypy
```

#### Step 4: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
# OPENAI_API_KEY=sk-your-key-here
# ANTHROPIC_API_KEY=sk-your-key-here
```

#### Step 5: Start Services

```bash
# Start Qdrant with Docker
docker-compose up -d

# Verify Qdrant is running
curl http://localhost:6333/health

# Run tests to verify setup
pytest backend/test_escalation_engine.py -v
```

---

## Development Environment Setup

### IDE Configuration

**VS Code Settings (`.vscode/settings.json`):**

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["backend/"],
  "editor.formatOnSave": true,
  "editor.rulers": [100]
}
```

**VS Code Extensions:**

- Python (Microsoft)
- Python Test Explorer (LittleFoxTeam)
- Pylance (Microsoft)
- GitLens (GitKraken)

### Pre-commit Hooks

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Run tests before committing
pytest backend/test_escalation_engine.py -q
# Check code style
black --check backend/
# Run linter
flake8 backend/
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

## Project Structure

### Directory Layout

```
DMLog/source_code/
├── backend/                          # Core Python modules
│   ├── escalation_engine.py          # Decision routing system
│   ├── memory_system.py              # 6-tier memory hierarchy
│   ├── vector_memory.py              # Qdrant vector store
│   ├── outcome_tracker.py            # Reward tracking
│   ├── training_data_collector.py    # Decision logging
│   ├── session_manager.py            # Session management
│   ├── api_server.py                 # FastAPI endpoints
│   ├── game_mechanics.py             # D&D 5e rules
│   ├── enhanced_character.py         # Character system
│   ├── character_brain.py            # Character AI
│   ├── combat_bots.py                # Combat AI
│   ├── social_bots.py                # Social AI
│   ├── llm_api_integration.py        # LLM providers
│   ├── local_llm_engine.py           # Local LLM support
│   ├── model_routing.py              # Model selection
│   ├── reflection_pipeline.py        # Post-session reflection
│   ├── advanced_consolidation.py     # Memory consolidation
│   ├── pathology_detection.py        # Memory issues
│   ├── cultural_transmission.py      # Skill sharing
│   ├── digital_twin.py               # Player learning
│   ├── dm_automation.py              # DM tools
│   ├── npc_manager.py                # NPC management
│   ├── perception_batch.py           # Batch processing
│   ├── metrics_dashboard.py          # System metrics
│   │
│   ├── test_*.py                     # Test files (70+ tests)
│   │
│   └── requirements.txt               # Python dependencies
│
├── docs/                             # Documentation
│   ├── API.md                        # API reference
│   ├── ARCHITECTURE.md               # System architecture
│   └── INSTALL.md                    # Installation guide
│
├── .env.example                      # Environment template
├── docker-compose.yml                # Docker services
├── Dockerfile                        # Container definition
├── setup.sh                          # Setup script
├── demo.py                           # Demo script
└── README.md                         # Project overview
```

### Module Dependencies

```
escalation_engine.py
    ├── training_data_collector.py
    │   └── outcome_tracker.py
    └── session_manager.py
        └── outcome_tracker.py

memory_system.py
    └── vector_memory.py
        ├── qdrant-client
        └── sentence-transformers

training_data_collector.py
    ├── outcome_tracker.py
    └── session_manager.py

api_server.py
    ├── escalation_engine.py
    ├── memory_system.py
    ├── game_mechanics.py
    └── enhanced_character.py
```

---

## API Reference

### REST API Endpoints

#### Campaign Management

**Create Campaign**

```http
POST /campaigns/create
Content-Type: application/json

{
  "campaign_name": "Lost Mine of Phandelver",
  "dm_id": "human_dm",
  "initial_world_lore": [
    "The town of Phandalin sits on the edge of the Sword Coast.",
    "Gundren Rockseeker has discovered Wave Echo Cave."
  ]
}
```

**Response:**
```json
{
  "campaign_id": "lost_mine_phandelver",
  "created_at": "2025-01-10T12:00:00Z",
  "world_lore_count": 2
}
```

#### Character Management

**Create Character**

```http
POST /characters/create
Content-Type: application/json

{
  "name": "Thorin Ironforge",
  "race": "Dwarf",
  "class_name": "Fighter",
  "level": 1,
  "personality_traits": ["Brave", "Stubborn", "Loyal"],
  "backstory": "A dwarf warrior seeking to reclaim his ancestral mine.",
  "strength": 16,
  "dexterity": 12,
  "constitution": 14,
  "intelligence": 10,
  "wisdom": 11,
  "charisma": 8
}
```

**Response:**
```json
{
  "character_id": "char_abc123",
  "name": "Thorin Ironforge",
  "created_at": "2025-01-10T12:00:00Z",
  "initial_hp": 12,
  "proficiency_bonus": 2
}
```

**Get Character**

```http
GET /characters/{character_id}
```

**Response:**
```json
{
  "character_id": "char_abc123",
  "name": "Thorin Ironforge",
  "race": "Dwarf",
  "class_name": "Fighter",
  "level": 1,
  "hp": 12,
  "max_hp": 12,
  "stats": {
    "strength": 16,
    "dexterity": 12,
    "constitution": 14,
    "intelligence": 10,
    "wisdom": 11,
    "charisma": 8
  },
  "memories_count": 15,
  "total_sessions": 3
}
```

**Get Character Memories**

```http
GET /characters/{character_id}/memories?limit=10&type=episodic
```

#### Session Management

**Create Session**

```http
POST /sessions/create
Content-Type: application/json

{
  "campaign_name": "Lost Mine of Phandelver",
  "session_number": 1
}
```

**Join Session**

```http
POST /sessions/join
Content-Type: application/json

{
  "session_id": "lost_mine_phandelver_session_1",
  "character_id": "char_abc123"
}
```

**Get Session Transcript**

```http
GET /sessions/{session_id}/transcript
```

#### Decision Making

**Route Decision**

```http
POST /decisions/route
Content-Type: application/json

{
  "character_id": "char_abc123",
  "situation_type": "combat",
  "situation_description": "Goblin attacks with sword",
  "stakes": 0.7,
  "urgency_ms": 1000,
  "character_hp_ratio": 0.8
}
```

**Response:**
```json
{
  "source": "bot",
  "reason": "routine_situation",
  "confidence_required": 0.7,
  "time_budget_ms": 1000,
  "allow_fallback": true
}
```

**Record Decision**

```http
POST /decisions/record
Content-Type: application/json

{
  "decision_id": "dec_001",
  "character_id": "char_abc123",
  "source": "bot",
  "action": "Attack with battleaxe",
  "confidence": 0.85,
  "time_taken_ms": 45.0
}
```

**Record Outcome**

```http
POST /decisions/outcome
Content-Type: application/json

{
  "decision_id": "dec_001",
  "success": true,
  "description": "Hit for 12 damage, goblin defeated"
}
```

### Python API Reference

#### EscalationEngine

```python
from escalation_engine import (
    EscalationEngine,
    DecisionContext,
    DecisionResult,
    DecisionSource,
    EscalationThresholds
)

# Initialize engine
engine = EscalationEngine(enable_training_data=True)

# Route decision
context = DecisionContext(
    character_id="char_001",
    situation_type="combat",
    situation_description="Goblin attacks",
    stakes=0.7,
    urgency_ms=1000
)
decision = engine.route_decision(context)

# Record decision
result = DecisionResult(
    decision_id="dec_001",
    source=decision.source,
    action="Attack",
    confidence=0.85,
    time_taken_ms=45.0
)
engine.record_decision(result)

# Record outcome
engine.record_outcome("dec_001", success=True)

# Get stats
stats = engine.get_character_stats("char_001")
```

#### MemoryConsolidationEngine

```python
from memory_system import (
    MemoryConsolidationEngine,
    MemoryType
)

# Initialize memory system
memory = MemoryConsolidationEngine(character_id="char_001")

# Store episodic memory
episodic = memory.store_memory(
    content="Fought goblins at the cave entrance",
    memory_type=MemoryType.EPISODIC,
    importance=7.0,
    emotional_valence=0.3,
    participants=["goblins", "party"],
    location="Cave Entrance"
)

# Retrieve memories
relevant = memory.retrieve_memories(
    query="combat goblins",
    top_k=5,
    alpha_recency=1.0,
    alpha_importance=1.5,
    alpha_relevance=1.0
)

# Trigger consolidation
reflection = memory.reflection_consolidation()
episodic_semantic = memory.episodic_to_semantic_consolidation()

# Generate narrative
narrative = memory.generate_autobiographical_narrative()
```

#### QdrantMemoryStore

```python
from vector_memory import (
    QdrantMemoryStore,
    MemoryVector
)
from datetime import datetime

# Initialize store
store = QdrantMemoryStore(
    character_id="char_001",
    qdrant_url="http://localhost:6333"
)

# Store memory
memory = MemoryVector(
    id="mem_001",
    content="Defeated the dragon at the mountain peak",
    character_id="char_001",
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
    alpha_recency=0.5,
    alpha_importance=2.0,
    alpha_relevance=1.0
)
```

#### OutcomeTracker

```python
from outcome_tracker import (
    OutcomeTracker,
    RewardDomain
)

tracker = OutcomeTracker()

# Track immediate outcome
outcome = tracker.track_immediate_outcome(
    decision_id="dec_001",
    description="Hit goblin for 15 damage",
    success=True,
    context={
        "decision_type": "combat_action",
        "damage_dealt": 15,
        "hp_remaining": 8
    }
)

# Get rewards
for reward in outcome.rewards:
    print(f"{reward.domain.value}: {reward.value:.3f}")

# Get aggregate reward
aggregate = tracker.get_aggregate_reward("dec_001")
```

#### TrainingDataCollector

```python
from training_data_collector import TrainingDataCollector

collector = TrainingDataCollector(db_path="data/decisions.db")

# Start session
session_id = collector.start_session(
    session_notes="Session 1 - Goblin cave",
    character_ids=["char_001", "char_002"],
    tags=["combat", "exploration"]
)

# Log decision
decision_id = collector.log_decision(
    character_id="char_001",
    situation_context={
        "situation_type": "combat",
        "stakes": 0.7
    },
    decision={
        "source": "bot",
        "action": "Attack",
        "confidence": 0.85
    },
    session_id=session_id
)

# Update outcome
collector.update_outcome(
    decision_id=decision_id,
    outcome={"success": True, "damage": 15},
    success=True
)

# End session
summary = collector.end_session()

# Export for training
training_data = collector.get_decisions_for_character(
    character_id="char_001",
    training_eligible_only=True
)
```

---

## Module Development

### Creating a New Decision Source

```python
from escalation_engine import DecisionSource, EscalationEngine

class CustomDecisionSource:
    """Custom decision source implementation"""

    def __init__(self, config: dict):
        self.config = config

    def decide(self, context: DecisionContext) -> str:
        """
        Make a decision based on context

        Args:
            context: Decision context

        Returns:
            Action description
        """
        # Your custom logic here
        return "Custom action"

    def get_confidence(self, context: DecisionContext) -> float:
        """Return confidence level for this decision"""
        return 0.8

# Register with engine
engine = EscalationEngine()
# Add custom handler
```

### Creating a New Memory Type

```python
from memory_system import MemoryType, Memory

# Add new memory type to enum
class ExtendedMemoryType(MemoryType):
    DREAM = "dream"           # Dream experiences
    VISION = "vision"         # Prophetic visions
    SOCIAL_BOND = "bond"      # Relationship memories

# Use custom memory type
memory.store_memory(
    content="Dreamed of a great dragon",
    memory_type=ExtendedMemoryType.DREAM,
    importance=8.0,
    emotional_valence=-0.5  # Nightmare
)
```

### Creating Custom Reward Domains

```python
from outcome_tracker import RewardDomain

# Add custom reward domain
class CustomRewardDomain(RewardDomain):
    DIPLOMATIC = "diplomatic"     # Diplomatic success
    CREATIVE = "creative"         # Creative solutions
    TEAMWORK = "teamwork"         # Team coordination

# Use in outcome tracking
outcome = tracker.track_immediate_outcome(
    decision_id="dec_001",
    description="Negotiated peace treaty",
    success=True,
    context={"domain": "diplomatic"}
)
```

---

## Testing Guide

### Running Tests

```bash
# Run all tests
pytest backend/ -v

# Run specific test file
pytest backend/test_escalation_engine.py -v

# Run with coverage
pytest backend/ --cov=backend --cov-report=html

# Run specific test
pytest backend/test_escalation_engine.py::test_route_decision -v

# Run tests matching pattern
pytest backend/ -k "escalation" -v
```

### Test Structure

```python
import pytest
from escalation_engine import (
    EscalationEngine,
    DecisionContext,
    DecisionSource
)

class TestEscalationEngine:
    """Test suite for EscalationEngine"""

    @pytest.fixture
    def engine(self):
        """Create engine for testing"""
        return EscalationEngine(enable_training_data=False)

    @pytest.fixture
    def sample_context(self):
        """Sample decision context"""
        return DecisionContext(
            character_id="test_char",
            situation_type="combat",
            situation_description="Test combat",
            stakes=0.5
        )

    def test_route_decision_bot(self, engine, sample_context):
        """Test bot routing for low stakes"""
        sample_context.stakes = 0.3
        decision = engine.route_decision(sample_context)
        assert decision.source == DecisionSource.BOT

    def test_route_decision_brain(self, engine, sample_context):
        """Test brain routing for high stakes"""
        sample_context.stakes = 0.8
        decision = engine.route_decision(sample_context)
        assert decision.source in [DecisionSource.BRAIN, DecisionSource.BOT]

    @pytest.mark.parametrize("stakes,expected", [
        (0.2, DecisionSource.BOT),
        (0.7, DecisionSource.BRAIN),
        (0.95, DecisionSource.HUMAN),
    ])
    def test_stakes_routing(self, engine, sample_context, stakes, expected):
        """Parametrized stakes routing test"""
        sample_context.stakes = stakes
        decision = engine.route_decision(sample_context)
        assert decision.source == expected
```

### Writing Integration Tests

```python
import pytest
from escalation_engine import EscalationEngine
from memory_system import MemoryConsolidationEngine

class TestIntegration:
    """Integration tests for DMLog"""

    @pytest.fixture
    def full_system(self):
        """Create integrated system"""
        engine = EscalationEngine()
        memory = MemoryConsolidationEngine("test_char")
        return {"engine": engine, "memory": memory}

    def test_decision_memory_flow(self, full_system):
        """Test decision to memory flow"""
        # 1. Route decision
        context = DecisionContext(
            character_id="test_char",
            situation_type="combat",
            situation_description="Goblin attack",
            stakes=0.7
        )
        decision = full_system["engine"].route_decision(context)

        # 2. Store memory
        memory = full_system["memory"].store_memory(
            content=f"Made decision: {decision.source.value}",
            memory_type=MemoryType.EPISODIC,
            importance=6.0
        )

        # 3. Verify
        assert memory.memory_type == MemoryType.EPISODIC
        assert decision.source is not None
```

### Test Coverage Goals

| Module | Target Coverage | Current |
|--------|-----------------|---------|
| Escalation Engine | 90% | 95% |
| Memory System | 85% | 90% |
| Vector Memory | 85% | 92% |
| Outcome Tracker | 90% | 88% |
| Training Data | 85% | 85% |
| Session Manager | 85% | 87% |

---

## Contributing Guidelines

### Code Style

Follow PEP 8 with project-specific conventions:

```python
# Good
from escalation_engine import EscalationEngine, DecisionContext

def route_decision(engine: EscalationEngine, context: DecisionContext) -> str:
    """Route a decision to appropriate source

    Args:
        engine: The escalation engine
        context: Decision context

    Returns:
        Action description
    """
    decision = engine.route_decision(context)
    return f"Route to: {decision.source.value}"

# Bad
from escalation_engine import *

def route(e, c):
    d = e.route(c)
    return d.source
```

### Naming Conventions

- **Classes**: `PascalCase` - `EscalationEngine`
- **Functions/Methods**: `snake_case` - `route_decision`
- **Constants**: `UPPER_SNAKE_CASE` - `MAX_RETRIES`
- **Private methods**: `_leading_underscore` - `_internal_method`

### Documentation Strings

```python
def complex_function(arg1: str, arg2: int, arg3: Optional[Dict] = None) -> Dict:
    """One-line summary.

    Extended description with details about the function's behavior,
    any edge cases, and examples.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2
        arg3: Description of arg3 (optional)

    Returns:
        Description of return value

    Raises:
        ValueError: When arg1 is invalid

    Examples:
        >>> result = complex_function("test", 42)
        >>> print(result["status"])
        'success'
    """
    pass
```

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation change
- `style`: Code style change
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Build process or auxiliary tool changes

**Example:**
```
feat(escalation): add custom decision source support

- Add CustomDecisionSource base class
- Implement registration in EscalationEngine
- Add tests for custom sources

Closes #123
```

### Pull Request Process

1. **Fork** the repository
2. **Create branch** from `main`: `git checkout -b feature/my-feature`
3. **Make changes** and commit with proper messages
4. **Run tests**: `pytest backend/ -v`
5. **Push** to fork: `git push origin feature/my-feature`
6. **Create PR** with:
   - Descriptive title
   - Summary of changes
   - Related issues
   - Test results
   - Screenshots (if UI changes)

---

## Troubleshooting

### Common Issues

#### Qdrant Connection Failed

**Error:** `ConnectionError: Failed to connect to Qdrant`

**Solutions:**
```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Start Qdrant
docker-compose up -d

# Check Qdrant health
curl http://localhost:6333/health

# Restart Qdrant if needed
docker-compose restart qdrant
```

#### OpenAI API Errors

**Error:** `openai.error.AuthenticationError`

**Solutions:**
```bash
# Check API key is set
echo $OPENAI_API_KEY

# Verify in .env file
cat .env | grep OPENAI_API_KEY

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

#### Module Import Errors

**Error:** `ModuleNotFoundError: No module named 'xyz'`

**Solutions:**
```bash
# Reinstall dependencies
pip install -r backend/requirements.txt

# Check virtual environment is activated
which python

# Install specific module
pip install <module_name>
```

#### Test Failures

**Error:** Tests failing after changes

**Solutions:**
```bash
# Run with verbose output
pytest backend/ -vv

# Run specific test to debug
pytest backend/test_escalation_engine.py::test_route_decision -vv

# Check test isolation
pytest backend/ --forcexit

# Run with debugger
pytest backend/ --pdb
```

### Debug Mode

Enable debug logging:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or for specific module
logging.getLogger("escalation_engine").setLevel(logging.DEBUG)
```

### Performance Profiling

```python
import cProfile
import pstats

# Profile escalation engine
profiler = cProfile.Profile()
profiler.enable()

# Run code to profile
engine.route_decision(context)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # Top 10 functions
```

---

## Development Workflow

### Feature Development Checklist

- [ ] Create issue describing feature
- [ ] Create feature branch
- [ ] Write tests first (TDD)
- [ ] Implement feature
- [ ] Add/update documentation
- [ ] Run tests: `pytest backend/ -v`
- [ ] Run linter: `flake8 backend/`
- [ ] Run formatter: `black backend/`
- [ ] Update CHANGELOG
- [ ] Create pull request
- [ ] Address review feedback
- [ ] Merge to main

### Release Process

1. **Update version** in `__init__.py`
2. **Update CHANGELOG** with release notes
3. **Run full test suite**: `pytest backend/ --cov`
4. **Tag release**: `git tag -a v1.0.0 -m "Release v1.0.0"`
5. **Push tag**: `git push origin v1.0.0`
6. **Create GitHub release**
7. **Publish to PyPI** (if applicable)

---

## Additional Resources

### Internal Documentation

- [Architecture Documentation](DMLOG_ARCHITECTURE_LEVEL1.md) - System architecture
- [API Reference](docs/API.md) - Complete API documentation
- [Installation Guide](docs/INSTALL.md) - Detailed installation

### External References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [OpenAI API Reference](https://platform.openai.com/docs/)
- [D&D 5e Rules](https://www.dndbeyond.com/sources/dnd-basic-rules)

---

**Document Version:** 1.0.0
**Last Updated:** 2025-01-10
**Author:** Documentation R&D Agent
