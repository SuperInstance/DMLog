# 🚀 QUICK START GUIDE

## ⚡ Get Running in 5 Minutes

### Step 1: Download the Project
You have the complete project at: `/mnt/user-data/outputs/ai_society_dnd/`

Download this entire folder to your computer.

### Step 2: Setup Environment
```bash
cd ai_society_dnd

# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
nano .env  # or use your favorite editor

# Add this line:
OPENAI_API_KEY=sk-your-key-here
```

### Step 3: Start Services
```bash
# Start Qdrant and API server
docker-compose up -d

# Verify it's running
curl http://localhost:8000/health
```

Expected output:
```json
{
  "status": "healthy",
  "campaigns": 0,
  "total_characters": 0,
  "active_sessions": 0
}
```

### Step 4: Run Demo
```bash
# Install Python dependencies (if not using Docker)
pip install -r backend/requirements.txt

# Run the demo
python demo.py
```

You'll see a complete D&D session with:
- Campaign creation
- Character creation (Thorin the Dwarf, Lyra the Elf)
- Game session with combat
- Memory formation
- Session archival

### Step 5: Try the API

#### Create a Campaign
```bash
curl -X POST http://localhost:8000/campaigns/create \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_name": "My_First_Campaign",
    "dm_id": "me"
  }'
```

#### Create a Character
```bash
curl -X POST http://localhost:8000/characters/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Aragorn",
    "race": "Human",
    "class_name": "Ranger",
    "level": 5,
    "personality_traits": ["Brave", "Leader", "Protective"],
    "backstory": "A ranger who protects the innocent."
  }'
```

Save the `character_id` from the response!

#### Create & Join Session
```bash
# Create session
curl -X POST http://localhost:8000/sessions/create \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_name": "My_First_Campaign",
    "session_number": 1
  }'

# Join with your character (use your character_id)
curl -X POST http://localhost:8000/sessions/join \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "My_First_Campaign_session_1",
    "character_id": "YOUR_CHARACTER_ID_HERE"
  }'
```

#### DM Narrates
```bash
curl -X POST http://localhost:8000/sessions/dm_narrate \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "My_First_Campaign_session_1",
    "narration": "You enter a dark tavern. A hooded figure sits in the corner."
  }'
```

#### Character Acts
```bash
curl -X POST http://localhost:8000/sessions/character_action \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "My_First_Campaign_session_1",
    "character_id": "YOUR_CHARACTER_ID_HERE",
    "action_description": "I approach the hooded figure cautiously."
  }'
```

#### View Transcript
```bash
curl "http://localhost:8000/sessions/My_First_Campaign_session_1/transcript?recent=10"
```

## 📚 What to Read Next

1. **README.md** - Complete documentation
2. **PROJECT_SUMMARY.md** - What I built for you
3. **demo.py** - Working example to study
4. **backend/api_server.py** - API reference

## 🎮 Common Commands

### Character Management
```bash
# Get character details
curl http://localhost:8000/characters/{character_id}

# Get character memories
curl http://localhost:8000/characters/{character_id}/memories

# Get character journal
curl http://localhost:8000/characters/{character_id}/journal

# Make skill check
curl -X POST http://localhost:8000/characters/{character_id}/skill_check \
  -H "Content-Type: application/json" \
  -d '{"skill": "perception", "advantage": false}'
```

### Combat
```bash
# Start combat
curl -X POST http://localhost:8000/sessions/combat/start \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "SESSION_ID",
    "enemies": [
      {"name": "Goblin", "dex_mod": 2}
    ]
  }'

# Attack in combat
curl -X POST http://localhost:8000/sessions/combat/action \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "SESSION_ID",
    "attacker_id": "YOUR_CHARACTER_ID",
    "action_type": "attack",
    "target_id": "enemy_0",
    "weapon": "Sword",
    "attack_bonus": 5,
    "damage_dice": "1d8",
    "damage_bonus": 3
  }'

# End combat
curl -X POST http://localhost:8000/sessions/SESSION_ID/combat/end
```

### Session Management
```bash
# Get session details
curl http://localhost:8000/sessions/{session_id}

# End session
curl -X POST http://localhost:8000/sessions/{session_id}/end
```

## 🐛 Troubleshooting

### Problem: "Connection refused" to API
**Solution**: Make sure Docker services are running
```bash
docker-compose ps
docker-compose up -d
```

### Problem: "Qdrant not available"
**Solution**: Check Qdrant is running
```bash
docker logs aisociety_qdrant
curl http://localhost:6333/
```

### Problem: "API Key error"
**Solution**: Check your .env file has valid OpenAI key
```bash
cat .env | grep OPENAI_API_KEY
```

### Problem: Demo crashes
**Solution**: Make sure you're in the right directory
```bash
cd ai_society_dnd
python demo.py
```

## 📦 Project Structure

```
ai_society_dnd/
├── backend/                    # All Python code
│   ├── api_server.py          # FastAPI REST API
│   ├── enhanced_character.py  # Character system
│   ├── game_mechanics.py      # D&D rules
│   ├── game_room.py           # Sessions & DM
│   ├── memory_system.py       # Temporal consciousness
│   ├── vector_memory.py       # Vector DB integration
│   ├── cultural_transmission.py # Skill learning
│   ├── requirements.txt       # Dependencies
│   └── Dockerfile             # Container config
├── docker-compose.yml         # Infrastructure
├── .env.example               # Config template
├── demo.py                    # Working example
├── README.md                  # Full documentation
└── PROJECT_SUMMARY.md         # What I built
```

## 🎯 What You Can Do Now

✅ Run a complete D&D game session
✅ Characters remember experiences
✅ Combat with initiative and turns
✅ Skill checks and dice rolls
✅ Memory-driven character decisions
✅ Session transcripts
✅ Character journals
✅ Campaign world lore

## 🚦 Next Steps

1. **Try the demo** - See everything working
2. **Play via API** - Use curl commands
3. **Build a UI** - Create React/Vue frontend
4. **Add features** - Extend the system

## 💡 Tips

- Start with the demo.py to see how it works
- Use the API for your own tools/UI
- Characters get better as they gain more memories
- DM can query campaign history at any time
- Sessions automatically archive to master DB

---

**You're ready to go!** Start with `docker-compose up` and `python demo.py` 🎉
