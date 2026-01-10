# 🏗️ LAYER 3 ARCHITECTURE - Multi-Agent Command & Control

## 🎯 **VISION STATEMENT**

Transform the D&D simulator into a **self-improving MUD-like experience** where:
- Local Small LMs act as "strategic brains" for characters
- Characters develop personalities through gameplay
- DM has intelligent automation assistant (digital twin)
- Multi-window chatroom interface (public, private, DM command)
- System learns and improves from every session
- Eventually exports to visual game engines

**Target Experience:** Critical Role / D20 transcript quality with real personality development

---

## 🏛️ **ARCHITECTURE OVERVIEW**

```
┌─────────────────────────────────────────────────────────────────┐
│                     LAYER 3: COMMAND & CONTROL                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   DM BRAIN   │  │ CHAR BRAIN 1 │  │ CHAR BRAIN N │          │
│  │              │  │              │  │              │          │
│  │ Local LM     │  │ Local LM     │  │ Local LM     │          │
│  │ + Vector DB  │  │ + Vector DB  │  │ + Vector DB  │          │
│  │ + Twin       │  │ + Profile    │  │ + Profile    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                  │
│         └──────────────────┴──────────────────┘                  │
│                            │                                     │
│                   ┌────────▼────────┐                           │
│                   │  PERCEPTION     │                           │
│                   │  BATCH ENGINE   │                           │
│                   └────────┬────────┘                           │
│                            │                                     │
│         ┌──────────────────┼──────────────────┐                 │
│         │                  │                  │                 │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐         │
│  │ MECHANICAL   │  │ MECHANICAL   │  │ MECHANICAL   │         │
│  │ BOT SWARM    │  │ BOT SWARM    │  │ BOT SWARM    │         │
│  │              │  │              │  │              │         │
│  │ Scripted     │  │ Scripted     │  │ Scripted     │         │
│  │ Behaviors    │  │ Behaviors    │  │ Behaviors    │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                 │
│         └──────────────────┴──────────────────┘                 │
│                            │                                     │
│                   ┌────────▼────────┐                           │
│                   │  ESCALATION     │                           │
│                   │  TRIGGER ENGINE │                           │
│                   └────────┬────────┘                           │
│                            │                                     │
│                   ┌────────▼────────┐                           │
│                   │ HUMAN-IN-LOOP   │                           │
│                   │ OR BIG LLM      │                           │
│                   └─────────────────┘                           │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  CHAT INTERFACE LAYER                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │  PUBLIC        │  │  PRIVATE MSG   │  │  DM COMMAND    │    │
│  │  TRANSCRIPT    │  │  CHANNELS      │  │  INTERFACE     │    │
│  │                │  │                │  │                │    │
│  │  MUD-like feed │  │  Player-Player │  │  LLM assist    │    │
│  │  with banter   │  │  Player-DM     │  │  Rule changes  │    │
│  │  & dice rolls  │  │                │  │  Twin suggest  │    │
│  └────────────────┘  └────────────────┘  └────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  LEARNING & IMPROVEMENT                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  • Session Analysis & Review (LLM judges quality)                │
│  • LoRA Training Pipeline (character-specific fine-tuning)       │
│  • System Prompt Evolution (auto-improvement)                    │
│  • DM Twin Training (learns DM preferences)                      │
│  • Transcript Quality Metrics (Critical Role benchmark)          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎮 **CORE COMPONENTS**

### 1. **LOCAL LM BRAIN SYSTEM**

#### Hardware Target: RTX 4050 (6GB VRAM)

**Model Tiers:**
- **Nano Tier (Fast Gameplay):** ~500M params, <1GB VRAM
  - Purpose: Real-time tactical decisions
  - Examples: TinyLlama, Phi-2 quantized
  - Response time: <100ms
  
- **Micro Tier (Standard Gameplay):** ~1-2B params, 1-2GB VRAM
  - Purpose: Character personality, dialogue
  - Examples: Gemma-2B, Phi-3-mini
  - Response time: 200-500ms
  
- **Small Tier (Reflection):** ~3-4B params, 3-4GB VRAM
  - Purpose: Self-study, planning, learning
  - Examples: Llama-3.1-8B quantized, Mistral-7B Q4
  - Response time: 1-3 seconds
  
- **Big LLM Fallback:** GPT-4/Claude (cloud)
  - Purpose: Novel situations, creative content
  - Only on escalation triggers

**Integration Points:**
- Local inference via `llama.cpp` or `vllm`
- Model hot-swapping based on context
- VRAM budget management
- Batched inference for multiple characters

---

### 2. **MULTI-WINDOW CHAT INTERFACE**

#### Window 1: Public Transcript (MUD-style)
```
[19:42] DM: The ancient door creaks open, revealing darkness beyond...
[19:42] Thorin rolls Investigation: [d20=14] +3 = 17
[19:42] Thorin: "I spot fresh tracks—something large was here recently."
[19:43] Elara: *readies her bow* "Stay close, everyone."
[19:43] Grunk: "Grunk no like dark. Grunk smash if need!"
[19:43] DM: Roll for initiative!
```

**Features:**
- MUD-style feed with timestamps
- Dice rolls displayed inline
- Character actions and dialogue
- DM narration
- Personality-driven banter
- Emote support (`*action*`)

#### Window 2: Private Messaging
```
Private Channels:
- Player-to-Player
- Player-to-DM
- DM visibility toggle (can DM see player-player?)
```

#### Window 3: DM Command Interface
```
┌─────────────────────────────────────┐
│ DM COMMAND CENTER                   │
├─────────────────────────────────────┤
│                                     │
│ > Ask Twin: "What should happen next if Thorin enters the room?"
│ 
│ [Twin Suggestion]
│ Based on your past style, I recommend:
│ - Ambush encounter (you like surprises)
│ - DC 15 Perception to notice hidden enemies
│ - Give Thorin a moment to shine
│ 
│ [Accept] [Modify] [Ignore]
│
│ Quick Commands:
│ /roll 3d6        - Roll dice
│ /npc create orc  - Spawn NPC
│ /pause           - Pause automation
│ /resume auto     - Resume DM twin suggestions
│ /setdc 18        - Set difficulty class
│
└─────────────────────────────────────┘
```

---

### 3. **MECHANICAL BOT FRAMEWORK**

#### Bot Types:

**Combat Bots:**
- Attack priority targeting
- Position optimization
- Resource management (HP, spells, items)
- Damage calculation
- Status effect tracking

**Social Bots:**
- Conversation context tracking
- Relationship matrices
- Mood/emotion state
- Dialogue pattern matching
- Persuasion/deception algorithms

**Exploration Bots:**
- Pathfinding
- Perception checks (automated)
- Trap detection
- Loot collection
- Map awareness

**Utility Bots:**
- Inventory management
- Spell slot tracking
- Rest recommendations
- Party coordination

#### Bot Control Interface:
```python
class MechanicalBot:
    """Base class for scripted behaviors"""
    
    def __init__(self, parameters):
        self.perception_range = parameters.get('perception_range', 60)
        self.aggression = parameters.get('aggression', 0.5)
        self.risk_tolerance = parameters.get('risk_tolerance', 0.3)
        self.priority_targets = parameters.get('priority_targets', [])
        
    def perceive(self, game_state):
        """Batch perception check - returns relevant info"""
        pass
        
    def decide(self, perception_data):
        """Scripted decision based on parameters"""
        pass
        
    def execute(self, action):
        """Perform the action"""
        pass
        
    def escalate_if_needed(self, confidence):
        """Check if Small LM should be consulted"""
        if confidence < self.escalation_threshold:
            return True
        return False
```

---

### 4. **PERCEPTION BATCHING SYSTEM**

**Goal:** Process all character perceptions efficiently in one pass

```python
class PerceptionBatchEngine:
    """Efficiently process multiple character perceptions"""
    
    def batch_perceive(self, characters, game_state):
        """
        Process all characters' perception in one batch
        Returns: Dict of perception data per character
        """
        results = {}
        
        # Batch 1: Visual perception (what can each see?)
        visible_entities = self._batch_visibility(characters, game_state)
        
        # Batch 2: Audio perception (what can each hear?)
        audible_events = self._batch_audio(characters, game_state)
        
        # Batch 3: Status effects (what affects each?)
        status_info = self._batch_status(characters, game_state)
        
        for char in characters:
            results[char.id] = {
                'visible': visible_entities[char.id],
                'audible': audible_events[char.id],
                'status': status_info[char.id],
                'health': char.current_hp / char.max_hp,
                'resources': self._get_resources(char)
            }
            
        return results
```

---

### 5. **ESCALATION TRIGGER ENGINE**

**When to escalate from Mechanical Bot → Small LM → Big LLM:**

#### Escalation Levels:

**Level 0: Pure Mechanical (No LM)**
- Routine combat actions
- Standard movement
- Basic perception checks
- Inventory management
- Confidence > 90%

**Level 1: Small LM (Local)**
- Tactical decisions with multiple good options
- Social interactions
- Planning ahead
- Interpreting ambiguous situations
- Confidence: 50-90%

**Level 2: Big LLM (Cloud)**
- Novel situations never encountered
- Critical story decisions
- Creative problem-solving
- Moral dilemmas
- Confidence < 50%

**Level 3: Human-in-Loop**
- System uncertainty > threshold
- Time-sensitive critical decision
- Player explicitly requests human
- DM override enabled

```python
class EscalationEngine:
    """Determine when to escalate decisions"""
    
    def should_escalate(self, situation, bot_confidence):
        """
        Returns: (escalate: bool, level: int)
        """
        
        # Check novelty
        novelty_score = self._calculate_novelty(situation)
        
        # Check stakes
        stakes = self._assess_stakes(situation)
        
        # Check time pressure
        time_critical = self._is_time_critical(situation)
        
        # Decision matrix
        if bot_confidence > 0.9 and novelty_score < 0.3:
            return False, 0  # Mechanical bot handles it
            
        if bot_confidence > 0.5 and stakes < 0.7:
            return True, 1  # Small LM handles it
            
        if novelty_score > 0.7 or stakes > 0.8:
            return True, 2  # Big LLM handles it
            
        if time_critical and bot_confidence < 0.6:
            return True, 3  # Human needed NOW
            
        return True, 1  # Default to Small LM
```

---

### 6. **DM AUTOMATION & DIGITAL TWIN**

#### DM Twin Capabilities:

**Auto-Response System:**
- Pattern-match common questions → instant response
- "How much HP does the orc have?" → Check database, respond
- "Can I do X?" → Check rules, provide instant ruling
- "What do I see?" → Generate description from world state

**Choose-Your-Own-Adventure Generator:**
When DM is stuck or wants automation:

```python
class DMAutomation:
    """Automated DM assistance"""
    
    async def generate_branching_scenario(self, current_state, num_branches=3):
        """
        Create multiple story paths with:
        - Dice checks
        - Conditional branches
        - Character-specific outcomes
        """
        
        # Analyze current situation
        context = self._build_context(current_state)
        
        # Generate branches
        branches = []
        for i in range(num_branches):
            branch = await self._create_branch(context, difficulty=i)
            branches.append(branch)
            
        return {
            'low_risk': branches[0],    # Easy path
            'medium_risk': branches[1],  # Balanced
            'high_risk': branches[2]     # Dramatic
        }
    
    def _create_branch(self, context, difficulty):
        """
        Returns scenario with:
        - Setup text
        - Required dice rolls
        - Branching outcomes
        - NPC reactions
        - Loot/consequences
        """
        pass
```

**Learning from DM:**
- Track DM decisions over time
- Identify patterns (prefers RP vs combat ratio, difficulty preferences)
- Build decision tree of "what would DM do?"
- Suggest increasingly accurate options

---

### 7. **AGENT PROFILE SYSTEM**

#### Character Profile Structure:
```
characters/
├── thorin_ironforge/
│   ├── profile.json          # Stats, background, personality
│   ├── vector_db/            # Personal memory database
│   ├── lora_weights/         # Character-specific fine-tuning
│   ├── conversation_log.txt  # All dialogue history
│   ├── decision_log.json     # All decisions made
│   ├── relationships.json    # How they feel about others
│   └── training_data.jsonl   # For LoRA training
```

#### Profile Fields:
```json
{
  "character_id": "thorin_ironforge",
  "name": "Thorin Ironforge",
  "class": "Fighter",
  "level": 5,
  "personality": {
    "traits": ["brave", "loyal", "stubborn"],
    "values": ["honor", "clan", "duty"],
    "speaking_style": "gruff, direct, occasional dwarvish phrases",
    "quirks": ["Always checks for traps", "Distrusts magic"]
  },
  "brain_config": {
    "base_model": "phi-3-mini",
    "lora_path": "characters/thorin_ironforge/lora_weights/",
    "temperature": 0.8,
    "system_prompt": "You are Thorin Ironforge, a gruff but loyal dwarf fighter..."
  },
  "bot_parameters": {
    "combat_style": "defensive",
    "aggression": 0.4,
    "risk_tolerance": 0.3,
    "target_priority": ["protect_party", "tank_damage", "control_battlefield"]
  }
}
```

---

### 8. **LEARNING & IMPROVEMENT PIPELINE**

#### LoRA Training System:
```python
class LoRATrainer:
    """Train character-specific LoRAs from gameplay"""
    
    async def collect_training_data(self, character_id, sessions):
        """
        Extract training examples from sessions:
        - Dialogue (input: situation → output: what character said)
        - Decisions (input: options → output: what character chose)
        - Style (how character expresses themselves)
        """
        pass
    
    async def train_lora(self, character_id, training_data):
        """
        Fine-tune small model on character's behavior
        Results in: character-specific LoRA weights
        """
        pass
```

#### Session Analysis:
```python
class SessionReviewer:
    """LLM judges session quality"""
    
    async def analyze_transcript(self, session_transcript):
        """
        Compare to Critical Role / D20 benchmarks:
        - Personality consistency
        - Dialogue quality
        - Story coherence
        - Player engagement
        - Pacing
        
        Returns: Quality score + improvement suggestions
        """
        pass
```

#### Auto-Improvement Loop:
```
Session → Transcript → Analysis → Training Data → LoRA → Better Character
   ↑                                                              ↓
   └──────────────────────────────────────────────────────────────┘
```

---

## 🔬 **RESEARCH QUESTIONS**

### Technical Research Needed:

1. **Local LM Performance**
   - What's the best quantization method for 6GB VRAM?
   - How fast can Phi-3-mini respond on RTX 4050?
   - Can we run multiple models simultaneously?
   - Best batching strategy for multi-character inference?

2. **LoRA Training**
   - How much training data needed for good character LoRA?
   - Can we train LoRAs during gameplay (online learning)?
   - Best base model for character fine-tuning?
   - How to prevent catastrophic forgetting?

3. **Transcript Quality**
   - What makes a good D&D transcript?
   - How to measure personality consistency?
   - Critical Role analysis: what patterns emerge?
   - Optimal RP-to-mechanics ratio?

4. **Vector DB Strategy**
   - Personal vector DB size (how many memories)?
   - Retrieval strategy during fast gameplay?
   - How to index decisions vs dialogue differently?
   - Memory consolidation frequency?

5. **Perception Batching**
   - Optimal batch size for perception checks?
   - Trade-offs: accuracy vs speed?
   - What needs real-time vs can be cached?

### Design Research Needed:

1. **DM Experience**
   - Study D20/Critical Role DM techniques
   - Identify automation opportunities
   - What decisions can be pre-computed?
   - When does automation break immersion?

2. **Character Personality Development**
   - How do D&D characters evolve naturally?
   - What creates memorable personalities?
   - Relationship development patterns?
   - Consistency vs growth balance?

3. **Escalation Thresholds**
   - When do players want tactical control vs automation?
   - Optimal confidence thresholds?
   - How to communicate escalation to users?

---

## 📊 **SUCCESS METRICS**

### Quality Metrics:
- **Personality Consistency Score:** 0-100 (LLM judge)
- **Transcript Readability:** How "Critical Role-like" is it?
- **Dialogue Quality:** Natural banter vs robotic responses
- **Decision Coherence:** Do actions match personality?

### Performance Metrics:
- **Response Latency:** <200ms for mechanical bots, <1s for Small LM
- **VRAM Usage:** Stay under 6GB total
- **Cost per Session:** Minimal Big LLM usage
- **Throughput:** Support 4-6 concurrent characters

### Learning Metrics:
- **LoRA Improvement:** Character consistency after training
- **DM Twin Accuracy:** % of suggestions accepted by human DM
- **Session Quality Trend:** Improving over time
- **Escalation Rate:** Fewer Big LLM calls as system learns

---

## 🚀 **IMPLEMENTATION PHASES**

### Phase 1: Multi-Agent Command (Week 1-2)
- [ ] Small LM integration (`llama.cpp` wrapper)
- [ ] Character brain management
- [ ] Multi-character inference batching
- [ ] Basic mechanical bot framework

### Phase 2: Chat Interface (Week 2-3)
- [ ] Multi-window chat system
- [ ] Public transcript feed (MUD-style)
- [ ] Private messaging
- [ ] DM command interface

### Phase 3: Perception & Bots (Week 3-4)
- [ ] Perception batching engine
- [ ] Combat bots
- [ ] Social interaction bots
- [ ] Utility bots

### Phase 4: Escalation & Automation (Week 4-5)
- [ ] Escalation trigger engine
- [ ] DM automation system
- [ ] Choose-your-own-adventure generator
- [ ] DM digital twin learning

### Phase 5: Learning Pipeline (Week 5-6)
- [ ] LoRA training system
- [ ] Session analysis & review
- [ ] Auto-improvement loop
- [ ] Quality metrics

### Phase 6: Polish & Integration (Week 6-7)
- [ ] Full system integration testing
- [ ] Performance optimization
- [ ] Documentation
- [ ] Example sessions

---

## 🎯 **IMMEDIATE NEXT STEPS**

1. **Create detailed task breakdown** (this document)
2. **Research local LM options** (identify best models)
3. **Build Small LM integration** (start with Phi-3-mini)
4. **Create mechanical bot framework**
5. **Implement perception batching**
6. **Build chat interface prototype**

---

## 📚 **REFERENCES & INSPIRATION**

- **Critical Role:** Study transcripts for personality patterns
- **Dimension 20:** High-energy, comedy-focused D&D
- **MUD Systems:** Text-based game interface design
- **LoRA Training:** Fine-tuning for character consistency
- **Agent Command & Control:** RTS game AI architectures

---

## 🔮 **FUTURE VISION**

**Once Layer 3 is complete:**
- Export to game engines (Godot integration)
- Voice-to-text for DM (podcast mode)
- Text-to-speech for characters (voiced gameplay)
- Visual character avatars
- Multiple game systems (not just D&D)
- Shared world persistence
- Player vs AI tournaments

**The Goal:** Create the best AI D&D simulator that learns, improves, and eventually becomes indistinguishable from playing with expert human players.

---

## 💬 **PHILOSOPHY**

> "We're not building a chatbot that plays D&D. We're building a society of AI agents that develop real personalities through lived experiences, just like humans do through play."

The system should feel alive, surprising, and authentic. Characters should become friends, rivals, and memorable personalities. The DM should feel supported, not replaced. The transcript should be something you'd want to read for fun.

**This is ambitious. This is achievable. Let's build it.** 🚀
