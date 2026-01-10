# 🔬 LAYER 3: RESEARCH ROADMAP

## 📋 **PURPOSE**

This document identifies key research questions that need answers before/during Layer 3 implementation. Each question includes investigation methods and success criteria.

---

## 🤖 **RESEARCH AREA 1: LOCAL LM PERFORMANCE**

### Priority: 🔴 CRITICAL (Week 1)

### Q1.1: Which local LM is optimal for RTX 4050 (6GB VRAM)?

**Investigation Plan:**
```python
# Benchmark Script
models_to_test = [
    ("TinyLlama-1.1B", "Q4_K_M"),
    ("Phi-3-mini-3.8B", "Q4_K_M"),
    ("Phi-3-mini-3.8B", "Q5_K_M"),
    ("Llama-3.1-8B", "Q4_K_M"),
    ("Mistral-7B", "Q4_K_M"),
    ("Gemma-2B", "Q4_K_M"),
]

test_scenarios = [
    "combat_decision",      # "Do I attack orc or goblin?"
    "social_dialogue",      # "Respond to innkeeper's question"
    "personality_check",    # "Stay in character as gruff dwarf"
    "tactical_planning"     # "What's my 3-turn strategy?"
]

metrics = {
    "vram_usage_mb": [],
    "response_time_ms": [],
    "personality_score": [],  # 0-100, LLM judge
    "coherence_score": [],    # 0-100, makes sense?
    "tokens_per_second": []
}
```

**Success Criteria:**
- Find model with <2GB VRAM, <500ms response, >80 personality score
- OR accept trade-offs if perfect model doesn't exist

**Deliverables:**
- Performance comparison table
- Recommended model(s) for each tier (fast/medium/reflection)
- VRAM budget allocation strategy

---

### Q1.2: How much context can small LMs handle effectively?

**Investigation Plan:**

Test prompt structure with varying context lengths:

```
Context Configurations:
1. Minimal (256 tokens):
   - Character profile summary
   - Current situation only
   - No history

2. Standard (1024 tokens):
   - Character profile
   - Last 3 actions
   - Current situation
   - Immediate goals

3. Extended (2048 tokens):
   - Full character profile
   - Last 10 actions
   - Current situation + surroundings
   - Short-term + long-term goals
   - Key relationships

4. Maximum (4096 tokens):
   - Everything above +
   - Recent memories from vector DB
   - Personality examples
   - Decision history
```

**Test Each Configuration:**
- Response quality (0-100)
- Response time (ms)
- Personality consistency across 20 decisions
- VRAM impact

**Success Criteria:**
- Identify sweet spot: max quality / acceptable speed
- Under 500ms response time
- >85 personality consistency

**Deliverables:**
- Context template for each model tier
- Prompt engineering best practices
- Dynamic context allocation algorithm

---

### Q1.3: Can we run multiple models simultaneously?

**Investigation Plan:**

**Scenario A: Multi-Model Resident**
- Keep Nano (500MB) + Micro (2GB) + Small (4GB) all loaded
- Total: ~6.5GB (too much!)
- Fallback: Nano (500MB) + Small (4GB) = 4.5GB ✓

**Scenario B: Hot Swapping**
- Load model → Use → Unload → Load next
- Measure swap time overhead
- Test caching strategies

**Scenario C: Hybrid**
- Keep one "primary" model loaded
- Hot-swap to others as needed
- Pre-warm next model in background

**Tests:**
```python
def test_multi_model():
    # Test 1: Simultaneous inference
    model_a = load_model("phi-3-mini")  # 2.5GB
    model_b = load_model("tinyllama")   # 0.7GB
    # Total: 3.2GB - leaves room for game state
    
    # Test 2: Hot swap timing
    start = time()
    unload_model(model_a)
    load_model("llama-8b")  # 4.5GB
    swap_time = time() - start  # Target: <2s
    
    # Test 3: Background loading
    # Load model async while other is running
```

**Success Criteria:**
- Identify viable strategy for 6GB limit
- <2s swap time if hot-swapping
- No memory leaks over 4-hour session

**Deliverables:**
- Multi-model management strategy
- Model loading/unloading API
- VRAM monitoring system

---

### Q1.4: What's optimal batching strategy for multi-character inference?

**Investigation Plan:**

Test batching configurations:

```python
batch_configs = [
    ("sequential", 1),      # One at a time
    ("small_batch", 2),     # 2 characters
    ("medium_batch", 4),    # 4 characters
    ("large_batch", 6),     # 6 characters (full party)
]

# For each config, measure:
# 1. Total throughput (chars/second)
# 2. Per-character latency
# 3. Quality degradation (if any)
# 4. VRAM pressure
# 5. CPU bottlenecks
```

**Key Question:** Does batching help or hurt on local GPU?
- Cloud LLMs: Batching = good (parallel processing)
- Local GPU: Might be sequential anyway?

**Tests:**
- Batch similar requests (all combat decisions)
- Batch dissimilar requests (combat + social)
- Mixed priorities (urgent vs routine)

**Success Criteria:**
- Throughput >4 chars/sec for routine decisions
- Maintain <500ms latency per character
- No quality loss from batching

**Deliverables:**
- Batching strategy recommendations
- Request queuing system
- Priority scheduling algorithm

---

## 🎭 **RESEARCH AREA 2: CHARACTER PERSONALITY**

### Priority: 🔴 CRITICAL (Week 1-2)

### Q2.1: What makes D&D characters feel consistent?

**Investigation Plan:**

**Step 1: Analyze Critical Role Characters**
- Study 20+ episodes
- Focus on 3-4 main characters
- Extract personality markers:
  - Speech patterns
  - Decision patterns
  - Relationship behaviors
  - Quirks and habits
  - Values and motivations
  - Emotional responses

**Step 2: Build Personality Model**
```json
{
  "personality_components": {
    "traits": ["brave", "impulsive", "loyal"],
    "values": ["freedom", "justice", "friendship"],
    "fears": ["abandonment", "failure"],
    "quirks": ["Always checks for traps", "Collects strange rocks"],
    "speech_patterns": {
      "catchphrases": ["By the gods!", "Not on my watch"],
      "sentence_structure": "short_declarative",
      "vocabulary_level": "common_with_occasional_arcane",
      "dialect": "rural_merchant"
    },
    "decision_patterns": {
      "risk_tolerance": 0.7,  # 0=cautious, 1=reckless
      "altruism": 0.8,         # 0=selfish, 1=selfless
      "planning": 0.3,         # 0=impulsive, 1=strategic
      "social": 0.6            # 0=loner, 1=social
    },
    "relationships": {
      "default_stance": "friendly_but_guarded",
      "trust_speed": "slow",
      "conflict_style": "direct_confrontation"
    }
  }
}
```

**Step 3: Test Consistency**
- Generate 50 decisions with model
- Have LLM judge consistency
- Have human judge consistency
- Compare scores

**Success Criteria:**
- Consistency score >85 (LLM judge)
- Consistency score >80 (human judge)
- Identifiable "voice" after 20 responses

**Deliverables:**
- Personality model schema
- CR character analysis (3-4 detailed profiles)
- Consistency evaluation rubric

---

### Q2.2: How do characters evolve naturally vs drift?

**Investigation Plan:**

**Study Natural Character Evolution:**
- Track CR character development across 50+ episodes
- Identify natural evolution patterns:
  - Relationship-driven changes
  - Experience-driven growth
  - Values refinement vs shifts
  - Trauma responses
  - Victory/success adaptations

**Define Drift:**
- Inconsistent decisions
- Personality contradiction
- Out-of-character actions
- Loss of distinctive voice
- Generic responses

**Create Evolution Rules:**
```python
class CharacterEvolution:
    """Natural vs drift detection"""
    
    def is_natural_evolution(self, old_decision, new_decision, context):
        """
        Natural evolution:
        - Gradual change
        - Justified by experiences
        - Core values stable
        - Voice remains distinct
        """
        
    def is_drift(self, decision_history, personality_profile):
        """
        Drift detection:
        - Sudden unexplained changes
        - Core value contradictions
        - Loss of quirks/patterns
        - Generic responses
        """
```

**Success Criteria:**
- Define clear evolution vs drift criteria
- Build detection system (>90% accuracy)
- Intervention when drift detected

**Deliverables:**
- Evolution vs drift taxonomy
- Detection algorithms
- Intervention strategies

---

### Q2.3: How effective is LoRA training for personality?

**Investigation Plan:**

**Experimental Design:**

```
Groups:
A. Base model (no LoRA)
B. LoRA trained on 50 examples
C. LoRA trained on 200 examples  
D. LoRA trained on 1000 examples
E. LoRA trained on 5000 examples

For each group:
- Generate 100 decisions
- Measure consistency score
- Measure personality match
- Measure response quality
```

**Training Data Sources:**
- Real gameplay transcripts
- Human-written examples
- LLM-generated augmentations
- Critical Role dialogue

**Metrics:**
```python
metrics = {
    "personality_consistency": 0-100,
    "speech_pattern_match": 0-100,
    "decision_coherence": 0-100,
    "quirk_preservation": 0-100,
    "overall_quality": 0-100
}
```

**Success Criteria:**
- Identify minimum examples for good LoRA
- Target: +15 points improvement over base
- Diminishing returns point identification

**Deliverables:**
- LoRA training guidelines
- Optimal dataset size recommendations
- Training data quality criteria

---

### Q2.4: How to model character relationships?

**Investigation Plan:**

**Approach 1: Simple Scores**
```python
relationships = {
    "thorin_to_elara": {
        "trust": 0.7,
        "friendship": 0.8,
        "respect": 0.9,
        "attraction": 0.0
    }
}
```

**Approach 2: Emotional Dynamics**
```python
relationships = {
    "thorin_to_elara": {
        "emotional_state": "protective",
        "trust_trend": "increasing",
        "recent_interactions": [
            {"event": "saved_thorin", "impact": +0.2},
            {"event": "disagreement", "impact": -0.05}
        ],
        "shared_experiences": [
            "survived_ambush_together",
            "shared_secret_about_past"
        ]
    }
}
```

**Approach 3: Narrative Representation**
```python
relationships = {
    "thorin_to_elara": {
        "summary": "Thorin deeply respects Elara after she saved his life...",
        "vector_embedding": [...],  # For semantic search
        "key_moments": [...]
    }
}
```

**Test Each Approach:**
- Affect on dialogue quality
- Computational overhead
- Ease of modification
- Emergent dynamics

**Success Criteria:**
- Natural relationship progression
- Influences dialogue appropriately
- Computational: <10ms lookup

**Deliverables:**
- Relationship model design
- Update algorithms
- Query interface

---

## 🎲 **RESEARCH AREA 3: TRANSCRIPT QUALITY**

### Priority: 🟡 HIGH (Week 2-3)

### Q3.1: What makes a D&D transcript compelling?

**Investigation Plan:**

**Step 1: Collect Example Transcripts**
- Critical Role (10+ episodes)
- Dimension 20 (5+ episodes)
- The Adventure Zone (5+ episodes)
- Glass Cannon Podcast (5+ episodes)
- Amateur D&D (5+ sessions from Reddit)

**Step 2: Analyze Patterns**

Extract features:
```python
transcript_features = {
    # Quantitative
    "words_per_turn": {"dm": 50, "players": 30},
    "turns_per_hour": 150,
    "combat_to_rp_ratio": 0.4,
    "joke_frequency": 8,  # per hour
    "dice_rolls_per_hour": 30,
    
    # Qualitative
    "banter_quality": "natural, builds relationships",
    "description_vividness": "high detail, sensory",
    "pacing": "varied, tension & release",
    "player_agency": "high, meaningful choices",
    "dm_responsiveness": "adapts to player actions",
    
    # Stylistic
    "narrative_voice": "third person with flavor",
    "dialogue_format": "quotes with attribution",
    "action_format": "italics or *asterisks*",
    "dice_format": "[d20=14] +3 = 17"
}
```

**Step 3: Build Quality Rubric**

```python
class TranscriptQuality:
    """Evaluate transcript quality"""
    
    categories = {
        "engagement": {
            "banter_naturalness": 0-100,
            "relationship_depth": 0-100,
            "tension_pacing": 0-100
        },
        "coherence": {
            "story_logic": 0-100,
            "character_consistency": 0-100,
            "world_consistency": 0-100
        },
        "readability": {
            "formatting_clarity": 0-100,
            "flow": 0-100,
            "accessibility": 0-100
        },
        "entertainment": {
            "humor_quality": 0-100,
            "dramatic_moments": 0-100,
            "surprise_delight": 0-100
        }
    }
```

**Success Criteria:**
- Create validated rubric (tested on 50+ transcripts)
- Automated scorer >80% agreement with humans
- Target: Generated transcripts score >80/100

**Deliverables:**
- Transcript quality rubric
- Automated evaluation system
- Benchmark comparisons (CR, D20, etc.)

---

### Q3.2: What's optimal RP-to-mechanics ratio?

**Investigation Plan:**

**Survey Players:**
- Casual players
- Hardcore role-players
- Combat-focused players
- Balanced players

**Questions:**
- Preferred session composition
- Ideal combat encounter length
- Tolerance for mechanics talk
- Preference for automation

**Analyze Actual Play:**
- Track CR episodes: RP vs combat split
- Track D20: More RP-heavy style
- Track Glass Cannon: More tactical
- Identify patterns in high-rated episodes

**Test Variations:**
```python
test_sessions = [
    {"rp": 0.2, "combat": 0.6, "exploration": 0.2},  # Combat-heavy
    {"rp": 0.5, "combat": 0.3, "exploration": 0.2},  # Balanced
    {"rp": 0.7, "combat": 0.2, "exploration": 0.1},  # RP-heavy
]

# Generate sessions, get feedback
```

**Success Criteria:**
- Identify preference distribution
- Configurable balance per campaign
- Default that satisfies 70%+ players

**Deliverables:**
- Balance recommendations
- Configuration system
- Player preference survey results

---

### Q3.3: How much can we automate without losing immersion?

**Investigation Plan:**

**Create Automation Levels:**

```python
automation_levels = {
    "none": {
        "dice_rolls": "manual",
        "stat_tracking": "manual",
        "npc_dialogue": "manual",
        "combat_resolution": "manual"
    },
    "minimal": {
        "dice_rolls": "auto",
        "stat_tracking": "auto",
        "npc_dialogue": "manual",
        "combat_resolution": "manual"
    },
    "moderate": {
        "dice_rolls": "auto",
        "stat_tracking": "auto",
        "npc_dialogue": "auto_simple",
        "combat_resolution": "assisted"
    },
    "high": {
        "dice_rolls": "auto",
        "stat_tracking": "auto",
        "npc_dialogue": "auto_all",
        "combat_resolution": "auto"
    }
}
```

**Test Each Level:**
- Run 5+ sessions at each level
- Survey players on immersion
- Measure DM satisfaction
- Track where automation helps vs hurts

**Key Questions:**
- Does auto dice rolling feel less exciting?
- Do auto NPC responses feel robotic?
- Is automated combat boring or helpful?

**Success Criteria:**
- Identify breaking points
- Find automation sweet spot
- >80% player satisfaction

**Deliverables:**
- Automation guidelines
- Configurable automation system
- Best practices document

---

## 🤖 **RESEARCH AREA 4: BOT DESIGN**

### Priority: 🟡 HIGH (Week 2-3)

### Q4.1: What bot parameters are most important?

**Investigation Plan:**

**Combat Bot Parameters:**
```python
combat_params = {
    # Targeting
    "aggression": 0.0-1.0,          # Conservative to aggressive
    "target_priority": ["type", "hp", "threat"],
    "focus_fire": True/False,
    
    # Positioning
    "risk_tolerance": 0.0-1.0,      # Safe to risky positions
    "formation_preference": ["front", "back", "flank"],
    "cover_seeking": 0.0-1.0,
    
    # Resources
    "hp_threshold_heal": 0.5,       # Heal at 50% HP
    "spell_conservation": 0.0-1.0,  # Conservative to liberal
    "consumable_usage": "rare"/"normal"/"liberal",
    
    # Tactics
    "team_coordination": 0.0-1.0,   # Solo to cooperative
    "combo_seeking": True/False,
    "opportunity_taking": 0.0-1.0   # Cautious to opportunistic
}
```

**Social Bot Parameters:**
```python
social_params = {
    # Conversation
    "talkativeness": 0.0-1.0,       # Quiet to chatty
    "joke_frequency": 0.0-1.0,      # Serious to jokey
    "empathy": 0.0-1.0,             # Self-focused to empathetic
    
    # Relationships
    "trust_speed": "slow"/"medium"/"fast",
    "conflict_avoidance": 0.0-1.0,
    "loyalty": 0.0-1.0,
    
    # Style
    "formality": 0.0-1.0,           # Casual to formal
    "verbosity": 0.0-1.0,           # Brief to wordy
    "emotionality": 0.0-1.0         # Reserved to expressive
}
```

**Test Methodology:**
- Create characters with extreme parameter values
- Have them interact in controlled scenarios
- Measure distinctiveness
- Survey: Do parameters create unique personalities?

**Success Criteria:**
- Parameters create distinguishable characters
- Parameters are intuitive to DM
- Easy to configure

**Deliverables:**
- Finalized parameter schema
- Parameter effect documentation
- Configuration UI mockups

---

### Q4.2: How to make bot decisions feel "human"?

**Investigation Plan:**

**Add Imperfection:**
```python
class HumanLikeBehavior:
    """Make decisions less optimal, more human"""
    
    def add_variability(self, optimal_action):
        """Sometimes choose sub-optimal for flavor"""
        if random() < self.imperfection_rate:
            return self.pick_interesting_alternative(optimal_action)
        return optimal_action
    
    def add_hesitation(self, decision):
        """Don't always act instantly"""
        if decision.importance > 0.7:
            self.think_time = random(1.0, 3.0)
        
    def add_mistakes(self, action):
        """Occasionally make errors"""
        if random() < self.error_rate:
            return self.apply_mistake(action)
        return action
```

**Test Different Levels:**
- 0% imperfection (optimal play)
- 5% imperfection
- 10% imperfection
- 20% imperfection

**Measure:**
- Player enjoyment
- Character believability
- Frustration level

**Success Criteria:**
- Find sweet spot: interesting but not annoying
- >85% players prefer imperfect over optimal

**Deliverables:**
- Human-like behavior system
- Configurable imperfection levels
- Best practices guide

---

### Q4.3: When should bots escalate to LM?

**Investigation Plan:**

**Define Escalation Triggers:**

```python
escalation_triggers = {
    "low_confidence": {
        "threshold": 0.5,
        "reason": "Multiple good options, unclear best choice"
    },
    "novel_situation": {
        "threshold": 0.7,  # Novelty score
        "reason": "Never encountered this before"
    },
    "high_stakes": {
        "threshold": 0.8,  # Stakes score
        "reason": "Decision has major consequences"
    },
    "moral_dilemma": {
        "always": True,
        "reason": "Involves character values/ethics"
    },
    "social_complexity": {
        "threshold": 0.6,
        "reason": "Complex social dynamics"
    },
    "creative_solution": {
        "always": True,
        "reason": "Standard actions won't work"
    }
}
```

**Test Scenarios:**
- Create 100 decision scenarios
- Classify by type (combat, social, exploration, etc.)
- Determine ground truth: should escalate or not?
- Test trigger rules, measure accuracy

**Metrics:**
- False positives: Escalated unnecessarily
- False negatives: Should have escalated, didn't
- Latency impact: Escalation time cost

**Success Criteria:**
- <10% false positives
- <5% false negatives
- Average escalation rate: 5-15% of decisions

**Deliverables:**
- Escalation trigger system
- Calibrated thresholds
- Override mechanisms

---

## 🔍 **RESEARCH AREA 5: DM AUTOMATION**

### Priority: 🟡 HIGH (Week 4-5)

### Q5.1: What DM tasks can be automated?

**Investigation Plan:**

**Survey DMs:**
- Most time-consuming tasks?
- Most repetitive tasks?
- Tasks they'd love to automate?
- Tasks that MUST stay manual?

**Analyze DM Actions:**
- Track 10+ D&D sessions
- Categorize every DM action
- Measure frequency and time

**Candidate Tasks:**
```python
automatable_tasks = {
    # High Priority (frequent, simple)
    "stat_lookups": {"frequency": "very_high", "complexity": "trivial"},
    "hp_tracking": {"frequency": "high", "complexity": "trivial"},
    "initiative_order": {"frequency": "medium", "complexity": "trivial"},
    "basic_npc_dialogue": {"frequency": "high", "complexity": "low"},
    
    # Medium Priority (frequent, moderate)
    "random_encounters": {"frequency": "medium", "complexity": "medium"},
    "loot_generation": {"frequency": "medium", "complexity": "medium"},
    "npc_reactions": {"frequency": "high", "complexity": "medium"},
    "environmental_descriptions": {"frequency": "high", "complexity": "medium"},
    
    # Low Priority (infrequent, complex)
    "plot_twists": {"frequency": "low", "complexity": "high"},
    "bbeg_monologues": {"frequency": "low", "complexity": "high"},
    "moral_dilemmas": {"frequency": "low", "complexity": "high"}
}
```

**Success Criteria:**
- Identify 10+ high-value automation targets
- DM approval >80% for suggested automations
- Time saved: >30 minutes per 4-hour session

**Deliverables:**
- DM task taxonomy
- Automation opportunity map
- Prioritized implementation roadmap

---

### Q5.2: How fast can DM digital twin learn?

**Investigation Plan:**

**Experimental Timeline:**

```
Session 1: Twin has no data
- Generate suggestions blindly
- Track acceptance rate (expected: ~20-30%)

Sessions 2-5: Twin learning
- Analyze previous decisions
- Build initial model
- Track improvement

Sessions 6-10: Twin refining
- More sophisticated patterns
- Personal style emerging
- Target: 50-60% acceptance

Sessions 11-20: Twin mature
- Confident suggestions
- Style well-captured
- Target: 70-80% acceptance
```

**Track Metrics:**
```python
twin_metrics = {
    "suggestion_acceptance_rate": [],
    "suggestion_confidence": [],
    "dm_override_frequency": [],
    "twin_suggestion_quality": [],
    "time_to_convergence": None
}
```

**Success Criteria:**
- >60% acceptance by session 10
- >75% acceptance by session 20
- Identifiable improvement trend

**Deliverables:**
- Learning curve analysis
- Feature importance rankings
- Convergence timeline estimates

---

### Q5.3: How to present suggestions without annoying DM?

**Investigation Plan:**

**UI Testing:**

**Approach A: Proactive (Always Visible)**
```
┌────────────────────────────────┐
│ Twin Suggestion (Conf: 85%)    │
│                                │
│ "Have the innkeeper mention    │
│ strange noises from the cellar"│
│                                │
│ [Use] [Edit] [Dismiss]         │
└────────────────────────────────┘
```

**Approach B: On-Demand (Hidden by Default)**
```
DM types: "What should happen next?"
Twin responds immediately with suggestion
```

**Approach C: Background (Subtle)**
```
Twin suggestion appears as:
💡 Suggestion available (click to view)
```

**Approach D: Confidence-Gated**
```
Only show suggestions when confidence > 80%
Otherwise, stay silent
```

**Test Each:**
- 5 DMs test each approach
- Run 3+ sessions
- Survey on annoyance vs helpfulness

**Metrics:**
- Annoyance rating (1-10)
- Helpfulness rating (1-10)
- Frequency of usage
- Preferred approach

**Success Criteria:**
- Annoyance < 3/10
- Helpfulness > 7/10
- Used by >70% of DMs

**Deliverables:**
- UI design recommendations
- Configurable suggestion settings
- Best practices guide

---

## ⚡ **RESEARCH AREA 6: PERFORMANCE OPTIMIZATION**

### Priority: 🟢 MEDIUM (Week 6-7)

### Q6.1: What's optimal perception batch window?

**Investigation Plan:**

**Test Different Windows:**
```python
batch_windows = [
    ("instant", 0),      # No batching
    ("fast", 50),        # 50ms window
    ("standard", 100),   # 100ms window
    ("slow", 200),       # 200ms window
    ("lazy", 500)        # 500ms window
]

for name, window_ms in batch_windows:
    # Run 10-minute combat simulation
    metrics = {
        "perception_accuracy": 0-100,
        "average_latency": ms,
        "throughput": perceptions/sec,
        "player_satisfaction": 0-10
    }
```

**Key Questions:**
- Is batching noticeable to players?
- Does batching hurt decision quality?
- What's the sweet spot?

**Success Criteria:**
- <100ms perceived latency
- No quality degradation
- 2x+ throughput improvement

**Deliverables:**
- Optimal batch window size
- Dynamic batching algorithm
- Performance benchmarks

---

### Q6.2: How to manage VRAM efficiently?

**Investigation Plan:**

**Test Strategies:**

**Strategy 1: Keep Primary Model Loaded**
```python
# Keep Phi-3-mini (2.5GB) always resident
# Hot-swap to others as needed
vram_profile = {
    "base": 2.5,  # Phi-3-mini
    "peak": 5.5   # When swapping
}
```

**Strategy 2: Aggressive Unloading**
```python
# Unload immediately after use
# Reload on demand
vram_profile = {
    "base": 1.0,  # Game state only
    "peak": 5.0   # During inference
}
```

**Strategy 3: Model Quantization Levels**
```python
# Keep multiple quantization levels
# Use Q4 normally, Q3 if memory pressure
models = {
    "phi-3-mini-q4": 2.5,  # Normal quality
    "phi-3-mini-q3": 1.8   # Lower quality, emergency
}
```

**Measure:**
- Swap frequency
- Swap latency impact
- OOM frequency
- Quality degradation

**Success Criteria:**
- No OOMs in 4-hour session
- <5.5GB peak usage
- <2s swap time

**Deliverables:**
- VRAM management strategy
- Memory monitor system
- Emergency fallback procedures

---

### Q6.3: When to use delta updates vs full refresh?

**Investigation Plan:**

**Perception Update Strategies:**

```python
# Strategy 1: Full Refresh
def full_refresh(characters, game_state):
    """Recompute all perception from scratch"""
    # Pro: Always accurate
    # Con: Expensive

# Strategy 2: Delta Updates
def delta_update(characters, changes):
    """Only update what changed"""
    # Pro: Fast
    # Con: Can drift from reality

# Strategy 3: Hybrid
def hybrid_update(characters, changes, tick_count):
    """Delta most of the time, full refresh periodically"""
    if tick_count % 100 == 0:
        return full_refresh(characters)
    return delta_update(characters, changes)
```

**Test Scenarios:**
- Combat (frequent changes)
- Exploration (infrequent changes)
- Social (minimal changes)

**Measure:**
- Accuracy drift over time
- Performance improvement
- CPU/memory impact

**Success Criteria:**
- <1% accuracy drift after 100 ticks
- 5x+ speedup from delta updates
- Full refresh <10ms

**Deliverables:**
- Update strategy recommendations
- Drift detection system
- Hybrid scheduler

---

## 📊 **VALIDATION METHODOLOGY**

### How to Validate Research Findings

**Quantitative Validation:**
- Automated benchmarks (performance, metrics)
- Statistical significance testing
- A/B testing where applicable
- Repeated trials for consistency

**Qualitative Validation:**
- User surveys (DMs and players)
- Expert reviews (experienced DMs)
- Playtesting sessions
- Transcript analysis

**Validation Checklist:**
```
For each research question:
☐ Hypothesis stated clearly
☐ Test methodology documented
☐ Data collection plan
☐ Success criteria defined
☐ Multiple trials conducted
☐ Results analyzed and documented
☐ Recommendations actionable
☐ Limitations acknowledged
```

---

## 🎯 **RESEARCH TIMELINE**

### Week 1: Critical Foundation
- Q1.1: Local LM selection 🔴
- Q1.2: Context window testing 🔴
- Q2.1: Personality consistency 🔴

### Week 2: Core Mechanics
- Q1.3: Multi-model strategy 🔴
- Q1.4: Batching optimization 🔴
- Q2.2: Evolution vs drift 🔴
- Q4.1: Bot parameters 🟡

### Week 3: Quality & Experience
- Q3.1: Transcript quality 🟡
- Q3.2: RP/mechanics ratio 🟡
- Q4.2: Human-like behavior 🟡
- Q4.3: Escalation triggers 🟡

### Week 4-5: DM Experience
- Q5.1: Automation opportunities 🟡
- Q5.2: Twin learning speed 🟡
- Q5.3: Suggestion UI 🟡
- Q3.3: Immersion testing 🟡

### Week 6-7: Optimization
- Q2.3: LoRA effectiveness 🟡
- Q2.4: Relationship modeling 🟡
- Q6.1: Batch windows 🟢
- Q6.2: VRAM management 🟢
- Q6.3: Update strategies 🟢

---

## 💡 **RESEARCH BEST PRACTICES**

1. **Document Everything**
   - Record all experiments
   - Save all test data
   - Version control configurations

2. **Iterate Quickly**
   - Start with simple tests
   - Fail fast, learn fast
   - Don't over-engineer early

3. **Validate Assumptions**
   - Don't assume anything
   - Test edge cases
   - Cross-validate findings

4. **Share Findings**
   - Write clear summaries
   - Include examples
   - Provide recommendations

5. **Stay Flexible**
   - Research may reveal surprises
   - Be ready to pivot
   - Update plans based on findings

---

## 🚀 **NEXT STEPS**

1. **This Week:**
   - Set up testing environment
   - Install local LM tools
   - Begin Q1.1 (model selection)

2. **Deliverable Template:**
   ```markdown
   # Research Finding: [Question]
   
   ## Hypothesis
   [What we expected]
   
   ## Methodology
   [How we tested]
   
   ## Results
   [What we found]
   
   ## Analysis
   [What it means]
   
   ## Recommendations
   [What to do]
   
   ## Limitations
   [What we didn't test]
   ```

3. **Progress Tracking:**
   - Weekly research updates
   - Findings document (running)
   - Decisions log (rationale)

---

## 🎊 **RESEARCH PHILOSOPHY**

> "We're not building what we think will work. We're discovering what actually works through rigorous testing and validation. Every assumption is a hypothesis to be tested."

**Remember:** The goal isn't to confirm our ideas. It's to find the truth, even if it means changing our plans.

**Let's discover what makes great AI D&D together!** 🔬🎲
