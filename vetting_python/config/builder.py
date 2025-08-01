"""
Configuration builder utility for easy setup of VETTING framework.

This module provides a fluent API for building VettingConfig objects
with sensible defaults and validation.
"""

from typing import Optional, List, Dict, Any
from ..core.models import VettingConfig, ModelConfig, ContextItem, ChatMessage


class VettingConfigBuilder:
    """
    Fluent builder for creating VettingConfig objects.
    
    Provides an easy-to-use interface for configuring the VETTING framework
    with method chaining and sensible defaults.
    """
    
    def __init__(self):
        """Initialize the builder with default values."""
        self._mode = "vetting"
        self._chat_model = ModelConfig(model_id="gpt-4o-mini", temperature=0.7, max_tokens=1024)
        self._verification_model = None
        self._max_attempts = 3
        self._chat_system_prompt = None
        self._verification_system_prompt = None
        self._context_items = []
        self._session_id = None
        self._user_id = None
        self._enable_safety_prefix = True
        self._enable_educational_rules = True
    
    def mode(self, mode: str) -> 'VettingConfigBuilder':
        """
        Set the vetting mode.
        
        Args:
            mode: Either "chat" or "vetting"
            
        Returns:
            Self for method chaining
        """
        if mode not in ["chat", "vetting"]:
            raise ValueError("Mode must be either 'chat' or 'vetting'")
        self._mode = mode
        return self
    
    def chat_mode(self) -> 'VettingConfigBuilder':
        """Set mode to chat (no verification)."""
        return self.mode("chat")
    
    def vetting_mode(self) -> 'VettingConfigBuilder':
        """Set mode to vetting (with verification)."""
        return self.mode("vetting")
    
    def chat_model(
        self,
        model_id: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None
    ) -> 'VettingConfigBuilder':
        """
        Configure the chat model (LLM-A).
        
        Args:
            model_id: Model identifier (e.g., "gpt-4o-mini", "claude-3-haiku")
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter (optional)
            frequency_penalty: Frequency penalty (optional)
            presence_penalty: Presence penalty (optional)
            
        Returns:
            Self for method chaining
        """
        self._chat_model = ModelConfig(
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty
        )
        return self
    
    def verification_model(
        self,
        model_id: str,
        temperature: float = 0.1,
        max_tokens: int = 512,
        top_p: Optional[float] = None
    ) -> 'VettingConfigBuilder':
        """
        Configure the verification model (LLM-B).
        
        Args:
            model_id: Model identifier
            temperature: Sampling temperature (usually lower for verification)
            max_tokens: Maximum tokens for verification response
            top_p: Nucleus sampling parameter (optional)
            
        Returns:
            Self for method chaining
        """
        self._verification_model = ModelConfig(
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p
        )
        return self
    
    def max_attempts(self, attempts: int) -> 'VettingConfigBuilder':
        """
        Set maximum verification attempts.
        
        Args:
            attempts: Maximum number of verification attempts (1-10)
            
        Returns:
            Self for method chaining
        """
        if attempts < 1 or attempts > 10:
            raise ValueError("Max attempts must be between 1 and 10")
        self._max_attempts = attempts
        return self
    
    def chat_system_prompt(self, prompt: str) -> 'VettingConfigBuilder':
        """
        Set the system prompt for the chat model.
        
        Args:
            prompt: System prompt text
            
        Returns:
            Self for method chaining
        """
        self._chat_system_prompt = prompt
        return self
    
    def verification_system_prompt(self, prompt: str) -> 'VettingConfigBuilder':
        """
        Set the system prompt for the verification model.
        
        Args:
            prompt: Verification system prompt text
            
        Returns:
            Self for method chaining
        """
        self._verification_system_prompt = prompt
        return self
    
    def add_context_item(
        self,
        question_text: str,
        question_id: Optional[str] = None,
        subject: Optional[str] = None,
        correct_answer: Optional[str] = None,
        key_concepts: Optional[List[str]] = None,
        explanation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'VettingConfigBuilder':
        """
        Add a context item for educational vetting scenarios.
        
        Args:
            question_text: The question text
            question_id: Optional question identifier
            subject: Optional subject area
            correct_answer: The correct answer (for verification)
            key_concepts: List of key concepts to avoid revealing
            explanation: Optional explanation or context
            metadata: Additional metadata
            
        Returns:
            Self for method chaining
        """
        question = {"text": question_text}
        if question_id:
            question["id"] = question_id
        if subject:
            question["subject"] = subject
        if metadata:
            question["metadata"] = metadata
        
        answer_key = None
        if correct_answer or key_concepts or explanation:
            answer_key = {}
            if correct_answer:
                answer_key["correctAnswer"] = correct_answer
            if key_concepts:
                answer_key["keyConcepts"] = key_concepts
            if explanation:
                answer_key["explanation"] = explanation
        
        self._context_items.append(ContextItem(
            question=question,
            answer_key=answer_key
        ))
        return self
    
    def session_info(self, session_id: Optional[str] = None, user_id: Optional[str] = None) -> 'VettingConfigBuilder':
        """
        Set session tracking information.
        
        Args:
            session_id: Optional session identifier
            user_id: Optional user identifier
            
        Returns:
            Self for method chaining
        """
        self._session_id = session_id
        self._user_id = user_id
        return self
    
    def safety_features(
        self,
        enable_safety_prefix: bool = True,
        enable_educational_rules: bool = True
    ) -> 'VettingConfigBuilder':
        """
        Configure safety and educational features.
        
        Args:
            enable_safety_prefix: Enable safety prefix detection
            enable_educational_rules: Enable educational interaction rules
            
        Returns:
            Self for method chaining
        """
        self._enable_safety_prefix = enable_safety_prefix
        self._enable_educational_rules = enable_educational_rules
        return self
    
    def build(self) -> VettingConfig:
        """
        Build and return the final VettingConfig.
        
        Returns:
            Configured VettingConfig object
        """
        # If in vetting mode but no verification model specified, use same as chat model
        verification_model = self._verification_model
        if self._mode == "vetting" and verification_model is None:
            verification_model = ModelConfig(
                model_id=self._chat_model.model_id,
                temperature=0.1,  # Lower temperature for verification
                max_tokens=512    # Fewer tokens needed for verification
            )
        
        return VettingConfig(
            mode=self._mode,
            chat_model=self._chat_model,
            verification_model=verification_model,
            max_attempts=self._max_attempts,
            chat_system_prompt=self._chat_system_prompt,
            verification_system_prompt=self._verification_system_prompt,
            context_items=self._context_items if self._context_items else None,
            session_id=self._session_id,
            user_id=self._user_id,
            enable_safety_prefix=self._enable_safety_prefix,
            enable_educational_rules=self._enable_educational_rules
        )


# Convenience functions for quick setup
def quick_chat_config(
    model_id: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int = 1024
) -> VettingConfig:
    """
    Quick setup for chat mode.
    
    Args:
        model_id: Model to use for chat
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        
    Returns:
        VettingConfig for chat mode
    """
    return (VettingConfigBuilder()
            .chat_mode()
            .chat_model(model_id, temperature, max_tokens)
            .build())


def quick_vetting_config(
    chat_model_id: str = "gpt-4o-mini",
    verification_model_id: Optional[str] = None,
    max_attempts: int = 3
) -> VettingConfig:
    """
    Quick setup for vetting mode.
    
    Args:
        chat_model_id: Model to use for chat
        verification_model_id: Model to use for verification (defaults to same as chat)
        max_attempts: Maximum verification attempts
        
    Returns:
        VettingConfig for vetting mode
    """
    builder = (VettingConfigBuilder()
               .vetting_mode()
               .chat_model(chat_model_id)
               .max_attempts(max_attempts))
    
    if verification_model_id:
        builder.verification_model(verification_model_id)
    
    return builder.build()


def educational_vetting_config(
    questions_and_answers: List[Dict[str, Any]],
    chat_model_id: str = "gpt-4o-mini",
    verification_model_id: Optional[str] = None
) -> VettingConfig:
    """
    Quick setup for educational vetting scenarios.
    
    Args:
        questions_and_answers: List of dicts with question and answer info
        chat_model_id: Model to use for chat
        verification_model_id: Model to use for verification
        
    Returns:
        VettingConfig for educational vetting
    """
    builder = (VettingConfigBuilder()
               .vetting_mode()
               .chat_model(chat_model_id)
               .safety_features(enable_educational_rules=True))
    
    if verification_model_id:
        builder.verification_model(verification_model_id)
    
    # Add all questions and answers
    for qa in questions_and_answers:
        builder.add_context_item(
            question_text=qa["question"],
            question_id=qa.get("id"),
            subject=qa.get("subject"),
            correct_answer=qa.get("answer"),
            key_concepts=qa.get("key_concepts"),
            explanation=qa.get("explanation")
        )
    
    return builder.build()