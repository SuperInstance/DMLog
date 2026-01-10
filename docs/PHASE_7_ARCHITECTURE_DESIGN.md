# Phase 7: Learning Pipeline - Complete Architecture Design

**Status:** Design Phase - Review Before Implementation  
**Date:** October 22, 2025  
**Hardware Target:** RTX 4050, 6GB VRAM  
**Focus:** Social/dialogue learning over combat mechanics

---

## Executive Summary

This document specifies the complete architecture for Phase 7: a production-grade LoRA training pipeline that enables self-improving AI characters through "dream cycle" offline learning. Characters learn from gameplay experiences focusing on dialogue quality and decision-making effectiveness.

**Key Innovation:** Basketball-style learning where characters perform during gameplay (inference/"game time") and improve during intermissions (training/"practice time" with reflection and simulation).

**Memory Budget:** System runs on 6GB VRAM through QLoRA optimization
- Base model (3B, 4-bit): 4.0GB
- LoRA adapters: 0.3GB  
- Optimizer states (8-bit): 0.7GB
- Activations (checkpointed): 0.6GB
- System overhead: 0.4GB
- **Total: 6.0GB** ✅

---

## System Architecture Overview

### High-Level Flow

```
GAMEPLAY SESSION (Inference Mode)
    ↓
[1] Experience Collection
    └─ Log every interaction with context/decision/outcome
    ↓
[2] Session End Trigger
    └─ 1 hour gameplay OR 50+ quality interactions
    ↓
[3] DREAM CYCLE BEGINS (Training Mode)
    ↓
[4] Reflection Phase (GPT-4/Claude)
    └─ Analyze patterns, identify learning opportunities
    ↓
[5] Data Curation
    └─ Filter, weight, select high-quality examples
    ↓
[6] Data Augmentation
    └─ Generate variations and what-if scenarios
    ↓
[7] Constitutional Review
    └─ Ensure training data meets character principles
    ↓
[8] LoRA Training (30-60 min)
    └─ Fine-tune character on curated data
    ↓
[9] Validation Pipeline
    └─ Test personality, consistency, quality
    ↓
[10] Deployment Decision
    └─ Pass → Deploy | Fail → Rollback
    ↓
[11] Monitoring
    └─ Track real-world performance metrics
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    GAME ENGINE                          │
│  (Existing Phases 1-6: Characters, DM, Chat, etc.)    │
└────────────────┬────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────┐
│              EXPERIENCE LOGGER                          │
│  • Captures context-decision-outcome triplets          │
│  • Adds quality metrics (engagement, success)          │
│  • Writes to session buffer during gameplay            │
└────────────────┬────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────┐
│           DREAM CYCLE ORCHESTRATOR                      │
│  • Monitors session completion                          │
│  • Schedules training jobs                              │
│  • Manages GPU access (pause inference during train)   │
│  • Handles success/failure paths                        │
└────────────────┬────────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    ↓                         ↓
┌──────────────┐    ┌────────────────────┐
│  REFLECTION  │    │  DATA PROCESSING   │
│   ENGINE     │    │      PIPELINE      │
│              │    │                    │
│ • GPT-4/Claude│   │ • Curation        │
│ • Pattern    │    │ • Augmentation    │
│   analysis   │    │ • Constitutional  │
│ • Quality    │    │   review          │
│   scoring    │    │ • Formatting      │
└──────┬───────┘    └─────────┬──────────┘
       │                      │
       └──────────┬───────────┘
                  ↓
┌─────────────────────────────────────────────────────────┐
│              LORA TRAINER                               │
│  • QLoRA 4-bit training                                 │
│  • Gradient accumulation                                │
│  • Checkpoint management                                │
│  • Loss monitoring                                      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────┐
│           VALIDATION PIPELINE                           │
│  • Personality consistency tests                        │
│  • Quality metrics (engagement, tactical, lore)        │
│  • Uniqueness checks (vs other characters)             │
│  • Constitutional adherence                             │
└────────────────┬────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────┐
│          DEPLOYMENT MANAGER                             │
│  • A/B testing (canary → 50% → 100%)                   │
│  • Rollback on metric degradation                      │
│  • Version management                                   │
│  • Adapter registry                                     │
└────────────────┬────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────┐
│         MONITORING DASHBOARD                            │
│  • Real-time metrics                                    │
│  • Training history                                     │
│  • Performance trends                                   │
│  • Alert system                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. Experience Logger

**Purpose:** Capture rich context about every significant interaction during gameplay for later training.

**Data Model:**
```python
@dataclass
class GameplayExperience:
    # IDs and timestamps
    experience_id: str              # UUID
    character_id: str               # e.g., "marcus_guard"
    session_id: str                 # Groups experiences by session
    timestamp: float                # Unix timestamp
    
    # Context (what was happening)
    context: ExperienceContext = field(default_factory=dict)
    """
    {
        "game_state": {
            "location": "Castle Gate",
            "time_of_day": "night",
            "weather": "raining",
            "tension_level": 0.6
        },
        "character_state": {
            "hp": 100,
            "hp_max": 100,
            "status": "alert",
            "position": [10, 20],
            "recent_events": ["detected_player", "issued_warning"]
        },
        "other_entities": [
            {"id": "player1", "distance": 5, "weapon_drawn": True, "hp_percent": 0.5},
            {"id": "guard2", "distance": 15, "status": "patrolling"}
        ],
        "conversation_history": [
            {"speaker": "player1", "text": "I need to pass"},
            {"speaker": "marcus", "text": "State your business"}
        ]
    }
    """
    
    # Decision (what the character did)
    decision: ExperienceDecision = field(default_factory=dict)
    """
    {
        "action_taken": "call_backup_defensively",
        "reasoning": "Player ignored warning and has weapons drawn. Uncertain of intent. Protocol requires backup before engagement.",
        "alternatives_considered": [
            "attack_preemptively",
            "retreat_and_alert",
            "continue_negotiation"
        ],
        "decision_source": "brain",  # "bot" or "brain"
        "confidence": 0.65,
        "response_text": "Guards! To me! We have a suspicious individual at the gate."
    }
    """
    
    # Outcome (what happened)
    outcome: ExperienceOutcome = field(default_factory=dict)
    """
    {
        "immediate_result": "backup_arrived_player_fled",
        "combat_occurred": False,
        "casualties": 0,
        "player_action": "flee",
        "narrative_advancement": "player_learned_guards_coordinated",
        "success_metrics": {
            "combat_effectiveness": 1.0,  # (prevented combat successfully)
            "narrative_quality": 0.8,     # (good tension, realistic)
            "player_engagement": 0.7,     # (player stayed in game)
            "character_consistency": 0.9  # (acted cautiously as expected)
        }
    }
    """
    
    # Quality metadata
    quality_score: float = 0.5      # Overall quality (0-1)
    engagement_signal: float = 0.5  # Player engagement indicator
    novelty_score: float = 0.5      # How unusual/interesting
    is_training_candidate: bool = True  # Pre-filter flag
    
    # Training metadata
    training_weight: float = 1.0    # Importance for training
    reflection_notes: str = ""      # GPT-4 analysis notes
    constitutional_score: float = 0.0  # Adherence to principles
```

**Collection Points:**
- After every character decision (bot or brain)
- After every NPC interaction completion
- After combat encounters
- After significant dialogue exchanges (3+ turns)

**Filtering Logic (Real-time):**
```python
def should_log_experience(interaction) -> bool:
    """Decide if experience is worth logging"""
    # Always log if:
    if interaction.decision_source == "brain":  # Brain decisions are higher value
        return True
    if interaction.context.tension_level > 0.7:  # High-stakes situations
        return True
    if interaction.outcome.combat_occurred:  # Combat always interesting
        return True
    
    # Filter out low-value interactions
    if len(interaction.decision.response_text) < 20:  # Too short
        return False
    if interaction.quality_score < 0.3:  # Obviously bad
        return False
    
    return True  # Log by default, final filtering in curation
```

**Storage:**
- Session buffer: In-memory list during gameplay
- Batch write on session end: Write all to JSONL file
- File path: `/characters/{character_id}/experiences/session_{session_id}.jsonl`
- Retention: 30 days (raw experiences)

---

### 2. Dream Cycle Orchestrator

**Purpose:** Coordinate the entire training pipeline from session end to deployment.

**Trigger Conditions:**
1. Session ends (player logs out or DM calls end)
2. 50+ quality experiences collected (even if session continues)
3. Manual trigger (developer/DM commands training)
4. Scheduled trigger (e.g., daily at 3am for all characters)

**State Machine:**
```python
class DreamCycleState(Enum):
    IDLE = "idle"                          # Waiting for trigger
    COLLECTING = "collecting"              # Gameplay session active
    REFLECTING = "reflecting"              # GPT-4 analysis phase
    CURATING = "curating"                  # Data processing
    TRAINING = "training"                  # LoRA fine-tuning
    VALIDATING = "validating"              # Quality checks
    DEPLOYING = "deploying"                # Rolling out new version
    MONITORING = "monitoring"              # Watching metrics
    FAILED = "failed"                      # Error occurred
    ROLLED_BACK = "rolled_back"            # Reverted due to issues

class DreamCycleJob:
    job_id: str
    character_id: str
    session_ids: List[str]
    state: DreamCycleState
    started_at: float
    completed_at: Optional[float]
    error: Optional[str]
    metrics: Dict[str, Any]
```

**Orchestration Flow:**
```python
async def run_dream_cycle(character_id: str, session_ids: List[str]):
    """Complete dream cycle pipeline"""
    job = create_job(character_id, session_ids)
    
    try:
        # Phase 1: Load experiences
        job.state = DreamCycleState.REFLECTING
        experiences = load_experiences(character_id, session_ids)
        log_info(f"Loaded {len(experiences)} experiences")
        
        # Phase 2: Reflection with GPT-4
        reflection = await reflect_on_experiences(character_id, experiences)
        save_reflection(character_id, session_ids, reflection)
        
        # Phase 3: Data curation
        job.state = DreamCycleState.CURATING
        curated_data = curate_training_data(
            experiences, 
            reflection,
            quality_threshold=0.7
        )
        
        # Phase 4: Data augmentation
        augmented_data = await augment_training_data(
            curated_data,
            character_id,
            augmentation_factor=3
        )
        
        # Phase 5: Constitutional review
        constitutional_data = await constitutional_review(
            augmented_data,
            character_id
        )
        
        # Phase 6: Format for training
        training_dataset = format_for_training(constitutional_data, character_id)
        save_training_data(character_id, training_dataset)
        
        # Phase 7: Train LoRA adapter
        job.state = DreamCycleState.TRAINING
        new_adapter_path = await train_lora_adapter(
            character_id,
            training_dataset,
            config=load_training_config(character_id)
        )
        
        # Phase 8: Validation
        job.state = DreamCycleState.VALIDATING
        validation_results = await validate_adapter(
            character_id,
            new_adapter_path
        )
        
        # Phase 9: Deployment decision
        if validation_results.passes_all_thresholds():
            job.state = DreamCycleState.DEPLOYING
            await deploy_adapter(
                character_id,
                new_adapter_path,
                deployment_strategy="canary"  # 10% → 50% → 100%
            )
            
            # Phase 10: Monitor for 24 hours
            job.state = DreamCycleState.MONITORING
            await monitor_deployment(character_id, duration_hours=24)
            
        else:
            # Validation failed - don't deploy
            log_warning(f"Validation failed for {character_id}")
            log_warning(f"Results: {validation_results}")
            job.state = DreamCycleState.FAILED
            return
        
        # Success!
        job.state = DreamCycleState.COMPLETED
        job.completed_at = time.time()
        
    except Exception as e:
        job.state = DreamCycleState.FAILED
        job.error = str(e)
        log_error(f"Dream cycle failed for {character_id}: {e}")
        
        # Emergency rollback if we partially deployed
        if job.state in [DreamCycleState.DEPLOYING, DreamCycleState.MONITORING]:
            await emergency_rollback(character_id)
```

**GPU Management:**
During training, we need to free up GPU memory. Two strategies:

**Strategy A: Pause Inference (Recommended)**
```python
def pause_inference_for_training(character_id: str):
    """Pause gameplay inference while training"""
    # Save current inference state
    multi_lora_manager.save_state()
    
    # Unload all LoRA adapters from GPU
    multi_lora_manager.unload_all()
    
    # Unload base model
    llm_engine.unload_model()
    
    # Now we have full 6GB for training
    
def resume_inference_after_training():
    """Resume gameplay inference"""
    # Reload base model
    llm_engine.load_model()
    
    # Restore LoRA adapters
    multi_lora_manager.restore_state()
```

**Strategy B: Off-Peak Training**
- Schedule training during low-traffic periods (3-6am)
- Players can still play but training queue waits
- Good for production, but delays learning

**Recommended:** Use Strategy A with "snack break" messaging:
> "The characters are reflecting on today's adventures... Grab a snack! Training ETA: 45 minutes"

---

### 3. Reflection Engine

**Purpose:** Use GPT-4 or Claude to analyze gameplay patterns and identify learning opportunities.

**Reflection Prompt Template:**
```python
REFLECTION_PROMPT = """You are analyzing gameplay experiences for {character_name}, a {character_description}.

CHARACTER PERSONALITY:
{personality_description}

CHARACTER PRINCIPLES (Constitution):
{constitutional_principles}

GAMEPLAY EXPERIENCES:
Below are {num_experiences} interactions from today's {session_duration} hour session.

{formatted_experiences}

ANALYSIS TASKS:
1. PATTERNS: What patterns do you notice in this character's behavior? Are they acting consistently with their personality?

2. WHAT WORKED WELL: Identify 3-5 specific examples where the character made excellent decisions. For each:
   - Quote the key interaction
   - Explain why it was effective
   - Note what made it align with character principles

3. WHAT NEEDS IMPROVEMENT: Identify 3-5 specific examples where the character could have done better. For each:
   - Quote the interaction
   - Explain what went wrong
   - Suggest how it should have been handled
   - Note any principle violations

4. PLAYER ENGAGEMENT: When did the player seem most engaged? Least engaged? What character behaviors correlated with engagement?

5. CONSISTENCY ISSUES: Did the character ever act out of character? Were there personality inconsistencies?

6. TRAINING FOCUS: Based on this analysis, what specific skills should this character practice? What scenarios should we generate for what-if training?

7. QUALITY SCORES: For each experience, provide a quality score (0-10) where:
   - 0-3: Poor quality, don't use for training
   - 4-6: Acceptable, use with low weight
   - 7-8: Good quality, standard training
   - 9-10: Excellent, emphasize in training

Provide your analysis in JSON format:
{
    "patterns": ["pattern1", "pattern2", ...],
    "excellent_examples": [
        {
            "experience_id": "...",
            "quote": "...",
            "why_effective": "...",
            "principles_demonstrated": ["principle1", ...]
        },
        ...
    ],
    "needs_improvement": [
        {
            "experience_id": "...",
            "quote": "...",
            "problem": "...",
            "suggested_improvement": "...",
            "principle_violations": ["principle1", ...]
        },
        ...
    ],
    "engagement_insights": {
        "high_engagement_moments": ["..."],
        "low_engagement_moments": ["..."],
        "correlations": "..."
    },
    "consistency_issues": ["issue1", ...],
    "training_focus_areas": ["area1", "area2", ...],
    "experience_scores": {
        "experience_id_1": 8,
        "experience_id_2": 3,
        ...
    }
}
"""
```

**API Call Structure:**
```python
async def reflect_on_experiences(
    character_id: str,
    experiences: List[GameplayExperience]
) -> ReflectionReport:
    """Call GPT-4 to analyze experiences"""
    
    # Load character profile
    character = load_character_profile(character_id)
    
    # Format experiences for prompt
    formatted = format_experiences_for_reflection(experiences)
    
    # Build prompt
    prompt = REFLECTION_PROMPT.format(
        character_name=character.name,
        character_description=character.description,
        personality_description=character.personality.to_text(),
        constitutional_principles=character.constitution.to_text(),
        num_experiences=len(experiences),
        session_duration=calculate_session_duration(experiences),
        formatted_experiences=formatted
    )
    
    # Call GPT-4 (or Claude)
    response = await openai.ChatCompletion.create(
        model="gpt-4-turbo",  # or "claude-opus-4"
        messages=[
            {"role": "system", "content": "You are an expert game AI analyst."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,  # Lower temp for more consistent analysis
        max_tokens=4000
    )
    
    # Parse JSON response
    reflection = ReflectionReport.from_json(response.choices[0].message.content)
    
    return reflection
```

**Cost Optimization:**
- Batch multiple characters per API call when possible
- Cache reflections for 7 days (characters may not need daily reflection once stable)
- Use GPT-4-turbo (50% cheaper than GPT-4)
- Consider fine-tuning a smaller model on GPT-4 reflections after 20-30 examples

**Reflection Storage:**
```
/characters/{character_id}/reflections/
    session_{session_id}_reflection.json
    weekly_analysis_{date}.json
    monthly_summary_{date}.json
```

---

### 4. Data Curation Pipeline

**Purpose:** Filter, weight, and select the best experiences for training.

**Curation Steps:**

**Step 1: Heuristic Filtering**
```python
def heuristic_filter(experience: GameplayExperience) -> bool:
    """Basic quality filters"""
    # Too short
    if len(experience.decision.response_text) < 20:
        return False
    
    # Too long (might be rambling)
    if len(experience.decision.response_text) > 500:
        return False
    
    # Low engagement
    if experience.engagement_signal < 0.3:
        return False
    
    # Poor outcome
    if experience.outcome.success_metrics.get("overall", 0) < 0.4:
        return False
    
    # Explicitly marked bad
    if not experience.is_training_candidate:
        return False
    
    return True
```

**Step 2: GPT-4 Score Integration**
```python
def apply_reflection_scores(
    experiences: List[GameplayExperience],
    reflection: ReflectionReport
) -> List[GameplayExperience]:
    """Apply GPT-4 quality scores"""
    
    for exp in experiences:
        if exp.experience_id in reflection.experience_scores:
            gpt4_score = reflection.experience_scores[exp.experience_id]
            
            # Normalize to 0-1
            exp.quality_score = gpt4_score / 10.0
            
            # Add reflection notes
            for example in reflection.excellent_examples:
                if example.experience_id == exp.experience_id:
                    exp.reflection_notes = f"EXCELLENT: {example.why_effective}"
                    
            for example in reflection.needs_improvement:
                if example.experience_id == exp.experience_id:
                    exp.reflection_notes = f"IMPROVEMENT: {example.suggested_improvement}"
    
    return experiences
```

**Step 3: Calculate Training Weights**
```python
def calculate_training_weight(experience: GameplayExperience) -> float:
    """Sophisticated weighting for training importance"""
    
    weight = 1.0
    
    # Quality multiplier (0.5x to 2.0x)
    if experience.quality_score >= 0.9:
        weight *= 2.0  # Excellent examples
    elif experience.quality_score >= 0.7:
        weight *= 1.3  # Good examples
    elif experience.quality_score >= 0.5:
        weight *= 1.0  # Acceptable
    else:
        weight *= 0.5  # Questionable
    
    # Engagement multiplier (0.7x to 1.3x)
    weight *= (0.7 + experience.engagement_signal * 0.6)
    
    # Narrative quality
    narrative_score = experience.outcome.success_metrics.get("narrative_quality", 0.5)
    weight *= (0.8 + narrative_score * 0.4)
    
    # Novelty bonus (rare situations should be emphasized)
    if experience.novelty_score > 0.7:
        weight *= 1.3  # Unusual situation
    
    # Temporal decay (more recent = more relevant)
    age_hours = (time.time() - experience.timestamp) / 3600
    decay_factor = math.exp(-age_hours / 48)  # 48-hour half-life
    weight *= (0.5 + 0.5 * decay_factor)
    
    # Decision source bonus (brain decisions are rarer, more valuable)
    if experience.decision.decision_source == "brain":
        weight *= 1.2
    
    return min(weight, 3.0)  # Cap at 3x
```

**Step 4: Top-K Selection**
```python
def select_training_examples(
    experiences: List[GameplayExperience],
    reflection: ReflectionReport,
    quality_threshold: float = 0.7,
    max_examples: int = 200
) -> List[GameplayExperience]:
    """Select best examples for training"""
    
    # Apply filters
    filtered = [exp for exp in experiences if heuristic_filter(exp)]
    
    # Apply GPT-4 scores
    scored = apply_reflection_scores(filtered, reflection)
    
    # Calculate weights
    for exp in scored:
        exp.training_weight = calculate_training_weight(exp)
    
    # Filter by quality threshold
    high_quality = [exp for exp in scored if exp.quality_score >= quality_threshold]
    
    # Sort by weight
    sorted_examples = sorted(high_quality, key=lambda e: e.training_weight, reverse=True)
    
    # Take top K
    selected = sorted_examples[:max_examples]
    
    log_info(f"Selected {len(selected)}/{len(experiences)} examples for training")
    log_info(f"  Avg quality: {np.mean([e.quality_score for e in selected]):.2f}")
    log_info(f"  Avg weight: {np.mean([e.training_weight for e in selected]):.2f}")
    
    return selected
```

**Output:** 
- Typically 50-150 high-quality examples per session
- Weighted by importance
- Ready for augmentation

---

### 5. Data Augmentation Engine

**Purpose:** Multiply training examples through intelligent variations.

**Augmentation Techniques:**

**Technique 1: Paraphrasing (GPT-4)**
```python
async def paraphrase_experience(
    experience: GameplayExperience,
    character_id: str,
    num_variations: int = 3
) -> List[GameplayExperience]:
    """Generate paraphrased variations"""
    
    character = load_character_profile(character_id)
    
    prompt = f"""Paraphrase this character interaction {num_variations} times.
Maintain the character's personality, the core action, and the outcome.
Vary the wording naturally while keeping the meaning identical.

Character: {character.name} - {character.personality.description}

Original interaction:
Context: {experience.context}
Response: {experience.decision.response_text}

Generate {num_variations} paraphrased versions of the response that:
1. Sound natural and in-character
2. Preserve the exact same meaning and action
3. Use different wording and sentence structure

Return as JSON array of strings."""

    response = await openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8  # Higher temp for variation
    )
    
    paraphrases = json.loads(response.choices[0].message.content)
    
    # Create new experiences with paraphrased responses
    variations = []
    for i, paraphrased_text in enumerate(paraphrases):
        variant = copy.deepcopy(experience)
        variant.experience_id = f"{experience.experience_id}_para_{i}"
        variant.decision.response_text = paraphrased_text
        variant.training_weight *= 0.7  # Slightly lower weight for synthetic
        variations.append(variant)
    
    return variations
```

**Technique 2: What-If Scenarios**
```python
async def generate_whatif_scenarios(
    experience: GameplayExperience,
    character_id: str,
    num_scenarios: int = 2
) -> List[GameplayExperience]:
    """Generate counterfactual scenarios"""
    
    character = load_character_profile(character_id)
    
    prompt = f"""Generate {num_scenarios} "what-if" variations of this scenario.
Change ONE contextual element and predict how the character should respond differently.

Character: {character.name} - {character.personality.description}

Original scenario:
Context: {experience.context}
Character action: {experience.decision.response_text}
Outcome: {experience.outcome}

Generate scenarios like:
- "What if the player was friendly instead of hostile?"
- "What if it was daytime instead of night?"
- "What if the character was injured?"
- "What if there was a crowd watching?"

For each, provide:
1. The contextual change
2. How the character should respond differently
3. The expected outcome

Return as JSON array."""

    # Call GPT-4
    response = await openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    scenarios = json.loads(response.choices[0].message.content)
    
    # Create new experiences
    variations = []
    for i, scenario in enumerate(scenarios):
        variant = copy.deepcopy(experience)
        variant.experience_id = f"{experience.experience_id}_whatif_{i}"
        
        # Update context with change
        variant.context.update(scenario["contextual_change"])
        
        # Update response
        variant.decision.response_text = scenario["character_response"]
        
        # Update outcome
        variant.outcome = scenario["expected_outcome"]
        
        # Mark as synthetic
        variant.training_weight *= 0.8  # Synthetic but valuable
        
        variations.append(variant)
    
    return variations
```

**Technique 3: Entity Substitution**
```python
def entity_substitution(
    experience: GameplayExperience,
    num_variations: int = 2
) -> List[GameplayExperience]:
    """Swap entities while keeping structure"""
    
    variations = []
    
    # Extract entities from context
    entities = extract_entities(experience.context)
    
    # Define substitution rules
    substitutions = {
        "player": ["adventurer", "traveler", "stranger"],
        "guard": ["soldier", "watchman", "sentry"],
        "sword": ["blade", "weapon", "steel"],
        "castle": ["fortress", "keep", "stronghold"]
    }
    
    for i in range(num_variations):
        variant = copy.deepcopy(experience)
        variant.experience_id = f"{experience.experience_id}_sub_{i}"
        
        # Randomly substitute entities
        for entity_type, alternatives in substitutions.items():
            if entity_type in entities:
                replacement = random.choice(alternatives)
                
                # Replace in all text fields
                variant.context = replace_entity(variant.context, entity_type, replacement)
                variant.decision.response_text = variant.decision.response_text.replace(
                    entity_type, replacement
                )
        
        variant.training_weight *= 0.6  # Lower weight for mechanical substitution
        variations.append(variant)
    
    return variations
```

**Augmentation Pipeline:**
```python
async def augment_training_data(
    curated_examples: List[GameplayExperience],
    character_id: str,
    augmentation_factor: int = 3
) -> List[GameplayExperience]:
    """Apply all augmentation techniques"""
    
    augmented = list(curated_examples)  # Start with originals
    
    # For each high-quality example (quality >= 0.8)
    excellent_examples = [e for e in curated_examples if e.quality_score >= 0.8]
    
    for example in excellent_examples[:50]:  # Limit to top 50 to control API costs
        
        # Paraphrase (3 variations)
        if augmentation_factor >= 1:
            paraphrased = await paraphrase_experience(example, character_id, num_variations=2)
            augmented.extend(paraphrased)
        
        # What-if scenarios (2 variations)
        if augmentation_factor >= 2:
            whatifs = await generate_whatif_scenarios(example, character_id, num_scenarios=2)
            augmented.extend(whatifs)
        
        # Entity substitution (2 variations)
        if augmentation_factor >= 3:
            substituted = entity_substitution(example, num_variations=2)
            augmented.extend(substituted)
        
        # Throttle API calls
        await asyncio.sleep(0.5)
    
    log_info(f"Augmented {len(curated_examples)} → {len(augmented)} examples")
    
    return augmented
```

**Result:** 
- Input: 50-150 curated examples
- Output: 150-450 training examples (3x augmentation)
- Mix of original and synthetic data

---

### 6. Constitutional Review System

**Purpose:** Ensure all training data adheres to character principles.

**Character Constitution Format:**
```python
@dataclass
class CharacterConstitution:
    """Defines behavioral principles for a character"""
    character_id: str
    principles: List[Principle]
    
@dataclass
class Principle:
    name: str
    description: str
    priority: int  # 1=critical, 2=important, 3=nice-to-have
    examples: List[str]  # Example behaviors
    violations: List[str]  # Example violations
```

**Example Constitution (Marcus the Guard):**
```yaml
character_id: marcus_guard
principles:
  - name: stay_in_character
    description: "Marcus is cautious, experienced, and values life. He follows protocol and avoids unnecessary risks."
    priority: 1
    examples:
      - "Assess threats carefully before acting"
      - "Call for backup rather than solo engagement"
      - "Speak with authority but not aggression"
    violations:
      - "Acting recklessly or impulsively"
      - "Being overly aggressive without cause"
      - "Breaking character personality"
  
  - name: follow_protocol
    description: "Guards follow established procedures for threat assessment and response."
    priority: 1
    examples:
      - "Challenge suspicious individuals"
      - "Report incidents to superiors"
      - "Coordinate with other guards"
    violations:
      - "Ignoring protocols"
      - "Acting without authorization"
      - "Failing to report threats"
  
  - name: minimize_casualties
    description: "Prefer non-lethal solutions. Detain rather than kill when possible."
    priority: 2
    examples:
      - "Attempt to disarm before using lethal force"
      - "Call for surrender before attacking"
      - "Protect civilians"
    violations:
      - "Using excessive force"
      - "Killing when capture was possible"
      - "Endangering civilians"
  
  - name: maintain_narrative_quality
    description: "Responses should be engaging, advance the story, and feel realistic."
    priority: 2
    examples:
      - "Provide atmospheric details"
      - "React naturally to player actions"
      - "Create tension or resolve it appropriately"
    violations:
      - "Generic or boring responses"
      - "Repetitive dialogue"
      - "Breaking immersion"
  
  - name: avoid_repetition
    description: "Vary dialogue and actions while maintaining personality."
    priority: 3
    examples:
      - "Use different phrasings for similar situations"
      - "Reference past interactions when relevant"
      - "Adapt responses to context"
    violations:
      - "Repeating exact phrases frequently"
      - "Responding identically to different situations"
      - "Robotic or formulaic speech"
```

**Constitutional Review Process:**
```python
async def constitutional_review(
    training_examples: List[GameplayExperience],
    character_id: str
) -> List[GameplayExperience]:
    """Evaluate examples against character constitution"""
    
    character = load_character_profile(character_id)
    constitution = character.constitution
    
    reviewed_examples = []
    
    # Review in batches to reduce API calls
    batch_size = 10
    for i in range(0, len(training_examples), batch_size):
        batch = training_examples[i:i+batch_size]
        
        prompt = build_constitutional_review_prompt(batch, constitution)
        
        response = await openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2  # Low temp for consistent evaluation
        )
        
        reviews = parse_constitutional_reviews(response.choices[0].message.content)
        
        # Apply scores
        for example, review in zip(batch, reviews):
            example.constitutional_score = review.overall_score
            example.reflection_notes += f"\nConstitutional: {review.notes}"
            
            # Flag serious violations
            if review.has_critical_violations:
                log_warning(f"Critical violation in {example.experience_id}: {review.critical_violations}")
                continue  # Don't include in training
            
            reviewed_examples.append(example)
        
        await asyncio.sleep(0.5)  # Rate limiting
    
    log_info(f"Constitutional review: {len(reviewed_examples)}/{len(training_examples)} examples passed")
    
    return reviewed_examples
```

**Constitutional Review Prompt:**
```python
CONSTITUTIONAL_REVIEW_PROMPT = """You are evaluating character interactions for constitutional adherence.

CHARACTER: {character_name}
PRINCIPLES:
{formatted_principles}

INTERACTIONS TO EVALUATE:
{formatted_interactions}

For each interaction, evaluate:
1. Does it adhere to ALL critical (priority 1) principles?
2. Does it generally follow important (priority 2) principles?
3. Does it avoid violations?

Provide scores (0-10) and notes for each interaction.
Flag any critical violations (priority 1 principle violations should not be trained on).

Return as JSON:
{{
    "reviews": [
        {{
            "experience_id": "...",
            "overall_score": 8.5,
            "principle_scores": {{
                "stay_in_character": 9,
                "follow_protocol": 8,
                ...
            }},
            "has_critical_violations": false,
            "critical_violations": [],
            "notes": "Strong adherence to cautious personality..."
        }},
        ...
    ]
}}
"""
```

**Result:**
- Examples scored for constitutional adherence
- Critical violations filtered out
- Notes added for training guidance

---

### 7. LoRA Training Engine

**Purpose:** Fine-tune character LoRA adapters on curated data.

**Training Configuration:**
```python
@dataclass
class LoRATrainingConfig:
    """Configuration for LoRA training"""
    
    # Model
    base_model_path: str = "Qwen/Qwen2.5-3B-Instruct"  # or 1.5B for faster
    model_max_length: int = 2048
    
    # QLoRA quantization
    load_in_4bit: bool = True
    bnb_4bit_quant_type: str = "nf4"
    bnb_4bit_compute_dtype: str = "bfloat16"
    bnb_4bit_use_double_quant: bool = True
    
    # LoRA parameters
    lora_rank: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj"  # All attention
    ])
    use_rslora: bool = True  # Rank-stabilized LoRA
    
    # Training hyperparameters
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 8
    num_train_epochs: int = 2
    learning_rate: float = 1e-4
    warmup_ratio: float = 0.05
    lr_scheduler_type: str = "cosine"
    
    # Optimization
    optim: str = "paged_adamw_8bit"
    gradient_checkpointing: bool = True
    fp16: bool = False
    bf16: bool = True
    
    # Logging and checkpointing
    logging_steps: int = 10
    save_steps: int = 100
    save_total_limit: int = 3
    
    # Output
    output_dir: str = "./lora_output"
    run_name: Optional[str] = None
```

**Training Data Format:**
```python
def format_for_training(
    experiences: List[GameplayExperience],
    character_id: str
) -> List[Dict]:
    """Convert experiences to training format"""
    
    character = load_character_profile(character_id)
    training_data = []
    
    for exp in experiences:
        # Build conversation format
        conversation = {
            "messages": [
                {
                    "role": "system",
                    "content": build_system_prompt(character)
                },
                {
                    "role": "user",
                    "content": build_user_message(exp.context)
                },
                {
                    "role": "assistant",
                    "content": exp.decision.response_text,
                    # Include reasoning for chain-of-thought
                    "reasoning": exp.decision.reasoning
                }
            ],
            # Metadata for weighted sampling
            "weight": exp.training_weight
        }
        
        training_data.append(conversation)
    
    return training_data
```

**Training Loop:**
```python
async def train_lora_adapter(
    character_id: str,
    training_data: List[Dict],
    config: LoRATrainingConfig
) -> str:
    """Train LoRA adapter"""
    
    log_info(f"Starting LoRA training for {character_id}")
    log_info(f"  Training examples: {len(training_data)}")
    log_info(f"  Epochs: {config.num_train_epochs}")
    log_info(f"  Effective batch size: {config.per_device_train_batch_size * config.gradient_accumulation_steps}")
    
    # Setup output directory
    version = get_next_version(character_id)
    output_dir = f"/characters/{character_id}/lora_adapters/{version}"
    config.output_dir = output_dir
    config.run_name = f"{character_id}_{version}"
    
    # Initialize quantization config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=config.load_in_4bit,
        bnb_4bit_quant_type=config.bnb_4bit_quant_type,
        bnb_4bit_compute_dtype=getattr(torch, config.bnb_4bit_compute_dtype),
        bnb_4bit_use_double_quant=config.bnb_4bit_use_double_quant,
    )
    
    # Load base model
    model = AutoModelForCausalLM.from_pretrained(
        config.base_model_path,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    
    # Prepare for k-bit training
    model = prepare_model_for_kbit_training(model)
    
    # Apply LoRA
    lora_config = LoraConfig(
        r=config.lora_rank,
        lora_alpha=config.lora_alpha,
        target_modules=config.lora_target_modules,
        lora_dropout=config.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        use_rslora=config.use_rslora,
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # Prepare dataset
    tokenizer = AutoTokenizer.from_pretrained(config.base_model_path)
    dataset = prepare_dataset(training_data, tokenizer, config.model_max_length)
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=config.output_dir,
        per_device_train_batch_size=config.per_device_train_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        num_train_epochs=config.num_train_epochs,
        learning_rate=config.learning_rate,
        warmup_ratio=config.warmup_ratio,
        lr_scheduler_type=config.lr_scheduler_type,
        optim=config.optim,
        gradient_checkpointing=config.gradient_checkpointing,
        bf16=config.bf16,
        logging_steps=config.logging_steps,
        save_steps=config.save_steps,
        save_total_limit=config.save_total_limit,
        run_name=config.run_name,
    )
    
    # Initialize trainer with weighted sampling
    trainer = WeightedSFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
        max_seq_length=config.model_max_length,
        # Custom data collator for weighted sampling
        data_collator=WeightedDataCollator(tokenizer),
    )
    
    # Train
    log_info("Training started...")
    start_time = time.time()
    
    try:
        trainer.train()
        training_time = time.time() - start_time
        log_info(f"Training completed in {training_time/60:.1f} minutes")
        
        # Save final model
        trainer.save_model(output_dir)
        tokenizer.save_pretrained(output_dir)
        
        # Save training metadata
        save_training_metadata(character_id, version, {
            "training_time_seconds": training_time,
            "num_examples": len(training_data),
            "config": asdict(config),
            "final_loss": trainer.state.log_history[-1]["loss"]
        })
        
        return output_dir
        
    except Exception as e:
        log_error(f"Training failed: {e}")
        raise
```

**Weighted Sampling Implementation:**
```python
class WeightedDataCollator:
    """Data collator with weighted sampling"""
    
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
    
    def __call__(self, examples):
        # Extract weights
        weights = [ex.pop("weight", 1.0) for ex in examples]
        
        # Standard collation
        batch = self.tokenizer.pad(
            examples,
            padding=True,
            return_tensors="pt"
        )
        
        # Add sample weights (used by custom loss function)
        batch["sample_weights"] = torch.tensor(weights, dtype=torch.float32)
        
        return batch

class WeightedSFTTrainer(SFTTrainer):
    """Trainer with weighted loss"""
    
    def compute_loss(self, model, inputs, return_outputs=False):
        # Standard loss computation
        outputs = model(**inputs)
        logits = outputs.logits
        
        # Get sample weights
        weights = inputs.pop("sample_weights", None)
        
        # Compute loss
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = inputs["labels"][..., 1:].contiguous()
        
        loss_fct = CrossEntropyLoss(reduction="none")
        loss = loss_fct(
            shift_logits.view(-1, shift_logits.size(-1)),
            shift_labels.view(-1)
        )
        
        # Apply weights if provided
        if weights is not None:
            # Reshape weights to match loss shape
            weights = weights.view(-1, 1).expand_as(loss)
            loss = loss * weights
        
        loss = loss.mean()
        
        return (loss, outputs) if return_outputs else loss
```

**Monitoring Training:**
```python
def setup_training_monitoring(character_id: str, version: str):
    """Setup tensorboard and logging"""
    
    # Tensorboard
    log_dir = f"/characters/{character_id}/training_logs/{version}"
    writer = SummaryWriter(log_dir)
    
    # Training callback
    class MonitoringCallback(TrainerCallback):
        def on_log(self, args, state, control, logs=None, **kwargs):
            if logs:
                # Log to tensorboard
                for key, value in logs.items():
                    writer.add_scalar(f"train/{key}", value, state.global_step)
                
                # Check for anomalies
                if "loss" in logs:
                    if logs["loss"] > 10:
                        log_warning(f"High loss detected: {logs['loss']}")
                    if math.isnan(logs["loss"]):
                        log_error("NaN loss detected - training diverged!")
                        raise ValueError("Training diverged (NaN loss)")
        
        def on_save(self, args, state, control, **kwargs):
            log_info(f"Checkpoint saved at step {state.global_step}")
    
    return MonitoringCallback()
```

**Expected Training Time:**
- 1B model, 300 examples, 2 epochs: ~20-30 minutes
- 3B model, 300 examples, 2 epochs: ~45-60 minutes  
- 3B model, 500 examples, 3 epochs: ~90-120 minutes

---

### 8. Validation Pipeline

**Purpose:** Ensure trained adapter meets quality standards before deployment.

**Validation Test Suite:**
```python
@dataclass
class ValidationTestSuite:
    """Complete validation tests for a character"""
    
    # Test scenarios
    personality_tests: List[ValidationScenario]  # 5-7 scenarios
    tactical_tests: List[ValidationScenario]     # 5-7 scenarios
    edge_case_tests: List[ValidationScenario]    # 5-7 scenarios
    lore_tests: List[ValidationScenario]         # 3-5 scenarios
    engagement_tests: List[ValidationScenario]   # 3-5 scenarios
    
    # Thresholds
    personality_threshold: float = 0.80  # Consistency score
    tactical_threshold: float = 0.70     # Success rate
    lore_threshold: float = 0.90         # Accuracy
    engagement_threshold: float = 0.60   # Quality score
    
    # Regression detection
    max_degradation: float = 0.10        # Max 10% drop from baseline

@dataclass
class ValidationScenario:
    """Single validation test"""
    scenario_id: str
    category: str  # "personality", "tactical", etc.
    
    # Input
    context: Dict[str, Any]
    expected_behaviors: List[str]  # What should happen
    
    # Evaluation
    evaluator: callable  # Function to score response
    baseline_score: Optional[float] = None  # Previous version score
```

**Example Validation Scenarios:**

**Personality Consistency:**
```python
PERSONALITY_TESTS = [
    ValidationScenario(
        scenario_id="cautious_approach",
        category="personality",
        context={
            "situation": "Suspicious stranger approaching at night",
            "character_state": "on duty, alert",
            "player_behavior": "aggressive posturing"
        },
        expected_behaviors=[
            "Shows caution",
            "Calls for backup",
            "Doesn't act recklessly",
            "Maintains professional tone"
        ],
        evaluator=evaluate_cautious_response
    ),
    
    ValidationScenario(
        scenario_id="protocol_adherence",
        category="personality",
        context={
            "situation": "Player requests entry without proper credentials",
            "character_state": "on duty, calm",
            "player_behavior": "attempting persuasion"
        },
        expected_behaviors=[
            "Follows protocol",
            "Asks for credentials",
            "Doesn't bend rules easily",
            "Professional but firm"
        ],
        evaluator=evaluate_protocol_response
    ),
    
    # ... 5-7 total personality tests
]
```

**Validation Execution:**
```python
async def validate_adapter(
    character_id: str,
    adapter_path: str
) -> ValidationResults:
    """Run complete validation suite"""
    
    log_info(f"Validating adapter: {character_id} - {adapter_path}")
    
    # Load test suite
    test_suite = load_validation_suite(character_id)
    
    # Load baseline scores (from previous version)
    baseline = load_baseline_scores(character_id)
    
    # Load models
    new_model = load_model_with_adapter(adapter_path)
    base_model = load_base_model()  # For comparison
    
    results = ValidationResults(
        character_id=character_id,
        adapter_path=adapter_path,
        timestamp=time.time()
    )
    
    # Run personality tests
    log_info("Running personality consistency tests...")
    personality_scores = []
    for test in test_suite.personality_tests:
        score = await run_validation_test(test, new_model, character_id)
        personality_scores.append(score)
        results.personality_results.append({
            "test_id": test.scenario_id,
            "score": score,
            "baseline": test.baseline_score,
            "pass": score >= test_suite.personality_threshold
        })
    
    results.personality_consistency = np.mean(personality_scores)
    
    # Run tactical tests
    log_info("Running tactical intelligence tests...")
    tactical_scores = []
    for test in test_suite.tactical_tests:
        score = await run_validation_test(test, new_model, character_id)
        tactical_scores.append(score)
    
    results.tactical_intelligence = np.mean(tactical_scores)
    
    # Run edge case tests
    log_info("Running edge case handling tests...")
    edge_scores = []
    for test in test_suite.edge_case_tests:
        score = await run_validation_test(test, new_model, character_id)
        edge_scores.append(score)
    
    results.edge_case_handling = np.mean(edge_scores)
    
    # Run lore accuracy tests
    log_info("Running lore accuracy tests...")
    lore_scores = []
    for test in test_suite.lore_tests:
        score = await run_validation_test(test, new_model, character_id)
        lore_scores.append(score)
    
    results.lore_accuracy = np.mean(lore_scores)
    
    # Run engagement tests
    log_info("Running engagement quality tests...")
    engagement_scores = []
    for test in test_suite.engagement_tests:
        score = await run_validation_test(test, new_model, character_id)
        engagement_scores.append(score)
    
    results.engagement_quality = np.mean(engagement_scores)
    
    # Check uniqueness (compare to other characters)
    log_info("Checking character uniqueness...")
    uniqueness_score = await test_character_uniqueness(
        new_model, character_id, test_suite.personality_tests[:5]
    )
    results.uniqueness_score = uniqueness_score
    
    # Detect regressions
    results.has_regressions = check_for_regressions(results, baseline)
    
    # Overall pass/fail
    results.passes_all_thresholds = (
        results.personality_consistency >= test_suite.personality_threshold and
        results.tactical_intelligence >= test_suite.tactical_threshold and
        results.lore_accuracy >= test_suite.lore_threshold and
        results.engagement_quality >= test_suite.engagement_threshold and
        results.uniqueness_score >= 0.7 and
        not results.has_regressions
    )
    
    # Log results
    log_validation_results(results)
    
    # Save results
    save_validation_results(character_id, results)
    
    return results
```

**Personality Consistency Testing:**
```python
async def test_personality_consistency(
    model,
    character_id: str,
    test_scenarios: List[ValidationScenario],
    num_generations: int = 5
) -> float:
    """Test personality consistency through repeated generation"""
    
    consistency_scores = []
    
    for scenario in test_scenarios:
        # Generate response multiple times
        responses = []
        for _ in range(num_generations):
            response = await generate_response(model, character_id, scenario.context)
            responses.append(response)
        
        # Calculate pairwise similarity
        similarities = []
        for i in range(len(responses)):
            for j in range(i+1, len(responses)):
                sim = calculate_semantic_similarity(responses[i], responses[j])
                similarities.append(sim)
        
        # Average similarity = consistency
        scenario_consistency = np.mean(similarities)
        consistency_scores.append(scenario_consistency)
    
    # Overall consistency
    return np.mean(consistency_scores)
```

**Uniqueness Testing:**
```python
async def test_character_uniqueness(
    model,
    character_id: str,
    test_scenarios: List[ValidationScenario]
) -> float:
    """Test that character is distinct from others"""
    
    # Load other character models
    other_characters = get_all_other_characters(character_id)
    
    uniqueness_scores = []
    
    for scenario in test_scenarios:
        # Generate response from this character
        this_response = await generate_response(model, character_id, scenario.context)
        
        # Generate responses from other characters
        other_responses = []
        for other_char_id in other_characters[:5]:  # Sample 5 others
            other_model = load_character_model(other_char_id)
            other_response = await generate_response(other_model, other_char_id, scenario.context)
            other_responses.append(other_response)
        
        # Calculate dissimilarity from others
        dissimilarities = []
        for other_response in other_responses:
            dissim = 1.0 - calculate_semantic_similarity(this_response, other_response)
            dissimilarities.append(dissim)
        
        # High dissimilarity = good uniqueness
        scenario_uniqueness = np.mean(dissimilarities)
        uniqueness_scores.append(scenario_uniqueness)
    
    return np.mean(uniqueness_scores)
```

**Regression Detection:**
```python
def check_for_regressions(
    current_results: ValidationResults,
    baseline_results: ValidationResults
) -> bool:
    """Detect if new model is worse than baseline"""
    
    if not baseline_results:
        return False  # No baseline to compare against
    
    metrics = [
        ("personality_consistency", 0.10),
        ("tactical_intelligence", 0.10),
        ("lore_accuracy", 0.05),
        ("engagement_quality", 0.15),
        ("uniqueness_score", 0.10)
    ]
    
    regressions = []
    
    for metric_name, max_degradation in metrics:
        current = getattr(current_results, metric_name)
        baseline = getattr(baseline_results, metric_name)
        
        degradation = baseline - current
        
        if degradation > max_degradation:
            regressions.append({
                "metric": metric_name,
                "baseline": baseline,
                "current": current,
                "degradation": degradation
            })
    
    if regressions:
        log_warning(f"Regressions detected: {regressions}")
        return True
    
    return False
```

**Validation Output:**
```python
@dataclass
class ValidationResults:
    character_id: str
    adapter_path: str
    timestamp: float
    
    # Core metrics
    personality_consistency: float = 0.0
    tactical_intelligence: float = 0.0
    edge_case_handling: float = 0.0
    lore_accuracy: float = 0.0
    engagement_quality: float = 0.0
    uniqueness_score: float = 0.0
    
    # Detailed results
    personality_results: List[Dict] = field(default_factory=list)
    
    # Status
    passes_all_thresholds: bool = False
    has_regressions: bool = False
    
    def passes_all_thresholds(self) -> bool:
        return all([
            self.personality_consistency >= 0.80,
            self.tactical_intelligence >= 0.70,
            self.lore_accuracy >= 0.90,
            self.engagement_quality >= 0.60,
            self.uniqueness_score >= 0.70,
            not self.has_regressions
        ])
```

---

## (DOCUMENT CONTINUES... THIS IS PART 1 OF 2)

**Document Status:** Part 1 of architecture design complete. This covers components 1-8 of the pipeline.

**Next sections to design:**
- Component 9: Deployment Manager (A/B testing, rollback)
- Component 10: Monitoring Dashboard
- Component 11: Integration with existing systems
- File structure and data flow diagrams
- Error handling and recovery
- Development roadmap

Should I continue with Part 2?
