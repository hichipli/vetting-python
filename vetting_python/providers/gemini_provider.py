"""
Google Gemini provider implementation for the VETTING framework.

This module provides integration with Google's Gemini models through the
Generative AI API, including proper content formatting and cost calculation.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any, Tuple
import json
import aiohttp
from ..core.models import ChatMessage, ModelConfig, Usage, Provider

logger = logging.getLogger(__name__)


class GeminiProvider(Provider):
    """Provider for Google Gemini models."""
    
    # Model pricing per 1M tokens (input, output) as of 2025-07-31
    MODEL_PRICING = {
        "gemini-2.5-pro": (1.25, 10.0),  # <= 200k tokens
        "gemini-2.5-flash": (0.3, 2.5),
        "gemini-2.5-flash-lite": (0.1, 0.4),
        "gemini-2.0-flash": (0.1, 0.4),
        "gemini-2.0-flash-lite": (0.075, 0.3),
    }
    
    # Model aliases
    MODEL_ALIASES = {
        "gemini-2.5": "gemini-2.5-pro",
        "gemini-2.0": "gemini-2.0-flash",
        "gemini-flash": "gemini-2.5-flash",
        "gemini-lite": "gemini-2.5-flash-lite",
    }
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://generativelanguage.googleapis.com",
        max_retries: int = 3,
        timeout: int = 60
    ):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Google AI API key
            base_url: API base URL
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Headers for Gemini API
        self.headers = {
            "Content-Type": "application/json"
        }
    
    async def generate_response(
        self,
        messages: List[ChatMessage],
        model_config: ModelConfig,
        system_prompt: Optional[str] = None
    ) -> Tuple[str, Usage, bool]:
        """
        Generate response using Gemini API.
        
        Args:
            messages: List of chat messages
            model_config: Model configuration
            system_prompt: Optional system prompt
            
        Returns:
            Tuple of (response_content, usage, requires_attention)
        """
        # Resolve model alias
        model_id = self._resolve_model_alias(model_config.model_id)
        
        # Convert messages to Gemini format
        gemini_contents = self._convert_messages_to_gemini_format(messages, system_prompt)
        
        # Prepare request body
        request_body = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": model_config.temperature,
                "maxOutputTokens": model_config.max_tokens,
            }
        }
        
        # Add optional parameters
        if model_config.top_p is not None:
            request_body["generationConfig"]["topP"] = model_config.top_p
            
        # Prepare URL with API key
        url = f"{self.base_url}/v1beta/models/{model_id}:generateContent?key={self.api_key}"
        
        # Make API call with retries
        for attempt in range(self.max_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.post(
                        url,
                        headers=self.headers,
                        json=request_body
                    ) as response:
                        
                        if not response.ok:
                            error_data = await response.json() if response.content_type == 'application/json' else {}
                            error_msg = f"Gemini API error ({response.status}): {error_data.get('error', {}).get('message', response.reason)}"
                            
                            # Handle rate limiting and server errors with retry
                            if (response.status == 429 or response.status >= 500) and attempt < self.max_retries:
                                wait_time = 2 ** attempt
                                logger.warning(f"Retrying Gemini request in {wait_time}s due to: {error_msg}")
                                await asyncio.sleep(wait_time)
                                continue
                            
                            raise Exception(error_msg)
                        
                        # Parse successful response
                        data = await response.json()
                        
                        # Extract content from Gemini response format
                        candidates = data.get("candidates", [])
                        if not candidates:
                            raise Exception("No candidates in Gemini response")
                        
                        # Get the first candidate's content
                        candidate = candidates[0]
                        content_parts = candidate.get("content", {}).get("parts", [])
                        
                        if not content_parts:
                            raise Exception("No content parts in Gemini response")
                        
                        # Combine all text parts
                        content = ""
                        for part in content_parts:
                            if "text" in part:
                                content += part["text"]
                        
                        # Check for safety prefix
                        requires_attention = False
                        safety_prefix = "[REQUIRES_ATTENTION] "
                        if content.startswith(safety_prefix):
                            requires_attention = True
                            content = content[len(safety_prefix):]
                            logger.info("Safety prefix detected and removed from Gemini response")
                        
                        # Extract usage information
                        usage_metadata = data.get("usageMetadata", {})
                        prompt_tokens = usage_metadata.get("promptTokenCount", 0)
                        completion_tokens = usage_metadata.get("candidatesTokenCount", 0)
                        
                        usage = Usage(
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            total_tokens=prompt_tokens + completion_tokens
                        )
                        
                        logger.debug(f"Gemini response generated successfully with {usage.total_tokens} tokens")
                        return content, usage, requires_attention
                        
            except Exception as e:
                if attempt == self.max_retries:
                    logger.error(f"Gemini API failed after {self.max_retries + 1} attempts: {e}")
                    raise Exception(f"Failed to get Gemini response after {self.max_retries + 1} attempts: {str(e)}")
                
                wait_time = 2 ** attempt
                logger.warning(f"Gemini API attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
        
        raise Exception("Unexpected error in Gemini provider")
    
    def _convert_messages_to_gemini_format(
        self, 
        messages: List[ChatMessage], 
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Convert messages to Gemini API format.
        
        Gemini uses a different message format with "contents" array containing
        "role" and "parts" fields.
        """
        contents = []
        
        # Add system prompt as first user message if provided
        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System Instructions: {system_prompt}\n\nNow, please respond to the following:"}]
            })
        
        # Convert messages
        for msg in messages:
            # Map roles: OpenAI uses "assistant", Gemini uses "model"
            role = "model" if msg.role == "assistant" else msg.role
            
            # Skip system messages as they're handled above
            if msg.role == "system":
                continue
            
            contents.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })
        
        # Ensure conversation starts with user message
        if contents and contents[0]["role"] != "user":
            contents.insert(0, {
                "role": "user", 
                "parts": [{"text": "Please continue our conversation."}]
            })
        
        return contents
    
    def calculate_cost(self, model_id: str, usage: Usage) -> float:
        """Calculate cost for Gemini API usage."""
        model_id = self._resolve_model_alias(model_id)
        
        if model_id not in self.MODEL_PRICING:
            logger.warning(f"No pricing data for model {model_id}, using gemini-2.5-flash pricing")
            model_id = "gemini-2.5-flash"
        
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
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": "Hello"}]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": 1
                }
            }
            
            url = f"{self.base_url}/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.post(
                    url,
                    headers=self.headers,
                    json=test_body
                ) as response:
                    return response.status != 401 and response.status != 403
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False