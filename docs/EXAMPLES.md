# DMLog UX Examples (Level 4)

**Real-World Usage Scenarios and Workflows**

---

## Table of Contents

1. [Usage Scenarios](#usage-scenarios)
2. [Complete Workflows](#complete-workflows)
3. [Example Sessions](#example-sessions)
4. [Character Progression](#character-progression)
5. [Advanced Patterns](#advanced-patterns)
6. [Troubleshooting Scenarios](#troubleshooting-scenarios)

---

## Usage Scenarios

### Scenario 1: Solo D&D with AI Party

**User Story:** I want to play D&D alone with AI party members who remember our adventures.

**Workflow:**

```
Day 1: Setup
├── Create campaign "The Dragon's Hoard"
├── Create 3 AI characters:
│   ├── Thorin (Fighter) - tank, brave
│   ├── Eldara (Wizard) - magic, cautious
│   └── Lira (Bard) - social, charismatic
└── Create Session 1

Day 1-5: Gameplay
├── Session 1: Goblin ambush (learn combat patterns)
├── Session 2: Town investigation (learn social patterns)
├── Session 3: Dungeon exploration (learn exploration)
├── Session 4: Boss fight (apply combat learning)
└── Session 5: Return to town (social development)

After Session 5:
├── Characters have 50+ memories each
├── Detect patterns: "Goblins always ambush at entrances"
├── Consolidate: "Dungeon entrances require caution"
└── Update: Thorin now always checks for ambushes

Day 6: Continue with improved characters!
```

**Example: First Combat Experience**

```
[DM] A goblin jumps from behind a rock!

[System] Routing decision for Thorin...
  Situation: Combat, goblin attack
  Stakes: 0.5 (routine combat)
  Novelty: 0.2 (seen goblins before)
  History: 3 previous goblin fights, 2 wins
  Route: BOT (fast, confident)

[Thorin] I swing my battleaxe! *rolls 15*
  DM: You hit for 7 damage. Goblin defeated.

[System] Recording outcome...
  Success: Yes
  Damage: 7
  Reward: +0.6 combat, +0.1 resource

[System] Memory formed:
  "Defeated goblin ambush on the trail"
  Type: EPISODIC
  Importance: 5.5 (routine)

[After 3 more similar fights]
[System] Consolidation triggered!
  Pattern: 4 goblin fights at trail entrances
  Semantic memory: "Goblins prefer trail ambushes"
  Procedural: "Always watch trails for goblin signs"

[Next Session]
[DM] You approach another trail entrance...

[System] Routing decision for Thorin...
  Memories retrieved: 5 about goblin ambushes
  Pattern matched: "trail = goblin ambush"
  Route: BOT with high confidence
  Action: "I carefully scan the trail for signs of goblins"

[Thorin] *Before walking* "Hold on, brothers. Goblins love these trails.
  Let me check for their signs first."
```

### Scenario 2: AI Dungeon Master

**User Story:** I want an AI DM who remembers our previous sessions and creates a coherent campaign.

**Workflow:**

```
Setup:
├── Create campaign "Shadows of Mystara"
├── Add player characters (human-controlled)
├── Enable DM automation
└── Load world lore

Session Flow:
├── DM retrieves world lore from vector store
├── DM recalls what happened last session
├── DM generates context-appropriate encounters
├── Players make decisions
├── DM tracks outcomes and updates world state
└── DM consolidates world changes

Over Time:
├── DM remembers killed NPCs
├── DM tracks faction relationships
├── DM evolves plot based on player choices
└── DM creates consistent world responses
```

**Example: Coherent World Response**

```
[Session 1]
[DM] You meet Gundren Rockseeker in town. He hires you to find
     his brothers at Wave Echo Cave.

[Player] We accept the quest!

[System] Memory: "Met Gundren, accepted Wave Echo Cave quest"
[World State] Gundren.status = "quest_giver_known"

---

[Session 3]
[Player] We return to town. Can we talk to Gundren?

[System] Retrieving memories about Gundren...
  Found: "Met Gundren, accepted Wave Echo Cave quest"
  Found: "Gundren's brothers are missing"
  Found: "Working for Gundren"

[DM] You find Gundren at the inn. He looks hopeful as you approach.
     "Did you find any news of my brothers?"

[Player] Yes, we found them! They're prisoners at the Cragmaw den.

[System] Memory: "Reported Rockseeker location to Gundren"
[World State] Gundren.status = "grateful"
[World State] Cragmaw.goblins.reputation = -2

---

[Session 5]
[Player] We're back in town. We need supplies.

[System] World knowledge:
  - Gundren is grateful (relationship: +2)
  - Party completed his quest
  - Town knows party helped Rockseekers

[DM] The townsfolk wave as you walk through. The innkeeper calls out,
     "Heroes of the Rockseeker family! Drinks are on the house tonight!"
     Gundren rushes over to thank you personally.

[Player] (Internal note: The world remembers what we did!)
```

### Scenario 3: Digital Twin Training

**User Story:** I want to create an AI that plays D&D like I do, so it can sub for me when I'm absent.

**Workflow:**

```
Phase 1: Data Collection (5-10 sessions)
├── Player makes decisions normally
├── System logs all decisions with context
├── System records outcomes
└── Quality scores calculated

Phase 2: Analysis
├── Review decision patterns
├── Identify playstyle (aggressive, cautious, social, etc.)
├── Note signature moves
└── Check success rate

Phase 3: Training
├── Export training data (high quality only)
├── Fine-tune model with QLoRA
├── Validate against test set
└── Deploy digital twin

Phase 4: Deployment
├── Digital twin plays in player's absence
├── Player can review and approve decisions
├── Twin continues learning from new sessions
└── Periodic re-training for improvement
```

**Example: Playstyle Capture**

```
[Player's Real Decisions over 5 Sessions]
├── Combat: Always checks for ambushes first
├── Social: Prefers diplomacy over violence
├── Exploration: Thorough, checks for traps
├── Magic: Saves spells for bosses
└── Roleplay: In-character, dramatic

[Captured Patterns]
Pattern 1: "Before any door, check for traps" (95% consistency)
Pattern 2: "Try talking first, fighting last" (80% consistency)
Pattern 3: "Save highest-level spell slot" (100% consistency)
Pattern 4: "Dramatic entrance for important scenes" (70% consistency)

[Digital Twin Behavior]
[DM] You reach the dungeon entrance.

[Twin] *Pauses dramatically* "Before us lies the entrance to the
     Crypt of Shadows. But before we rush in..." *checks door carefully*
     "...let me make sure there are no unpleasant surprises."

[Player] That's exactly what I would do!

[System] Digital twin confidence: 92%
[System] Match to playstyle: High
```

---

## Complete Workflows

### Workflow 1: Complete Campaign Setup

```
Step 1: Create Campaign
├── Define campaign name and setting
├── Add initial world lore (3-5 key facts)
├── Set DM (human or AI)
└── Save campaign_id

Step 2: Create Characters
├── For each character:
│   ├── Define name, race, class
│   ├── Set ability scores
│   ├── Add personality traits (3-5)
│   ├── Write backstory (1-2 paragraphs)
│   └── Save character_id
└── Typical party: 3-5 characters

Step 3: Create First Session
├── Link to campaign
├── Set session number
└── Join all characters

Step 4: Gameplay Loop
├── For each situation:
│   ├── Describe situation
│   ├── Route decisions per character
│   ├── Execute actions
│   ├── Record outcomes
│   └── Form memories
└── Continue until session end

Step 5: End Session
├── Calculate session metrics
├── Trigger consolidation
└── Save for next time
```

### Workflow 2: Character Development Session

```
Pre-Session: Review
├── Check character memories
├── Note recent learning
├── Identify growth areas
└── Plan encounters for growth

During Session: Challenges
├── Present novel situations
├── Require different decision types
├── Vary stakes levels
└── Track decision quality

Post-Session: Analysis
├── Review teaching moments
├── Note patterns emerged
├── Check consolidation results
└── Adjust thresholds if needed
```

---

## Example Sessions

### Example Session 1: Learning from Combat

**Scenario:** Party encounters goblins for the third time

**Initial State (Sessions 1-2):**
- Party fought goblins twice, lost both times
- Characters have low confidence vs goblins
- Memories: "Goblins are dangerous", "We lost to goblins"

**Session 3:**

```
[Turn 1]
[DM] Three goblins appear on the ridge!

[System] Routing for Thorin (Fighter)...
  Context: Combat, goblins (seen 2x, lost both)
  Stakes: 0.7 (high - lost before)
  Recent failures: 2 (both vs goblins)
  Confidence: LOW
  Route: BRAIN (needs careful thinking)

[Thorin] "Goblins again! Everyone form a defensive line.
  Don't let them flank us like last time!"

[System] Memory formed:
  "Recognized goblin threat from past losses"
  Type: EPISODIC
  Importance: 8.0 (learning from failure)

---

[Turn 3]
[DM] A goblin breaks through and charges Eldara!

[System] Routing for Thorin...
  Context: Ally threatened, goblin combat
  Stakes: 0.9 (ally danger)
  Memory: "Lost to goblin flank last time"
  Route: BRAIN/HUMAN (high stakes)

[Thorin] "Not this time!" *intercepts goblin* "Over here,
  you little menace!" *rolls 18, hits for 9 damage*

[System] Memory formed:
  "Protected ally from goblin flank"
  Type: EPISODIC
  Importance: 9.0 (emotional peak)
  Landmark: PEAK_EMOTION

---

[After Combat - Victory]
[System] Outcome tracking...
  Success: YES (first victory vs goblins)
  Teaching moments: 2 (good tactics learned)
  Rewards: COMBAT +0.8, STRATEGIC +0.6

[System] Consolidation check...
  Importance accumulator: 45.3 (not yet at 150)

---

[After Session 5 - Multiple goblin fights, some wins]
[System] Consolidation triggered!
  Pattern: 5 goblin fights, 3 wins, 2 losses
  Semantic: "Goblins are dangerous but beatable with tactics"
  Procedural: "Always protect casters from goblin flanking"
  Landmark created: "First major victory vs goblins"

[Next session]
[DM] Goblins appear!

[System] Routing for Thorin...
  Context: Combat, goblins
  Memories: 8 goblin-related memories
  Semantic: "Beat goblins with tactics"
  Confidence: HIGH (0.82)
  Route: BOT with confidence

[Thorin] *Immediately* "Everyone stay together! Casters in back,
  protect the flanks! We've beaten them before, we'll do it again!"
```

### Example Session 2: Social Development

**Scenario:** Bard character develops diplomatic skills

**Progression:**

```
[Session 1 - First Social Encounter]
[Lira's Attempt]
[System] Route: BRAIN (novel social situation)
[Lira] "Hello there! We're just passing through..."
[Innkeeper] *Suspicious* "What do you want?"
[Lira] *Nervous* "Well, um, information?"

[System] Outcome: Mixed success
Memory: "First inn interaction - awkward"
Importance: 6.0

---

[Session 3 - Getting Better]
[System] Route: BRAIN (some experience)
[Memories Retrieved]: 2 inn interactions, 1 success
[Lira] "Good sir! My companions and I have had a long journey.
  Might we trouble you for a drink and some local news?"

[System] Outcome: Success!
[Lira] *Thinking* "I'm getting better at this..."

[System] Memory: "Successfully got information with politeness"
Importance: 7.5

---

[Session 5 - Consolidation]
[System] Pattern detected: 5 successful social interactions using:
  - Politeness
  - Offering payment/custom
  - Flattery
  - Honest intentions

[System] Semantic memory: "Most people respond well to
  respectful, honest approach"
System] Procedural: "Always be polite first, offer trade second"

---

[Session 10 - Expert Social Character]
[DM] The suspicious guard blocks your path.

[System] Route: BOT (high confidence - 0.9)
[Memories]: 15+ successful social interactions
[Semantic]: "Guards respond to respect and authority"

[Lira] *Confidently* "Good sir, we are on official business for
  the Town Council. Would you really delay us and risk
  explaining why to your captain?"

[Guard] *Pauses, then steps aside* "Very well. Pass."

[Lira] *To party* "See? Respect and authority - works every time."

[System] Memory: "Successfully used authority with guard"
Importance: 6.0 (routine success now)
```

---

## Character Progression

### Example: Thorin's Growth Over 10 Sessions

**Session 1: Novice Warrior**
```
Decisions: 12
Success Rate: 42%
Route Distribution: 10% Bot, 60% Brain, 30% Human
Memories: 8
Key Learning: "Combat is dangerous"
```

**Session 5: Developing Fighter**
```
Decisions: 15
Success Rate: 67%
Route Distribution: 30% Bot, 50% Brain, 20% Human
Memories: 42
Key Learning: "Team tactics win fights"
Semantic Memories: 3
- "Protect the casters"
- "Goblins flank from sides"
- "Always check for traps"
```

**Session 10: Veteran Warrior**
```
Decisions: 18
Success Rate: 81%
Route Distribution: 55% Bot, 35% Brain, 10% Human
Memories: 89
Key Learning: "Experience guides my blade"
Semantic Memories: 12
Procedural Memories: 5
Temporal Landmarks: 3
- First battle victory
- Near-death experience
- Leadership moment

Autobiographical Narrative:
"I am Thorin Ironforge, a dwarf who has learned that the axe is not
the only weapon a warrior carries. I have fought goblins, orcs,
and worse, and learned that protecting my companions is more
important than personal glory. I remember the fear of my first
battle, the warmth of victory, and the cold touch of death's
door when I fell. These experiences have made me not just a
fighter, but a guardian. My companions trust me to watch their
backs, and that trust is my greatest treasure."
```

---

## Advanced Patterns

### Pattern 1: Multi-Character Coordination

```
[System] Recognizes party formation:
  - Thorin (Fighter) - Front
  - Eldara (Wizard) - Back
  - Lira (Bard) - Middle

[System] Coordinates actions:
  Thorin: "I hold the front line!"
  Eldara: "Magic support from rear!"
  Lira: "I'll support both!"

[System] Memory: "Effective party formation established"
```

### Pattern 2: Adaptive Difficulty

```
[System] Notices: Party winning easily
[System] Increases stakes subtly:
  - More enemies
  - Smarter tactics
  - Environmental hazards

[System] Party adapts:
  - New strategies learned
  - Memories of harder fights
  - Growth through challenge
```

### Pattern 3: Emotional Development

```
[Early Sessions]
[Thorin] "I fight for gold!"
[Emotional Valence]: Neutral (0.0)

[Middle Sessions]
[Thorin] "I fight for my friends!"
[Emotional Valence]: Positive (0.6)
[Landmark]: "First time prioritizing others over self"

[Late Sessions]
[Thorin] "I fight because someone must."
[Emotional Valence]: Complex (-0.2, noble melancholy)
[Landmark]: "Mature understanding of violence"
```

---

## Troubleshooting Scenarios

### Scenario: Character Making Bad Decisions

**Problem:** Character keeps routing to Bot when Brain would be better

**Diagnosis:**
```
[System] Check character thresholds...
  bot_min_confidence: 0.7 (default)
  recent_failures: 0
  success_rate: 85%

[Issue]: High success rate = lower thresholds = more Bot routes
```

**Solution:**
```
Option 1: Adjust thresholds
  engine.set_thresholds(char_id,
    EscalationThresholds(bot_min_confidence=0.5))

Option 2: Increase stakes
  context.stakes = 0.8  # Forces Brain route

Option 3: Add novelty
  Make situations more unique
```

### Scenario: Memory Overload

**Problem:** Too many memories, slow retrieval

**Diagnosis:**
```
[System] Memory count: 542
[System] Average retrieval time: 450ms (target: <50ms)

[Issue]: Unpruned memories, no consolidation
```

**Solution:**
```
Option 1: Manual prune
  memory.prune_old_memories(days=90, importance_lt=5.0)

Option 2: Force consolidation
  memory.episodic_to_semantic_consolidation()

Option 3: Adjust retention
  memory.set_max_memories(max_episodic=200)
```

### Scenario: Character Drifting

**Problem:** Character acting out of personality

**Diagnosis:**
```
[System] Identity Coherence Index: 0.62 (warning)
[System] Core trait "bravery": Started at 0.8, now 0.5

[Issue]: Identity drift from poor quality decisions
```

**Solution:**
```
Option 1: Identity reinforcement
  memory.reinforce_identity_traits()

Option 2: Adjust training data
  Exclude low-quality decisions from training

Option 3: Manual trait reset
  character.reset_traits_to_baseline()
```

---

## Visual Guides

### Decision Flow Visualized

```
DECISION FLOW (Timeline)

|<- 50ms ->|<- 500ms ->|<- 2000ms ->|<- 5000ms ->|
   Urgent    Fast       Normal     Complex

 BOT ───────┬─────────┬──────────────┬─────────────
            │         │              │
            v         v              v
          Route    Execute        Record
                    Action        Outcome

 BRAIN ──────┬──────────┬─────────────┬─────────────
             │          │             │
             v          v             v
           Route      LLM Call     Execute
           (100ms)   (1-2s)        Record

 HUMAN ──────┬──────────────┬─────────────────────
             │              │
             v              v
           Route         Wait for
           (10ms)        Human Input
```

### Memory Consolidation Timeline

```
SESSION     |----|----|----|----|----|----|----|----|
            1    2    3    4    5    6    7    8    9

Consolidation     ^                   ^         ^
Points            |                   |         |
               Reflection           Sleep     Narrative
               (Immediate)       (Daily)    (Weekly)

Memory Types
EPISODIC  |████████████████████████████████|
SEMANTIC        |████████████████████████|
PROCEDURAL             |██████████████|
```

---

**Document Version:** 1.0.0
**Last Updated:** 2025-01-10
**Author:** Documentation R&D Agent
