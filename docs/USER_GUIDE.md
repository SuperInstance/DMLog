# DMLog User Guide (Level 3)

**Complete User Documentation for the Temporal Consciousness D&D System**

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [First Campaign](#first-campaign)
4. [Character Management](#character-management)
5. [Running Sessions](#running-sessions)
6. [Memory & Learning](#memory--learning)
7. [API Usage](#api-usage)
8. [Configuration](#configuration)
9. [Best Practices](#best-practices)
10. [FAQ](#faq)

---

## Quick Start

### What is DMLog?

DMLog is a D&D system where AI characters learn and grow through gameplay. Unlike traditional NPCs that remain static, DMLog characters:

- **Remember** their experiences as episodic memories
- **Learn** patterns from those memories
- **Develop** autobiographical narratives
- **Improve** their decision-making over time

### 5-Minute Setup

#### Step 1: Install Dependencies

```bash
# Install Python dependencies
cd DMLog/source_code/backend
pip install -r requirements.txt
```

#### Step 2: Start Qdrant

```bash
# From project root
docker-compose up -d
```

#### Step 3: Configure API Keys

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-your-key-here
```

#### Step 4: Start the Server

```bash
# From backend directory
python api_server.py
```

#### Step 5: Create Your First Character

```bash
curl -X POST http://localhost:8000/characters/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Thorin Ironforge",
    "race": "Dwarf",
    "class_name": "Fighter",
    "level": 1,
    "strength": 16,
    "dexterity": 12,
    "constitution": 14,
    "intelligence": 10,
    "wisdom": 11,
    "charisma": 8
  }'
```

Save the `character_id` from the response!

---

## Installation

### Option 1: Docker (Recommended)

**Pros:** Isolated environment, easy setup, cross-platform

```bash
# Navigate to project directory
cd DMLog/source_code

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Option 2: Local Python

**Pros:** Direct code access, easier debugging

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Start Qdrant (still needs Docker)
docker run -p 6333:6333 -d qdrant/qdrant

# Start API server
cd backend
python api_server.py
```

### Environment Variables

Create `.env` file:

```bash
# Required
OPENAI_API_KEY=sk-your-openai-key
QDRANT_URL=http://localhost:6333

# Optional
ANTHROPIC_API_KEY=sk-your-anthropic-key
DEFAULT_MODEL=gpt-4
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Storage
DATA_PATH=./data
VECTOR_STORAGE_PATH=./data/qdrant_storage

# Training (Phase 7)
TRAINING_ENABLED=true
```

---

## First Campaign

### Creating a Campaign

A campaign is the container for your D&D adventures. It stores world lore and connects sessions.

```bash
curl -X POST http://localhost:8000/campaigns/create \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_name": "Lost Mine of Phandelver",
    "dm_id": "human_dm",
    "initial_world_lore": [
      "The town of Phandalin sits on the edge of the Sword Coast.",
      "Gundren Rockseeker has discovered Wave Echo Cave.",
      "The Rockseeker brothers are missing.",
      "Goblins have been raiding trade routes along the Triboar Trail."
    ]
  }'
```

**Response:**
```json
{
  "campaign_id": "lost_mine_phandelver",
  "created_at": "2025-01-10T12:00:00Z",
  "world_lore_count": 4
}
```

### Creating Characters

Characters are the protagonists (or antagonists) of your campaign.

```bash
curl -X POST http://localhost:8000/characters/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Eldara the Wise",
    "race": "Elf",
    "class_name": "Wizard",
    "level": 1,
    "personality_traits": ["Curious", "Studious", "Cautious"],
    "backstory": "A graduate of the Infinite Library seeking lost knowledge.",
    "strength": 8,
    "dexterity": 14,
    "constitution": 12,
    "intelligence": 16,
    "wisdom": 13,
    "charisma": 10
  }'
```

**Save the character_id!** You'll need it for sessions.

### Starting a Session

A session is a single gameplay session where characters adventure.

```bash
# Create session
curl -X POST http://localhost:8000/sessions/create \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_name": "Lost Mine of Phandelver",
    "session_number": 1
  }'

# Join characters to session
curl -X POST http://localhost:8000/sessions/join \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "lost_mine_phandelver_session_1",
    "character_id": "YOUR_CHARACTER_ID_HERE"
  }'
```

---

## Character Management

### Viewing Characters

```bash
# Get character details
curl http://localhost:8000/characters/{character_id}

# Get character memories
curl http://localhost:8000/characters/{character_id}/memories

# Get character stats
curl http://localhost:8000/characters/{character_id}/stats
```

### Character Stats

Characters track:

| Stat | Description |
|------|-------------|
| HP | Current and maximum hit points |
| AC | Armor class |
| Ability Scores | STR, DEX, CON, INT, WIS, CHA |
| Proficiency Bonus | Based on level |
| Memories | Total memories stored |
| Sessions | Sessions participated in |
| Decisions | Total decisions made |
| Success Rate | Percentage of successful decisions |

### Updating Characters

```bash
curl -X PATCH http://localhost:8000/characters/{character_id} \
  -H "Content-Type: application/json" \
  -d '{
    "hp": 8,
    "level": 2,
    "experience": 300
  }'
```

---

## Running Sessions

### Session Flow

```
1. CREATE SESSION
   - Define campaign and session number
   - Set initial conditions

2. JOIN CHARACTERS
   - Add participating characters
   - Characters load their memories

3. PLAY
   - Describe situations
   - Route decisions
   - Execute actions
   - Track outcomes

4. END SESSION
   - Calculate metrics
   - Trigger consolidation
   - Update character growth
```

### Decision Flow During Session

```bash
# 1. Present situation
# "A goblin jumps out from behind a rock, sword raised!"

# 2. Route decision for character
curl -X POST http://localhost:8000/decisions/route \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "char_abc123",
    "situation_type": "combat",
    "situation_description": "Goblin jumps out with sword, attacks!",
    "stakes": 0.6,
    "urgency_ms": 5000,
    "character_hp_ratio": 1.0
  }'

# Response might say "bot" - use rules for this familiar combat

# 3. Execute action
# "Thorin swings his battleaxe at the goblin!"
# Roll: d20 + 5 = 12 (hits!)
# Damage: 1d8 + 3 = 7 damage

# 4. Record outcome
curl -X POST http://localhost:8000/decisions/outcome \
  -H "Content-Type: application/json" \
  -d '{
    "decision_id": "dec_001",
    "success": true,
    "description": "Hit for 7 damage, goblin defeated"
  }'
```

### Ending a Session

```bash
curl -X POST http://localhost:8000/sessions/end \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "lost_mine_phandelver_session_1"
  }'
```

**Response includes:**
- Total decisions made
- Success rate
- Characters who improved
- Teaching moments (learning opportunities)
- Session rewards

---

## Memory & Learning

### How Memory Works

```
EPISODIC MEMORY
"I fought goblins at the cave entrance on Tuesday"
    |
    v (Consolidation)
SEMANTIC MEMORY
"Goblins are aggressive enemies that often guard caves"
    |
    v (More consolidation)
PROCEDURAL MEMORY
"When entering caves, be ready for goblin ambushes"
```

### Viewing Character Memories

```bash
# Get all memories
curl http://localhost:8000/characters/{character_id}/memories

# Filter by type
curl "http://localhost:8000/characters/{character_id}/memories?type=episodic"

# Get recent memories
curl "http://localhost:8000/characters/{character_id}/memories?recent=24h"

# Get important memories
curl "http://localhost:8000/characters/{character_id}/memories?importance_gte=7"
```

### Understanding Memory Types

| Type | Description | Example |
|------|-------------|---------|
| WORKING | Current focus | "Currently in combat with goblin" |
| MID-TERM | Session buffer | "Earlier, we found a goblin trail" |
| LONG-TERM | Consolidated | "Goblins live in the Cragmaw area" |
| EPISODIC | Specific event | "Defeated goblin chief on day 3" |
| SEMANTIC | General knowledge | "Goblins are cunning but cowardly" |
| PROCEDURAL | Skills/habits | "Always check for ambushes in caves" |

### Temporal Landmarks

Characters automatically detect significant events:

- **First Time**: First combat, first social interaction
- **Peak Emotion**: Most intense positive/negative experiences
- **Transitions**: Entering new locations, major changes
- **Social Events**: Meeting important NPCs

Landmarks become anchor points that other memories cluster around.

### Autobiographical Narrative

Characters generate life stories from their memories:

```bash
# Get character narrative
curl http://localhost:8000/characters/{character_id}/narrative
```

**Example Output:**
```
I am Thorin Ironforge, a dwarf fighter seeking to reclaim my ancestral mine.
My journey began when I left my home to search for the Rockseeker brothers.
I have fought many goblins along the Triboar Trail and learned that they are
working for someone called the Black Spider. My companions trust me in combat,
and I've learned to always be prepared for ambushes. Though I miss my home,
I am determined to see this quest through to the end.
```

---

## API Usage

### Python SDK Example

```python
import requests
import json

API_BASE = "http://localhost:8000"

class DMLogClient:
    """Simple client for DMLog API"""

    def __init__(self, base_url=API_BASE):
        self.base_url = base_url

    def create_character(self, name, race, class_name, **stats):
        """Create a new character"""
        response = requests.post(
            f"{self.base_url}/characters/create",
            json={
                "name": name,
                "race": race,
                "class_name": class_name,
                **stats
            }
        )
        return response.json()

    def route_decision(self, character_id, situation_type, description, **kwargs):
        """Route a decision"""
        response = requests.post(
            f"{self.base_url}/decisions/route",
            json={
                "character_id": character_id,
                "situation_type": situation_type,
                "situation_description": description,
                **kwargs
            }
        )
        return response.json()

    def record_outcome(self, decision_id, success, description):
        """Record decision outcome"""
        response = requests.post(
            f"{self.base_url}/decisions/outcome",
            json={
                "decision_id": decision_id,
                "success": success,
                "description": description
            }
        )
        return response.json()

# Usage
client = DMLogClient()

# Create character
char = client.create_character(
    name="Gimli",
    race="Dwarf",
    class_name="Fighter",
    level=1,
    strength=16
)
character_id = char["character_id"]

# Route decision
decision = client.route_decision(
    character_id=character_id,
    situation_type="combat",
    description="Orc attacks with axe",
    stakes=0.7,
    urgency_ms=3000
)

print(f"Route to: {decision['source']}")

# Record outcome
client.record_outcome(
    decision_id="dec_001",
    success=True,
    description="Hit orc for 8 damage"
)
```

### cURL Examples

```bash
# Create campaign
curl -X POST http://localhost:8000/campaigns/create \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_name": "Curse of Strahd",
    "dm_id": "dm_001",
    "initial_world_lore": [
      "Barovia is a land of mists and darkness.",
      "Count Strahd rules from Castle Ravenloft."
    ]
  }'

# Create character
curl -X POST http://localhost:8000/characters/create \
  -H "Content-Type: application/json" \
  -d @character.json

# Get character
curl http://localhost:8000/characters/char_abc123

# Get memories
curl http://localhost:8000/characters/char_abc123/memories?limit=10
```

---

## Configuration

### Escalation Thresholds

Control how decisions are routed per character:

```python
from escalation_engine import EscalationThresholds, EscalationEngine

engine = EscalationEngine()

# Set custom thresholds for a character
engine.set_thresholds(
    "char_001",
    EscalationThresholds(
        bot_min_confidence=0.6,      # Lower for bold characters
        brain_min_confidence=0.4,    # More independent
        high_stakes_threshold=0.8,   # Only escalate for very important
        critical_stakes_threshold=0.95
    )
)
```

### Memory Configuration

```python
from memory_system import MemoryConsolidationEngine

memory = MemoryConsolidationEngine("char_001")

# Configure consolidation
memory.REFLECTION_THRESHOLD = 120.0  # Consolidate more often
memory.CONSOLIDATION_WINDOW_HOURS = 12  # Consolidate twice daily
memory.TEMPORAL_LANDMARK_SIMILARITY_THRESHOLD = 0.9  # More selective
```

### Cost Tracking

Monitor and limit API costs:

```python
from escalation_engine import EscalationEngine

engine = EscalationEngine()

# Set daily budget
engine.set_daily_budget(budget_usd=5.0)

# Check current spending
stats = engine.get_global_stats()
print(f"Today's cost: ${stats['total_cost']:.2f}")
```

---

## Best Practices

### For Dungeon Masters

1. **Start Simple**: Begin with pre-generated characters
2. **Review Memories**: Check character memories before sessions
3. **Use Teaching Moments**: Note low-quality decisions for improvement
4. **Adjust Stakes**: Use appropriate stakes for decision routing
5. **Monitor Growth**: Track character improvement over sessions

### For Character Creation

1. **Clear Backstory**: Helps generate coherent memories
2. **Defined Traits**: Personality should be specific
3. **Balanced Stats**: Avoid min-maxing for better AI decisions
4. **Clear Goals**: Give characters motivations

### For Session Management

1. **Regular Sessions**: Consistent play helps consolidation
2. **Varied Situations**: Mix combat, social, exploration
3. **Document Outcomes**: Always record decision outcomes
4. **Review Summaries**: Check session summaries for insights

---

## FAQ

### General Questions

**Q: Do I need to be a programmer to use DMLog?**
A: Basic knowledge helps, but the API is simple. You can use cURL for most operations.

**Q: Can I use DMLog for games other than D&D?**
A: Yes! The system is game-agnostic. Just adjust the stats and mechanics.

**Q: How much does it cost to run?**
A: With the escalation engine, expect $2-5/month per character depending on usage.

**Q: Can I run DMLog offline?**
A: Partially. You can use Ollama for local LLM decisions, but some features require internet.

### Technical Questions

**Q: What LLMs are supported?**
A: OpenAI (GPT-4, GPT-3.5), Anthropic (Claude), and local models via Ollama.

**Q: How are memories stored?**
A: Episodic memories in SQLite, embeddings in Qdrant vector database.

**Q: Can I export my data?**
A: Yes, all data can be exported via the API.

**Q: How many characters can I run?**
A: Limited by your hardware. 10-20 concurrent characters is typical for consumer hardware.

### Gameplay Questions

**Q: How fast do characters learn?**
A: Noticeable improvement after 3-5 sessions (15-20 hours of gameplay).

**Q: Can characters "forget" things?**
A: Yes, low-importance memories decay over time (simulating forgetting).

**Q: Do characters collaborate?**
A: In Phase 8, characters will share skills. Currently, they learn independently.

**Q: Can I override character decisions?**
A: Yes, you can always escalate to human (yourself) for any decision.

---

## Tutorials

### Tutorial 1: Your First Combat

```bash
# 1. Create fighter character
curl -X POST http://localhost:8000/characters/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Aragorn",
    "race": "Human",
    "class_name": "Fighter",
    "level": 1,
    "strength": 16,
    "dexterity": 12,
    "constitution": 14,
    "intelligence": 10,
    "wisdom": 13,
    "charisma": 11
  }'

# 2. Route first combat decision
curl -X POST http://localhost:8000/decisions/route \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "CHAR_ID_HERE",
    "situation_type": "combat",
    "situation_description": "Goblin attacks with rusty scimitar",
    "stakes": 0.5,
    "urgency_ms": 5000
  }'

# 3. Execute and record outcome
# (Roll dice, determine result)

curl -X POST http://localhost:8000/decisions/outcome \
  -H "Content-Type: application/json" \
  -d '{
    "decision_id": "DECISION_ID_HERE",
    "success": true,
    "description": "Hit goblin for 8 damage"
  }'

# 4. Check what was learned
curl http://localhost:8000/characters/CHAR_ID_HERE/memories
```

### Tutorial 2: Social Interaction

```bash
# 1. Create bard character
curl -X POST http://localhost:8000/characters/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Lira",
    "race": "Half-Elf",
    "class_name": "Bard",
    "level": 1,
    "charisma": 16
  }'

# 2. Social situation
curl -X POST http://localhost:8000/decisions/route \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "CHAR_ID_HERE",
    "situation_type": "social",
    "situation_description": "Innkeeper refuses to give information",
    "stakes": 0.4
  }'

# Note: Social situations default to Brain for nuanced interaction
```

---

**Document Version:** 1.0.0
**Last Updated:** 2025-01-10
**Author:** Documentation R&D Agent
