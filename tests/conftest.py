"""
Pytest configuration and shared fixtures for VETTING framework tests.
"""

import pytest
import os
from unittest.mock import Mock, patch
from typing import Dict, Any

from vetting_python.core.models import (
    ChatMessage, ModelConfig, VettingConfig, Usage, 
    VettingResponse, ContextItem
)
from vetting_python.config.settings import VettingSettings, ProviderConfig
from vetting_python.providers import OpenAIProvider


@pytest.fixture
def sample_usage():
    """Fixture providing a sample Usage object."""
    return Usage(
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150
    )


@pytest.fixture
def sample_chat_messages():
    """Fixture providing sample chat messages."""
    return [
        ChatMessage("system", "You are a helpful assistant."),
        ChatMessage("user", "Hello, how are you?"),
        ChatMessage("assistant", "I'm doing well, thank you! How can I help you today?"),
        ChatMessage("user", "Can you explain photosynthesis?")
    ]


@pytest.fixture
def sample_model_config():
    """Fixture providing a sample ModelConfig."""
    return ModelConfig(
        model_id="gpt-4o-mini",
        temperature=0.7,
        max_tokens=1024,
        top_p=0.9
    )


@pytest.fixture
def sample_vetting_config(sample_model_config):
    """Fixture providing a sample VettingConfig."""
    return VettingConfig(
        mode="vetting",
        chat_model=sample_model_config,
        verification_model=ModelConfig(
            model_id="gpt-4o-mini",
            temperature=0.1,
            max_tokens=512
        ),
        max_attempts=3,
        enable_safety_prefix=True,
        enable_educational_rules=True
    )


@pytest.fixture
def sample_context_item():
    """Fixture providing a sample ContextItem."""
    return ContextItem(
        question={
            "text": "What is the capital of France?",
            "id": "geo_001",
            "subject": "Geography"
        },
        answer_key={
            "correctAnswer": "Paris",
            "keyConcepts": ["Paris", "France", "capital city"],
            "explanation": "Paris is the capital and largest city of France."
        }
    )


@pytest.fixture
def sample_vetting_response(sample_usage):
    """Fixture providing a sample VettingResponse."""
    return VettingResponse(
        content="I'd be happy to help you learn about that topic! Instead of giving you the direct answer, let me ask you what you already know about French geography?",
        mode="vetting",
        requires_attention=False,
        verification_passed=True,
        attempt_count=1,
        chat_usage=sample_usage,
        verification_usage=Usage(prompt_tokens=50, completion_tokens=25, total_tokens=75),
        total_cost=0.0012,
        processing_time_ms=1500.0,
        chat_model_used="gpt-4o-mini",
        verification_model_used="gpt-4o-mini"
    )


@pytest.fixture
def sample_provider_config():
    """Fixture providing a sample ProviderConfig."""
    return ProviderConfig(
        provider_type="openai",
        api_key="sk-test123456789",
        base_url="https://api.openai.com/v1",
        timeout=60,
        max_retries=3
    )


@pytest.fixture
def sample_vetting_settings(sample_provider_config):
    """Fixture providing a sample VettingSettings."""
    settings = VettingSettings()
    settings.providers["openai"] = sample_provider_config
    settings.default_provider = "openai"
    return settings


@pytest.fixture
def mock_openai_provider():
    """Fixture providing a mock OpenAI provider."""
    provider = Mock(spec=OpenAIProvider)
    provider.api_key = "sk-test123"
    provider.base_url = "https://api.openai.com/v1"
    
    # Mock methods
    async def mock_generate_response(messages, model_config, system_prompt=None):
        return "Mock response", Usage(100, 50, 150), False
    
    provider.generate_response = mock_generate_response
    provider.calculate_cost = Mock(return_value=0.0015)
    provider.get_model_aliases = Mock(return_value={"viable-3": "gpt-4o-mini"})
    
    return provider


@pytest.fixture
def mock_successful_api_response():
    """Fixture providing a mock successful API response."""
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "This is a mock response from the API."
                }
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }


@pytest.fixture
def mock_error_api_response():
    """Fixture providing a mock error API response."""
    return {
        "error": {
            "message": "API key is invalid",
            "type": "invalid_request_error",
            "code": "invalid_api_key"
        }
    }


@pytest.fixture
def temp_config_file(tmp_path):
    """Fixture providing a temporary configuration file."""
    config_data = {
        "providers": {
            "openai": {
                "provider_type": "openai",
                "api_key": "sk-test123",
                "timeout": 60,
                "max_retries": 3
            }
        },
        "default_provider": "openai",
        "default_chat_model": "gpt-4o-mini",
        "enable_safety_prefix": True
    }
    
    config_file = tmp_path / "test_config.json"
    config_file.write_text(str(config_data).replace("'", '"'))
    return str(config_file)


@pytest.fixture
def env_vars_openai():
    """Fixture that sets OpenAI environment variables for testing."""
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'sk-test123456789',
        'VETTING_DEFAULT_CHAT_MODEL': 'gpt-4o-mini',
        'VETTING_DEFAULT_PROVIDER': 'openai',
        'VETTING_ENABLE_SAFETY_PREFIX': 'true'
    }):
        yield


@pytest.fixture
def env_vars_multi_provider():
    """Fixture that sets multiple provider environment variables."""
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'sk-openai-test123',
        'ANTHROPIC_API_KEY': 'sk-ant-test123',
        'GOOGLE_API_KEY': 'google-test123',
        'VETTING_DEFAULT_PROVIDER': 'openai'
    }):
        yield


# Pytest markers for different test categories
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


@pytest.fixture(autouse=True)
def reset_environment():
    """Automatically reset environment variables after each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


class MockAsyncContextManager:
    """Helper class for mocking async context managers."""
    
    def __init__(self, return_value):
        self.return_value = return_value
    
    async def __aenter__(self):
        return self.return_value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_aiohttp_session():
    """Fixture providing a mock aiohttp session."""
    session_mock = Mock()
    
    # Create a mock response
    response_mock = Mock()
    response_mock.ok = True
    response_mock.status = 200
    response_mock.json = Mock(return_value={
        "choices": [{"message": {"content": "Mock response"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    })
    
    # Mock the post method to return the response in an async context manager
    session_mock.post.return_value = MockAsyncContextManager(response_mock)
    
    return session_mock


# Helper functions for tests
def assert_valid_usage(usage: Usage):
    """Assert that a Usage object is valid."""
    assert isinstance(usage, Usage)
    assert usage.prompt_tokens >= 0
    assert usage.completion_tokens >= 0
    assert usage.total_tokens >= 0
    assert usage.total_tokens == usage.prompt_tokens + usage.completion_tokens


def assert_valid_vetting_response(response: VettingResponse):
    """Assert that a VettingResponse object is valid."""
    assert isinstance(response, VettingResponse)
    assert isinstance(response.content, str)
    assert response.mode in ["chat", "vetting"]
    assert isinstance(response.requires_attention, bool)
    assert response.attempt_count >= 1
    
    if response.total_usage:
        assert_valid_usage(response.total_usage)
    
    if response.total_cost:
        assert response.total_cost >= 0