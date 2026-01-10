"""
Reflection Pipeline

Uses LLM (GPT-4/Claude/DeepSeek) to analyze gameplay decisions and provide quality labels,
teaching moments, and improvement suggestions for character training.

Phase 7.2.1 - Reflection Pipeline
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)

# Import LLM API integration
try:
    from llm_api_integration import LLMAPIClient, LLMConfig, get_config_preset
    LLM_API_AVAILABLE = True
except ImportError:
    LLM_API_AVAILABLE = False
    logger.warning("LLM API integration not available - using automated analysis only")


class ReflectionQuality(Enum):
    """Quality labels for decisions"""
    EXCELLENT = "excellent"      # 0.9-1.0: Outstanding decision
    GOOD = "good"               # 0.7-0.9: Solid decision
    ACCEPTABLE = "acceptable"    # 0.5-0.7: Adequate decision
    POOR = "poor"               # 0.3-0.5: Suboptimal decision
    BAD = "bad"                 # 0.0-0.3: Wrong decision
    TEACHING_MOMENT = "teaching_moment"  # Special: High learning value


@dataclass
class ReflectionPrompt:
    """Prompt template for LLM reflection"""
    system_prompt: str
    user_prompt_template: str
    expected_format: Dict[str, Any]
    max_tokens: int = 1500
    temperature: float = 0.3  # Low for consistent analysis


@dataclass
class ReflectionResult:
    """Result of decision reflection"""
    decision_id: str
    quality_label: ReflectionQuality
    quality_score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    
    # Analysis
    what_worked: List[str] = field(default_factory=list)
    what_failed: List[str] = field(default_factory=list)
    why_it_worked_or_failed: str = ""
    
    # Learning
    improvement_suggestions: List[str] = field(default_factory=list)
    teaching_value: float = 0.0  # 0.0 to 1.0
    
    # Training data
    training_eligible: bool = True
    training_weight: float = 1.0  # Higher for teaching moments
    
    # Meta
    reflection_timestamp: float = field(default_factory=time.time)
    model_used: str = ""
    processing_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "decision_id": self.decision_id,
            "quality_label": self.quality_label.value,
            "quality_score": self.quality_score,
            "confidence": self.confidence,
            "what_worked": self.what_worked,
            "what_failed": self.what_failed,
            "why_it_worked_or_failed": self.why_it_worked_or_failed,
            "improvement_suggestions": self.improvement_suggestions,
            "teaching_value": self.teaching_value,
            "training_eligible": self.training_eligible,
            "training_weight": self.training_weight,
            "reflection_timestamp": self.reflection_timestamp,
            "model_used": self.model_used,
            "processing_time_ms": self.processing_time_ms
        }


class ReflectionPipeline:
    """
    Analyzes gameplay decisions using LLM reflection.
    
    Features:
    - Quality labeling (excellent → bad → teaching moment)
    - Improvement suggestions
    - Training data curation
    - Batch processing
    - Cost tracking
    """
    
    def __init__(
        self, 
        llm_client: Optional[Any] = None,
        api_key: Optional[str] = None, 
        model: str = "gpt-4"
    ):
        """
        Initialize reflection pipeline
        
        Args:
            llm_client: Optional LLMAPIClient instance
            api_key: Optional API key (for creating client)
            model: LLM model to use
        """
        self.llm_client = llm_client
        self.api_key = api_key
        self.model = model
        
        # Statistics
        self.stats = {
            "total_reflections": 0,
            "by_quality": {},
            "avg_processing_time_ms": 0.0,
            "total_api_cost": 0.0,
            "teaching_moments_found": 0
        }
        
        # Prompts
        self.prompts = self._build_prompts()
        
        logger.info(f"ReflectionPipeline initialized with model: {model}")
    
    def _build_prompts(self) -> Dict[str, ReflectionPrompt]:
        """Build prompt templates for reflection"""
        prompts = {}
        
        # Decision quality analysis prompt
        prompts["quality_analysis"] = ReflectionPrompt(
            system_prompt="""You are an expert D&D game master and decision analyst. 
Your role is to analyze gameplay decisions made by AI characters and provide:
1. Quality assessment (excellent, good, acceptable, poor, bad, or teaching_moment)
2. What worked and what didn't
3. Why the decision succeeded or failed
4. Improvement suggestions for future training

Be objective, specific, and educational. Focus on tactical and strategic thinking.
Teaching moments are decisions that failed but offer high learning value.""",
            
            user_prompt_template="""Analyze this gameplay decision:

CHARACTER: {character_id}
SITUATION: {situation_description}
CHARACTER STATE: {character_state}
PERCEPTION: {perception_summary}

DECISION MADE:
- Action: {action}
- Reasoning: {reasoning}
- Confidence: {confidence}
- Source: {decision_source}

OUTCOME:
- Success: {success}
- Immediate Result: {immediate_outcome}
- Rewards Earned: {rewards_summary}
- Quality Score (automated): {automated_quality_score}

Analyze this decision and respond in JSON format:
{{
  "quality_label": "excellent|good|acceptable|poor|bad|teaching_moment",
  "quality_score": 0.0-1.0,
  "confidence": 0.0-1.0,
  "what_worked": ["list", "of", "strengths"],
  "what_failed": ["list", "of", "weaknesses"],
  "why_it_worked_or_failed": "brief explanation",
  "improvement_suggestions": ["specific", "actionable", "suggestions"],
  "teaching_value": 0.0-1.0,
  "training_weight": 1.0-3.0
}}""",
            
            expected_format={
                "quality_label": str,
                "quality_score": float,
                "confidence": float,
                "what_worked": list,
                "what_failed": list,
                "why_it_worked_or_failed": str,
                "improvement_suggestions": list,
                "teaching_value": float,
                "training_weight": float
            }
        )
        
        return prompts
    
    async def reflect_on_decision(
        self,
        decision_data: Dict[str, Any],
        outcome_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ReflectionResult:
        """
        Analyze a single decision using LLM reflection
        
        Args:
            decision_data: Decision details
            outcome_data: Outcome with rewards
            context: Game context
            
        Returns:
            ReflectionResult
        """
        start_time = time.time()
        
        # Build prompt
        prompt = self._build_decision_prompt(decision_data, outcome_data, context)
        
        # Get LLM response
        if self.llm_client:
            llm_response = await self._call_llm(prompt)
        else:
            # Fallback: Use automated analysis
            llm_response = self._automated_analysis(decision_data, outcome_data)
        
        # Parse response
        result = self._parse_llm_response(
            decision_id=decision_data.get("decision_id", "unknown"),
            llm_response=llm_response,
            processing_time_ms=(time.time() - start_time) * 1000
        )
        
        # Update statistics
        self._update_stats(result)
        
        return result
    
    def _build_decision_prompt(
        self,
        decision_data: Dict[str, Any],
        outcome_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Build prompt for decision analysis"""
        prompt_template = self.prompts["quality_analysis"]
        
        # Extract data
        character_id = context.get("character_id", "unknown")
        situation = context.get("situation_context", {})
        
        # Build situation description
        game_state = situation.get("game_state", {})
        situation_desc = game_state.get("description", "Unknown situation")
        if not situation_desc or situation_desc == "Unknown situation":
            situation_desc = f"Turn {game_state.get('turn', '?')}, Location: {game_state.get('location', '?')}"
        
        # Character state
        char_state = situation.get("character_state", {})
        char_state_str = f"HP: {char_state.get('hp', '?')}/{char_state.get('max_hp', '?')}"
        
        # Perception summary
        perception = situation.get("perception_data", {})
        perception_str = json.dumps(perception) if perception else "No special perception"
        
        # Decision details
        action = decision_data.get("action", "unknown")
        reasoning = decision_data.get("reasoning", "No reasoning provided")
        confidence = decision_data.get("confidence", 0.5)
        decision_source = decision_data.get("source", "unknown")
        
        # Outcome
        success = outcome_data.get("success", False)
        immediate = outcome_data.get("immediate", "Unknown outcome")
        
        # Rewards summary
        reward_signals = outcome_data.get("reward_signals", [])
        rewards_str = ", ".join([
            f"{sig.get('domain')}: {sig.get('value', 0):.2f}"
            for sig in reward_signals
        ]) if reward_signals else "No rewards"
        
        # Quality score
        quality_analysis = outcome_data.get("quality_analysis", {})
        auto_quality = quality_analysis.get("quality_score", 0.5)
        
        # Fill template
        prompt = prompt_template.user_prompt_template.format(
            character_id=character_id,
            situation_description=situation_desc,
            character_state=char_state_str,
            perception_summary=perception_str,
            action=action,
            reasoning=reasoning,
            confidence=confidence,
            decision_source=decision_source,
            success="Yes" if success else "No",
            immediate_outcome=immediate,
            rewards_summary=rewards_str,
            automated_quality_score=f"{auto_quality:.2f}"
        )
        
        return prompt
    
    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """
        Call LLM API for reflection
        
        Args:
            prompt: Formatted prompt
            
        Returns:
            LLM response as dictionary
        """
        if not self.llm_client:
            logger.warning("LLM API client not configured - using automated analysis")
            return self._automated_analysis({}, {})
        
        try:
            # Get system prompt
            system_prompt = self.prompts["quality_analysis"].system_prompt
            
            # Call LLM
            response = await self.llm_client.call(
                system_prompt=system_prompt,
                user_prompt=prompt
            )
            
            if not response.success:
                logger.error(f"LLM API call failed: {response.error}")
                return self._automated_analysis({}, {})
            
            # Update cost tracking
            self.stats["total_api_cost"] += response.cost
            
            # Parse JSON response
            try:
                return json.loads(response.content)
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM response as JSON, using automated analysis")
                return self._automated_analysis({}, {})
                
        except Exception as e:
            logger.error(f"LLM API call error: {e}")
            return self._automated_analysis({}, {})
    
    def _automated_analysis(
        self,
        decision_data: Dict[str, Any],
        outcome_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fallback automated analysis (no LLM required)
        
        Args:
            decision_data: Decision details
            outcome_data: Outcome details
            
        Returns:
            Analysis in LLM response format
        """
        # Extract key metrics
        success = outcome_data.get("success", False)
        quality_analysis = outcome_data.get("quality_analysis", {})
        auto_score = quality_analysis.get("quality_score", 0.5)
        confidence = decision_data.get("confidence", 0.5)
        
        # Determine quality label
        if auto_score >= 0.85:
            quality_label = "excellent"
        elif auto_score >= 0.7:
            quality_label = "good"
        elif auto_score >= 0.5:
            quality_label = "acceptable"
        elif auto_score >= 0.3:
            quality_label = "poor"
        else:
            quality_label = "bad"
        
        # Check if teaching moment (failed but with learning potential)
        if not success and auto_score < 0.4:
            quality_label = "teaching_moment"
        
        # Build response
        return {
            "quality_label": quality_label,
            "quality_score": auto_score,
            "confidence": 0.7,  # Moderate confidence in automated analysis
            "what_worked": ["Decision was executed"] if success else [],
            "what_failed": ["Decision did not achieve goal"] if not success else [],
            "why_it_worked_or_failed": "Automated analysis based on outcome metrics",
            "improvement_suggestions": [
                "Consider alternative approaches",
                "Analyze similar situations for patterns"
            ] if not success else [
                "Continue similar decision-making"
            ],
            "teaching_value": 0.7 if not success else 0.3,
            "training_weight": 2.0 if quality_label == "teaching_moment" else 1.0
        }
    
    def _parse_llm_response(
        self,
        decision_id: str,
        llm_response: Dict[str, Any],
        processing_time_ms: float
    ) -> ReflectionResult:
        """Parse LLM response into ReflectionResult"""
        quality_label_str = llm_response.get("quality_label", "acceptable")
        
        try:
            quality_label = ReflectionQuality(quality_label_str)
        except ValueError:
            logger.warning(f"Invalid quality label: {quality_label_str}, using ACCEPTABLE")
            quality_label = ReflectionQuality.ACCEPTABLE
        
        return ReflectionResult(
            decision_id=decision_id,
            quality_label=quality_label,
            quality_score=llm_response.get("quality_score", 0.5),
            confidence=llm_response.get("confidence", 0.7),
            what_worked=llm_response.get("what_worked", []),
            what_failed=llm_response.get("what_failed", []),
            why_it_worked_or_failed=llm_response.get("why_it_worked_or_failed", ""),
            improvement_suggestions=llm_response.get("improvement_suggestions", []),
            teaching_value=llm_response.get("teaching_value", 0.0),
            training_eligible=True,
            training_weight=llm_response.get("training_weight", 1.0),
            model_used=self.model,
            processing_time_ms=processing_time_ms
        )
    
    def _update_stats(self, result: ReflectionResult) -> None:
        """Update pipeline statistics"""
        self.stats["total_reflections"] += 1
        
        # By quality
        quality = result.quality_label.value
        self.stats["by_quality"][quality] = self.stats["by_quality"].get(quality, 0) + 1
        
        # Processing time
        total = self.stats["total_reflections"]
        current_avg = self.stats["avg_processing_time_ms"]
        self.stats["avg_processing_time_ms"] = (
            (current_avg * (total - 1) + result.processing_time_ms) / total
        )
        
        # Teaching moments
        if result.quality_label == ReflectionQuality.TEACHING_MOMENT:
            self.stats["teaching_moments_found"] += 1
    
    async def reflect_on_batch(
        self,
        decisions: List[Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]],
        max_concurrent: int = 5
    ) -> List[ReflectionResult]:
        """
        Analyze multiple decisions in parallel
        
        Args:
            decisions: List of (decision_data, outcome_data, context) tuples
            max_concurrent: Maximum concurrent API calls
            
        Returns:
            List of ReflectionResults
        """
        # Use semaphore to limit concurrent API calls
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def reflect_with_limit(decision, outcome, context):
            async with semaphore:
                return await self.reflect_on_decision(decision, outcome, context)
        
        tasks = [
            reflect_with_limit(dec, out, ctx)
            for dec, out, ctx in decisions
        ]
        
        results = await asyncio.gather(*tasks)
        
        logger.info(f"Batch reflection complete: {len(results)} decisions analyzed")
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get reflection pipeline statistics"""
        stats = dict(self.stats)
        
        # Add percentages
        if self.stats["total_reflections"] > 0:
            for quality, count in self.stats["by_quality"].items():
                pct_key = f"{quality}_pct"
                stats[pct_key] = count / self.stats["total_reflections"]
        
        return stats
    
    def get_teaching_moments(
        self,
        decisions: List[Dict[str, Any]],
        min_teaching_value: float = 0.6
    ) -> List[str]:
        """
        Identify decisions that are good teaching moments
        
        Args:
            decisions: List of decisions with reflections
            min_teaching_value: Minimum teaching value threshold
            
        Returns:
            List of decision IDs that are teaching moments
        """
        teaching_moments = []
        
        for decision in decisions:
            reflection = decision.get("reflection")
            if not reflection:
                continue
            
            if (reflection.get("quality_label") == "teaching_moment" or
                reflection.get("teaching_value", 0) >= min_teaching_value):
                teaching_moments.append(decision.get("decision_id"))
        
        return teaching_moments


# Test functionality
async def test_reflection_pipeline():
    """Test the reflection pipeline"""
    print("Testing ReflectionPipeline...")
    
    pipeline = ReflectionPipeline()
    
    # Test decision
    decision_data = {
        "decision_id": "dec_123",
        "action": "attack",
        "reasoning": "Enemy is low HP, finish them",
        "confidence": 0.85,
        "source": "bot"
    }
    
    outcome_data = {
        "success": True,
        "immediate": "Hit for 15 damage, enemy defeated",
        "reward_signals": [
            {"domain": "combat", "value": 0.8, "confidence": 0.9}
        ],
        "quality_analysis": {"quality_score": 0.75}
    }
    
    context = {
        "character_id": "thorin",
        "situation_context": {
            "game_state": {"turn": 5, "location": "Cave"},
            "character_state": {"hp": 35, "max_hp": 50}
        }
    }
    
    # Reflect
    result = await pipeline.reflect_on_decision(decision_data, outcome_data, context)
    
    print(f"✓ Reflection complete:")
    print(f"   Quality: {result.quality_label.value}")
    print(f"   Score: {result.quality_score:.2f}")
    print(f"   Teaching value: {result.teaching_value:.2f}")
    print(f"   Processing time: {result.processing_time_ms:.0f}ms")
    
    # Get stats
    stats = pipeline.get_statistics()
    print(f"✓ Statistics:")
    print(f"   Total reflections: {stats['total_reflections']}")
    print(f"   By quality: {stats['by_quality']}")
    
    print("\n✅ All reflection pipeline tests passed!")


if __name__ == "__main__":
    asyncio.run(test_reflection_pipeline())
