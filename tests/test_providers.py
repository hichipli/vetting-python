"""
Tests for provider implementations.

Note: These tests focus on provider setup, configuration, and utility methods.
They do not make actual API calls to avoid requiring API keys in tests.
"""

import pytest
from unittest.mock import Mock, patch

from vetting_python.providers import OpenAIProvider, ClaudeProvider, GeminiProvider
from vetting_python.core.models import ModelConfig, Usage


class TestOpenAIProvider:
    """Test the OpenAIProvider class."""
    
    def test_openai_provider_initialization(self):
        """Test OpenAI provider initialization."""
        provider = OpenAIProvider(
            api_key="sk-test123",
            base_url="https://api.openai.com/v1",
            max_retries=3,
            timeout=60
        )
        
        assert provider.api_key == "sk-test123"
        assert provider.base_url == "https://api.openai.com/v1"
        assert provider.max_retries == 3
        assert provider.timeout == 60
        assert "Authorization" in provider.headers
        assert provider.headers["Authorization"] == "Bearer sk-test123"
    
    def test_openai_provider_with_organization(self):
        """Test OpenAI provider with organization ID."""
        provider = OpenAIProvider(
            api_key="sk-test123",
            organization="org-123"
        )
        
        assert provider.headers["OpenAI-Organization"] == "org-123"
    
    def test_openai_model_aliases(self):
        """Test OpenAI model alias resolution."""
        provider = OpenAIProvider(api_key="sk-test123")
        
        aliases = provider.get_model_aliases()
        assert "viable-3" in aliases
        assert aliases["viable-3"] == "gpt-4o-mini"
    
    def test_openai_resolve_model_alias(self):
        """Test resolving model aliases."""
        provider = OpenAIProvider(api_key="sk-test123")
        
        # Test alias resolution
        assert provider._resolve_model_alias("viable-3") == "gpt-4o-mini"
        
        # Test direct model ID
        assert provider._resolve_model_alias("gpt-4") == "gpt-4"
        
        # Test unknown alias
        assert provider._resolve_model_alias("unknown-model") == "unknown-model"
    
    def test_openai_cost_calculation(self):
        """Test OpenAI cost calculation for known models."""
        provider = OpenAIProvider(api_key="sk-test123")
        usage = Usage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        
        # Test known model
        cost = provider.calculate_cost("gpt-4o-mini", usage)
        assert cost > 0
        assert isinstance(cost, float)
        
        # Test alias resolution in cost calculation
        cost_alias = provider.calculate_cost("viable-3", usage)
        assert cost_alias == cost  # Should be same as gpt-4o-mini
    
    def test_openai_cost_calculation_unknown_model(self):
        """Test cost calculation for unknown model (should use default)."""
        provider = OpenAIProvider(api_key="sk-test123")
        usage = Usage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        
        cost = provider.calculate_cost("unknown-model", usage)
        assert cost > 0  # Should use fallback pricing
    
    def test_openai_supported_models(self):
        """Test getting supported models list."""
        provider = OpenAIProvider(api_key="sk-test123")
        models = provider.get_supported_models()
        
        assert "gpt-4o-mini" in models
        assert "gpt-4" in models
        assert "viable-3" in models  # Alias should be included


class TestClaudeProvider:
    """Test the ClaudeProvider class."""
    
    def test_claude_provider_initialization(self):
        """Test Claude provider initialization."""
        provider = ClaudeProvider(
            api_key="sk-ant-test123",
            base_url="https://api.anthropic.com",
            max_retries=3,
            timeout=60
        )
        
        assert provider.api_key == "sk-ant-test123"
        assert provider.base_url == "https://api.anthropic.com"
        assert provider.max_retries == 3
        assert provider.timeout == 60
        assert "x-api-key" in provider.headers
        assert provider.headers["x-api-key"] == "sk-ant-test123"
    
    def test_claude_model_aliases(self):
        """Test Claude model alias resolution."""
        provider = ClaudeProvider(api_key="sk-ant-test123")
        
        aliases = provider.get_model_aliases()
        assert "claude-sonnet" in aliases
        assert aliases["claude-sonnet"] == "claude-3-5-sonnet-20241022"
    
    def test_claude_resolve_model_alias(self):
        """Test resolving Claude model aliases."""
        provider = ClaudeProvider(api_key="sk-ant-test123")
        
        # Test alias resolution
        assert provider._resolve_model_alias("claude-sonnet") == "claude-3-5-sonnet-20241022"
        
        # Test direct model ID
        assert provider._resolve_model_alias("claude-3-haiku-20240307") == "claude-3-haiku-20240307"
    
    def test_claude_cost_calculation(self):
        """Test Claude cost calculation."""
        provider = ClaudeProvider(api_key="sk-ant-test123")
        usage = Usage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        
        cost = provider.calculate_cost("claude-3-haiku-20240307", usage)
        assert cost > 0
        assert isinstance(cost, float)
    
    def test_claude_message_conversion(self):
        """Test Claude message format conversion."""
        provider = ClaudeProvider(api_key="sk-ant-test123")
        
        from vetting_python.core.models import ChatMessage
        messages = [
            ChatMessage("system", "You are helpful"),  # Should be filtered out
            ChatMessage("user", "Hello"),
            ChatMessage("assistant", "Hi there"),
            ChatMessage("user", "How are you?")
        ]
        
        claude_messages = provider._convert_messages_to_claude_format(messages)
        
        # System message should be filtered out
        assert len(claude_messages) == 3
        assert claude_messages[0]["role"] == "user"
        assert claude_messages[0]["content"] == "Hello"
        assert claude_messages[1]["role"] == "assistant"
        assert claude_messages[2]["role"] == "user"
    
    def test_claude_ensure_alternating_pattern(self):
        """Test Claude alternating message pattern enforcement."""
        provider = ClaudeProvider(api_key="sk-ant-test123")
        
        # Test consecutive user messages
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "user", "content": "Are you there?"},
            {"role": "assistant", "content": "Yes, I'm here"}
        ]
        
        result = provider._ensure_alternating_pattern(messages)
        
        # Should merge consecutive user messages
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert "Hello" in result[0]["content"] and "Are you there?" in result[0]["content"]
        assert result[1]["role"] == "assistant"


class TestGeminiProvider:
    """Test the GeminiProvider class."""
    
    def test_gemini_provider_initialization(self):
        """Test Gemini provider initialization."""
        provider = GeminiProvider(
            api_key="test-api-key",
            base_url="https://generativelanguage.googleapis.com",
            max_retries=3,
            timeout=60
        )
        
        assert provider.api_key == "test-api-key"
        assert provider.base_url == "https://generativelanguage.googleapis.com"
        assert provider.max_retries == 3
        assert provider.timeout == 60
    
    def test_gemini_model_aliases(self):
        """Test Gemini model alias resolution."""
        provider = GeminiProvider(api_key="test-key")
        
        aliases = provider.get_model_aliases()
        assert "gemini-pro" in aliases
        assert aliases["gemini-pro"] == "gemini-1.0-pro"
    
    def test_gemini_cost_calculation(self):
        """Test Gemini cost calculation."""
        provider = GeminiProvider(api_key="test-key")
        usage = Usage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        
        cost = provider.calculate_cost("gemini-1.5-flash", usage)
        assert cost > 0
        assert isinstance(cost, float)
    
    def test_gemini_message_conversion(self):
        """Test Gemini message format conversion."""
        provider = GeminiProvider(api_key="test-key")
        
        from vetting_python.core.models import ChatMessage
        messages = [
            ChatMessage("user", "Hello"),
            ChatMessage("assistant", "Hi there"),
            ChatMessage("user", "How are you?")
        ]
        
        gemini_contents = provider._convert_messages_to_gemini_format(messages)
        
        assert len(gemini_contents) == 3
        assert gemini_contents[0]["role"] == "user"
        assert gemini_contents[0]["parts"][0]["text"] == "Hello"
        assert gemini_contents[1]["role"] == "model"  # Gemini uses "model" instead of "assistant"
        assert gemini_contents[2]["role"] == "user"
    
    def test_gemini_message_conversion_with_system_prompt(self):
        """Test Gemini message conversion with system prompt."""
        provider = GeminiProvider(api_key="test-key")
        
        from vetting_python.core.models import ChatMessage
        messages = [
            ChatMessage("user", "Hello")
        ]
        
        gemini_contents = provider._convert_messages_to_gemini_format(
            messages, 
            system_prompt="You are helpful"
        )
        
        # Should add system instruction as first user message
        assert len(gemini_contents) == 2
        assert "System Instructions" in gemini_contents[0]["parts"][0]["text"]
        assert gemini_contents[1]["role"] == "user"
        assert gemini_contents[1]["parts"][0]["text"] == "Hello"


class TestProviderComparison:
    """Test common functionality across providers."""
    
    def test_all_providers_have_required_methods(self):
        """Test that all providers implement required methods."""
        providers = [
            OpenAIProvider(api_key="test"),
            ClaudeProvider(api_key="test"),
            GeminiProvider(api_key="test")
        ]
        
        for provider in providers:
            # Check required methods exist
            assert hasattr(provider, 'generate_response')
            assert hasattr(provider, 'calculate_cost')
            assert hasattr(provider, 'get_model_aliases')
            
            # Check they return expected types
            aliases = provider.get_model_aliases()
            assert isinstance(aliases, dict)
            
            usage = Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
            cost = provider.calculate_cost("test-model", usage)
            assert isinstance(cost, (int, float))
    
    def test_all_providers_cost_calculation_positive(self):
        """Test that all providers return positive costs for valid usage."""
        providers = [
            OpenAIProvider(api_key="test"),
            ClaudeProvider(api_key="test"),
            GeminiProvider(api_key="test")
        ]
        
        usage = Usage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        
        for provider in providers:
            # Use a model that should exist for each provider
            if isinstance(provider, OpenAIProvider):
                model = "gpt-4o-mini"
            elif isinstance(provider, ClaudeProvider):
                model = "claude-3-haiku-20240307"
            else:  # GeminiProvider
                model = "gemini-1.5-flash"
            
            cost = provider.calculate_cost(model, usage)
            assert cost > 0, f"Cost should be positive for {provider.__class__.__name__}"