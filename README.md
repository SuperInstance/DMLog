# AI Society D&D - Temporal Consciousness Game System

A D&D simulator where AI characters develop through lived experiences using **temporal consciousness** and **cultural transmission**. Characters have personal memories, learn from each other, and evolve through gameplay.

## 🎯 Core Features

### **1. Temporal Consciousness**
- **Personal Vector Databases**: Each character has their own vector DB storing subjective memories
- **Memory Consolidation**: Episodic memories (events) automatically consolidate into semantic knowledge (understanding)
- **Autobiographical Narratives**: Characters build coherent life stories from experiences
- **Identity Persistence**: Characters maintain consistent personalities while allowing growth

### **2. Character System**
- **Character Laptops**: Personal notebooks with journal entries, documents, and private LLM access
- **D&D Mechanics**: Full D&D 5e stats (ability scores, HP, AC, skills)
- **Memory-Driven Decisions**: Characters make choices based on personality + past experiences
- **Cultural Learning**: Characters learn skills from each other

### **3. Game System**
- **D&D Sessions**: Turn-based gameplay with initiative, combat, and skill checks
- **DM System**: Human Dungeon Master with master vector DB for world lore
- **Real-time Updates**: WebSocket support for live gameplay
- **Session Transcripts**: Complete recording of all events for memory formation

### **4. Digital Twin Learning** (Future)
- Learn from human players' decisions
- Observe behavioral patterns (timing, preferences, strategies)
- Create AI doubles that mimic play style

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API key (for LLM calls)
- (Optional) Anthropic API key

### Installation

1. **Clone and setup**:
```bash
cd /home/claude/ai_society_dnd
cp .env.example .env
# Edit .env and add your API keys
```

2. **Start services**:
```bash
docker-compose up -d
```

This starts:
- **Qdrant** (vector database) on `localhost:6333`
- **Backend API** on `localhost:8000`

3. **Verify it's running**:
```bash
curl http://localhost:8000/health
```

### Create Your First Campaign

```bash
# 1. Create a campaign
curl -X POST http://localhost:8000/campaigns/create \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_name": "Lost Mine of Phandelver",
    "dm_id": "human_dm",
    "initial_world_lore": [
      "The town of Phandalin sits on the edge of the Sword Coast.",
      "Gundren Rockseeker has discovered the location of Wave Echo Cave."
    ]
  }'

# 2. Create a character
curl -X POST http://localhost:8000/characters/create \
  -H "Content-Type: application/json" \
  -d '{
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
  }'

# Save the character_id from the response!

# 3. Create a game session
curl -X POST http://localhost:8000/sessions/create \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_name": "Lost Mine of Phandelver",
    "session_number": 1
  }'

# Save the session_id from the response!

# 4. Join the session
curl -X POST http://localhost:8000/sessions/join \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "Lost Mine of Phandelver_session_1",
    "character_id": "YOUR_CHARACTER_ID_HERE"
  }'
```

## 🎮 Playing the Game

### DM Narration
```bash
curl -X POST http://localhost:8000/sessions/dm_narrate \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "Lost Mine of Phandelver_session_1",
    "narration": "You find yourselves on the High Road, escorting a wagon to Phandalin. Suddenly, you see two dead horses blocking the path ahead."
  }'
```

### Character Actions
```bash
curl -X POST http://localhost:8000/sessions/character_action \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "Lost Mine of Phandelver_session_1",
    "character_id": "YOUR_CHARACTER_ID",
    "action_description": "I approach cautiously, battleaxe in hand, looking for signs of an ambush.",
    "action_type": "roleplay"
  }'
```

### Skill Checks
```bash
curl -X POST http://localhost:8000/characters/YOUR_CHARACTER_ID/skill_check \
  -H "Content-Type: application/json" \
  -d '{
    "skill": "perception",
    "advantage": false,
    "disadvantage": false
  }'
```

### Start Combat
```bash
curl -X POST http://localhost:8000/sessions/combat/start \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "Lost Mine of Phandelver_session_1",
    "enemies": [
      {"name": "Goblin 1", "dex_mod": 2},
      {"name": "Goblin 2", "dex_mod": 1},
      {"name": "Goblin 3", "dex_mod": 2}
    ]
  }'
```

### Combat Actions
```bash
curl -X POST http://localhost:8000/sessions/combat/action \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "Lost Mine of Phandelver_session_1",
    "attacker_id": "YOUR_CHARACTER_ID",
    "action_type": "attack",
    "target_id": "enemy_0",
    "weapon": "Battleaxe",
    "attack_bonus": 5,
    "damage_dice": "1d8",
    "damage_bonus": 3
  }'
```

### View Session Transcript
```bash
curl http://localhost:8000/sessions/Lost_Mine_of_Phandelver_session_1/transcript?recent=10
```

### View Character Memories
```bash
curl http://localhost:8000/characters/YOUR_CHARACTER_ID/memories
```

## 🧠 How Memory & Learning Works

### Memory Formation
1. **During Gameplay**: Every action, narration, and event is stored as an **episodic memory**
2. **After Session**: Memories consolidate into **semantic knowledge** (patterns, learnings)
3. **Vector Storage**: Memories are embedded and stored in personal vector DB for retrieval

### Memory-Driven Decisions
When a character needs to act:
```python
# 1. Query their personal vector DB for relevant memories
relevant_memories = character.vector_store.retrieve_memories(
    query="encountering goblins in ambush",
    top_k=5
)

# 2. Use memories + personality + situation to decide
decision = await character.make_decision(
    situation="Goblins ambush the wagon",
    use_memories=True
)

# 3. Character acts based on past experiences
# If they were burned by goblins before → more cautious
# If they defeated goblins easily → more confident
```

### Character Laptop (Private Notebook)
Each character has a "laptop" with:
- **Journal entries**: Personal reflections on events
- **Documents**: Notes, maps, letters
- **Private LLM access**: Can ask questions privately (DM may or may not see)

```bash
# Character makes private query
curl -X POST http://localhost:8000/characters/YOUR_CHARACTER_ID/private_query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What do I know about goblin tactics? Should I be worried?"
  }'
```

## 📊 Monitoring & Metrics

### Campaign Stats
```bash
curl http://localhost:8000/campaigns/Lost_Mine_of_Phandelver
```

### Character Stats
```bash
curl http://localhost:8000/characters/YOUR_CHARACTER_ID
```

### Health Check
```bash
curl http://localhost:8000/health
```

## 🎯 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Human DM (Dungeon Master)              │
│  - Master Vector DB (world lore, campaign history)      │
│  - NPC control                                          │
│  - Oversight and narrative control                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     │
┌────────────────────▼────────────────────────────────────┐
│              Game Session (D&D Room)                     │
│  - Turn-based gameplay                                  │
│  - Combat encounters                                    │
│  - Skill checks & dice rolls                           │
│  - Transcript recording                                │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼──────┐ ┌──▼──────┐ ┌──▼──────┐
│  Character 1 │ │ Char 2  │ │ Char 3  │
│              │ │         │ │         │
│ Personal     │ │Personal │ │Personal │
│ Vector DB    │ │VectorDB │ │VectorDB │
│              │ │         │ │         │
│ Memory       │ │Memory   │ │Memory   │
│ System       │ │System   │ │System   │
│              │ │         │ │         │
│ Laptop       │ │Laptop   │ │Laptop   │
│ (Journal)    │ │(Journal)│ │(Journal)│
└──────────────┘ └─────────┘ └─────────┘
```

## 🔧 API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/health` | GET | Detailed health status |

### Character Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/characters/create` | POST | Create new character |
| `/characters/{id}` | GET | Get character details |
| `/characters/{id}/memories` | GET | Get character memories |
| `/characters/{id}/journal` | GET | Get journal entries |
| `/characters/{id}/private_query` | POST | Private LLM query |
| `/characters/{id}/skill_check` | POST | Make skill check |

### Campaign Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/campaigns/create` | POST | Create new campaign |
| `/campaigns/{name}` | GET | Get campaign stats |
| `/campaigns/{name}/lore` | POST | Add world lore |
| `/campaigns/{name}/lore?query=X` | GET | Query world lore |

### Session Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sessions/create` | POST | Create game session |
| `/sessions/join` | POST | Join character to session |
| `/sessions/{id}` | GET | Get session details |
| `/sessions/{id}/transcript` | GET | Get session transcript |
| `/sessions/dm_narrate` | POST | DM narrates |
| `/sessions/character_action` | POST | Character acts |
| `/sessions/{id}/end` | POST | End session |

### Combat

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sessions/combat/start` | POST | Start combat |
| `/sessions/combat/action` | POST | Combat action |
| `/sessions/{id}/combat/end` | POST | End combat |

## 🎓 Advanced Features

### Memory Consolidation
Memories automatically consolidate after sessions:
```python
# Episodic: "I fought goblins near the wagon"
# ↓ (consolidation)
# Semantic: "Goblins often ambush on roads near forests"
```

### Cultural Transmission
Characters can learn skills from each other:
```python
# Character A teaches Character B stealth tactics
cultural_engine.teach_skill(
    teacher_id="char_a",
    learner_id="char_b",
    skill_name="Forest Stealth"
)
```

### Identity Persistence
Characters maintain core personality while growing:
```python
identity_system.get_identity_coherence_index()
# > 0.7 = healthy personality
# 0.4-0.7 = monitor for drift
# < 0.4 = intervention needed
```

## 🛠️ Development

### Running Locally (Without Docker)

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Start Qdrant separately
docker run -p 6333:6333 qdrant/qdrant:latest

# Set environment variables
export OPENAI_API_KEY=your_key_here
export QDRANT_URL=http://localhost:6333

# Run server
python api_server.py
```

### Project Structure
```
ai_society_dnd/
├── backend/
│   ├── api_server.py              # FastAPI server
│   ├── enhanced_character.py      # Character system
│   ├── game_mechanics.py          # D&D rules engine
│   ├── game_room.py               # Game sessions & DM
│   ├── memory_system.py           # Temporal consciousness
│   ├── vector_memory.py           # Vector DB integration
│   ├── cultural_transmission.py   # Skill learning
│   ├── requirements.txt
│   └── Dockerfile
├── data/
│   ├── qdrant_storage/           # Vector DB persistence
│   └── logs/                     # Application logs
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🚧 Roadmap

### ✅ Phase 1: Core System (Complete)
- [x] Character system with D&D stats
- [x] Memory consolidation engine
- [x] Personal vector databases
- [x] Game sessions and rooms
- [x] DM system with master DB
- [x] Combat mechanics
- [x] Character laptops (journals)

### 🔨 Phase 2: Enhanced Features (In Progress)
- [ ] Web UI for easier interaction
- [ ] Skill learning between characters
- [ ] Advanced memory pathology detection
- [ ] Model routing (GPT-4 for complex, GPT-3.5 for simple)

### 🔮 Phase 3: Digital Twin Learning
- [ ] Record human player behavior
- [ ] Train behavioral models
- [ ] Create AI doubles of players
- [ ] DM digital twin for encounter design

### 🌟 Phase 4: Advanced AI
- [ ] Multi-agent coordination
- [ ] Emergent social dynamics
- [ ] Dynamic world generation
- [ ] Self-directed quests

## 📝 Example Session Flow

1. **DM creates campaign**: "Curse of Strahd"
2. **Players create characters**: Warrior, Rogue, Wizard
3. **DM starts session**: "You arrive in the village of Barovia..."
4. **Characters act**: Based on personalities + memories
5. **Combat**: Initiative, attacks, spell casting
6. **Memories form**: Each character stores experiences
7. **Session ends**: Memories consolidate overnight
8. **Next session**: Characters remember previous events

## 🤝 Contributing

This is a prototype system. Key areas for contribution:
- **UI Development**: Build React/Vue frontend
- **Memory Optimization**: Improve consolidation algorithms
- **Game Mechanics**: Expand D&D rule coverage
- **Digital Twin**: Implement behavior learning

## 📄 License

MIT License - See LICENSE file

## 🙏 Acknowledgments

Built with:
- FastAPI for API server
- LangChain for LLM integration
- Qdrant for vector storage
- Sentence Transformers for embeddings

---

**Ready to play?** Start with `docker-compose up` and follow the Quick Start guide!
