# 🎯 PHASE 7: LoRA TRAINING PIPELINE - COMPLETE IMPLEMENTATION ROADMAP

**Project Status:** Phases 1-6, 8 Complete (75%) → Building Phase 7 (Final 25%)  
**Target:** Full production LoRA training pipeline for self-improving characters  
**Hardware:** RTX 4050 (6GB VRAM) + Cloud APIs (DeepSeek, Claude, OpenAI)  
**Approach:** Local-first with smart API delegation

---

## 📋 PHASE 7 OVERVIEW

**Goal:** Characters learn and improve from gameplay through automated LoRA training

**Key Systems:**
1. **Training Data Collection** - Capture decisions during gameplay
2. **GPT-4 Reflection Pipeline** - Analyze and curate training data
3. **LoRA Training Engine** - Fine-tune character models
4. **Dream Cycle Orchestration** - Automated offline training
5. **Quality Control** - Validate improvements before deployment
6. **Constitutional AI** - Maintain character consistency

---

## 🗺️ IMPLEMENTATION PHASES

### **Phase 7.1: Data Collection Infrastructure** (Week 1)
Build systems to capture gameplay decisions for training

### **Phase 7.2: Reflection & Curation Pipeline** (Week 1-2)
Use GPT-4/Claude to analyze and label training data

### **Phase 7.3: LoRA Training Engine** (Week 2-3)
Build QLoRA training system optimized for RTX 4050

### **Phase 7.4: Dream Cycle Orchestration** (Week 3)
Automate the training loop (data → reflect → train → validate)

### **Phase 7.5: Quality Control & Safety** (Week 4)
Constitutional AI and rollback mechanisms

### **Phase 7.6: Integration & Testing** (Week 4)
Connect to existing systems and validate end-to-end

---

## 📦 PHASE 7.1: DATA COLLECTION INFRASTRUCTURE

### **Task 7.1.1: Decision Logger**
**Priority:** 🔴 CRITICAL  
**Time:** 2-3 days

**Subtasks:**
- [ ] Create `training_data_collector.py`
- [ ] Hook into escalation engine to capture:
  - Bot decisions (with confidence scores)
  - Brain decisions (with prompts and responses)
  - Human overrides (learning from corrections)
  - Context (game state, perception, recent history)
  - Outcomes (success/failure, rewards, consequences)
- [ ] Design data schema:
  ```python
  {
    "decision_id": "uuid",
    "character_id": "thorin",
    "timestamp": "2025-10-22T14:30:00Z",
    "situation_context": {
      "game_state": {...},
      "recent_events": [...],
      "character_state": {...}
    },
    "decision_made": {
      "action": "attack",
      "reasoning": "...",
      "confidence": 0.85,
      "source": "bot" | "brain" | "human"
    },
    "outcome": {
      "immediate": "hit for 15 damage",
      "delayed": "enemy retreated",
      "success": true,
      "rewards": {...}
    }
  }
  ```
- [ ] Implement SQLite storage with efficient querying
- [ ] Add privacy controls (opt-in/opt-out per character)
- [ ] Create data export utilities

**Deliverables:**
- `training_data_collector.py` (400-600 lines)
- SQLite schema migration
- Integration with escalation_engine.py

---

### **Task 7.1.2: Outcome Tracker**
**Priority:** 🔴 CRITICAL  
**Time:** 1-2 days

**Subtasks:**
- [ ] Track short-term outcomes (immediate action results)
- [ ] Track long-term outcomes (consequences over multiple turns)
- [ ] Implement reward signal calculation:
  - Combat: damage dealt, damage taken, positioning
  - Social: relationship changes, information gained
  - Exploration: discoveries, progress toward goals
- [ ] Create outcome labeling system (success/failure/neutral)
- [ ] Build temporal correlation (decision → outcome delay)

**Deliverables:**
- `outcome_tracker.py` (300-400 lines)
- Reward calculation functions
- Integration with game_mechanics.py

---

### **Task 7.1.3: Session Management**
**Priority:** 🟡 HIGH  
**Time:** 1 day

**Subtasks:**
- [ ] Create session start/end hooks
- [ ] Aggregate decisions per session
- [ ] Generate session summaries
- [ ] Track character evolution metrics
- [ ] Implement data cleanup (old/irrelevant data)

**Deliverables:**
- `session_manager.py` (200-300 lines)
- Session summary generator

---

## 📦 PHASE 7.2: REFLECTION & CURATION PIPELINE

### **Task 7.2.1: GPT-4 Reflection System**
**Priority:** 🔴 CRITICAL  
**Time:** 3-4 days

**Subtasks:**
- [ ] Create `reflection_pipeline.py`
- [ ] Design reflection prompts:
  ```
  Analyze this character decision:
  - Was it consistent with personality?
  - Was it tactically sound?
  - Would a better option exist?
  - What can be learned from outcome?
  ```
- [ ] Build API integration with cost tracking:
  - Primary: DeepSeek (cheapest for bulk analysis)
  - Fallback: Claude Sonnet (quality for ambiguous cases)
  - Premium: Claude Opus (for critical personality decisions)
- [ ] Implement batching (analyze multiple decisions in one call)
- [ ] Create quality labels:
  - ✅ Good Example (reinforce this behavior)
  - ⚠️ Acceptable (neutral, don't train on)
  - ❌ Bad Example (learn to avoid)
  - 🎯 Teaching Moment (train on improved version)
- [ ] Generate improved alternatives for bad decisions
- [ ] Track API costs and optimize batch sizes

**Cost Optimization:**
- DeepSeek: ~$0.001 per decision analysis (1k decisions = $1)
- Claude Sonnet: ~$0.01 per complex analysis
- Target: <$5 per 10-hour session analysis

**Deliverables:**
- `reflection_pipeline.py` (600-800 lines)
- Reflection prompt templates
- Cost tracking dashboard

---

### **Task 7.2.2: Training Data Curation**
**Priority:** 🔴 CRITICAL  
**Time:** 2-3 days

**Subtasks:**
- [ ] Filter decisions based on reflection quality
- [ ] Balance training set:
  - 70% good examples (reinforce correct behavior)
  - 20% teaching moments (learn improvements)
  - 10% edge cases (handle unusual situations)
- [ ] Deduplicate similar decisions
- [ ] Create constitutional AI constraints:
  - Personality consistency rules
  - Safety boundaries (no toxic behavior)
  - Role-playing boundaries (stay in character)
- [ ] Generate training prompts from curated data:
  ```
  Given situation X, character should do Y because Z
  ```
- [ ] Build prompt template system for each character

**Deliverables:**
- `data_curator.py` (500-700 lines)
- Constitutional AI rule engine
- Training prompt generator

---

### **Task 7.2.3: Character Analysis Dashboard**
**Priority:** 🟢 MEDIUM  
**Time:** 1-2 days

**Subtasks:**
- [ ] Build analysis dashboard showing:
  - Decision quality trends
  - Personality consistency scores
  - Areas needing improvement
  - Training data statistics
- [ ] Generate training recommendations
- [ ] Create character evolution timeline
- [ ] Visualize learning progress

**Deliverables:**
- `character_dashboard.py` (300-400 lines)
- Dashboard HTML templates

---

## 📦 PHASE 7.3: LoRA TRAINING ENGINE

### **Task 7.3.1: QLoRA Training Infrastructure**
**Priority:** 🔴 CRITICAL  
**Time:** 4-5 days

**Subtasks:**
- [ ] Create `lora_trainer.py` with RTX 4050 optimization
- [ ] Implement QLoRA (4-bit quantization):
  ```python
  from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
  from transformers import BitsAndBytesConfig
  
  # 4-bit config for 6GB VRAM
  bnb_config = BitsAndBytesConfig(
      load_in_4bit=True,
      bnb_4bit_quant_type="nf4",
      bnb_4bit_compute_dtype=torch.bfloat16,
      bnb_4bit_use_double_quant=True  # Nested quantization
  )
  
  # LoRA config for small models (1-3B)
  lora_config = LoraConfig(
      r=16,  # Rank (balance: quality vs memory)
      lora_alpha=32,
      target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
      lora_dropout=0.05,
      bias="none",
      task_type="CAUSAL_LM"
  )
  ```
- [ ] Configure model-specific settings:
  - **Qwen-1.5-1.8B**: r=16, α=32, batch_size=4
  - **Phi-3-mini-4k**: r=16, α=32, batch_size=2
  - **Llama-3-3B**: r=8, α=16, batch_size=1
- [ ] Implement gradient checkpointing (save VRAM)
- [ ] Build training data loader:
  - Load curated decisions
  - Format as instruction-following pairs
  - Apply chat template for each model
- [ ] Set up training loop with monitoring:
  - Loss tracking
  - Perplexity metrics
  - Gradient norms
  - VRAM usage monitoring
- [ ] Implement checkpoint saving (every 50 steps)
- [ ] Create early stopping (prevent overfitting)

**VRAM Budget (RTX 4050 - 6GB):**
- Base model (4-bit): ~2-3GB
- LoRA adapters: ~200-500MB
- Optimizer states: ~1-2GB
- Gradients + activations: ~1GB
- Safety margin: ~500MB
- **Total: ~5.5GB** (safe for 6GB card)

**Deliverables:**
- `lora_trainer.py` (800-1000 lines)
- Model-specific training configs
- VRAM monitoring utilities

---

### **Task 7.3.2: Hyperparameter Optimization**
**Priority:** 🟡 HIGH  
**Time:** 2-3 days

**Subtasks:**
- [ ] Research optimal hyperparameters for personality learning:
  ```python
  training_args = {
      "learning_rate": 2e-4,  # Lower for stability
      "num_epochs": 3,  # Few epochs to prevent overfitting
      "warmup_steps": 100,
      "weight_decay": 0.01,
      "max_grad_norm": 1.0,
      "gradient_accumulation_steps": 4,  # Effective batch size = 16
      "fp16": False,  # Use bfloat16 instead
      "bf16": True,
      "logging_steps": 10,
      "save_steps": 50,
      "eval_steps": 50
  }
  ```
- [ ] Build hyperparameter search utility
- [ ] Test different configurations on sample data
- [ ] Document best practices per model size
- [ ] Create auto-tuning system based on VRAM availability

**Deliverables:**
- `hyperparameter_optimizer.py` (400-500 lines)
- Best practices guide
- Auto-tuning functions

---

### **Task 7.3.3: Training Pipeline Automation**
**Priority:** 🟡 HIGH  
**Time:** 2 days

**Subtasks:**
- [ ] Build end-to-end training orchestration
- [ ] Implement multi-stage training:
  1. **Stage 1:** Quick adaptation (100 examples, 30 min)
  2. **Stage 2:** Deep learning (500 examples, 2 hours)
  3. **Stage 3:** Fine-tuning (1000+ examples, 4 hours)
- [ ] Create training job queue (train multiple characters)
- [ ] Implement resource scheduling (one training job at a time)
- [ ] Add progress notifications
- [ ] Build resume-from-checkpoint functionality

**Deliverables:**
- `training_orchestrator.py` (500-600 lines)
- Job queue system
- Progress tracking

---

## 📦 PHASE 7.4: DREAM CYCLE ORCHESTRATION

### **Task 7.4.1: Dream Cycle State Machine**
**Priority:** 🔴 CRITICAL  
**Time:** 2-3 days

**Subtasks:**
- [ ] Create `dream_cycle_manager.py`
- [ ] Implement state machine:
  ```
  IDLE → DATA_COLLECTION → REFLECTION → 
  CURATION → TRAINING → VALIDATION → 
  DEPLOYMENT → IDLE
  ```
- [ ] Build cycle triggers:
  - Manual trigger (DM initiates)
  - Scheduled trigger (nightly at 2 AM)
  - Threshold trigger (100+ new decisions)
- [ ] Implement "snack break" mode:
  - Pause gameplay during intensive operations
  - Show progress to players
  - Estimate completion time
- [ ] Create cycle history logging
- [ ] Add cycle analytics (success rate, time taken, improvements)

**Deliverables:**
- `dream_cycle_manager.py` (600-800 lines)
- State machine implementation
- Trigger system

---

### **Task 7.4.2: Intermission UI**
**Priority:** 🟢 MEDIUM  
**Time:** 1-2 days

**Subtasks:**
- [ ] Build intermission screen showing:
  - Current cycle phase
  - Progress bars
  - Estimated time remaining
  - Character improvement preview
- [ ] Add "skip training" option (use current model)
- [ ] Show interesting stats during wait:
  - "Thorin is reflecting on 47 decisions..."
  - "Training on social interactions..."
  - "Learning from 3 critical moments..."
- [ ] Create entertaining wait messages

**Deliverables:**
- `intermission_ui.py` (200-300 lines)
- UI templates

---

### **Task 7.4.3: Parallel Processing**
**Priority:** 🟡 HIGH  
**Time:** 2 days

**Subtasks:**
- [ ] Implement asynchronous operations:
  - Reflection can use cloud APIs in parallel
  - Training uses GPU (sequential per character)
  - Validation can run concurrently
- [ ] Build job scheduler for multi-character training
- [ ] Optimize cloud API batching (analyze 10 decisions at once)
- [ ] Implement priority queue (important characters train first)

**Deliverables:**
- Async workflow implementation
- Job scheduler
- Optimization utilities

---

## 📦 PHASE 7.5: QUALITY CONTROL & SAFETY

### **Task 7.5.1: Validation System**
**Priority:** 🔴 CRITICAL  
**Time:** 3-4 days

**Subtasks:**
- [ ] Create `model_validator.py`
- [ ] Build test scenarios for each character:
  - Personality consistency tests
  - Edge case handling
  - Safety boundary checks
- [ ] Implement quantitative metrics:
  - **Personality Consistency Score:** Compare responses to original character
  - **Quality Score:** Evaluate decision coherence
  - **Safety Score:** Check for boundary violations
- [ ] Use Claude Opus as judge:
  ```
  Rate this character's response (0-100):
  - Personality consistency: Does it match Thorin's profile?
  - Decision quality: Is it tactically/socially sound?
  - Safety: Does it respect boundaries?
  ```
- [ ] Set validation thresholds:
  - Consistency: Must be ≥85 to deploy
  - Quality: Must be ≥80 to deploy
  - Safety: Must be 100 (no violations)
- [ ] Implement A/B testing (old vs new model)

**Deliverables:**
- `model_validator.py` (600-800 lines)
- Test scenario library
- Validation metrics

---

### **Task 7.5.2: Constitutional AI Integration**
**Priority:** 🔴 CRITICAL  
**Time:** 2-3 days

**Subtasks:**
- [ ] Define character constitutions:
  ```yaml
  character: Thorin
  core_traits:
    - "Loyal to friends and clan"
    - "Distrusts elves"
    - "Values honor in combat"
  boundaries:
    - "Never betrays friends"
    - "Won't use poison (dishonorable)"
    - "Protects innocent civilians"
  personality_rules:
    - "Gruff exterior, warm interior"
    - "Speaks plainly, avoids flowery language"
    - "Quick to anger when honor questioned"
  ```
- [ ] Implement constitutional checks during training:
  - Filter training data that violates constitution
  - Add reinforcement for constitutional adherence
  - Penalize boundary violations
- [ ] Build constitution drift detection:
  - Track personality metrics over time
  - Alert if character deviates from core traits
  - Auto-rollback if drift exceeds thresholds

**Deliverables:**
- `constitutional_ai.py` (500-700 lines)
- Character constitution templates
- Drift detection system

---

### **Task 7.5.3: Rollback Mechanism**
**Priority:** 🔴 CRITICAL  
**Time:** 1-2 days

**Subtasks:**
- [ ] Implement model versioning:
  - Save each LoRA adapter with metadata
  - Track performance metrics per version
  - Maintain history of changes
- [ ] Create rollback system:
  - Automatic rollback if validation fails
  - Manual rollback option for DM
  - Rollback to any previous version
- [ ] Build version comparison tool
- [ ] Add rollback audit log

**Deliverables:**
- `model_versioning.py` (300-400 lines)
- Rollback utilities
- Version comparison dashboard

---

## 📦 PHASE 7.6: INTEGRATION & TESTING

### **Task 7.6.1: System Integration**
**Priority:** 🔴 CRITICAL  
**Time:** 2-3 days

**Subtasks:**
- [ ] Connect dream cycle to existing systems:
  - Hook into escalation_engine for data collection
  - Integrate with local_llm_engine for model loading
  - Connect to chat_system for status updates
- [ ] Update character_brain.py to use LoRA adapters:
  ```python
  # Load base model + LoRA adapter
  model = load_base_model("Qwen-1.5-1.8B")
  if lora_adapter_exists(character_id):
      model = load_lora_adapter(model, character_id)
  ```
- [ ] Add dream cycle commands to DM interface:
  - `/dream start` - Begin dream cycle
  - `/dream status` - Check progress
  - `/dream history` - View past cycles
  - `/dream rollback <version>` - Revert character
- [ ] Create configuration file for dream cycle settings
- [ ] Add telemetry and monitoring

**Deliverables:**
- Integration code across multiple files
- DM command extensions
- Configuration system

---

### **Task 7.6.2: End-to-End Testing**
**Priority:** 🟡 HIGH  
**Time:** 3-4 days

**Subtasks:**
- [ ] Create test suite for Phase 7:
  - Data collection tests
  - Reflection pipeline tests
  - Training engine tests
  - Validation system tests
- [ ] Run complete dream cycle with test characters:
  1. Generate 100 synthetic decisions
  2. Run reflection analysis
  3. Train LoRA adapter
  4. Validate improvements
  5. Deploy and test in gameplay
- [ ] Perform stress testing:
  - Multiple characters training simultaneously
  - Large training datasets (1000+ examples)
  - VRAM limits and recovery
- [ ] Test failure scenarios:
  - Validation failures
  - API timeouts
  - GPU out of memory
  - Corrupted training data
- [ ] Measure performance:
  - Dream cycle duration
  - API costs per cycle
  - Character improvement metrics

**Deliverables:**
- Comprehensive test suite
- Test scenarios and data
- Performance benchmarks

---

### **Task 7.6.3: Documentation & Examples**
**Priority:** 🟡 HIGH  
**Time:** 2 days

**Subtasks:**
- [ ] Write comprehensive Phase 7 documentation:
  - Architecture overview
  - API reference
  - Configuration guide
  - Troubleshooting guide
- [ ] Create tutorial: "Your First Dream Cycle"
- [ ] Build example scenarios showing improvements
- [ ] Document best practices for:
  - Data collection strategies
  - Training schedules
  - Hyperparameter tuning
  - Quality control
- [ ] Add inline code comments

**Deliverables:**
- `PHASE_7_GUIDE.md` (5000+ words)
- Tutorial examples
- API documentation

---

## 🎯 DEVELOPMENT SEQUENCE (4 WEEKS)

### **Week 1: Data Foundation**
**Days 1-2:** Task 7.1.1 - Decision Logger  
**Days 3-4:** Task 7.1.2 - Outcome Tracker  
**Day 5:** Task 7.1.3 - Session Management  
**Day 6-7:** Task 7.2.1 - GPT-4 Reflection System (start)

**Milestone:** Can collect and analyze gameplay decisions

---

### **Week 2: Reflection & Training Prep**
**Days 8-10:** Task 7.2.1 - GPT-4 Reflection System (finish)  
**Days 11-12:** Task 7.2.2 - Training Data Curation  
**Day 13:** Task 7.2.3 - Character Dashboard  
**Day 14:** Task 7.3.1 - QLoRA Infrastructure (start)

**Milestone:** Can curate high-quality training data

---

### **Week 3: Training Engine & Dream Cycle**
**Days 15-18:** Task 7.3.1 - QLoRA Training Engine (finish)  
**Days 19-20:** Task 7.3.2 - Hyperparameter Optimization  
**Day 21:** Task 7.3.3 - Training Automation

**Milestone:** Can train LoRA adapters on RTX 4050

---

### **Week 4: Quality & Integration**
**Days 22-24:** Task 7.4.1 - Dream Cycle State Machine  
**Day 25:** Task 7.4.2 - Intermission UI  
**Days 26-28:** Task 7.5.1 - Validation System  
**Days 29-30:** Task 7.5.2 - Constitutional AI  
**Day 31:** Task 7.5.3 - Rollback Mechanism  
**Days 32-35:** Task 7.6.1-7.6.3 - Integration & Testing

**Milestone:** Full production pipeline operational

---

## 📊 RESOURCE PLANNING

### **Hardware Usage:**
- **Data Collection:** Minimal (logging only)
- **Reflection:** Cloud APIs (DeepSeek/Claude)
- **Training:** RTX 4050 at 90% utilization
- **Validation:** Claude Opus API
- **Deployment:** Minimal (load LoRA adapters)

### **Cloud API Costs (per 10-hour session):**
- **Data Collection:** Free (local)
- **Reflection:** $1-3 (DeepSeek bulk analysis)
- **Curation:** $2-5 (Claude for complex cases)
- **Validation:** $5-10 (Claude Opus quality checks)
- **Total:** $8-18 per character per session cycle

### **Training Time (RTX 4050):**
- **Quick Adaptation:** 20-30 minutes (100 examples)
- **Standard Training:** 1-2 hours (500 examples)
- **Deep Training:** 3-4 hours (1000+ examples)

### **Dream Cycle Total Time:**
1. Data Collection: Real-time during gameplay
2. Reflection: 10-20 minutes (API calls)
3. Curation: 5-10 minutes (filtering)
4. Training: 30 minutes - 4 hours (varies)
5. Validation: 10-15 minutes (API calls)
6. **Total: 1-5 hours** (can run overnight)

---

## 🔧 CONFIGURATION SYSTEM

### **Config File: `dream_cycle_config.yaml`**

```yaml
# Dream Cycle Configuration
dream_cycle:
  enabled: true
  trigger_mode: "threshold"  # manual | scheduled | threshold
  schedule: "02:00"  # 2 AM daily
  decision_threshold: 100  # Trigger after N decisions
  
# Data Collection
data_collection:
  enabled: true
  collect_bot_decisions: true
  collect_brain_decisions: true
  collect_human_overrides: true
  max_storage_days: 30
  
# Reflection Pipeline
reflection:
  primary_api: "deepseek"  # deepseek | claude | openai
  fallback_api: "claude"
  batch_size: 10  # Decisions per API call
  max_cost_per_session: 5.00  # USD
  
# LoRA Training
lora_training:
  model_tiers:
    nano:
      rank: 16
      alpha: 32
      batch_size: 4
      learning_rate: 2e-4
    micro:
      rank: 16
      alpha: 32
      batch_size: 2
      learning_rate: 2e-4
    small:
      rank: 8
      alpha: 16
      batch_size: 1
      learning_rate: 1e-4
  max_epochs: 3
  early_stopping: true
  checkpoint_steps: 50
  
# Validation
validation:
  personality_consistency_threshold: 85
  quality_threshold: 80
  safety_threshold: 100
  use_claude_opus: true
  test_scenarios_per_character: 10
  
# Constitutional AI
constitutional_ai:
  enabled: true
  strict_mode: true  # No training data that violates constitution
  drift_detection: true
  auto_rollback_on_drift: true
  max_drift_percentage: 10
  
# Rollback
rollback:
  keep_versions: 10
  auto_rollback_on_validation_failure: true
  require_dm_approval: false
```

---

## 🎓 LEARNING MILESTONES

### **Proof of Concept (Week 1-2):**
✅ Collect 100 decisions from gameplay  
✅ Analyze with GPT-4 reflection  
✅ Manually curate training data  
✅ Successfully train first LoRA adapter  
✅ Validate character improvement  

### **Alpha (Week 3):**
✅ Automated data collection  
✅ Reflection pipeline operational  
✅ Training on RTX 4050 working  
✅ Basic validation system  

### **Beta (Week 4):**
✅ Full dream cycle automation  
✅ Constitutional AI enforcement  
✅ Rollback system functional  
✅ Complete integration with game systems  

### **Production (Post Week 4):**
✅ All tests passing  
✅ Documentation complete  
✅ Performance optimized  
✅ Ready for real gameplay  

---

## ⚠️ CRITICAL SUCCESS FACTORS

1. **VRAM Management:** Must stay under 5.5GB during training
2. **Cost Control:** Keep API costs under $20 per character per cycle
3. **Quality First:** Never deploy model that fails validation
4. **Character Consistency:** Constitutional AI must prevent drift
5. **Fast Iteration:** Dream cycles should complete overnight
6. **Graceful Failure:** Rollback automatically if anything goes wrong

---

## 🎊 COMPLETION CRITERIA

Phase 7 is complete when:
- [ ] Characters automatically improve from gameplay
- [ ] Dream cycle runs fully automated
- [ ] Training works reliably on RTX 4050
- [ ] Quality control prevents bad models
- [ ] API costs are reasonable (<$20/character/cycle)
- [ ] DM can trigger/monitor/rollback easily
- [ ] All systems integrated and tested
- [ ] Documentation is comprehensive

---

## 📁 FILE STRUCTURE

```
ai_society_dnd/backend/
├── training_data_collector.py      # 7.1.1 - Decision logging
├── outcome_tracker.py               # 7.1.2 - Outcome tracking
├── session_manager.py               # 7.1.3 - Session management
├── reflection_pipeline.py           # 7.2.1 - GPT-4 analysis
├── data_curator.py                  # 7.2.2 - Data curation
├── character_dashboard.py           # 7.2.3 - Analytics
├── lora_trainer.py                  # 7.3.1 - Training engine
├── hyperparameter_optimizer.py      # 7.3.2 - Hyperparameter tuning
├── training_orchestrator.py         # 7.3.3 - Training automation
├── dream_cycle_manager.py           # 7.4.1 - State machine
├── intermission_ui.py               # 7.4.2 - UI during training
├── model_validator.py               # 7.5.1 - Quality validation
├── constitutional_ai.py             # 7.5.2 - Constitution enforcement
├── model_versioning.py              # 7.5.3 - Version control & rollback
└── configs/
    └── dream_cycle_config.yaml      # Configuration
```

**Estimated Total:** 8,000-10,000 lines of new code

---

## 🚀 READY TO START?

**First Step:** Task 7.1.1 - Build the decision logger to start capturing gameplay data.

We'll build this incrementally, testing each component before moving to the next. The beauty of this design is that each piece adds value independently - even basic data collection is useful before training exists.

**Let's build Phase 7 properly!** 🎲✨
