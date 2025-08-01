"""
Tests for configuration system.
"""

import os
import tempfile
import json
from unittest.mock import patch
import pytest

from vetting_python.config.settings import VettingSettings, ProviderConfig
from vetting_python.config.builder import VettingConfigBuilder, quick_chat_config, quick_vetting_config
from vetting_python.core.models import ModelConfig


class TestProviderConfig:
    """Test the ProviderConfig class."""
    
    def test_provider_config_creation(self):
        """Test creating a ProviderConfig."""
        config = ProviderConfig(
            provider_type="openai",
            api_key="sk-test123",
            base_url="https://api.openai.com/v1",
            timeout=60
        )
        
        assert config.provider_type == "openai"
        assert config.api_key == "sk-test123"
        assert config.base_url == "https://api.openai.com/v1"
        assert config.timeout == 60
    
    def test_provider_config_validation_valid(self):
        """Test ProviderConfig validation with valid data."""
        config = ProviderConfig(
            provider_type="openai",
            api_key="sk-test123"
        )
        assert config.validate() is True
    
    def test_provider_config_validation_no_api_key(self):
        """Test ProviderConfig validation with missing API key."""
        config = ProviderConfig(
            provider_type="openai",
            api_key=""
        )
        assert config.validate() is False
    
    def test_provider_config_validation_invalid_type(self):
        """Test ProviderConfig validation with invalid provider type."""
        config = ProviderConfig(
            provider_type="invalid",
            api_key="test-key"
        )
        assert config.validate() is False


class TestVettingSettings:
    """Test the VettingSettings class."""
    
    def test_settings_creation(self):
        """Test creating VettingSettings."""
        settings = VettingSettings()
        assert settings.default_chat_model == "gpt-4o-mini"
        assert settings.default_verification_model == "gpt-4o-mini"
        assert settings.default_provider == "openai"
        assert settings.enable_safety_prefix is True
    
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'sk-test123',
        'VETTING_DEFAULT_CHAT_MODEL': 'gpt-4',
        'VETTING_ENABLE_SAFETY_PREFIX': 'false'
    })
    def test_settings_from_env(self):
        """Test loading settings from environment variables."""
        settings = VettingSettings.from_env()
        
        assert "openai" in settings.providers
        assert settings.providers["openai"].api_key == "sk-test123"
        assert settings.default_chat_model == "gpt-4"
        assert settings.enable_safety_prefix is False
    
    def test_settings_from_dict(self):
        """Test loading settings from dictionary."""
        config_dict = {
            "providers": {
                "openai": {
                    "provider_type": "openai",
                    "api_key": "sk-test123",
                    "timeout": 30
                }
            },
            "default_chat_model": "gpt-3.5-turbo",
            "enable_cost_tracking": False
        }
        
        settings = VettingSettings.from_dict(config_dict)
        
        assert "openai" in settings.providers
        assert settings.providers["openai"].api_key == "sk-test123"
        assert settings.providers["openai"].timeout == 30
        assert settings.default_chat_model == "gpt-3.5-turbo"
        assert settings.enable_cost_tracking is False
    
    def test_settings_from_file_json(self):
        """Test loading settings from JSON file."""
        config_data = {
            "providers": {
                "openai": {
                    "provider_type": "openai",
                    "api_key": "sk-test123"
                }
            },
            "default_provider": "openai"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            settings = VettingSettings.from_file(f.name)
            assert "openai" in settings.providers
            assert settings.default_provider == "openai"
            
            os.unlink(f.name)
    
    def test_settings_validation_valid(self):
        """Test settings validation with valid configuration."""
        settings = VettingSettings()
        settings.providers["openai"] = ProviderConfig(
            provider_type="openai",
            api_key="sk-test123"
        )
        
        assert settings.validate() is True
    
    def test_settings_validation_no_providers(self):
        """Test settings validation with no providers."""
        settings = VettingSettings()
        settings.providers = {}
        
        assert settings.validate() is False
    
    def test_settings_to_dict(self):
        """Test converting settings to dictionary."""
        settings = VettingSettings()
        settings.providers["openai"] = ProviderConfig(
            provider_type="openai",
            api_key="sk-test123"
        )
        
        settings_dict = settings.to_dict()
        
        assert "providers" in settings_dict
        assert "openai" in settings_dict["providers"]
        assert settings_dict["providers"]["openai"]["api_key"] == "sk-test123"
        assert settings_dict["default_chat_model"] == "gpt-4o-mini"
    
    def test_create_default_vetting_config(self):
        """Test creating default VettingConfig from settings."""
        settings = VettingSettings()
        settings.providers["openai"] = ProviderConfig(
            provider_type="openai",
            api_key="sk-test123"
        )
        
        config = settings.create_default_vetting_config(mode="chat")
        
        assert config.mode == "chat"
        assert config.chat_model.model_id == "gpt-4o-mini"
        assert config.verification_model is None


class TestVettingConfigBuilder:
    """Test the VettingConfigBuilder class."""
    
    def test_builder_chat_mode(self):
        """Test building a chat mode configuration."""
        config = (VettingConfigBuilder()
                  .chat_mode()
                  .chat_model("gpt-4", temperature=0.8, max_tokens=2000)
                  .build())
        
        assert config.mode == "chat"
        assert config.chat_model.model_id == "gpt-4"
        assert config.chat_model.temperature == 0.8
        assert config.chat_model.max_tokens == 2000
        assert config.verification_model is None
    
    def test_builder_vetting_mode(self):
        """Test building a vetting mode configuration."""
        config = (VettingConfigBuilder()
                  .vetting_mode()
                  .chat_model("gpt-4o-mini")
                  .verification_model("gpt-4o-mini", temperature=0.1)
                  .max_attempts(2)
                  .build())
        
        assert config.mode == "vetting"
        assert config.chat_model.model_id == "gpt-4o-mini"
        assert config.verification_model.model_id == "gpt-4o-mini"
        assert config.verification_model.temperature == 0.1
        assert config.max_attempts == 2
    
    def test_builder_context_items(self):
        """Test adding context items with builder."""
        config = (VettingConfigBuilder()
                  .vetting_mode()
                  .chat_model("gpt-4o-mini")
                  .add_context_item(
                      question_text="What is 2+2?",
                      question_id="math_001", 
                      correct_answer="4",
                      key_concepts=["addition", "arithmetic"]
                  )
                  .add_context_item(
                      question_text="What is the capital of France?",
                      correct_answer="Paris"
                  )
                  .build())
        
        assert len(config.context_items) == 2
        assert config.context_items[0].question["text"] == "What is 2+2?"
        assert config.context_items[0].question["id"] == "math_001"
        assert config.context_items[0].answer_key["correctAnswer"] == "4"
        assert config.context_items[1].question["text"] == "What is the capital of France?"
    
    def test_builder_session_info(self):
        """Test setting session info with builder."""
        config = (VettingConfigBuilder()
                  .chat_mode()
                  .chat_model("gpt-4o-mini")
                  .session_info(session_id="session_123", user_id="user_456")
                  .build())
        
        assert config.session_id == "session_123"
        assert config.user_id == "user_456"
    
    def test_builder_safety_features(self):
        """Test configuring safety features with builder."""
        config = (VettingConfigBuilder()
                  .chat_mode()
                  .chat_model("gpt-4o-mini")
                  .safety_features(enable_safety_prefix=False, enable_educational_rules=False)
                  .build())
        
        assert config.enable_safety_prefix is False
        assert config.enable_educational_rules is False


class TestQuickConfigFunctions:
    """Test the quick configuration helper functions."""
    
    def test_quick_chat_config(self):
        """Test quick_chat_config function."""
        config = quick_chat_config(
            model_id="gpt-4",
            temperature=0.8,
            max_tokens=2000
        )
        
        assert config.mode == "chat"
        assert config.chat_model.model_id == "gpt-4"
        assert config.chat_model.temperature == 0.8
        assert config.chat_model.max_tokens == 2000
    
    def test_quick_vetting_config(self):
        """Test quick_vetting_config function."""
        config = quick_vetting_config(
            chat_model_id="gpt-4o-mini",
            verification_model_id="gpt-4o-mini",
            max_attempts=2
        )
        
        assert config.mode == "vetting"
        assert config.chat_model.model_id == "gpt-4o-mini"
        assert config.verification_model.model_id == "gpt-4o-mini"
        assert config.max_attempts == 2
    
    def test_quick_vetting_config_default_verification(self):
        """Test quick_vetting_config with default verification model."""
        config = quick_vetting_config(chat_model_id="gpt-4")
        
        assert config.mode == "vetting"
        assert config.chat_model.model_id == "gpt-4"
        # Should auto-create verification model same as chat
        assert config.verification_model.model_id == "gpt-4"
        assert config.verification_model.temperature == 0.1  # Default verification temp