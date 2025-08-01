"""
Validation utilities for the VETTING framework.

This module provides comprehensive validation for configurations,
messages, and other framework components.
"""

import re
from typing import List, Dict, Any, Optional, Union
from ..core.models import (
    VettingConfig, ChatMessage, ModelConfig, ContextItem, 
    StopReason, Usage
)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class ValidationUtils:
    """Comprehensive validation utilities for the VETTING framework."""
    
    # Known model patterns for different providers
    PROVIDER_MODEL_PATTERNS = {
        "openai": [
            r"gpt-3\.5-turbo.*",
            r"gpt-4.*",
            r"text-davinci.*",
            r"viable-.*"  # Custom alias
        ],
        "claude": [
            r"claude-3.*",
            r"claude-.*"
        ],
        "gemini": [
            r"gemini.*",
            r"models/gemini.*"
        ]
    }
    
    @staticmethod
    def validate_vetting_config(config: VettingConfig) -> Dict[str, Any]:
        """
        Validate a VettingConfig object.
        
        Args:
            config: VettingConfig to validate
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        # Validate mode
        if config.mode not in ["chat", "vetting"]:
            issues.append(f"Invalid mode: {config.mode}. Must be 'chat' or 'vetting'")
        
        # Validate chat model
        if not config.chat_model:
            issues.append("Chat model configuration is required")
        else:
            model_validation = ValidationUtils.validate_model_config(config.chat_model)
            if not model_validation["valid"]:
                issues.extend([f"Chat model: {issue}" for issue in model_validation["issues"]])
            warnings.extend([f"Chat model: {warning}" for warning in model_validation["warnings"]])
        
        # Validate verification model for vetting mode
        if config.mode == "vetting":
            if not config.verification_model:
                warnings.append("No verification model specified for vetting mode, will use same as chat model")
            else:
                model_validation = ValidationUtils.validate_model_config(config.verification_model)
                if not model_validation["valid"]:
                    issues.extend([f"Verification model: {issue}" for issue in model_validation["issues"]])
                warnings.extend([f"Verification model: {warning}" for warning in model_validation["warnings"]])
        
        # Validate max attempts
        if config.max_attempts < 1 or config.max_attempts > 10:
            issues.append(f"Max attempts ({config.max_attempts}) must be between 1 and 10")
        
        # Validate context items for vetting mode
        if config.mode == "vetting" and config.context_items:
            for i, item in enumerate(config.context_items):
                item_validation = ValidationUtils.validate_context_item(item)
                if not item_validation["valid"]:
                    issues.extend([f"Context item {i}: {issue}" for issue in item_validation["issues"]])
                warnings.extend([f"Context item {i}: {warning}" for warning in item_validation["warnings"]])
        
        # Validate system prompts
        if config.chat_system_prompt and len(config.chat_system_prompt) > 8000:
            warnings.append("Chat system prompt is very long, may cause token limit issues")
        
        if config.verification_system_prompt and len(config.verification_system_prompt) > 8000:
            warnings.append("Verification system prompt is very long, may cause token limit issues")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }
    
    @staticmethod
    def validate_model_config(config: ModelConfig) -> Dict[str, Any]:
        """
        Validate a ModelConfig object.
        
        Args:
            config: ModelConfig to validate
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        # Validate model ID
        if not config.model_id:
            issues.append("Model ID is required")
        elif not isinstance(config.model_id, str):
            issues.append("Model ID must be a string")
        
        # Validate temperature
        if not (0.0 <= config.temperature <= 2.0):
            issues.append(f"Temperature ({config.temperature}) must be between 0.0 and 2.0")
        
        # Validate max tokens
        if config.max_tokens < 1 or config.max_tokens > 128000:
            issues.append(f"Max tokens ({config.max_tokens}) must be between 1 and 128000")
        
        if config.max_tokens > 8192:
            warnings.append(f"Max tokens ({config.max_tokens}) is quite high, may increase costs")
        
        # Validate optional parameters
        if config.top_p is not None and not (0.0 <= config.top_p <= 1.0):
            issues.append(f"top_p ({config.top_p}) must be between 0.0 and 1.0")
        
        if config.frequency_penalty is not None and not (-2.0 <= config.frequency_penalty <= 2.0):
            issues.append(f"frequency_penalty ({config.frequency_penalty}) must be between -2.0 and 2.0")
        
        if config.presence_penalty is not None and not (-2.0 <= config.presence_penalty <= 2.0):
            issues.append(f"presence_penalty ({config.presence_penalty}) must be between -2.0 and 2.0")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }
    
    @staticmethod
    def validate_context_item(item: ContextItem) -> Dict[str, Any]:
        """
        Validate a ContextItem object.
        
        Args:
            item: ContextItem to validate
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        # Validate question
        if not item.question:
            issues.append("Question is required")
        else:
            if "text" not in item.question:
                issues.append("Question must have 'text' field")
            elif not item.question["text"].strip():
                issues.append("Question text cannot be empty")
            
            # Check for overly long question
            if "text" in item.question and len(item.question["text"]) > 2000:
                warnings.append("Question text is very long")
        
        # Validate answer key
        if item.answer_key:
            if "correctAnswer" in item.answer_key:
                if not item.answer_key["correctAnswer"].strip():
                    warnings.append("Correct answer is empty")
            
            if "keyConcepts" in item.answer_key:
                key_concepts = item.answer_key["keyConcepts"]
                if not isinstance(key_concepts, list):
                    issues.append("Key concepts must be a list")
                elif len(key_concepts) == 0:
                    warnings.append("Key concepts list is empty")
                elif any(not isinstance(concept, str) or not concept.strip() for concept in key_concepts):
                    issues.append("All key concepts must be non-empty strings")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }
    
    @staticmethod
    def validate_messages(messages: List[ChatMessage]) -> Dict[str, Any]:
        """
        Validate a list of ChatMessage objects.
        
        Args:
            messages: List of ChatMessage objects to validate
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        if not messages:
            issues.append("Message list cannot be empty")
            return {"valid": False, "issues": issues, "warnings": warnings}
        
        for i, msg in enumerate(messages):
            # Validate role
            if msg.role not in ["user", "assistant", "system"]:
                issues.append(f"Message {i}: Invalid role '{msg.role}'")
            
            # Validate content
            if not isinstance(msg.content, str):
                issues.append(f"Message {i}: Content must be a string")
            elif not msg.content.strip():
                warnings.append(f"Message {i}: Content is empty")
            elif len(msg.content) > 10000:
                warnings.append(f"Message {i}: Content is very long ({len(msg.content)} chars)")
        
        # Check conversation flow
        non_system_msgs = [msg for msg in messages if msg.role != "system"]
        if non_system_msgs:
            if non_system_msgs[0].role != "user":
                warnings.append("Conversation should typically start with user message")
            
            # Check for proper alternation (allowing for multiple consecutive system messages)
            last_role = None
            consecutive_count = 0
            for msg in non_system_msgs:
                if msg.role == last_role:
                    consecutive_count += 1
                    if consecutive_count >= 2 and msg.role != "system":
                        warnings.append(f"Multiple consecutive {msg.role} messages detected")
                else:
                    consecutive_count = 0
                    last_role = msg.role
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }
    
    @staticmethod
    def validate_api_key(api_key: str, provider: str) -> Dict[str, Any]:
        """
        Validate API key format for different providers.
        
        Args:
            api_key: API key to validate
            provider: Provider name ("openai", "claude", "gemini")
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        if not api_key:
            issues.append("API key cannot be empty")
            return {"valid": False, "issues": issues, "warnings": warnings}
        
        if not isinstance(api_key, str):
            issues.append("API key must be a string")
            return {"valid": False, "issues": issues, "warnings": warnings}
        
        # Provider-specific validation
        if provider == "openai":
            if not api_key.startswith("sk-"):
                warnings.append("OpenAI API keys typically start with 'sk-'")
            if len(api_key) < 40:
                warnings.append("OpenAI API key seems too short")
                
        elif provider == "claude":
            if not api_key.startswith("sk-ant-"):
                warnings.append("Claude API keys typically start with 'sk-ant-'")
            if len(api_key) < 60:
                warnings.append("Claude API key seems too short")
                
        elif provider == "gemini":
            if len(api_key) < 30:
                warnings.append("Gemini API key seems too short")
        
        # General validation
        if " " in api_key:
            issues.append("API key should not contain spaces")
        
        if len(api_key) < 20:
            issues.append("API key is too short to be valid")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }
    
    @staticmethod
    def validate_model_for_provider(model_id: str, provider: str) -> Dict[str, Any]:
        """
        Validate that a model ID is appropriate for a provider.
        
        Args:
            model_id: Model ID to validate
            provider: Provider name
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        if provider not in ValidationUtils.PROVIDER_MODEL_PATTERNS:
            warnings.append(f"Unknown provider '{provider}', cannot validate model compatibility")
            return {"valid": True, "issues": issues, "warnings": warnings}
        
        patterns = ValidationUtils.PROVIDER_MODEL_PATTERNS[provider]
        model_matches = any(re.match(pattern, model_id) for pattern in patterns)
        
        if not model_matches:
            warnings.append(f"Model '{model_id}' may not be compatible with provider '{provider}'")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }
    
    @staticmethod
    def validate_usage(usage: Usage) -> Dict[str, Any]:
        """
        Validate a Usage object.
        
        Args:
            usage: Usage object to validate
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        if usage.prompt_tokens < 0:
            issues.append("Prompt tokens cannot be negative")
        
        if usage.completion_tokens < 0:
            issues.append("Completion tokens cannot be negative")
        
        if usage.total_tokens < 0:
            issues.append("Total tokens cannot be negative")
        
        # Check if total matches sum
        expected_total = usage.prompt_tokens + usage.completion_tokens
        if usage.total_tokens != expected_total:
            warnings.append(f"Total tokens ({usage.total_tokens}) doesn't match sum of prompt + completion ({expected_total})")
        
        # Warn about high usage
        if usage.total_tokens > 50000:
            warnings.append(f"Very high token usage: {usage.total_tokens}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }
    
    @staticmethod
    def validate_and_raise(validation_result: Dict[str, Any], context: str = ""):
        """
        Validate a result and raise ValidationError if invalid.
        
        Args:
            validation_result: Result from validation function
            context: Additional context for error message
            
        Raises:
            ValidationError: If validation failed
        """
        if not validation_result["valid"]:
            context_str = f" ({context})" if context else ""
            issues_str = "; ".join(validation_result["issues"])
            raise ValidationError(f"Validation failed{context_str}: {issues_str}")