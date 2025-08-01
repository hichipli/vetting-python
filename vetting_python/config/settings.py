"""
Configuration settings and environment management for VETTING framework.

This module provides configuration management with support for environment variables,
configuration files, and programmatic setup.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass, field
from pathlib import Path

from ..core.models import ModelConfig, VettingConfig
from ..providers import OpenAIProvider, ClaudeProvider, GeminiProvider

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for a specific provider."""
    provider_type: str  # "openai", "claude", "gemini"
    api_key: str
    base_url: Optional[str] = None
    organization: Optional[str] = None  # For OpenAI
    timeout: int = 60
    max_retries: int = 3
    
    def validate(self) -> bool:
        """Validate the provider configuration."""
        if not self.api_key:
            logger.error(f"API key is required for {self.provider_type} provider")
            return False
        
        if self.provider_type not in ["openai", "claude", "gemini"]:
            logger.error(f"Unsupported provider type: {self.provider_type}")
            return False
        
        return True


@dataclass 
class VettingSettings:
    """
    Main settings class for the VETTING framework.
    
    Supports loading from environment variables, configuration files,
    and programmatic configuration.
    """
    
    # Provider configurations
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
    
    # Default models
    default_chat_model: str = "gpt-4o-mini"
    default_verification_model: str = "gpt-4o-mini"
    default_provider: str = "openai"
    
    # Default generation parameters
    default_temperature_chat: float = 0.7
    default_temperature_verification: float = 0.1
    default_max_tokens_chat: int = 1024
    default_max_tokens_verification: int = 512
    default_max_attempts: int = 3
    
    # Safety and educational features
    enable_safety_prefix: bool = True
    enable_educational_rules: bool = True
    enable_cost_tracking: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_requests: bool = False
    
    @classmethod
    def from_env(cls) -> 'VettingSettings':
        """Create settings from environment variables."""
        settings = cls()
        
        # Load provider configurations from environment
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            settings.providers["openai"] = ProviderConfig(
                provider_type="openai",
                api_key=openai_key,
                base_url=os.getenv("OPENAI_API_BASE_URL"),
                organization=os.getenv("OPENAI_ORGANIZATION"),
                timeout=int(os.getenv("OPENAI_TIMEOUT", "60")),
                max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3"))
            )
        
        claude_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        if claude_key:
            settings.providers["claude"] = ProviderConfig(
                provider_type="claude",
                api_key=claude_key,
                base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
                timeout=int(os.getenv("ANTHROPIC_TIMEOUT", "60")),
                max_retries=int(os.getenv("ANTHROPIC_MAX_RETRIES", "3"))
            )
        
        gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if gemini_key:
            settings.providers["gemini"] = ProviderConfig(
                provider_type="gemini",
                api_key=gemini_key,
                base_url=os.getenv("GOOGLE_AI_BASE_URL", "https://generativelanguage.googleapis.com"),
                timeout=int(os.getenv("GOOGLE_TIMEOUT", "60")),
                max_retries=int(os.getenv("GOOGLE_MAX_RETRIES", "3"))
            )
        
        # Load other settings from environment
        settings.default_chat_model = os.getenv("VETTING_DEFAULT_CHAT_MODEL", settings.default_chat_model)
        settings.default_verification_model = os.getenv("VETTING_DEFAULT_VERIFICATION_MODEL", settings.default_verification_model)
        settings.default_provider = os.getenv("VETTING_DEFAULT_PROVIDER", settings.default_provider)
        
        settings.default_temperature_chat = float(os.getenv("VETTING_TEMPERATURE_CHAT", str(settings.default_temperature_chat)))
        settings.default_temperature_verification = float(os.getenv("VETTING_TEMPERATURE_VERIFICATION", str(settings.default_temperature_verification)))
        settings.default_max_tokens_chat = int(os.getenv("VETTING_MAX_TOKENS_CHAT", str(settings.default_max_tokens_chat)))
        settings.default_max_tokens_verification = int(os.getenv("VETTING_MAX_TOKENS_VERIFICATION", str(settings.default_max_tokens_verification)))
        settings.default_max_attempts = int(os.getenv("VETTING_MAX_ATTEMPTS", str(settings.default_max_attempts)))
        
        settings.enable_safety_prefix = os.getenv("VETTING_ENABLE_SAFETY_PREFIX", "true").lower() == "true"
        settings.enable_educational_rules = os.getenv("VETTING_ENABLE_EDUCATIONAL_RULES", "true").lower() == "true"
        settings.enable_cost_tracking = os.getenv("VETTING_ENABLE_COST_TRACKING", "true").lower() == "true"
        
        settings.log_level = os.getenv("VETTING_LOG_LEVEL", settings.log_level)
        settings.log_requests = os.getenv("VETTING_LOG_REQUESTS", "false").lower() == "true"
        
        return settings
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> 'VettingSettings':
        """Load settings from a JSON or YAML configuration file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        # Load file content
        with open(file_path, 'r') as f:
            if file_path.suffix.lower() in ['.yml', '.yaml']:
                try:
                    import yaml
                    config_data = yaml.safe_load(f)
                except ImportError:
                    raise ImportError("PyYAML is required to load YAML configuration files. Install with: pip install PyYAML")
            else:
                config_data = json.load(f)
        
        return cls.from_dict(config_data)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'VettingSettings':
        """Create settings from a dictionary."""
        settings = cls()
        
        # Load provider configurations
        providers_config = config_dict.get("providers", {})
        for provider_name, provider_data in providers_config.items():
            settings.providers[provider_name] = ProviderConfig(**provider_data)
        
        # Load other settings
        for key, value in config_dict.items():
            if key != "providers" and hasattr(settings, key):
                setattr(settings, key, value)
        
        return settings
    
    def get_provider_instance(self, provider_name: str):
        """Create and return a provider instance."""
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not configured")
        
        config = self.providers[provider_name]
        if not config.validate():
            raise ValueError(f"Invalid configuration for provider '{provider_name}'")
        
        if config.provider_type == "openai":
            return OpenAIProvider(
                api_key=config.api_key,
                base_url=config.base_url or "https://api.openai.com/v1",
                max_retries=config.max_retries,
                timeout=config.timeout,
                organization=config.organization
            )
        elif config.provider_type == "claude":
            return ClaudeProvider(
                api_key=config.api_key,
                base_url=config.base_url or "https://api.anthropic.com",
                max_retries=config.max_retries,
                timeout=config.timeout
            )
        elif config.provider_type == "gemini":
            return GeminiProvider(
                api_key=config.api_key,
                base_url=config.base_url or "https://generativelanguage.googleapis.com",
                max_retries=config.max_retries,
                timeout=config.timeout
            )
        else:
            raise ValueError(f"Unsupported provider type: {config.provider_type}")
    
    def create_default_vetting_config(
        self,
        mode: str = "vetting",
        chat_model_override: Optional[str] = None,
        verification_model_override: Optional[str] = None,
        provider_override: Optional[str] = None
    ) -> VettingConfig:
        """Create a default VettingConfig using the settings."""
        
        # Determine which provider to use
        provider_name = provider_override or self.default_provider
        if provider_name not in self.providers:
            # Use first available provider
            if not self.providers:
                raise ValueError("No providers configured")
            provider_name = next(iter(self.providers.keys()))
        
        # Create model configurations
        chat_model = ModelConfig(
            model_id=chat_model_override or self.default_chat_model,
            temperature=self.default_temperature_chat,
            max_tokens=self.default_max_tokens_chat
        )
        
        verification_model = None
        if mode == "vetting":
            verification_model = ModelConfig(
                model_id=verification_model_override or self.default_verification_model,
                temperature=self.default_temperature_verification,
                max_tokens=self.default_max_tokens_verification
            )
        
        return VettingConfig(
            mode=mode,
            chat_model=chat_model,
            verification_model=verification_model,
            max_attempts=self.default_max_attempts,
            enable_safety_prefix=self.enable_safety_prefix,
            enable_educational_rules=self.enable_educational_rules
        )
    
    def validate(self) -> bool:
        """Validate the settings configuration."""
        if not self.providers:
            logger.error("No providers configured")
            return False
        
        # Validate all providers
        for name, provider in self.providers.items():
            if not provider.validate():
                logger.error(f"Invalid configuration for provider '{name}'")
                return False
        
        # Check if default provider exists
        if self.default_provider not in self.providers:
            logger.warning(f"Default provider '{self.default_provider}' not configured")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary format."""
        return {
            "providers": {
                name: {
                    "provider_type": config.provider_type,
                    "api_key": config.api_key,
                    "base_url": config.base_url,
                    "organization": config.organization,
                    "timeout": config.timeout,
                    "max_retries": config.max_retries
                }
                for name, config in self.providers.items()
            },
            "default_chat_model": self.default_chat_model,
            "default_verification_model": self.default_verification_model,
            "default_provider": self.default_provider,
            "default_temperature_chat": self.default_temperature_chat,
            "default_temperature_verification": self.default_temperature_verification,
            "default_max_tokens_chat": self.default_max_tokens_chat,
            "default_max_tokens_verification": self.default_max_tokens_verification,
            "default_max_attempts": self.default_max_attempts,
            "enable_safety_prefix": self.enable_safety_prefix,
            "enable_educational_rules": self.enable_educational_rules,
            "enable_cost_tracking": self.enable_cost_tracking,
            "log_level": self.log_level,
            "log_requests": self.log_requests
        }
    
    def save_to_file(self, file_path: Union[str, Path]):
        """Save settings to a JSON file."""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        
        logger.info(f"Settings saved to {file_path}")
    
    def setup_logging(self):
        """Setup logging based on the settings."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper(), logging.INFO),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        if self.log_requests:
            # Enable HTTP request logging
            logging.getLogger("aiohttp").setLevel(logging.DEBUG)