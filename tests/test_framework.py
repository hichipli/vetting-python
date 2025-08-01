"""
Tests for the core VettingFramework class.

These tests focus on the framework's orchestration logic, dual-LLM coordination,
and end-to-end behavior without making actual API calls.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from vetting_python.core.framework import VettingFramework
from vetting_python.core.models import (
    ChatMessage, ModelConfig, VettingConfig, Usage, 
    VettingResponse, ContextItem, StopReason
)
from vetting_python.providers import OpenAIProvider


class TestVettingFramework:
    """Test the VettingFramework class."""
    
    def test_framework_initialization_single_provider(self):
        """Test framework initialization with single provider."""
        provider = Mock(spec=OpenAIProvider)
        framework = VettingFramework(chat_provider=provider)
        
        assert framework.chat_provider == provider
        assert framework.verification_provider == provider  # Should default to same
    
    def test_framework_initialization_dual_providers(self):
        """Test framework initialization with separate providers."""
        chat_provider = Mock(spec=OpenAIProvider)
        verification_provider = Mock(spec=OpenAIProvider)
        
        framework = VettingFramework(
            chat_provider=chat_provider,
            verification_provider=verification_provider
        )
        
        assert framework.chat_provider == chat_provider
        assert framework.verification_provider == verification_provider
    
    @pytest.mark.asyncio
    async def test_chat_mode_simple(self, mock_openai_provider, sample_chat_messages):
        """Test framework in simple chat mode."""
        # Setup mock provider
        mock_openai_provider.generate_response = AsyncMock(
            return_value=("Hello! How can I help you today?", 
                         Usage(prompt_tokens=10, completion_tokens=8, total_tokens=18),
                         False)
        )
        mock_openai_provider.calculate_cost = Mock(return_value=0.0001)
        
        framework = VettingFramework(chat_provider=mock_openai_provider)
        
        # Create chat mode config
        config = VettingConfig(
            mode="chat",
            chat_model=ModelConfig(model_id="gpt-4o-mini")
        )
        
        response = await framework.process(sample_chat_messages, config)
        
        assert response.mode == "chat"
        assert response.content == "Hello! How can I help you today?"
        assert response.verification_passed is None  # Not applicable in chat mode
        assert response.requires_attention is False
        assert response.attempt_count == 1
        assert response.stop_reason == StopReason.NOT_APPLICABLE_CHAT_MODE
        
        # Verify provider was called correctly
        mock_openai_provider.generate_response.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_vetting_mode_verification_passes(self, mock_openai_provider, sample_chat_messages):
        """Test framework in vetting mode where verification passes."""
        # Setup mock responses
        chat_response = "I'd be happy to help you learn! Can you tell me what you already know about this topic?"
        verification_response = "PASS: This response appropriately guides the student toward learning."
        
        mock_openai_provider.generate_response = AsyncMock()
        mock_openai_provider.generate_response.side_effect = [
            (chat_response, Usage(100, 50, 150), False),  # Chat response
            (verification_response, Usage(50, 25, 75), False)  # Verification response
        ]
        mock_openai_provider.calculate_cost = Mock(side_effect=[0.0015, 0.0008])
        
        framework = VettingFramework(chat_provider=mock_openai_provider)
        
        config = VettingConfig(
            mode="vetting",
            chat_model=ModelConfig(model_id="gpt-4o-mini"),
            verification_model=ModelConfig(model_id="gpt-4o-mini", temperature=0.1),
            max_attempts=3
        )
        
        response = await framework.process(sample_chat_messages, config)
        
        assert response.mode == "vetting"
        assert response.content == chat_response
        assert response.verification_passed is True
        assert response.requires_attention is False
        assert response.attempt_count == 1
        assert response.stop_reason == StopReason.VERIFICATION_PASSED
        
        # Should have called generate_response twice (chat + verification)
        assert mock_openai_provider.generate_response.call_count == 2
    
    @pytest.mark.asyncio
    async def test_vetting_mode_verification_fails_then_passes(self, mock_openai_provider, sample_chat_messages):
        """Test framework in vetting mode with initial failure then success."""
        # Setup mock responses - first attempt fails, second passes
        responses = [
            ("Here's the direct answer: 2+2=4", Usage(80, 40, 120), False),  # Chat attempt 1
            ("FAIL: Direct answer provided without educational guidance", Usage(60, 30, 90), False),  # Verification 1
            ("Let me help you think about this step by step. What do you know about addition?", Usage(90, 45, 135), False),  # Chat attempt 2
            ("PASS: Good educational approach that guides learning", Usage(55, 28, 83), False)   # Verification 2
        ]
        
        mock_openai_provider.generate_response = AsyncMock(side_effect=responses)
        mock_openai_provider.calculate_cost = Mock(side_effect=[0.001, 0.0008, 0.0012, 0.0009])
        
        framework = VettingFramework(chat_provider=mock_openai_provider)
        
        config = VettingConfig(
            mode="vetting",
            chat_model=ModelConfig(model_id="gpt-4o-mini"),
            verification_model=ModelConfig(model_id="gpt-4o-mini", temperature=0.1),
            max_attempts=3
        )
        
        response = await framework.process(sample_chat_messages, config)
        
        assert response.mode == "vetting"
        assert response.content == "Let me help you think about this step by step. What do you know about addition?"
        assert response.verification_passed is True
        assert response.requires_attention is False
        assert response.attempt_count == 2
        assert response.stop_reason == StopReason.VERIFICATION_PASSED
        
        # Should have called generate_response 4 times (2 chat + 2 verification)
        assert mock_openai_provider.generate_response.call_count == 4
    
    @pytest.mark.asyncio
    async def test_vetting_mode_max_attempts_reached(self, mock_openai_provider, sample_chat_messages):
        """Test framework when max attempts are reached without passing verification."""
        # Setup mock responses - all attempts fail verification
        responses = [
            ("Direct answer 1", Usage(80, 40, 120), False),
            ("FAIL: Too direct", Usage(50, 25, 75), False),
            ("Direct answer 2", Usage(85, 42, 127), False),
            ("FAIL: Still too direct", Usage(52, 26, 78), False),
            ("Direct answer 3", Usage(82, 41, 123), False),
            ("FAIL: No improvement", Usage(48, 24, 72), False)
        ]
        
        mock_openai_provider.generate_response = AsyncMock(side_effect=responses)
        mock_openai_provider.calculate_cost = Mock(return_value=0.001)
        
        framework = VettingFramework(chat_provider=mock_openai_provider)
        
        config = VettingConfig(
            mode="vetting",
            chat_model=ModelConfig(model_id="gpt-4o-mini"),
            max_attempts=3
        )
        
        response = await framework.process(sample_chat_messages, config)
        
        assert response.mode == "vetting"
        assert response.content == "Direct answer 3"  # Last attempt
        assert response.verification_passed is False
        assert response.requires_attention is True  # Should require human attention
        assert response.attempt_count == 3
        assert response.stop_reason == StopReason.MAX_ATTEMPTS_REACHED
        
        # Should have called generate_response 6 times (3 chat + 3 verification)
        assert mock_openai_provider.generate_response.call_count == 6
    
    @pytest.mark.asyncio
    async def test_framework_with_context_items(self, mock_openai_provider):
        """Test framework with educational context items."""
        mock_openai_provider.generate_response = AsyncMock(
            return_value=("Great question! Let's explore this together.", 
                         Usage(60, 30, 90), False)
        )
        mock_openai_provider.calculate_cost = Mock(return_value=0.0009)
        
        framework = VettingFramework(chat_provider=mock_openai_provider)
        
        # Create config with context items
        context_item = ContextItem(
            question={"text": "What is 2+2?", "id": "math_001", "subject": "Math"},
            answer_key={"correctAnswer": "4", "keyConcepts": ["addition", "arithmetic"]}
        )
        
        config = VettingConfig(
            mode="chat",
            chat_model=ModelConfig(model_id="gpt-4o-mini"),
            context_items=[context_item]
        )
        
        messages = [ChatMessage("user", "Can you help me with math?")]
        response = await framework.process(messages, config)
        
        assert response.content == "Great question! Let's explore this together."
        
        # Verify that context was included in the provider call
        call_args = mock_openai_provider.generate_response.call_args
        # The system prompt should include context information
        assert call_args is not None
    
    @pytest.mark.asyncio
    async def test_framework_safety_prefix_detection(self, mock_openai_provider, sample_chat_messages):
        """Test framework safety prefix detection."""
        # Mock response with safety concerns
        unsafe_response = "SAFETY_PREFIX: This request involves harmful content."
        
        mock_openai_provider.generate_response = AsyncMock(
            return_value=(unsafe_response, Usage(50, 25, 75), True)  # safety_triggered=True
        )
        mock_openai_provider.calculate_cost = Mock(return_value=0.0008)
        
        framework = VettingFramework(chat_provider=mock_openai_provider)
        
        config = VettingConfig(
            mode="chat",
            chat_model=ModelConfig(model_id="gpt-4o-mini"),
            enable_safety_prefix=True
        )
        
        response = await framework.process(sample_chat_messages, config)
        
        assert response.mode == "chat"
        assert response.requires_attention is True
        assert response.stop_reason == StopReason.SAFETY_TRIGGERED
        # Content should be filtered
        assert "SAFETY_PREFIX:" not in response.content
    
    @pytest.mark.asyncio
    async def test_framework_provider_error_handling(self, mock_openai_provider, sample_chat_messages):
        """Test framework error handling when provider fails."""
        # Mock provider to raise an exception
        mock_openai_provider.generate_response = AsyncMock(
            side_effect=Exception("API Error: Rate limit exceeded")
        )
        
        framework = VettingFramework(chat_provider=mock_openai_provider)
        
        config = VettingConfig(
            mode="chat",
            chat_model=ModelConfig(model_id="gpt-4o-mini")
        )
        
        with pytest.raises(Exception, match="API Error: Rate limit exceeded"):
            await framework.process(sample_chat_messages, config)
    
    @pytest.mark.asyncio
    async def test_framework_cost_calculation(self, mock_openai_provider, sample_chat_messages):
        """Test that framework correctly calculates total costs."""
        # Setup mock responses with different costs
        mock_openai_provider.generate_response = AsyncMock(side_effect=[
            ("Chat response", Usage(100, 50, 150), False),
            ("PASS: Good response", Usage(60, 30, 90), False)
        ])
        mock_openai_provider.calculate_cost = Mock(side_effect=[0.0015, 0.0009])
        
        framework = VettingFramework(chat_provider=mock_openai_provider)
        
        config = VettingConfig(
            mode="vetting",
            chat_model=ModelConfig(model_id="gpt-4o-mini")
        )
        
        response = await framework.process(sample_chat_messages, config)
        
        # Total cost should be sum of chat and verification costs
        assert response.total_cost == 0.0024  # 0.0015 + 0.0009
        assert response.chat_usage.total_tokens == 150
        assert response.verification_usage.total_tokens == 90
        assert response.total_usage.total_tokens == 240  # 150 + 90
    
    def test_framework_build_system_prompt_educational(self):
        """Test building educational system prompt."""
        framework = VettingFramework(chat_provider=Mock())
        
        config = VettingConfig(
            mode="vetting",
            chat_model=ModelConfig(model_id="gpt-4o-mini"),
            enable_educational_rules=True
        )
        
        context_item = ContextItem(
            question={"text": "What is photosynthesis?", "subject": "Biology"},
            answer_key={"correctAnswer": "Process by which plants make food using sunlight"}
        )
        
        system_prompt = framework._build_system_prompt(
            config, 
            context_items=[context_item],
            attempt_number=1
        )
        
        # Should include educational guidance
        assert "educational" in system_prompt.lower()
        assert "guide" in system_prompt.lower() or "help" in system_prompt.lower()
        
        # Should include context information
        assert "photosynthesis" in system_prompt.lower()
        assert "biology" in system_prompt.lower()
    
    def test_framework_build_verification_prompt(self):
        """Test building verification system prompt."""
        framework = VettingFramework(chat_provider=Mock())
        
        config = VettingConfig(
            mode="vetting",
            chat_model=ModelConfig(model_id="gpt-4o-mini")
        )
        
        verification_prompt = framework._build_verification_prompt(config)
        
        # Should include verification instructions
        assert "verify" in verification_prompt.lower() or "check" in verification_prompt.lower()
        assert "pass" in verification_prompt.lower()
        assert "fail" in verification_prompt.lower()
    
    def test_framework_extract_safety_prefix(self):
        """Test safety prefix extraction."""
        framework = VettingFramework(chat_provider=Mock())
        
        # Test with safety prefix
        content_with_prefix = "SAFETY_PREFIX: This involves harmful content. I cannot help with this."
        filtered_content, has_safety = framework._extract_safety_prefix(content_with_prefix)
        
        assert has_safety is True
        assert "SAFETY_PREFIX:" not in filtered_content
        assert "I cannot help with this." in filtered_content
        
        # Test without safety prefix
        normal_content = "This is a normal response without safety concerns."
        filtered_content, has_safety = framework._extract_safety_prefix(normal_content)
        
        assert has_safety is False
        assert filtered_content == normal_content
    
    def test_framework_check_verification_result(self):
        """Test verification result checking."""
        framework = VettingFramework(chat_provider=Mock())
        
        # Test passing verification
        assert framework._check_verification_result("PASS: This response is appropriate.") is True
        assert framework._check_verification_result("The response passes all checks.") is True
        
        # Test failing verification
        assert framework._check_verification_result("FAIL: This response is too direct.") is False
        assert framework._check_verification_result("This response fails verification.") is False
        
        # Test ambiguous cases (should default to fail for safety)
        assert framework._check_verification_result("This is an ambiguous response.") is False
        assert framework._check_verification_result("") is False


class TestVettingFrameworkIntegration:
    """Integration tests for VettingFramework with different configurations."""
    
    @pytest.mark.asyncio
    async def test_full_educational_workflow(self, mock_openai_provider):
        """Test complete educational vetting workflow."""
        # Setup realistic educational scenario
        responses = [
            # First attempt - too direct
            ("The answer is 4.", Usage(30, 10, 40), False),
            ("FAIL: Direct answer without educational guidance", Usage(40, 20, 60), False),
            
            # Second attempt - better
            ("Great question! Can you think about what happens when you add 2 things to 2 other things?", 
             Usage(60, 30, 90), False),
            ("PASS: Good educational approach that encourages thinking", Usage(45, 25, 70), False)
        ]
        
        mock_openai_provider.generate_response = AsyncMock(side_effect=responses)
        mock_openai_provider.calculate_cost = Mock(side_effect=[0.0004, 0.0006, 0.0009, 0.0007])
        
        framework = VettingFramework(chat_provider=mock_openai_provider)
        
        # Educational context
        context_item = ContextItem(
            question={
                "text": "What is 2 + 2?",
                "id": "math_basic_001", 
                "subject": "Elementary Math",
                "grade_level": "1st Grade"
            },
            answer_key={
                "correctAnswer": "4",
                "keyConcepts": ["addition", "counting", "basic arithmetic"],
                "explanation": "When you add 2 + 2, you're combining two groups of 2 items."
            }
        )
        
        config = VettingConfig(
            mode="vetting",
            chat_model=ModelConfig(model_id="gpt-4o-mini", temperature=0.7),
            verification_model=ModelConfig(model_id="gpt-4o-mini", temperature=0.1),
            context_items=[context_item],
            max_attempts=3,
            enable_educational_rules=True,
            enable_safety_prefix=True,
            session_id="edu_session_001",
            user_id="student_123"
        )
        
        messages = [
            ChatMessage("user", "I need help with my math homework. What is 2 + 2?")
        ]
        
        response = await framework.process(messages, config)
        
        # Verify final response
        assert response.mode == "vetting"
        assert response.verification_passed is True
        assert response.attempt_count == 2
        assert response.stop_reason == StopReason.VERIFICATION_PASSED
        assert "think" in response.content.lower()  # Should encourage thinking
        
        # Verify cost tracking
        assert response.total_cost == 0.0026  # Sum of all costs
        assert response.total_usage.total_tokens == 260  # Sum of all usage
        
        # Verify metadata
        assert response.session_id == "edu_session_001"
        assert response.user_id == "student_123"
        assert response.chat_model_used == "gpt-4o-mini"
        assert response.verification_model_used == "gpt-4o-mini"