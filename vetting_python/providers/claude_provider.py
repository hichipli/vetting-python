"""
Anthropic Claude provider implementation for the VETTING framework.

This module provides integration with Anthropic's Claude models, including proper
message formatting and cost calculation.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any, Tuple
import json
import aiohttp
from ..core.models import ChatMessage, ModelConfig, Usage, Provider

logger = logging.getLogger(__name__)


class ClaudeProvider(Provider):
    """Provider for Anthropic Claude models."""
    
    # Model pricing per 1M tokens (input, output) as of 2025-07-31
    MODEL_PRICING = {
        "claude-sonnet-4": (3.0, 15.0),
        "claude-sonnet-3.7": (3.0, 15.0),
        "claude-sonnet-3.5": (3.0, 15.0),
    }
    
    # Model aliases
    MODEL_ALIASES = {
        "claude-4": "claude-sonnet-4",
        "claude-3.7": "claude-sonnet-3.7",
        "claude-3.5": "claude-sonnet-3.5",
        "claude-sonnet": "claude-sonnet-4",
    }
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
        max_retries: int = 3,
        timeout: int = 60,
        anthropic_version: str = "2023-06-01"
    ):
        """
        Initialize Claude provider.
        
        Args:
            api_key: Anthropic API key
            base_url: API base URL
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            anthropic_version: API version to use
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.timeout = timeout
        self.anthropic_version = anthropic_version
        
        # Setup headers
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": anthropic_version
        }
    
    async def generate_response(
        self,
        messages: List[ChatMessage],
        model_config: ModelConfig,
        system_prompt: Optional[str] = None
    ) -> Tuple[str, Usage, bool]:
        """
        Generate response using Claude API.
        
        Args:
            messages: List of chat messages
            model_config: Model configuration
            system_prompt: Optional system prompt
            
        Returns:
            Tuple of (response_content, usage, requires_attention)
        """
        # Resolve model alias
        model_id = self._resolve_model_alias(model_config.model_id)
        
        # Convert messages to Claude format
        claude_messages = self._convert_messages_to_claude_format(messages)
        
        # Prepare request body
        request_body = {
            "model": model_id,
            "messages": claude_messages,
            "max_tokens": model_config.max_tokens,
            "temperature": model_config.temperature,
        }
        
        # Add system prompt if provided
        if system_prompt:
            request_body["system"] = system_prompt
        
        # Add optional parameters
        if model_config.top_p is not None:
            request_body["top_p"] = model_config.top_p
        
        # Make API call with retries
        for attempt in range(self.max_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.post(
                        f"{self.base_url}/v1/messages",
                        headers=self.headers,
                        json=request_body
                    ) as response:
                        
                        if not response.ok:
                            error_data = await response.json() if response.content_type == 'application/json' else {}
                            error_msg = f"Claude API error ({response.status}): {error_data.get('error', {}).get('message', response.reason)}"
                            
                            # Handle rate limiting and server errors with retry
                            if (response.status == 429 or response.status >= 500) and attempt < self.max_retries:
                                wait_time = 2 ** attempt
                                logger.warning(f"Retrying Claude request in {wait_time}s due to: {error_msg}")
                                await asyncio.sleep(wait_time)
                                continue
                            
                            raise Exception(error_msg)
                        
                        # Parse successful response
                        data = await response.json()
                        
                        # Extract content from Claude response format
                        content_blocks = data.get("content", [])
                        if not content_blocks:
                            raise Exception("No content in Claude response")
                        
                        # Combine all text content blocks
                        content = ""
                        for block in content_blocks:
                            if block.get("type") == "text":
                                content += block.get("text", "")
                        
                        # Check for safety prefix
                        requires_attention = False
                        safety_prefix = "[REQUIRES_ATTENTION] "
                        if content.startswith(safety_prefix):
                            requires_attention = True
                            content = content[len(safety_prefix):]
                            logger.info("Safety prefix detected and removed from Claude response")
                        
                        # Extract usage information
                        usage_data = data.get("usage", {})
                        usage = Usage(
                            prompt_tokens=usage_data.get("input_tokens", 0),
                            completion_tokens=usage_data.get("output_tokens", 0),
                            total_tokens=usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0)
                        )
                        
                        logger.debug(f"Claude response generated successfully with {usage.total_tokens} tokens")
                        return content, usage, requires_attention
                        
            except Exception as e:
                if attempt == self.max_retries:
                    logger.error(f"Claude API failed after {self.max_retries + 1} attempts: {e}")
                    raise Exception(f"Failed to get Claude response after {self.max_retries + 1} attempts: {str(e)}")
                
                wait_time = 2 ** attempt
                logger.warning(f"Claude API attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
        
        raise Exception("Unexpected error in Claude provider")
    
    def _convert_messages_to_claude_format(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """
        Convert messages to Claude API format.
        
        Claude requires alternating user/assistant messages and doesn't support system messages
        in the messages array (they go in the system parameter).
        """
        claude_messages = []
        
        for msg in messages:
            if msg.role == "system":
                # Skip system messages - they should be handled in the system parameter
                continue
            elif msg.role in ["user", "assistant"]:
                claude_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Ensure alternating user/assistant pattern
        return self._ensure_alternating_pattern(claude_messages)
    
    def _ensure_alternating_pattern(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Ensure messages alternate between user and assistant.
        Claude API requires this pattern.
        """
        if not messages:
            return messages
        
        result = []
        last_role = None
        
        for msg in messages:
            if msg["role"] == last_role:
                # Same role as previous - merge content
                if result:
                    result[-1]["content"] += "\n\n" + msg["content"]
                else:
                    result.append(msg)
            else:
                result.append(msg)
                last_role = msg["role"]
        
        # Ensure first message is from user
        if result and result[0]["role"] != "user":
            result.insert(0, {"role": "user", "content": "Please continue our conversation."})
        
        return result
    
    def calculate_cost(self, model_id: str, usage: Usage) -> float:
        """Calculate cost for Claude API usage."""
        model_id = self._resolve_model_alias(model_id)
        
        if model_id not in self.MODEL_PRICING:
            logger.warning(f"No pricing data for model {model_id}, using claude-sonnet-3.5 pricing")
            model_id = "claude-sonnet-3.5"
        
        input_price, output_price = self.MODEL_PRICING[model_id]
        
        # Calculate cost per 1M tokens
        input_cost = (usage.prompt_tokens / 1000000) * input_price
        output_cost = (usage.completion_tokens / 1000000) * output_price
        
        return input_cost + output_cost
    
    def get_model_aliases(self) -> Dict[str, str]:
        """Get mapping of model aliases to actual model IDs."""
        return self.MODEL_ALIASES.copy()
    
    def _resolve_model_alias(self, model_id: str) -> str:
        """Resolve model alias to actual model ID."""
        return self.MODEL_ALIASES.get(model_id, model_id)
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported model IDs (including aliases)."""
        return list(self.MODEL_PRICING.keys()) + list(self.MODEL_ALIASES.keys())
    
    async def validate_api_key(self) -> bool:
        """Validate the API key by making a test request."""
        try:
            # Make a minimal test request
            test_body = {
                "model": "claude-3-haiku-20240307",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 1
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.post(
                    f"{self.base_url}/v1/messages",
                    headers=self.headers,
                    json=test_body
                ) as response:
                    return response.status != 401
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False