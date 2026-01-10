# Phase 7: Learning Pipeline - Architecture Design (Part 2)

**Continued from Part 1...**

---

## Component Specifications (Continued)

### 9. Deployment Manager

**Purpose:** Safely roll out new adapters with A/B testing and automatic rollback.

**Deployment Strategies:**

**Strategy 1: Canary Deployment (Recommended)**
```python
class CanaryDeployment:
    """Gradual traffic shifting with monitoring"""
    
    def __init__(self, character_id: str, new_adapter_path: str):
        self.character_id = character_id
        self.new_adapter_path = new_adapter_path
        self.old_adapter_path = get_current_adapter(character_id)
        
        # Traffic percentages
        self.stages = [
            {"name": "canary", "new_traffic": 0.10, "duration_hours": 24},
            {"name": "half", "new_traffic": 0.50, "duration_hours": 24},
            {"name": "full", "new_traffic": 1.00, "duration_hours": 48}
        ]
        
        self.current_stage = 0
        self.metrics_history = []
    
    async def deploy(self):
        """Execute canary deployment"""
        
        for stage in self.stages:
            log_info(f"Deploying {self.character_id} to stage: {stage['name']}")
            log_info(f"  New adapter traffic: {stage['new_traffic']*100}%")
            
            # Update traffic routing
            self.set_traffic_split(
                new_traffic=stage['new_traffic'],
                old_traffic=1.0 - stage['new_traffic']
            )
            
            # Monitor for duration
            start_time = time.time()
            duration_seconds = stage['duration_hours'] * 3600
            
            while time.time() - start_time < duration_seconds:
                # Collect metrics every 5 minutes
                await asyncio.sleep(300)
                
                metrics = await self.collect_comparative_metrics()
                self.metrics_history.append(metrics)
                
                # Check for issues
                if self.should_rollback(metrics):
                    log_error(f"Rollback triggered at stage {stage['name']}")
                    await self.rollback()
                    return False
            
            # Stage completed successfully
            log_info(f"Stage {stage['name']} completed successfully")
            self.current_stage += 1
        
        # Deployment complete
        log_info(f"Deployment complete for {self.character_id}")
        self.finalize_deployment()
        return True
    
    def set_traffic_split(self, new_traffic: float, old_traffic: float):
        """Update traffic routing configuration"""
        
        traffic_config = {
            self.character_id: {
                "adapters": [
                    {"path": self.new_adapter_path, "weight": new_traffic},
                    {"path": self.old_adapter_path, "weight": old_traffic}
                ],
                "strategy": "weighted_random"
            }
        }
        
        # Update multi-LoRA manager
        multi_lora_manager.update_traffic_config(traffic_config)
    
    async def collect_comparative_metrics(self) -> Dict:
        """Compare new vs old adapter metrics"""
        
        # Query metrics database for both adapters
        new_metrics = await get_adapter_metrics(
            self.character_id,
            self.new_adapter_path,
            last_n_minutes=60
        )
        
        old_metrics = await get_adapter_metrics(
            self.character_id,
            self.old_adapter_path,
            last_n_minutes=60
        )
        
        comparison = {
            "timestamp": time.time(),
            "new": {
                "requests": new_metrics.request_count,
                "avg_latency": new_metrics.avg_latency_ms,
                "error_rate": new_metrics.error_rate,
                "engagement_score": new_metrics.avg_engagement,
                "consistency_score": new_metrics.avg_consistency,
            },
            "old": {
                "requests": old_metrics.request_count,
                "avg_latency": old_metrics.avg_latency_ms,
                "error_rate": old_metrics.error_rate,
                "engagement_score": old_metrics.avg_engagement,
                "consistency_score": old_metrics.avg_consistency,
            },
            "delta": {
                "latency": new_metrics.avg_latency_ms - old_metrics.avg_latency_ms,
                "error_rate": new_metrics.error_rate - old_metrics.error_rate,
                "engagement": new_metrics.avg_engagement - old_metrics.avg_engagement,
                "consistency": new_metrics.avg_consistency - old_metrics.avg_consistency,
            }
        }
        
        return comparison
    
    def should_rollback(self, metrics: Dict) -> bool:
        """Determine if deployment should be rolled back"""
        
        # Rollback triggers
        triggers = [
            # Error rate increased by more than 3%
            metrics['delta']['error_rate'] > 0.03,
            
            # Engagement dropped by more than 15%
            metrics['delta']['engagement'] < -0.15,
            
            # Consistency dropped by more than 10%
            metrics['delta']['consistency'] < -0.10,
            
            # Latency increased by more than 100ms
            metrics['delta']['latency'] > 100,
            
            # Absolute error rate above 5%
            metrics['new']['error_rate'] > 0.05,
        ]
        
        if any(triggers):
            log_warning(f"Rollback trigger activated: {metrics['delta']}")
            return True
        
        return False
    
    async def rollback(self):
        """Immediately revert to old adapter"""
        
        log_info(f"Rolling back {self.character_id} to previous version")
        
        # Set 100% traffic to old adapter
        self.set_traffic_split(new_traffic=0.0, old_traffic=1.0)
        
        # Mark new adapter as failed
        mark_adapter_failed(self.character_id, self.new_adapter_path)
        
        # Send alert
        send_alert(
            title=f"Rollback: {self.character_id}",
            message=f"New adapter rolled back due to metric degradation",
            severity="warning"
        )
    
    def finalize_deployment(self):
        """Complete deployment - make new adapter official"""
        
        # Update "latest" symlink
        update_latest_symlink(self.character_id, self.new_adapter_path)
        
        # Archive old adapter
        archive_old_adapter(self.character_id, self.old_adapter_path)
        
        # Update baseline metrics
        update_baseline_metrics(self.character_id, self.metrics_history[-1]['new'])
```

**Strategy 2: Blue-Green Deployment**
```python
class BlueGreenDeployment:
    """Full environment swap for major versions"""
    
    def __init__(self):
        self.blue_env = "production"  # Current
        self.green_env = "staging"    # New
    
    async def deploy(self, character_ids: List[str], new_adapters: Dict[str, str]):
        """Deploy multiple characters simultaneously"""
        
        # 1. Deploy to green environment
        log_info("Deploying to green environment")
        for char_id in character_ids:
            deploy_to_environment(
                environment=self.green_env,
                character_id=char_id,
                adapter_path=new_adapters[char_id]
            )
        
        # 2. Run smoke tests on green
        log_info("Running smoke tests on green")
        smoke_results = await run_smoke_tests(
            environment=self.green_env,
            character_ids=character_ids
        )
        
        if not smoke_results.all_passed():
            log_error("Smoke tests failed - aborting deployment")
            return False
        
        # 3. Switch traffic from blue to green
        log_info("Switching traffic: blue → green")
        switch_traffic(from_env=self.blue_env, to_env=self.green_env)
        
        # 4. Monitor for 2 hours
        log_info("Monitoring green environment")
        await asyncio.sleep(7200)
        
        issues = await check_for_issues(environment=self.green_env)
        
        if issues:
            # Quick rollback
            log_error("Issues detected - rolling back to blue")
            switch_traffic(from_env=self.green_env, to_env=self.blue_env)
            return False
        
        # 5. Success - green becomes new blue
        log_info("Deployment successful")
        promote_environment(from_env=self.green_env, to_env=self.blue_env)
        
        return True
```

**Traffic Router:**
```python
class TrafficRouter:
    """Routes character requests to appropriate adapters"""
    
    def __init__(self):
        self.routing_table = {}
        self.load_routing_config()
    
    def load_routing_config(self):
        """Load from config file or database"""
        with open("/config/traffic_routing.json") as f:
            self.routing_table = json.load(f)
    
    def route_request(self, character_id: str) -> str:
        """Determine which adapter to use"""
        
        if character_id not in self.routing_table:
            # Default to latest
            return get_latest_adapter(character_id)
        
        config = self.routing_table[character_id]
        
        if config['strategy'] == 'single':
            # Only one adapter
            return config['adapter_path']
        
        elif config['strategy'] == 'weighted_random':
            # Weighted random selection (for A/B testing)
            adapters = config['adapters']
            weights = [a['weight'] for a in adapters]
            selected = random.choices(adapters, weights=weights)[0]
            return selected['path']
        
        elif config['strategy'] == 'feature_flag':
            # Route based on feature flags
            if check_feature_flag(f"use_new_adapter_{character_id}"):
                return config['new_adapter_path']
            else:
                return config['old_adapter_path']
```

**Deployment API:**
```python
class DeploymentManager:
    """Main deployment manager"""
    
    async def deploy_adapter(
        self,
        character_id: str,
        adapter_path: str,
        strategy: str = "canary",
        auto_rollback: bool = True
    ):
        """Deploy adapter with specified strategy"""
        
        log_info(f"Starting deployment: {character_id}")
        log_info(f"  Strategy: {strategy}")
        log_info(f"  Adapter: {adapter_path}")
        
        if strategy == "canary":
            deployment = CanaryDeployment(character_id, adapter_path)
            success = await deployment.deploy()
            
        elif strategy == "blue_green":
            deployment = BlueGreenDeployment()
            success = await deployment.deploy([character_id], {character_id: adapter_path})
            
        elif strategy == "immediate":
            # Direct replacement (not recommended for production)
            success = self.immediate_deploy(character_id, adapter_path)
        
        if success:
            log_info(f"Deployment successful: {character_id}")
            record_deployment_success(character_id, adapter_path)
        else:
            log_error(f"Deployment failed: {character_id}")
            record_deployment_failure(character_id, adapter_path)
        
        return success
    
    def immediate_deploy(self, character_id: str, adapter_path: str) -> bool:
        """Immediate deployment (for development/testing)"""
        update_latest_symlink(character_id, adapter_path)
        multi_lora_manager.reload_character(character_id)
        return True
```

---

### 10. Monitoring Dashboard

**Purpose:** Real-time visibility into system health and character performance.

**Metrics Collection:**
```python
class MetricsCollector:
    """Collects and stores performance metrics"""
    
    def __init__(self):
        self.metrics_db = MetricsDatabase()
        self.buffer = []
        self.flush_interval = 60  # seconds
    
    def record_request(
        self,
        character_id: str,
        adapter_path: str,
        request_data: Dict,
        response_data: Dict,
        metadata: Dict
    ):
        """Record a single request/response"""
        
        metric = {
            "timestamp": time.time(),
            "character_id": character_id,
            "adapter_path": adapter_path,
            "adapter_version": extract_version(adapter_path),
            
            # Request metrics
            "request_length": len(request_data.get("context", "")),
            
            # Response metrics
            "response_length": len(response_data.get("text", "")),
            "latency_ms": metadata.get("latency_ms", 0),
            "confidence": response_data.get("confidence", 0),
            
            # Quality metrics (from other systems)
            "engagement_signal": metadata.get("engagement", 0.5),
            "consistency_score": metadata.get("consistency", 0.5),
            
            # Errors
            "error": metadata.get("error", None),
            "error_type": metadata.get("error_type", None),
        }
        
        self.buffer.append(metric)
        
        # Flush if buffer full
        if len(self.buffer) >= 100:
            self.flush()
    
    def flush(self):
        """Write buffered metrics to database"""
        if self.buffer:
            self.metrics_db.insert_batch(self.buffer)
            self.buffer = []
    
    async def run_periodic_flush(self):
        """Flush metrics every N seconds"""
        while True:
            await asyncio.sleep(self.flush_interval)
            self.flush()
```

**Dashboard Metrics:**
```python
@dataclass
class DashboardMetrics:
    """Real-time dashboard data"""
    
    # System-wide
    total_requests_per_second: float
    total_error_rate: float
    avg_latency_ms: float
    active_characters: int
    active_users: int
    
    # Per-character breakdowns
    character_metrics: Dict[str, CharacterMetrics]
    
    # Training pipeline
    dream_cycles_running: int
    dream_cycles_queued: int
    recent_deployments: List[DeploymentInfo]
    
    # Alerts
    active_alerts: List[Alert]
    
    # Trends (last 24h)
    requests_trend: List[Tuple[float, int]]  # (timestamp, count)
    error_rate_trend: List[Tuple[float, float]]
    engagement_trend: List[Tuple[float, float]]

@dataclass
class CharacterMetrics:
    """Metrics for a single character"""
    character_id: str
    character_name: str
    
    # Usage
    requests_last_hour: int
    requests_last_day: int
    unique_users_last_day: int
    
    # Performance
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_rate: float
    
    # Quality
    avg_engagement_score: float
    avg_consistency_score: float
    personality_consistency: float
    
    # Training
    current_adapter_version: str
    last_training_date: float
    next_training_scheduled: Optional[float]
    
    # Status
    status: str  # "healthy", "degraded", "down", "training"
    deployment_stage: Optional[str]  # "canary", "half", "full"
```

**Dashboard API:**
```python
class DashboardAPI:
    """API for dashboard queries"""
    
    def __init__(self):
        self.metrics_db = MetricsDatabase()
        self.cache = Cache(ttl=30)  # 30 second cache
    
    @cached
    async def get_system_overview(self) -> DashboardMetrics:
        """Get system-wide metrics"""
        
        # Query recent metrics
        recent_metrics = await self.metrics_db.query_last_n_minutes(60)
        
        # Calculate aggregates
        total_requests = len(recent_metrics)
        total_errors = sum(1 for m in recent_metrics if m['error'])
        
        dashboard = DashboardMetrics(
            total_requests_per_second=total_requests / 3600,
            total_error_rate=total_errors / total_requests if total_requests > 0 else 0,
            avg_latency_ms=np.mean([m['latency_ms'] for m in recent_metrics]),
            active_characters=len(set(m['character_id'] for m in recent_metrics)),
            active_users=await self.count_active_users(),
            character_metrics=await self.get_all_character_metrics(),
            dream_cycles_running=await self.count_running_dream_cycles(),
            dream_cycles_queued=await self.count_queued_dream_cycles(),
            recent_deployments=await self.get_recent_deployments(limit=10),
            active_alerts=await self.get_active_alerts(),
            requests_trend=await self.get_requests_trend(hours=24),
            error_rate_trend=await self.get_error_rate_trend(hours=24),
            engagement_trend=await self.get_engagement_trend(hours=24)
        )
        
        return dashboard
    
    async def get_character_detail(self, character_id: str) -> CharacterDetailView:
        """Get detailed view for one character"""
        
        metrics = await self.get_character_metrics(character_id)
        
        # Get training history
        training_history = await self.get_training_history(character_id, limit=20)
        
        # Get recent interactions
        recent_interactions = await self.get_recent_interactions(
            character_id,
            limit=50
        )
        
        # Get validation history
        validation_history = await self.get_validation_history(
            character_id,
            limit=10
        )
        
        detail = CharacterDetailView(
            metrics=metrics,
            training_history=training_history,
            recent_interactions=recent_interactions,
            validation_history=validation_history,
            personality_profile=load_character_profile(character_id),
            constitution=load_character_constitution(character_id)
        )
        
        return detail
```

**Alert System:**
```python
class AlertSystem:
    """Monitors metrics and triggers alerts"""
    
    def __init__(self):
        self.alert_rules = self.load_alert_rules()
        self.active_alerts = {}
    
    def load_alert_rules(self) -> List[AlertRule]:
        """Load alert configuration"""
        return [
            AlertRule(
                name="high_error_rate",
                condition=lambda metrics: metrics.error_rate > 0.05,
                severity="critical",
                message="Error rate above 5%: {error_rate:.2%}"
            ),
            AlertRule(
                name="engagement_drop",
                condition=lambda metrics: (
                    metrics.avg_engagement_score < metrics.baseline_engagement * 0.85
                ),
                severity="warning",
                message="Engagement dropped 15% below baseline"
            ),
            AlertRule(
                name="high_latency",
                condition=lambda metrics: metrics.p95_latency_ms > 500,
                severity="warning",
                message="P95 latency above 500ms: {p95_latency_ms:.0f}ms"
            ),
            AlertRule(
                name="training_failed",
                condition=lambda job: job.state == DreamCycleState.FAILED,
                severity="warning",
                message="Dream cycle failed for {character_id}: {error}"
            ),
            AlertRule(
                name="validation_failed",
                condition=lambda results: not results.passes_all_thresholds(),
                severity="info",
                message="Validation failed for {character_id}"
            ),
        ]
    
    async def check_alerts(self):
        """Check all alert rules"""
        
        # Get current metrics for all characters
        for character_id in get_all_character_ids():
            metrics = await get_character_metrics(character_id)
            
            for rule in self.alert_rules:
                # Check condition
                if rule.condition(metrics):
                    # Create or update alert
                    alert_key = f"{character_id}:{rule.name}"
                    
                    if alert_key not in self.active_alerts:
                        # New alert
                        alert = Alert(
                            id=alert_key,
                            character_id=character_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            message=rule.message.format(**metrics.__dict__),
                            triggered_at=time.time()
                        )
                        
                        self.active_alerts[alert_key] = alert
                        await self.send_alert(alert)
                
                else:
                    # Condition resolved
                    if alert_key in self.active_alerts:
                        alert = self.active_alerts.pop(alert_key)
                        await self.resolve_alert(alert)
    
    async def send_alert(self, alert: Alert):
        """Send alert notification"""
        
        if alert.severity == "critical":
            # Send to Slack/email immediately
            await slack_webhook.send(
                channel="#ai-alerts",
                text=f"🚨 CRITICAL: {alert.message}",
                color="danger"
            )
        
        elif alert.severity == "warning":
            # Log and send to dashboard
            log_warning(alert.message)
            dashboard.add_alert(alert)
        
        else:  # info
            # Just log
            log_info(alert.message)
    
    async def run_monitoring_loop(self):
        """Continuous monitoring"""
        while True:
            await self.check_alerts()
            await asyncio.sleep(60)  # Check every minute
```

---

### 11. Integration with Existing Systems

**Purpose:** Connect Phase 7 to Phases 1-6 seamlessly.

**Integration Points:**

**1. Character Brain Integration:**
```python
# In character_brain.py - add experience logging

class CharacterBrain:
    def __init__(self, ...):
        # ... existing code ...
        self.experience_logger = ExperienceLogger(character_id)
    
    async def make_decision(self, context: DecisionContext) -> Decision:
        # ... existing decision logic ...
        
        decision = await self._generate_decision(context)
        
        # Log experience for learning
        self.experience_logger.log_decision(
            context=context,
            decision=decision,
            outcome=None  # Will be updated later
        )
        
        return decision
    
    def update_decision_outcome(
        self,
        decision_id: str,
        outcome: Dict[str, Any]
    ):
        """Update outcome after action execution"""
        self.experience_logger.update_outcome(decision_id, outcome)
```

**2. Escalation Engine Integration:**
```python
# In escalation_engine.py - track learning signals

class EscalationEngine:
    async def route_decision(self, context: EscalationContext) -> EscalationRouting:
        # ... existing routing logic ...
        
        routing = self._determine_routing(context)
        
        # If brain made the decision, mark for learning
        if routing.source == DecisionSource.BRAIN:
            # Higher value for learning
            context.metadata['high_learning_value'] = True
        
        return routing
```

**3. Chat System Integration:**
```python
# In chat_system.py - add engagement tracking

class ChatSystem:
    async def send_message(self, ...):
        # ... existing send logic ...
        
        # Track player engagement signals
        if message_type == MessageType.ACTION:
            # Measure player response time
            time_since_last = time.time() - self.last_player_message_time
            
            engagement_signal = calculate_engagement(
                response_time=time_since_last,
                message_length=len(content),
                context=self.conversation_context
            )
            
            # Attach to experience logger
            experience_logger.update_engagement_signal(
                session_id=self.session_id,
                engagement=engagement_signal
            )
```

**4. Multi-LoRA Manager Integration:**
```python
# In local_llm_engine.py - add adapter registry

class MultiLoRAManager:
    def __init__(self):
        # ... existing code ...
        self.traffic_router = TrafficRouter()
    
    def get_character_adapter(self, character_id: str) -> str:
        """Get adapter path with traffic routing"""
        
        # Use traffic router for A/B testing
        adapter_path = self.traffic_router.route_request(character_id)
        
        return adapter_path
    
    def reload_character(self, character_id: str):
        """Reload character after training"""
        
        # Unload old adapter
        if character_id in self.loaded_adapters:
            self.unload_adapter(character_id)
        
        # Load new adapter
        new_adapter_path = self.get_character_adapter(character_id)
        self.load_adapter(character_id, new_adapter_path)
        
        log_info(f"Reloaded {character_id} with adapter: {new_adapter_path}")
```

**5. DM Automation Integration:**
```python
# In dm_automation.py - trigger dream cycles

class DMDigitalTwin:
    async def end_session(self, session_id: str):
        """Called when gameplay session ends"""
        
        # ... existing session end logic ...
        
        # Trigger dream cycles for all characters
        characters_in_session = self.get_session_characters(session_id)
        
        for character_id in characters_in_session:
            dream_cycle_orchestrator.schedule_training(
                character_id=character_id,
                session_ids=[session_id]
            )
        
        log_info(f"Scheduled dream cycles for {len(characters_in_session)} characters")
```

**Complete Integration Flow:**
```
GAMEPLAY:
  Player action
     ↓
  Chat System (log engagement)
     ↓
  Character Brain (make decision)
     ↓
  Experience Logger (log context + decision)
     ↓
  Action Execution
     ↓
  Experience Logger (update outcome)
     ↓
  [Repeat for session duration]

SESSION END:
  DM calls end_session()
     ↓
  Dream Cycle Orchestrator triggered
     ↓
  [Phase 7 pipeline runs]
     ↓
  New adapter deployed
     ↓
  Multi-LoRA Manager reloads
     ↓
  Character uses improved adapter

NEXT SESSION:
  Character is smarter!
```

---

## File System Structure

```
ai_society_dnd/
├── backend/
│   ├── # Existing Phase 1-6 files
│   ├── local_llm_engine.py
│   ├── character_brain.py
│   ├── ...
│   │
│   ├── # NEW Phase 7 files
│   ├── experience_logger.py
│   ├── dream_cycle_orchestrator.py
│   ├── reflection_engine.py
│   ├── data_curation.py
│   ├── data_augmentation.py
│   ├── constitutional_review.py
│   ├── lora_trainer.py
│   ├── validation_pipeline.py
│   ├── deployment_manager.py
│   ├── monitoring_dashboard.py
│   ├── metrics_collector.py
│   └── alert_system.py
│
├── characters/
│   ├── marcus_guard/
│   │   ├── profile.yaml                    # Character definition
│   │   ├── constitution.yaml               # Behavioral principles
│   │   │
│   │   ├── experiences/                    # Raw gameplay logs
│   │   │   ├── session_2025-10-22_001.jsonl
│   │   │   ├── session_2025-10-22_002.jsonl
│   │   │   └── ...
│   │   │
│   │   ├── reflections/                    # GPT-4 analysis
│   │   │   ├── session_2025-10-22_001_reflection.json
│   │   │   ├── weekly_2025-10-22.json
│   │   │   └── ...
│   │   │
│   │   ├── training_data/                  # Curated datasets
│   │   │   ├── curated/
│   │   │   │   ├── 2025-10-22_high_quality.jsonl
│   │   │   │   └── ...
│   │   │   ├── augmented/
│   │   │   │   ├── 2025-10-22_augmented.jsonl
│   │   │   │   └── ...
│   │   │   └── final/
│   │   │       ├── 2025-10-22_training.jsonl
│   │   │       └── ...
│   │   │
│   │   ├── lora_adapters/                  # Trained weights
│   │   │   ├── v1.0.0/
│   │   │   │   ├── adapter_config.json
│   │   │   │   ├── adapter_model.bin
│   │   │   │   └── training_metadata.json
│   │   │   ├── v1.1.0/
│   │   │   ├── v1.2.0/
│   │   │   └── latest -> v1.2.0            # Symlink to deployed version
│   │   │
│   │   ├── validation/                     # Test results
│   │   │   ├── test_scenarios.yaml
│   │   │   ├── v1.0.0_results.json
│   │   │   ├── v1.1.0_results.json
│   │   │   └── baseline.json
│   │   │
│   │   └── metrics/                        # Performance logs
│   │       ├── performance_2025-10-22.json
│   │       └── ...
│   │
│   ├── elara_ranger/
│   │   └── [same structure]
│   │
│   └── [other characters]/
│
├── shared/
│   ├── base_models/                        # Base LLMs
│   │   ├── qwen2.5-3b-instruct/
│   │   │   ├── model.safetensors
│   │   │   ├── config.json
│   │   │   └── tokenizer/
│   │   └── qwen2.5-1.5b-instruct/
│   │
│   ├── configs/                            # Shared configs
│   │   ├── lora_training_default.yaml
│   │   ├── validation_thresholds.yaml
│   │   ├── traffic_routing.json
│   │   └── alert_rules.yaml
│   │
│   └── prompts/                            # Prompt templates
│       ├── reflection_prompt.txt
│       ├── constitutional_review_prompt.txt
│       └── augmentation_prompts/
│
├── infrastructure/
│   ├── database/                           # Metrics DB
│   │   ├── schema.sql
│   │   └── migrations/
│   │
│   ├── monitoring/                         # Dashboard
│   │   ├── dashboard_server.py
│   │   ├── templates/
│   │   └── static/
│   │
│   └── orchestration/                      # Job management
│       ├── job_queue.py
│       ├── scheduler.py
│       └── worker.py
│
├── docs/
│   ├── PHASE_7_ARCHITECTURE_DESIGN.md     # This document
│   ├── PHASE_7_QUICKSTART.md
│   └── PHASE_7_API_REFERENCE.md
│
└── tests/
    ├── test_experience_logger.py
    ├── test_data_curation.py
    ├── test_lora_trainer.py
    ├── test_validation.py
    └── test_integration.py
```

---

## Error Handling and Recovery

**1. Training Failures:**
```python
class TrainingErrorHandler:
    """Handle training failures gracefully"""
    
    def handle_training_error(self, error: Exception, context: Dict):
        """Route error to appropriate handler"""
        
        if isinstance(error, torch.cuda.OutOfMemoryError):
            return self.handle_oom_error(context)
        
        elif isinstance(error, TrainingDivergenceError):
            return self.handle_divergence_error(context)
        
        elif isinstance(error, CheckpointLoadError):
            return self.handle_checkpoint_error(context)
        
        else:
            return self.handle_unknown_error(error, context)
    
    def handle_oom_error(self, context: Dict):
        """Handle CUDA out of memory"""
        log_warning("CUDA OOM detected - reducing batch size")
        
        # Reduce batch size and retry
        config = context['config']
        config.per_device_train_batch_size = max(1, config.per_device_train_batch_size // 2)
        config.gradient_accumulation_steps *= 2  # Maintain effective batch size
        
        # Or reduce rank
        config.lora_rank = max(4, config.lora_rank // 2)
        
        return "retry_with_reduced_memory"
    
    def handle_divergence_error(self, context: Dict):
        """Handle training divergence (loss exploding)"""
        log_warning("Training divergence detected - reducing learning rate")
        
        config = context['config']
        config.learning_rate *= 0.5  # Cut learning rate in half
        
        # Load from earlier checkpoint
        last_good_checkpoint = find_last_stable_checkpoint(context['character_id'])
        context['resume_from_checkpoint'] = last_good_checkpoint
        
        return "retry_with_reduced_lr"
```

**2. Validation Failures:**
```python
def handle_validation_failure(
    character_id: str,
    validation_results: ValidationResults,
    adapter_path: str
):
    """Handle failed validation"""
    
    log_warning(f"Validation failed for {character_id}")
    log_warning(f"  Results: {validation_results}")
    
    # Don't deploy failed adapter
    mark_adapter_failed(character_id, adapter_path)
    
    # Analyze failure
    failure_reasons = analyze_validation_failure(validation_results)
    
    # Generate failure report
    report = {
        "character_id": character_id,
        "adapter_path": adapter_path,
        "timestamp": time.time(),
        "validation_results": asdict(validation_results),
        "failure_reasons": failure_reasons,
        "recommended_actions": generate_recommendations(failure_reasons)
    }
    
    save_failure_report(character_id, report)
    
    # Alert developer
    send_alert(
        title=f"Validation Failed: {character_id}",
        message=f"Reasons: {failure_reasons}",
        severity="info"
    )
    
    # Keep using current adapter
    log_info(f"Continuing to use current adapter for {character_id}")
```

**3. Deployment Rollback:**
```python
async def emergency_rollback(character_id: str):
    """Emergency rollback to last known good version"""
    
    log_error(f"EMERGENCY ROLLBACK: {character_id}")
    
    # Find last good version
    last_good = find_last_good_adapter(character_id)
    
    if not last_good:
        log_critical(f"No good adapter found for {character_id}!")
        # Fall back to base model
        last_good = "base_model"
    
    # Immediate traffic switch
    traffic_router.set_single_adapter(character_id, last_good)
    
    # Reload adapter
    multi_lora_manager.reload_character(character_id)
    
    # Alert
    send_alert(
        title=f"Emergency Rollback: {character_id}",
        message=f"Rolled back to: {last_good}",
        severity="critical"
    )
    
    log_info(f"Rolled back {character_id} to {last_good}")
```

**4. Data Corruption:**
```python
def validate_training_data(training_data: List[Dict]) -> bool:
    """Validate training data integrity"""
    
    for i, example in enumerate(training_data):
        try:
            # Check required fields
            assert "messages" in example
            assert len(example["messages"]) > 0
            
            # Check message structure
            for msg in example["messages"]:
                assert "role" in msg
                assert "content" in msg
                assert msg["role"] in ["system", "user", "assistant"]
            
            # Check for empty content
            for msg in example["messages"]:
                if not msg["content"] or len(msg["content"].strip()) == 0:
                    log_warning(f"Empty content in example {i}")
                    return False
            
        except Exception as e:
            log_error(f"Invalid training data at index {i}: {e}")
            return False
    
    return True
```

---

## Development Roadmap

**Week 1-2: Core Infrastructure**
- [ ] Experience Logger
- [ ] Dream Cycle Orchestrator (basic)
- [ ] Reflection Engine (GPT-4 integration)
- [ ] LoRA Trainer (basic training loop)
- [ ] Test with 1 character, manual trigger

**Week 3-4: Data Pipeline**
- [ ] Data Curation (filtering, weighting)
- [ ] Data Augmentation (paraphrasing, what-if)
- [ ] Constitutional Review
- [ ] Improved training data quality
- [ ] Test with 2-3 characters

**Week 5-6: Validation & Quality Control**
- [ ] Validation Pipeline (test scenarios)
- [ ] Personality consistency tests
- [ ] Uniqueness tests
- [ ] Regression detection
- [ ] Automated pass/fail gates

**Week 7-8: Deployment & Monitoring**
- [ ] Deployment Manager (canary, blue-green)
- [ ] Traffic Router (A/B testing)
- [ ] Metrics Collector
- [ ] Monitoring Dashboard (basic)
- [ ] Alert System

**Week 9-10: Integration & Polish**
- [ ] Full integration with Phases 1-6
- [ ] Automated dream cycle triggers
- [ ] Multi-character training
- [ ] Performance optimization
- [ ] Documentation

**Week 11-12: Production Readiness**
- [ ] Error handling & recovery
- [ ] Rollback mechanisms
- [ ] Production monitoring
- [ ] Cost optimization (GPT-4 usage)
- [ ] End-to-end testing

**Week 13-14: Advanced Features**
- [ ] Meta-learning across characters
- [ ] Cross-character knowledge transfer
- [ ] Advanced augmentation techniques
- [ ] Self-distillation for efficiency
- [ ] Long-term trend analysis

---

## Quick Start Guide

**Prerequisites:**
- Phases 1-6 completed and working
- RTX 4050 with 6GB VRAM (or better)
- GPT-4 or Claude API access
- 50GB+ free disk space

**Step 1: Install Dependencies**
```bash
pip install transformers==4.39.0
pip install peft==0.10.0
pip install bitsandbytes==0.43.0
pip install torch==2.3.0
pip install trl==0.8.0
pip install datasets
pip install accelerate==0.28.0
pip install openai  # For GPT-4
pip install tensorboard
```

**Step 2: Configure Character**
```bash
# Create character constitution
cat > characters/marcus_guard/constitution.yaml << EOF
character_id: marcus_guard
principles:
  - name: stay_in_character
    description: "Cautious, experienced, values life"
    priority: 1
  - name: follow_protocol
    description: "Follow guard protocols"
    priority: 1
  # ... more principles
EOF
```

**Step 3: Run First Dream Cycle**
```python
# test_dream_cycle.py
import asyncio
from dream_cycle_orchestrator import DreamCycleOrchestrator

async def test_first_training():
    orchestrator = DreamCycleOrchestrator()
    
    # Manually trigger for one character
    result = await orchestrator.run_dream_cycle(
        character_id="marcus_guard",
        session_ids=["test_session_001"]
    )
    
    print(f"Training result: {result}")

asyncio.run(test_first_training())
```

**Step 4: Validate Results**
```python
# Check if adapter was created
import os
adapters_path = "characters/marcus_guard/lora_adapters"
latest = os.readlink(f"{adapters_path}/latest")
print(f"Latest adapter: {latest}")

# Check validation results
import json
with open(f"{adapters_path}/{latest}/validation_results.json") as f:
    results = json.load(f)
    print(f"Validation: {results['passes_all_thresholds']}")
```

**Step 5: Test Improved Character**
```python
# Compare before/after
from character_brain import CharacterBrain
from local_llm_engine import LocalLLMEngine

# Load with new adapter
llm = LocalLLMEngine()
await llm.start()

brain = CharacterBrain("marcus_guard", llm)

# Test scenario
test_context = DecisionContext(
    decision_type=DecisionType.SOCIAL,
    situation="Suspicious player approaching at night",
    urgency=0.6
)

decision = await brain.make_decision(test_context)
print(f"Response: {decision.decision}")
```

---

## Configuration Reference

**LoRA Training Config:**
```yaml
# config/lora_training_default.yaml
base_model: "Qwen/Qwen2.5-3B-Instruct"
model_max_length: 2048

quantization:
  load_in_4bit: true
  quant_type: "nf4"
  compute_dtype: "bfloat16"
  use_double_quant: true

lora:
  rank: 16
  alpha: 32
  dropout: 0.05
  target_modules: ["q_proj", "k_proj", "v_proj", "o_proj"]
  use_rslora: true

training:
  per_device_batch_size: 1
  gradient_accumulation_steps: 8
  num_epochs: 2
  learning_rate: 1.0e-4
  warmup_ratio: 0.05
  lr_scheduler: "cosine"
  optim: "paged_adamw_8bit"
  gradient_checkpointing: true
  bf16: true

logging:
  logging_steps: 10
  save_steps: 100
  save_total_limit: 3
```

**Validation Thresholds:**
```yaml
# config/validation_thresholds.yaml
personality_consistency: 0.80
tactical_intelligence: 0.70
lore_accuracy: 0.90
engagement_quality: 0.60
uniqueness_score: 0.70

max_regression:
  personality: 0.10
  tactical: 0.10
  lore: 0.05
  engagement: 0.15
```

**Alert Rules:**
```yaml
# config/alert_rules.yaml
alerts:
  - name: high_error_rate
    condition: "error_rate > 0.05"
    severity: critical
    
  - name: engagement_drop
    condition: "engagement < baseline * 0.85"
    severity: warning
    
  - name: training_failed
    condition: "dream_cycle_state == FAILED"
    severity: warning
    
  - name: validation_failed
    condition: "validation_passed == false"
    severity: info
```

---

## Testing Strategy

**Unit Tests:**
```python
# tests/test_experience_logger.py
def test_experience_logging():
    logger = ExperienceLogger("test_char")
    
    exp = logger.log_decision(
        context={"location": "test"},
        decision={"action": "test"},
        outcome={"success": True}
    )
    
    assert exp.experience_id is not None
    assert exp.character_id == "test_char"

# tests/test_data_curation.py
def test_quality_filtering():
    experiences = create_test_experiences(100)
    
    curated = curate_training_data(
        experiences,
        quality_threshold=0.7
    )
    
    assert len(curated) < len(experiences)
    assert all(e.quality_score >= 0.7 for e in curated)
```

**Integration Tests:**
```python
# tests/test_integration.py
@pytest.mark.asyncio
async def test_full_dream_cycle():
    """Test complete pipeline"""
    
    # Setup
    character_id = "test_character"
    session_ids = ["test_session"]
    
    # Run pipeline
    orchestrator = DreamCycleOrchestrator()
    result = await orchestrator.run_dream_cycle(
        character_id,
        session_ids
    )
    
    # Verify
    assert result.state == DreamCycleState.COMPLETED
    assert os.path.exists(f"characters/{character_id}/lora_adapters/v1.0.0")
```

**Performance Tests:**
```python
# tests/test_performance.py
def test_training_time():
    """Ensure training completes in reasonable time"""
    
    start = time.time()
    
    train_lora_adapter(
        character_id="test",
        training_data=create_test_data(300),
        config=get_test_config()
    )
    
    duration = time.time() - start
    
    assert duration < 3600  # Should complete in under 1 hour
```

---

## API Reference

**Main APIs:**

```python
# Dream Cycle API
orchestrator = DreamCycleOrchestrator()
await orchestrator.run_dream_cycle(character_id, session_ids)
await orchestrator.schedule_training(character_id, session_ids)

# Experience Logging API
logger = ExperienceLogger(character_id)
logger.log_decision(context, decision, outcome)
logger.update_outcome(experience_id, outcome)

# Training API
trainer = LoRATrainer(config)
adapter_path = await trainer.train(character_id, training_data)

# Validation API
validator = ValidationPipeline()
results = await validator.validate(character_id, adapter_path)

# Deployment API
deployer = DeploymentManager()
await deployer.deploy_adapter(character_id, adapter_path, strategy="canary")

# Monitoring API
dashboard = DashboardAPI()
metrics = await dashboard.get_system_overview()
details = await dashboard.get_character_detail(character_id)
```

---

## Summary

This completes the Phase 7 architecture design. The system provides:

✅ **Complete pipeline:** Experience → Reflection → Training → Validation → Deployment  
✅ **Memory efficient:** Runs on 6GB VRAM through QLoRA  
✅ **Production ready:** Error handling, rollback, monitoring  
✅ **Quality controlled:** Constitutional AI, validation gates  
✅ **Safe deployment:** Canary releases, A/B testing  
✅ **Integrated:** Seamless connection to Phases 1-6  

**Next Step:** Review this architecture, then we'll implement component by component!

---

**Architecture Design Status:** ✅ COMPLETE  
**Ready for:** Implementation review and build phase  
**Estimated Implementation:** 12-14 weeks (phased rollout)
