"""
Tests for core models and data structures.
"""

import pytest
from vetting_python.core.models import (
    Usage, ModelConfig, ChatMessage, VettingConfig, 
    ContextItem, StopReason
)


class TestUsage:
    """Test the Usage class."""
    
    def test_usage_creation(self):
        """Test creating a Usage object."""
        usage = Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
    
    def test_usage_addition(self):
        """Test adding two Usage objects."""
        usage1 = Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        usage2 = Usage(prompt_tokens=200, completion_tokens=75, total_tokens=275)
        
        total = usage1 + usage2
        assert total.prompt_tokens == 300
        assert total.completion_tokens == 125
        assert total.total_tokens == 425


class TestModelConfig:
    """Test the ModelConfig class."""
    
    def test_model_config_creation(self):
        """Test creating a ModelConfig object."""
        config = ModelConfig(
            model_id="gpt-4o-mini",
            temperature=0.7,
            max_tokens=1024
        )
        assert config.model_id == "gpt-4o-mini"
        assert config.temperature == 0.7
        assert config.max_tokens == 1024
    
    def test_model_config_to_dict(self):
        """Test converting ModelConfig to dictionary."""
        config = ModelConfig(
            model_id="gpt-4o-mini",
            temperature=0.7,
            max_tokens=1024,
            top_p=0.9
        )
        
        config_dict = config.to_dict()
        expected = {
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 1024,
            "top_p": 0.9
        }
        assert config_dict == expected


class TestChatMessage:
    """Test the ChatMessage class."""
    
    def test_chat_message_creation(self):
        """Test creating a ChatMessage object."""
        message = ChatMessage("user", "Hello, world!")
        assert message.role == "user"
        assert message.content == "Hello, world!"
        assert message.metadata is None
    
    def test_chat_message_with_metadata(self):
        """Test creating a ChatMessage with metadata."""
        metadata = {"timestamp": "2024-01-01T00:00:00Z"}
        message = ChatMessage("user", "Hello!", metadata=metadata)
        assert message.metadata == metadata
    
    def test_chat_message_to_dict(self):
        """Test converting ChatMessage to dictionary."""
        message = ChatMessage("assistant", "Hello there!")
        message_dict = message.to_dict()
        expected = {"role": "assistant", "content": "Hello there!"}
        assert message_dict == expected


class TestContextItem:
    """Test the ContextItem class."""
    
    def test_context_item_creation(self):
        """Test creating a ContextItem object."""
        question = {"text": "What is 2+2?", "id": "math_001"}
        answer_key = {"correctAnswer": "4", "keyConcepts": ["addition", "arithmetic"]}
        
        item = ContextItem(question=question, answer_key=answer_key)
        assert item.question == question
        assert item.answer_key == answer_key
    
    def test_context_item_validation_valid(self):
        """Test ContextItem validation with valid data."""
        question = {"text": "What is the capital of France?"}
        item = ContextItem(question=question)
        # Should not raise an exception
        assert item.question == question
    
    def test_context_item_validation_invalid(self):
        """Test ContextItem validation with invalid data."""
        with pytest.raises(ValueError, match="Context item question must be a dict with 'text' field"):
            ContextItem(question={"invalid": "no text field"})
        
        with pytest.raises(ValueError, match="Context item question must be a dict with 'text' field"):
            ContextItem(question="not a dict")


class TestVettingConfig:
    """Test the VettingConfig class."""
    
    def test_vetting_config_chat_mode(self):
        """Test creating a VettingConfig for chat mode."""
        chat_model = ModelConfig(model_id="gpt-4o-mini")
        config = VettingConfig(
            mode="chat",
            chat_model=chat_model
        )
        
        assert config.mode == "chat"
        assert config.chat_model == chat_model
        assert config.verification_model is None
    
    def test_vetting_config_vetting_mode(self):
        """Test creating a VettingConfig for vetting mode."""
        chat_model = ModelConfig(model_id="gpt-4o-mini")
        verification_model = ModelConfig(model_id="gpt-4o-mini", temperature=0.1)
        
        config = VettingConfig(
            mode="vetting",
            chat_model=chat_model,
            verification_model=verification_model
        )
        
        assert config.mode == "vetting"
        assert config.chat_model == chat_model
        assert config.verification_model == verification_model
    
    def test_vetting_config_auto_verification_model(self):
        """Test that VettingConfig auto-creates verification model in vetting mode."""
        chat_model = ModelConfig(model_id="gpt-4o-mini", temperature=0.7)
        config = VettingConfig(
            mode="vetting",
            chat_model=chat_model
        )
        
        # Should auto-create verification model
        assert config.verification_model is not None
        assert config.verification_model.model_id == "gpt-4o-mini"
        assert config.verification_model.temperature == 0.1  # Lower for verification
        assert config.verification_model.max_tokens == 512   # Fewer tokens for verification


class TestStopReason:
    """Test the StopReason enum."""
    
    def test_stop_reason_values(self):
        """Test StopReason enum values."""
        assert StopReason.VERIFICATION_PASSED.value == "VERIFICATION_PASSED"
        assert StopReason.MAX_ATTEMPTS_REACHED.value == "MAX_ATTEMPTS_REACHED"
        assert StopReason.SAFETY_TRIGGERED.value == "SAFETY_TRIGGERED"
        assert StopReason.GENERATION_ERROR.value == "GENERATION_ERROR"
        assert StopReason.VERIFICATION_ERROR.value == "VERIFICATION_ERROR"
        assert StopReason.NOT_APPLICABLE_CHAT_MODE.value == "NOT_APPLICABLE_CHAT_MODE"