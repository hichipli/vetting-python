"""
Tests for utility functions.
"""

import pytest
from vetting_python.utils.message_utils import MessageUtils
from vetting_python.utils.validation import ValidationUtils, ValidationError
from vetting_python.core.models import ChatMessage, VettingConfig, ModelConfig, Usage


class TestMessageUtils:
    """Test the MessageUtils class."""
    
    def test_from_openai_format(self):
        """Test converting from OpenAI format to ChatMessage objects."""
        openai_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        messages = MessageUtils.from_openai_format(openai_messages)
        
        assert len(messages) == 3
        assert messages[0].role == "system"
        assert messages[0].content == "You are a helpful assistant."
        assert messages[1].role == "user"
        assert messages[1].content == "Hello!"
        assert messages[2].role == "assistant"
        assert messages[2].content == "Hi there!"
    
    def test_to_openai_format(self):
        """Test converting ChatMessage objects to OpenAI format."""
        messages = [
            ChatMessage("system", "You are a helpful assistant."),
            ChatMessage("user", "Hello!"),
            ChatMessage("assistant", "Hi there!")
        ]
        
        openai_format = MessageUtils.to_openai_format(messages)
        
        expected = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        assert openai_format == expected
    
    def test_create_conversation(self):
        """Test creating a conversation from separate message lists."""
        user_messages = ["Hello!", "How are you?", "Goodbye!"]
        assistant_messages = ["Hi there!", "I'm doing well, thanks!"]
        system_prompt = "You are a helpful assistant."
        
        conversation = MessageUtils.create_conversation(
            user_messages, assistant_messages, system_prompt
        )
        
        assert len(conversation) == 6  # 1 system + 3 user + 2 assistant
        assert conversation[0].role == "system"
        assert conversation[0].content == system_prompt
        assert conversation[1].role == "user"
        assert conversation[1].content == "Hello!"
        assert conversation[2].role == "assistant"
        assert conversation[2].content == "Hi there!"
        assert conversation[5].role == "user"
        assert conversation[5].content == "Goodbye!"
    
    def test_extract_system_prompt(self):
        """Test extracting system prompt from messages."""
        messages = [
            ChatMessage("system", "You are a helpful assistant."),
            ChatMessage("user", "Hello!"),
            ChatMessage("assistant", "Hi there!")
        ]
        
        system_prompt = MessageUtils.extract_system_prompt(messages)
        assert system_prompt == "You are a helpful assistant."
        
        # Test with no system message
        messages_no_system = [
            ChatMessage("user", "Hello!"),
            ChatMessage("assistant", "Hi there!")
        ]
        
        system_prompt = MessageUtils.extract_system_prompt(messages_no_system)
        assert system_prompt is None
    
    def test_remove_system_messages(self):
        """Test removing system messages from conversation."""
        messages = [
            ChatMessage("system", "You are a helpful assistant."),
            ChatMessage("user", "Hello!"),
            ChatMessage("system", "Additional instruction."),
            ChatMessage("assistant", "Hi there!")
        ]
        
        filtered = MessageUtils.remove_system_messages(messages)
        
        assert len(filtered) == 2
        assert filtered[0].role == "user"
        assert filtered[1].role == "assistant"
    
    def test_count_tokens_estimate(self):
        """Test token count estimation."""
        messages = [
            ChatMessage("user", "Hello, this is a test message."),
            ChatMessage("assistant", "This is a response.")
        ]
        
        token_count = MessageUtils.count_tokens_estimate(messages)
        
        # Should be roughly (len("Hello, this is a test message.This is a response.") / 4)
        assert token_count > 0
        assert isinstance(token_count, int)
    
    def test_get_conversation_stats(self):
        """Test getting conversation statistics."""
        messages = [
            ChatMessage("system", "System prompt"),
            ChatMessage("user", "Hello there!"),
            ChatMessage("assistant", "Hi! How can I help?"),
            ChatMessage("user", "Tell me about AI.")
        ]
        
        stats = MessageUtils.get_conversation_stats(messages)
        
        assert stats["total_messages"] == 4
        assert stats["role_breakdown"]["system"] == 1
        assert stats["role_breakdown"]["user"] == 2
        assert stats["role_breakdown"]["assistant"] == 1
        assert stats["total_characters"] > 0
        assert stats["total_words"] > 0
        assert stats["estimated_tokens"] > 0
        assert stats["average_message_length"] > 0
    
    def test_validate_conversation(self):
        """Test conversation validation."""
        # Valid conversation
        valid_messages = [
            ChatMessage("user", "Hello!"),
            ChatMessage("assistant", "Hi there!")
        ]
        
        result = MessageUtils.validate_conversation(valid_messages)
        assert result["valid"] is True
        assert len(result["issues"]) == 0
        
        # Empty conversation
        result = MessageUtils.validate_conversation([])
        assert result["valid"] is False
        assert "Conversation is empty" in result["issues"]
        
        # Conversation with empty message
        messages_with_empty = [
            ChatMessage("user", "Hello!"),
            ChatMessage("assistant", "")
        ]
        
        result = MessageUtils.validate_conversation(messages_with_empty)
        assert result["valid"] is False
        assert any("Empty message" in issue for issue in result["issues"])


class TestValidationUtils:
    """Test the ValidationUtils class."""
    
    def test_validate_vetting_config_valid(self):
        """Test validating a valid VettingConfig."""
        config = VettingConfig(
            mode="vetting",
            chat_model=ModelConfig(model_id="gpt-4o-mini", temperature=0.7),
            verification_model=ModelConfig(model_id="gpt-4o-mini", temperature=0.1),
            max_attempts=3
        )
        
        result = ValidationUtils.validate_vetting_config(config)
        assert result["valid"] is True
        assert len(result["issues"]) == 0
    
    def test_validate_vetting_config_invalid_mode(self):
        """Test validating VettingConfig with invalid mode."""
        config = VettingConfig(
            mode="invalid_mode",
            chat_model=ModelConfig(model_id="gpt-4o-mini")
        )
        
        result = ValidationUtils.validate_vetting_config(config)
        assert result["valid"] is False
        assert any("Invalid mode" in issue for issue in result["issues"])
    
    def test_validate_model_config_valid(self):
        """Test validating a valid ModelConfig."""
        config = ModelConfig(
            model_id="gpt-4o-mini",
            temperature=0.7,
            max_tokens=1024
        )
        
        result = ValidationUtils.validate_model_config(config)
        assert result["valid"] is True
        assert len(result["issues"]) == 0
    
    def test_validate_model_config_invalid_temperature(self):
        """Test validating ModelConfig with invalid temperature."""
        config = ModelConfig(
            model_id="gpt-4o-mini",
            temperature=3.0,  # Invalid - should be <= 2.0
            max_tokens=1024
        )
        
        result = ValidationUtils.validate_model_config(config)
        assert result["valid"] is False
        assert any("Temperature" in issue for issue in result["issues"])
    
    def test_validate_model_config_invalid_max_tokens(self):
        """Test validating ModelConfig with invalid max_tokens."""
        config = ModelConfig(
            model_id="gpt-4o-mini",
            temperature=0.7,
            max_tokens=0  # Invalid - should be > 0
        )
        
        result = ValidationUtils.validate_model_config(config)
        assert result["valid"] is False
        assert any("Max tokens" in issue for issue in result["issues"])
    
    def test_validate_messages_valid(self):
        """Test validating valid messages."""
        messages = [
            ChatMessage("user", "Hello!"),
            ChatMessage("assistant", "Hi there!")
        ]
        
        result = ValidationUtils.validate_messages(messages)
        assert result["valid"] is True
        assert len(result["issues"]) == 0
    
    def test_validate_messages_empty(self):
        """Test validating empty message list."""
        result = ValidationUtils.validate_messages([])
        assert result["valid"] is False
        assert "Message list cannot be empty" in result["issues"]
    
    def test_validate_messages_invalid_role(self):
        """Test validating messages with invalid role."""
        messages = [
            ChatMessage("invalid_role", "Hello!")
        ]
        
        result = ValidationUtils.validate_messages(messages)
        assert result["valid"] is False
        assert any("Invalid role" in issue for issue in result["issues"])
    
    def test_validate_api_key_openai_valid(self):
        """Test validating valid OpenAI API key format."""
        result = ValidationUtils.validate_api_key("sk-1234567890abcdef", "openai")
        assert result["valid"] is True
        assert len(result["issues"]) == 0
    
    def test_validate_api_key_openai_invalid_format(self):
        """Test validating OpenAI API key with invalid format."""
        result = ValidationUtils.validate_api_key("invalid-key", "openai")
        assert result["valid"] is True  # Still valid, just warnings
        assert len(result["warnings"]) > 0
        assert any("typically start with 'sk-'" in warning for warning in result["warnings"])
    
    def test_validate_api_key_empty(self):
        """Test validating empty API key."""
        result = ValidationUtils.validate_api_key("", "openai")
        assert result["valid"] is False
        assert "API key cannot be empty" in result["issues"]
    
    def test_validate_api_key_too_short(self):
        """Test validating API key that's too short."""
        result = ValidationUtils.validate_api_key("short", "openai")
        assert result["valid"] is False
        assert "API key is too short" in result["issues"]
    
    def test_validate_usage_valid(self):
        """Test validating valid Usage object."""
        usage = Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        
        result = ValidationUtils.validate_usage(usage)
        assert result["valid"] is True
        assert len(result["issues"]) == 0
    
    def test_validate_usage_negative_tokens(self):
        """Test validating Usage with negative tokens."""
        usage = Usage(prompt_tokens=-10, completion_tokens=50, total_tokens=40)
        
        result = ValidationUtils.validate_usage(usage)
        assert result["valid"] is False
        assert "Prompt tokens cannot be negative" in result["issues"]
    
    def test_validate_usage_mismatched_total(self):
        """Test validating Usage with mismatched total."""
        usage = Usage(prompt_tokens=100, completion_tokens=50, total_tokens=200)  # Should be 150
        
        result = ValidationUtils.validate_usage(usage)
        assert result["valid"] is True  # Valid but with warning
        assert len(result["warnings"]) > 0
        assert any("doesn't match sum" in warning for warning in result["warnings"])
    
    def test_validate_and_raise_valid(self):
        """Test validate_and_raise with valid result."""
        result = {"valid": True, "issues": [], "warnings": []}
        
        # Should not raise an exception
        ValidationUtils.validate_and_raise(result, "test context")
    
    def test_validate_and_raise_invalid(self):
        """Test validate_and_raise with invalid result."""
        result = {"valid": False, "issues": ["Test error"], "warnings": []}
        
        with pytest.raises(ValidationError, match="Validation failed.*test context.*Test error"):
            ValidationUtils.validate_and_raise(result, "test context")