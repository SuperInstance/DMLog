# 🎴 TASK 7.1.1 QUICK REFERENCE

**Training Data Collector - Essential Commands**

---

## 📦 IMPORT

```python
from training_data_collector import TrainingDataCollector
from escalation_engine import EscalationEngine
```

---

## 🚀 BASIC USAGE

### **Automatic Logging (Recommended)**

```python
# Create engine (training data enabled by default)
escalation = EscalationEngine()

# Start session
escalation.training_data_collector.start_session()

# Make decisions (logged automatically!)
# ... gameplay happens ...

# End session
escalation.training_data_collector.end_session()
```

### **Manual Logging (Advanced)**

```python
collector = TrainingDataCollector()

# Log decision
decision_id = collector.log_decision(
    character_id="thorin",
    situation_context={"game_state": {...}},
    decision={"action": "attack", "source": "bot"}
)

# Update outcome
collector.update_outcome(
    decision_id=decision_id,
    outcome={"result": "success"},
    success=True
)
```

---

## 🔍 QUERYING DATA

### **Get Decisions**

```python
# All decisions for character
decisions = collector.get_decisions_for_character("thorin")

# Training-eligible only
training_data = collector.get_training_eligible_decisions("thorin")

# Filter by quality
good_decisions = collector.get_training_eligible_decisions(
    "thorin",
    min_quality="good"
)

# Limit results
recent = collector.get_decisions_for_character("thorin", limit=10)
```

### **Get Statistics**

```python
# Character stats
stats = collector.get_statistics(character_id="thorin")

# Print summary
print(f"Total: {stats['total_decisions']}")
print(f"Success rate: {stats['success_rate']:.1%}")
print(f"Bot: {stats['by_source'].get('bot', 0)}")
print(f"Brain: {stats['by_source'].get('brain', 0)}")
```

### **Session Summary**

```python
summary = collector.get_session_summary(session_id)
print(summary)
```

---

## 🔐 PRIVACY CONTROLS

### **Get Settings**

```python
settings = collector.get_character_settings("thorin")
```

### **Update Settings**

```python
settings.collect_bot_decisions = False  # Don't log bot decisions
settings.retention_days = 60           # Keep for 60 days
settings.training_eligible = True       # Can be used for training

collector.update_character_settings(settings)
```

---

## 💾 DATA MANAGEMENT

### **Export to JSON**

```python
collector.export_to_json(
    character_id="thorin",
    output_path="thorin_data.json",
    include_all=False  # Only training-eligible
)
```

### **Clean Old Data**

```python
# Clean based on retention policy
deleted = collector.cleanup_old_data(character_id="thorin")
print(f"Deleted {deleted} old decisions")
```

---

## 🏷️ QUALITY LABELING

```python
# Update quality (from reflection pipeline)
collector.update_quality_label(
    decision_id="dec_123",
    quality_label="good",  # 'good', 'acceptable', 'bad', 'teaching_moment'
    reflection_notes="Excellent tactical choice"
)
```

---

## 🧪 TESTING

### **Run All Tests**

```bash
# Unit tests
python test_training_data_collector.py

# Integration tests
python test_integration_training_data.py

# Quick test script
python test_task_7_1_1.py
```

---

## 📊 DATABASE

**Location:** `data/decisions.db`  
**Type:** SQLite3  
**Tables:**
- `decisions` - All decision records
- `sessions` - Gameplay sessions
- `character_settings` - Privacy settings

**Direct Access:**

```bash
sqlite3 data/decisions.db

# Query examples
SELECT COUNT(*) FROM decisions WHERE character_id = 'thorin';
SELECT * FROM decisions WHERE success = 1 LIMIT 10;
SELECT quality_label, COUNT(*) FROM decisions GROUP BY quality_label;
```

---

## 🎯 COMMON PATTERNS

### **Full Gameplay Session**

```python
from escalation_engine import EscalationEngine

# Setup
escalation = EscalationEngine()
session_id = escalation.training_data_collector.start_session(
    session_notes="Evening session"
)

# Play game...
# (decisions logged automatically)

# Cleanup
escalation.training_data_collector.end_session()

# Review
stats = escalation.training_data_collector.get_statistics()
print(f"Session: {stats['total_decisions']} decisions")
```

### **Export for Analysis**

```python
collector = TrainingDataCollector()

# Export each character
for char_id in ["thorin", "elara", "gandor"]:
    collector.export_to_json(
        character_id=char_id,
        output_path=f"{char_id}_training.json"
    )

print("✓ Exported all training data")
```

### **Check Data Quality**

```python
stats = collector.get_statistics(character_id="thorin")

total = stats['total_decisions']
eligible = stats['training_eligible']
successes = stats['successes']
failures = stats['failures']

print(f"Data Quality for Thorin:")
print(f"  Total decisions: {total}")
print(f"  Training eligible: {eligible} ({eligible/total:.0%})")
print(f"  Success rate: {successes/(successes+failures):.1%}")
print(f"  Quality labels: {stats['by_quality']}")
```

---

## ⚙️ CONFIGURATION

### **Disable Training Data**

```python
# Disable globally
escalation = EscalationEngine(enable_training_data=False)

# Or per character
settings = collector.get_character_settings("thorin")
settings.enabled = False
collector.update_character_settings(settings)
```

### **Custom Database Location**

```python
collector = TrainingDataCollector(db_path="/custom/path/decisions.db")
```

---

## 🐛 TROUBLESHOOTING

**Database locked:**
```python
# Close all connections
collector = None  # Let GC clean up
```

**Import error:**
```python
# Make sure files are in same directory
import sys
sys.path.append('/path/to/backend')
```

**Tests failing:**
```bash
# Check Python version
python --version  # Should be 3.10+

# Verify files
ls -la *.py
```

---

## 📚 API SUMMARY

| Function | Purpose | Returns |
|----------|---------|---------|
| `log_decision()` | Log a decision | decision_id or None |
| `update_outcome()` | Add outcome to decision | None |
| `update_quality_label()` | Set quality label | None |
| `get_decisions_for_character()` | Query decisions | List[Dict] |
| `get_training_eligible_decisions()` | Get training data | List[Dict] |
| `get_statistics()` | Get stats | Dict |
| `export_to_json()` | Export data | None |
| `cleanup_old_data()` | Delete old data | int (deleted count) |
| `start_session()` | Begin session | session_id |
| `end_session()` | End session | None |

---

## 🔢 METRICS

**Performance:**
- Decision logging: <1ms
- Outcome update: <1ms
- Query (100 decisions): <100ms
- Database size: ~1KB per decision

**Storage:**
- ~10-20MB per 100 hours gameplay
- Auto-cleanup based on retention policy

---

**Quick Reference v1.0**  
*Task 7.1.1 - Decision Logger*  
*October 22, 2025*
