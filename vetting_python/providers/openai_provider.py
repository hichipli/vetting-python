"""
OpenAI provider implementation for the VETTING framework.

This module provides integration with OpenAI's GPT models, including cost calculation
and proper handling of the safety prefix system.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any, Tuple
import json
import aiohttp
from ..core.models import ChatMessage, ModelConfig, Usage, Provider

logger = logging.getLogger(__name__)


class OpenAIProvider(Provider):
    """Provider for OpenAI GPT models."""
    
    # Model pricing per 1M tokens (input, output) as of 2025-07-31
    MODEL_PRICING = {
        "gpt-4.1": (2.0, 8.0),
        "gpt-4.1-2025-04-14": (2.0, 8.0),
        "gpt-4.1-mini": (0.4, 1.6),
        "gpt-4.1-mini-2025-04-14": (0.4, 1.6),
        "gpt-4.1-nano": (0.1, 0.4),
        "gpt-4.1-nano-2025-04-14": (0.1, 0.4),
        "gpt-4o": (2.5, 10.0),
        "gpt-4o-2024-08-06": (2.5, 10.0),
        "gpt-4o-mini": (0.15, 0.6),
        "gpt-4o-mini-2024-07-18": (0.15, 0.6),
    }
    
    # Model aliases
    MODEL_ALIASES = {
        "gpt-4o-latest": "gpt-4o",
        "gpt-3.5": "gpt-3.5-turbo",
    }
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        max_retries: int = 3,
        timeout: int = 60,
        organization: Optional[str] = None
    ):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            base_url: API base URL (for custom endpoints)
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            organization: OpenAI organization ID (optional)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.timeout = timeout
        self.organization = organization
        
        # Setup headers
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        if organization:
            self.headers["OpenAI-Organization"] = organization
    
    async def generate_response(
        self,
        messages: List[ChatMessage],
        model_config: ModelConfig,
        system_prompt: Optional[str] = None
    ) -> Tuple[str, Usage, bool]:
        """
        Generate response using OpenAI API.
        
        Args:
            messages: List of chat messages
            model_config: Model configuration
            system_prompt: Optional system prompt to prepend
            
        Returns:
            Tuple of (response_content, usage, requires_attention)
        """
        # Resolve model alias
        model_id = self._resolve_model_alias(model_config.model_id)
        
        # Prepare messages for API
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation messages
        api_messages.extend([msg.to_dict() for msg in messages])
        
        # Prepare request body
        request_body = {
            "model": model_id,
            "messages": api_messages,
            **model_config.to_dict()
        }
        # Remove the model key since we already set it above
        request_body.pop("model", None)
        request_body["model"] = model_id
        
        # Make API call with retries
        for attempt in range(self.max_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.post(
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json=request_body
                    ) as response:
                        
                        if not response.ok:
                            error_data = await response.json() if response.content_type == 'application/json' else {}
                            error_msg = f"OpenAI API error ({response.status}): {error_data.get('error', {}).get('message', response.reason)}"
                            
                            # Handle specific error cases
                            if response.status == 400 and error_data.get('error', {}).get('code') == 'context_length_exceeded':
                                # Try to truncate context and retry
                                if len(api_messages) > 10 and attempt < self.max_retries:
                                    logger.warning(f"Context length exceeded, truncating messages for retry {attempt + 1}")
                                    # Remove older messages but keep system prompt
                                    system_messages = [msg for msg in api_messages if msg["role"] == "system"]
                                    other_messages = [msg for msg in api_messages if msg["role"] != "system"]
                                    if len(other_messages) > 10:
                                        api_messages = system_messages + other_messages[-10:]  # Keep last 10 non-system messages
                                        request_body["messages"] = api_messages
                                        await asyncio.sleep(0.25)
                                        continue
                            
                            # For 5xx errors or 429, retry with backoff
                            if (response.status >= 500 or response.status == 429) and attempt < self.max_retries:
                                wait_time = 2 ** attempt
                                logger.warning(f"Retrying OpenAI request in {wait_time}s due to: {error_msg}")
                                await asyncio.sleep(wait_time)
                                continue
                            
                            raise Exception(error_msg)
                        
                        # Parse successful response
                        data = await response.json()
                        
                        # Extract content and check for safety prefix
                        content = data["choices"][0]["message"]["content"]
                        requires_attention = False
                        
                        safety_prefix = "[REQUIRES_ATTENTION] "
                        if content.startswith(safety_prefix):
                            requires_attention = True
                            content = content[len(safety_prefix):]
                            logger.info("Safety prefix detected and removed from OpenAI response")
                        
                        # Extract usage information
                        usage_data = data.get("usage", {})
                        usage = Usage(
                            prompt_tokens=usage_data.get("prompt_tokens", 0),
                            completion_tokens=usage_data.get("completion_tokens", 0),
                            total_tokens=usage_data.get("total_tokens", 0)
                        )
                        
                        logger.debug(f"OpenAI response generated successfully with {usage.total_tokens} tokens")
                        return content, usage, requires_attention
                        
            except Exception as e:
                if attempt == self.max_retries:
                    logger.error(f"OpenAI API failed after {self.max_retries + 1} attempts: {e}")
                    raise Exception(f"Failed to get OpenAI response after {self.max_retries + 1} attempts: {str(e)}")
                
                wait_time = 2 ** attempt
                logger.warning(f"OpenAI API attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
        
        raise Exception("Unexpected error in OpenAI provider")
    
    def calculate_cost(self, model_id: str, usage: Usage) -> float:
        """Calculate cost for OpenAI API usage."""
        model_id = self._resolve_model_alias(model_id)
        
        if model_id not in self.MODEL_PRICING:
            logger.warning(f"No pricing data for model {model_id}, using gpt-4o-mini pricing")
            model_id = "gpt-4o-mini"
        
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
            test_messages = [{"role": "user", "content": "Hello"}]
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": test_messages,
                        "max_tokens": 1
                    }
                ) as response:
                    return response.status != 401
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False