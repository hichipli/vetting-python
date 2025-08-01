"""
Data models for the VETTING framework.

This module defines the core data structures used throughout the framework,
including configuration objects, message formats, and response structures.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union, Literal
from enum import Enum
from abc import ABC, abstractmethod
import time


class StopReason(Enum):
    """Enumeration of possible stop reasons for the vetting process."""
    VERIFICATION_PASSED = "VERIFICATION_PASSED"
    MAX_ATTEMPTS_REACHED = "MAX_ATTEMPTS_REACHED"
    SAFETY_TRIGGERED = "SAFETY_TRIGGERED"
    GENERATION_ERROR = "GENERATION_ERROR"
    VERIFICATION_ERROR = "VERIFICATION_ERROR"
    NOT_APPLICABLE_CHAT_MODE = "NOT_APPLICABLE_CHAT_MODE"


@dataclass
class Usage:
    """Token usage information for LLM calls."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def __add__(self, other: 'Usage') -> 'Usage':
        """Add two Usage objects together."""
        return Usage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens
        )


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    model_id: str
    temperature: float = 0.7
    max_tokens: int = 1024
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        config = {
            "model": self.model_id,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        if self.top_p is not None:
            config["top_p"] = self.top_p
        if self.frequency_penalty is not None:
            config["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty is not None:
            config["presence_penalty"] = self.presence_penalty
            
        return config


@dataclass
class ChatMessage:
    """Represents a chat message in the conversation."""
    role: Literal["user", "assistant", "system"]
    content: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format for API calls."""
        return {"role": self.role, "content": self.content}


@dataclass
class ContextItem:
    """Context item for educational vetting scenarios."""
    question: Dict[str, Any]
    answer_key: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate context item structure."""
        if not isinstance(self.question, dict) or "text" not in self.question:
            raise ValueError("Context item question must be a dict with 'text' field")


@dataclass
class VettingConfig:
    """Complete configuration for the VETTING framework."""
    
    # Required configurations
    chat_model: ModelConfig
    verification_model: Optional[ModelConfig] = None
    
    # Mode selection
    mode: Literal["chat", "vetting"] = "vetting"
    
    # Retry configuration
    max_attempts: int = 3
    
    # System prompts
    chat_system_prompt: Optional[str] = None
    verification_system_prompt: Optional[str] = None
    
    # Context for educational scenarios
    context_items: Optional[List[ContextItem]] = None
    
    # Session tracking
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Safety settings
    enable_safety_prefix: bool = True
    enable_educational_rules: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.mode == "vetting" and self.verification_model is None:
            # Use same model as chat by default
            self.verification_model = ModelConfig(
                model_id=self.chat_model.model_id,
                temperature=0.1,  # Lower temperature for verification
                max_tokens=512    # Fewer tokens needed for verification
            )


@dataclass
class VerificationResult:
    """Result of the verification process for a single attempt."""
    passed: bool
    verification_output: str
    attempt_number: int
    requires_attention: bool = False
    usage: Optional[Usage] = None
    cost: float = 0.0


@dataclass 
class AttemptDetail:
    """Detailed information about a single generation attempt."""
    attempt_number: int
    chat_response: str
    verification_passed: bool
    verification_output: str
    requires_attention: bool = False
    chat_usage: Optional[Usage] = None
    verification_usage: Optional[Usage] = None
    chat_cost: float = 0.0
    verification_cost: float = 0.0


@dataclass
class VettingResponse:
    """Complete response from the VETTING framework."""
    
    # Core response
    content: str
    mode: Literal["chat", "vetting"]
    
    # Safety signals
    requires_attention: bool = False
    
    # Verification details (only for vetting mode)
    verification_passed: Optional[bool] = None
    attempt_count: int = 1
    stop_reason: Optional[StopReason] = None
    attempts: Optional[List[AttemptDetail]] = None
    
    # Usage and cost tracking
    chat_usage: Optional[Usage] = None
    verification_usage: Optional[Usage] = None
    total_usage: Optional[Usage] = None
    total_cost: float = 0.0
    
    # Metadata
    processing_time_ms: Optional[float] = None
    timestamp: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    chat_model_used: Optional[str] = None
    verification_model_used: Optional[str] = None
    
    def __post_init__(self):
        """Set default values after initialization."""
        if self.timestamp is None:
            self.timestamp = str(int(time.time()))
            
        # Calculate total usage if components are available
        if self.chat_usage and self.verification_usage and self.total_usage is None:
            self.total_usage = self.chat_usage + self.verification_usage
        elif self.chat_usage and not self.verification_usage and self.total_usage is None:
            self.total_usage = self.chat_usage


class Provider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate_response(
        self,
        messages: List[ChatMessage],
        model_config: ModelConfig,
        system_prompt: Optional[str] = None
    ) -> tuple[str, Usage, bool]:
        """
        Generate a response from the LLM.
        
        Args:
            messages: List of chat messages
            model_config: Model configuration
            system_prompt: Optional system prompt to prepend
            
        Returns:
            Tuple of (response_content, usage, requires_attention)
        """
        pass
    
    @abstractmethod
    def calculate_cost(self, model_id: str, usage: Usage) -> float:
        """Calculate the cost for a given model and usage."""
        pass
    
    @abstractmethod
    def get_model_aliases(self) -> Dict[str, str]:
        """Get mapping of model aliases to actual model IDs."""
        pass