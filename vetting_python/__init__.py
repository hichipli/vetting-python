"""
VETTING: A Python framework for implementing dual-LLM safety architecture.

This package implements the VETTING framework as described in the research paper,
providing architectural policy isolation between conversational logic and safety enforcement.

Key Components:
- Chat-Layer (LLM-A): User-facing conversational model
- Verification-Layer (LLM-B): Policy enforcement model  
- Feedback Loop: Iterative refinement process

Supported Providers:
- OpenAI (GPT models)
- Anthropic Claude
- Google Gemini
"""

from .core.framework import VettingFramework
from .core.models import (
    VettingConfig,
    ChatMessage,
    VettingResponse,
    VerificationResult,
    ModelConfig,
    Usage
)
from .providers import OpenAIProvider, ClaudeProvider, GeminiProvider
from .config import VettingSettings

__version__ = "0.1.0"  # Released 2025-07-31
__author__ = "VETTING Research Team"
__email__ = "hli3@ufl.edu"

__all__ = [
    "VettingFramework",
    "VettingConfig", 
    "ChatMessage",
    "VettingResponse",
    "VerificationResult",
    "ModelConfig",
    "Usage",
    "OpenAIProvider",
    "ClaudeProvider", 
    "GeminiProvider",
    "VettingSettings"
]