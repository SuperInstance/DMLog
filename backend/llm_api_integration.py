"""
LLM API Integration

Handles API calls to various LLM providers (OpenAI GPT-4, Anthropic Claude, DeepSeek).
Provides unified interface with cost tracking and rate limiting.

Phase 7.2.1 - Reflection Pipeline - API Integration
"""

import os
import time
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"          # GPT-4, GPT-4-turbo
    ANTHROPIC = "anthropic"    # Claude 3.5 Sonnet, etc
    DEEPSEEK = "deepseek"      # DeepSeek models


@dataclass
class LLMConfig:
    """Configuration for LLM API"""
    provider: LLMProvider
    model: str
    api_key: str
    api_base: Optional[str] = None
    max_tokens: int = 1500
    temperature: float = 0.3
    top_p: float = 0.95
    
    # Rate limiting
    max_requests_per_minute: int = 60
    max_tokens_per_minute: int = 90000
    
    # Cost tracking (per 1K tokens)
    cost_per_1k_input_tokens: float = 0.0
    cost_per_1k_output_tokens: float = 0.0


@dataclass
class LLMResponse:
    """Response from LLM"""
    content: str
    model: str
    provider: str
    tokens_used: int
    input_tokens: int
    output_tokens: int
    cost: float
    latency_ms: float
    success: bool
    error: Optional[str] = None


class LLMAPIClient:
    """
    Unified client for LLM API calls with cost tracking and rate limiting.
    
    Supports:
    - OpenAI GPT-4
    - Anthropic Claude
    - DeepSeek
    """
    
    def __init__(self, config: LLMConfig):
        """
        Initialize API client
        
        Args:
            config: LLM configuration
        """
        self.config = config
        
        # Rate limiting
        self.request_times: List[float] = []
        self.token_usage: List[Tuple[float, int]] = []
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "avg_latency_ms": 0.0
        }
        
        logger.info(f"LLMAPIClient initialized: {config.provider.value}/{config.model}")
    
    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        Make LLM API call
        
        Args:
            system_prompt: System message
            user_prompt: User message
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse
        """
        start_time = time.time()
        
        # Rate limiting
        await self._check_rate_limits()
        
        # Call appropriate provider
        try:
            if self.config.provider == LLMProvider.OPENAI:
                response = await self._call_openai(system_prompt, user_prompt, **kwargs)
            elif self.config.provider == LLMProvider.ANTHROPIC:
                response = await self._call_anthropic(system_prompt, user_prompt, **kwargs)
            elif self.config.provider == LLMProvider.DEEPSEEK:
                response = await self._call_deepseek(system_prompt, user_prompt, **kwargs)
            else:
                raise ValueError(f"Unsupported provider: {self.config.provider}")
            
            response.latency_ms = (time.time() - start_time) * 1000
            
            # Update statistics
            self._update_stats(response)
            
            return response
            
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            
            error_response = LLMResponse(
                content="",
                model=self.config.model,
                provider=self.config.provider.value,
                tokens_used=0,
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                latency_ms=(time.time() - start_time) * 1000,
                success=False,
                error=str(e)
            )
            
            self.stats["failed_requests"] += 1
            
            return error_response
    
    async def _check_rate_limits(self) -> None:
        """Check and enforce rate limits"""
        current_time = time.time()
        
        # Remove old request times (older than 1 minute)
        self.request_times = [
            t for t in self.request_times 
            if current_time - t < 60
        ]
        
        # Check request limit
        if len(self.request_times) >= self.config.max_requests_per_minute:
            wait_time = 60 - (current_time - self.request_times[0])
            if wait_time > 0:
                logger.info(f"Rate limit: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        
        # Record this request
        self.request_times.append(current_time)
    
    async def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Call OpenAI API"""
        api_base = self.config.api_base or "https://api.openai.com/v1"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }
        
        data = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "top_p": kwargs.get("top_p", self.config.top_p)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_base}/chat/completions",
                headers=headers,
                json=data
            ) as resp:
                result = await resp.json()
                
                if resp.status != 200:
                    raise Exception(f"OpenAI API error: {result.get('error', {}).get('message', 'Unknown')}")
                
                # Parse response
                content = result["choices"][0]["message"]["content"]
                usage = result["usage"]
                
                # Calculate cost
                cost = (
                    (usage["prompt_tokens"] / 1000) * self.config.cost_per_1k_input_tokens +
                    (usage["completion_tokens"] / 1000) * self.config.cost_per_1k_output_tokens
                )
                
                return LLMResponse(
                    content=content,
                    model=result["model"],
                    provider="openai",
                    tokens_used=usage["total_tokens"],
                    input_tokens=usage["prompt_tokens"],
                    output_tokens=usage["completion_tokens"],
                    cost=cost,
                    latency_ms=0.0,  # Set by caller
                    success=True
                )
    
    async def _call_anthropic(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Call Anthropic Claude API"""
        api_base = self.config.api_base or "https://api.anthropic.com/v1"
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": self.config.model,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_base}/messages",
                headers=headers,
                json=data
            ) as resp:
                result = await resp.json()
                
                if resp.status != 200:
                    raise Exception(f"Anthropic API error: {result.get('error', {}).get('message', 'Unknown')}")
                
                # Parse response
                content = result["content"][0]["text"]
                usage = result["usage"]
                
                # Calculate cost
                cost = (
                    (usage["input_tokens"] / 1000) * self.config.cost_per_1k_input_tokens +
                    (usage["output_tokens"] / 1000) * self.config.cost_per_1k_output_tokens
                )
                
                return LLMResponse(
                    content=content,
                    model=result["model"],
                    provider="anthropic",
                    tokens_used=usage["input_tokens"] + usage["output_tokens"],
                    input_tokens=usage["input_tokens"],
                    output_tokens=usage["output_tokens"],
                    cost=cost,
                    latency_ms=0.0,
                    success=True
                )
    
    async def _call_deepseek(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Call DeepSeek API"""
        api_base = self.config.api_base or "https://api.deepseek.com/v1"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }
        
        data = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_base}/chat/completions",
                headers=headers,
                json=data
            ) as resp:
                result = await resp.json()
                
                if resp.status != 200:
                    raise Exception(f"DeepSeek API error: {result.get('error', {}).get('message', 'Unknown')}")
                
                # Parse response (similar to OpenAI format)
                content = result["choices"][0]["message"]["content"]
                usage = result["usage"]
                
                # Calculate cost
                cost = (
                    (usage["prompt_tokens"] / 1000) * self.config.cost_per_1k_input_tokens +
                    (usage["completion_tokens"] / 1000) * self.config.cost_per_1k_output_tokens
                )
                
                return LLMResponse(
                    content=content,
                    model=result["model"],
                    provider="deepseek",
                    tokens_used=usage["total_tokens"],
                    input_tokens=usage["prompt_tokens"],
                    output_tokens=usage["completion_tokens"],
                    cost=cost,
                    latency_ms=0.0,
                    success=True
                )
    
    def _update_stats(self, response: LLMResponse) -> None:
        """Update API statistics"""
        self.stats["total_requests"] += 1
        
        if response.success:
            self.stats["successful_requests"] += 1
            self.stats["total_tokens"] += response.tokens_used
            self.stats["total_cost"] += response.cost
            
            # Update average latency
            total = self.stats["successful_requests"]
            current_avg = self.stats["avg_latency_ms"]
            self.stats["avg_latency_ms"] = (
                (current_avg * (total - 1) + response.latency_ms) / total
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        stats = dict(self.stats)
        
        if self.stats["total_requests"] > 0:
            stats["success_rate"] = (
                self.stats["successful_requests"] / self.stats["total_requests"]
            )
        
        return stats


# Configuration presets
def get_config_preset(provider: str, api_key: str) -> LLMConfig:
    """Get configuration preset for a provider"""
    
    if provider == "openai-gpt4":
        return LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4-turbo-preview",
            api_key=api_key,
            cost_per_1k_input_tokens=0.01,
            cost_per_1k_output_tokens=0.03
        )
    
    elif provider == "anthropic-claude":
        return LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            api_key=api_key,
            cost_per_1k_input_tokens=0.003,
            cost_per_1k_output_tokens=0.015
        )
    
    elif provider == "deepseek":
        return LLMConfig(
            provider=LLMProvider.DEEPSEEK,
            model="deepseek-chat",
            api_key=api_key,
            cost_per_1k_input_tokens=0.0002,  # Very cheap!
            cost_per_1k_output_tokens=0.0006
        )
    
    else:
        raise ValueError(f"Unknown provider preset: {provider}")


# Test functionality
async def test_llm_api_client():
    """Test the LLM API client (requires API key)"""
    print("Testing LLMAPIClient...")
    
    # This is a placeholder test - requires actual API key
    print("⚠️  API testing requires valid API keys")
    print("   Use get_config_preset() to configure")
    print("\nExample usage:")
    print("""
    from llm_api_integration import get_config_preset, LLMAPIClient
    
    config = get_config_preset("deepseek", "your-api-key")
    client = LLMAPIClient(config)
    
    response = await client.call(
        system_prompt="You are a helpful assistant.",
        user_prompt="Say hello!"
    )
    
    print(f"Response: {response.content}")
    print(f"Cost: ${response.cost:.4f}")
    """)


if __name__ == "__main__":
    asyncio.run(test_llm_api_client())
