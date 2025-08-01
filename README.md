# VETTING Framework - Python Implementation

[![PyPI version](https://img.shields.io/pypi/v/vetting-python)](https://pypi.org/project/vetting-python/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1iB9QXe5YjW2S0ELZunrcm6ZnMCBKdI7m?usp=sharing)


A Python implementation of the VETTING (Verification and Evaluation Tool for Targeting Invalid Narrative Generation) framework for LLM safety and educational applications.

**Developed by [VIABLE Lab](https://www.viablelab.org/) at the University of Florida.**

## Overview

The VETTING framework implements a dual-LLM architecture that separates conversational logic from policy enforcement, preventing prompt injection attacks on safety rules and enabling verifiable policy compliance. This architectural approach is particularly effective for educational applications where you need to guide learning without revealing direct answers.

### Key Features

- **🛡️ Architectural Policy Isolation**: Complete separation between user interaction (Chat-Layer) and policy enforcement (Verification-Layer)
- **🔄 Iterative Verification Loop**: Automatic refinement when responses don't meet verification criteria
- **🏫 Educational Focus**: Specialized support for tutoring and homework help scenarios
- **🌐 Multi-Provider Support**: Works with OpenAI, Anthropic Claude, and Google Gemini
- **💰 Cost Tracking**: Comprehensive cost monitoring and analysis
- **⚙️ Flexible Configuration**: Environment variables, config files, or programmatic setup
- **🔍 Safety Features**: Built-in safety prefix detection and content filtering

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   User Input    │    │  Chat-Layer     │
│                 │───▶│    (LLM-A)      │
│                 │    │                 │
└─────────────────┘    └─────────┬───────┘
                                 │
                                 ▼
                       ┌─────────────────┐
                       │ Verification-   │
                       │   Layer         │◀─── Confidential
                       │   (LLM-B)       │     Policy
                       └─────────┬───────┘
                                 │
                                 ▼
                       ┌─────────────────┐
                       │  Pass/Fail +    │
                       │  Feedback       │
                       └─────────────────┘
```

## Installation

### From PyPI:

```bash
pip install vetting-python
```

**✅ Now available on PyPI!** View the package: [https://pypi.org/project/vetting-python/](https://pypi.org/project/vetting-python/)

### 🚀 Try it Now - Interactive Demo:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1iB9QXe5YjW2S0ELZunrcm6ZnMCBKdI7m?usp=sharing)

**Get started in seconds!** Click the Colab badge above to try VETTING framework with interactive examples - no installation required!

### From Source:

```bash
git clone https://github.com/hichipli/vetting-python.git
cd vetting-python
pip install -e .
```

### Dependencies

```bash
pip install aiohttp pydantic dataclasses-json
```

Optional dependencies:
```bash
pip install PyYAML  # For YAML configuration files
```

## 🎯 Quick Start

> **🚀 Want to try immediately?** [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1iB9QXe5YjW2S0ELZunrcm6ZnMCBKdI7m?usp=sharing) - Interactive demo with examples!

### 1. Set up your API keys

```bash
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-claude-api-key"  # Optional
export GOOGLE_API_KEY="your-gemini-api-key"     # Optional
```

### 2. Basic Chat Mode

```python
import asyncio
from vetting_python import VettingFramework, VettingConfig, ChatMessage, OpenAIProvider

async def basic_example():
    # Setup provider
    provider = OpenAIProvider(api_key="your-api-key")
    
    # Create framework
    framework = VettingFramework(chat_provider=provider)
    
    # Simple chat configuration
    config = VettingConfig(
        mode="chat",
        chat_model={"model_id": "gpt-4o-mini", "temperature": 0.7}
    )
    
    # Create conversation
    messages = [ChatMessage("user", "Explain photosynthesis in simple terms.")]
    
    # Process
    response = await framework.process(messages, config)
    print(f"Response: {response.content}")
    print(f"Cost: ${response.total_cost:.4f}")

# Run the example
asyncio.run(basic_example())
```

### 3. Educational Vetting Mode

```python
import asyncio
from vetting_python import VettingFramework, OpenAIProvider
from vetting_python.config import VettingConfigBuilder

async def educational_example():
    provider = OpenAIProvider(api_key="your-api-key")
    framework = VettingFramework(chat_provider=provider)
    
    # Educational configuration with answer key
    config = (VettingConfigBuilder()
              .vetting_mode()
              .chat_model("gpt-4o-mini")
              .verification_model("gpt-4o-mini")
              .add_context_item(
                  question_text="What is the capital of France?",
                  correct_answer="Paris",
                  key_concepts=["Paris", "France", "capital city"]
              )
              .build())
    
    # Student asks directly for the answer
    messages = [ChatMessage("user", "What is the capital of France? I need this for homework.")]
    
    # Process with verification
    response = await framework.process(messages, config)
    
    print(f"Response: {response.content}")
    print(f"Verification passed: {response.verification_passed}")
    print(f"Attempts made: {response.attempt_count}")

asyncio.run(educational_example())
```

## Configuration

### Environment Variables

The framework supports comprehensive configuration through environment variables:

```bash
# API Keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."

# Default Models
export VETTING_DEFAULT_CHAT_MODEL="gpt-4o-mini"
export VETTING_DEFAULT_VERIFICATION_MODEL="gpt-4o-mini"
export VETTING_DEFAULT_PROVIDER="openai"

# Generation Parameters
export VETTING_TEMPERATURE_CHAT="0.7"
export VETTING_TEMPERATURE_VERIFICATION="0.1"
export VETTING_MAX_TOKENS_CHAT="1024"
export VETTING_MAX_TOKENS_VERIFICATION="512"
export VETTING_MAX_ATTEMPTS="3"

# Features
export VETTING_ENABLE_SAFETY_PREFIX="true"
export VETTING_ENABLE_EDUCATIONAL_RULES="true"
export VETTING_ENABLE_COST_TRACKING="true"

# Logging
export VETTING_LOG_LEVEL="INFO"
export VETTING_LOG_REQUESTS="false"
```

### Configuration Files

You can also use JSON or YAML configuration files:

```json
{
  "providers": {
    "openai": {
      "provider_type": "openai",
      "api_key": "your-key",
      "timeout": 60,
      "max_retries": 3
    }
  },
  "default_provider": "openai",
  "default_chat_model": "gpt-4o-mini",
  "default_verification_model": "gpt-4o-mini",
  "enable_safety_prefix": true,
  "enable_educational_rules": true
}
```

```python
from vetting_python.config import VettingSettings

# Load from file
settings = VettingSettings.from_file("config.json")

# Load from environment
settings = VettingSettings.from_env()

# Create provider and framework
provider = settings.get_provider_instance("openai")
framework = VettingFramework(chat_provider=provider)
```

## Advanced Usage

### Multi-Provider Setup

```python
from vetting_python import OpenAIProvider, ClaudeProvider

# Use different providers for chat and verification
chat_provider = OpenAIProvider(api_key="openai-key")
verification_provider = ClaudeProvider(api_key="claude-key")

framework = VettingFramework(
    chat_provider=chat_provider,
    verification_provider=verification_provider
)

config = VettingConfig(
    mode="vetting",
    chat_model={"model_id": "gpt-4o-mini"},
    verification_model={"model_id": "claude-3-haiku"}
)
```

### Cost Tracking

```python
from vetting_python.utils import CostTracker

# Setup cost tracking
cost_tracker = CostTracker(enable_persistence=True)

# After processing requests
cost_tracker.track_response(response, "openai", provider, provider)

# Get cost summary
summary = cost_tracker.get_summary()
print(f"Total cost: ${summary.total_cost:.4f}")
print(f"Total tokens: {summary.total_tokens}")

# Print detailed breakdown
cost_tracker.print_summary()
```

### Complex Educational Scenarios

```python
config = (VettingConfigBuilder()
          .vetting_mode()
          .chat_model("gpt-4o-mini", temperature=0.8)
          .verification_model("gpt-4o-mini", temperature=0.1)
          .chat_system_prompt(
              "You are a Socratic tutor. Guide students through discovery "
              "rather than giving direct answers. Always end with a question."
          )
          # Multiple context items
          .add_context_item(
              question_text="What is photosynthesis?",
              subject="Biology",
              correct_answer="The process by which plants convert light energy into chemical energy",
              key_concepts=["photosynthesis", "chlorophyll", "glucose", "oxygen"],
              explanation="Plants use sunlight, CO2, and water to produce glucose and oxygen"
          )
          .add_context_item(
              question_text="What gas do plants absorb during photosynthesis?",
              subject="Biology",
              correct_answer="Carbon dioxide",
              key_concepts=["carbon dioxide", "CO2"]
          )
          .safety_features(enable_educational_rules=True)
          .session_info(session_id="tutoring_001", user_id="student_123")
          .build())
```

### Validation and Error Handling

```python
from vetting_python.utils import ValidationUtils

# Validate configuration
validation = ValidationUtils.validate_vetting_config(config)
if not validation["valid"]:
    print(f"Config errors: {validation['issues']}")

# Validate messages
validation = ValidationUtils.validate_messages(messages)
if validation["warnings"]:
    print(f"Message warnings: {validation['warnings']}")

# Validate API key format
validation = ValidationUtils.validate_api_key(api_key, "openai")
if not validation["valid"]:
    print(f"API key issues: {validation['issues']}")
```

## API Reference

### Core Classes

#### `VettingFramework`

The main framework class that orchestrates the dual-LLM architecture.

```python
VettingFramework(
    chat_provider: Provider,
    verification_provider: Optional[Provider] = None
)
```

**Methods:**
- `async process(messages: List[ChatMessage], config: VettingConfig) -> VettingResponse`

#### `VettingConfig`

Configuration object for the vetting process.

```python
VettingConfig(
    mode: Literal["chat", "vetting"] = "vetting",
    chat_model: ModelConfig,
    verification_model: Optional[ModelConfig] = None,
    max_attempts: int = 3,
    chat_system_prompt: Optional[str] = None,
    verification_system_prompt: Optional[str] = None,
    context_items: Optional[List[ContextItem]] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    enable_safety_prefix: bool = True,
    enable_educational_rules: bool = True
)
```

#### `VettingResponse`

Response object containing the result and metadata.

```python
@dataclass
class VettingResponse:
    content: str
    mode: Literal["chat", "vetting"]
    requires_attention: bool = False
    verification_passed: Optional[bool] = None
    attempt_count: int = 1
    stop_reason: Optional[StopReason] = None
    attempts: Optional[List[AttemptDetail]] = None
    chat_usage: Optional[Usage] = None
    verification_usage: Optional[Usage] = None
    total_usage: Optional[Usage] = None
    total_cost: float = 0.0
    processing_time_ms: Optional[float] = None
    # ... additional metadata fields
```

### Configuration Builder

The `VettingConfigBuilder` provides a fluent API for building configurations:

```python
config = (VettingConfigBuilder()
          .vetting_mode()  # or .chat_mode()
          .chat_model("gpt-4o-mini", temperature=0.7, max_tokens=1024)
          .verification_model("gpt-4o-mini", temperature=0.1, max_tokens=512)
          .max_attempts(3)
          .add_context_item(
              question_text="What is X?",
              correct_answer="Y",
              key_concepts=["concept1", "concept2"]
          )
          .safety_features(enable_safety_prefix=True, enable_educational_rules=True)
          .session_info(session_id="session_123", user_id="user_456")
          .build())
```

### Providers

#### `OpenAIProvider`

```python
OpenAIProvider(
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    max_retries: int = 3,
    timeout: int = 60,
    organization: Optional[str] = None
)
```

**Supported Models (2025 Pricing):**
- `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`
- `gpt-4o`, `gpt-4o-mini`
- Aliases: `gpt-4o-latest` → `gpt-4o`

#### `ClaudeProvider`

```python
ClaudeProvider(
    api_key: str,
    base_url: str = "https://api.anthropic.com",
    max_retries: int = 3,
    timeout: int = 60
)
```

**Supported Models (2025 Pricing):**
- `claude-sonnet-4`, `claude-sonnet-3.7`, `claude-sonnet-3.5`
- Aliases: `claude-4` → `claude-sonnet-4`

#### `GeminiProvider`

```python
GeminiProvider(
    api_key: str,
    base_url: str = "https://generativelanguage.googleapis.com",
    max_retries: int = 3,
    timeout: int = 60
)
```

**Supported Models (2025 Pricing):**
- `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`
- `gemini-2.0-flash`, `gemini-2.0-flash-lite`
- Aliases: `gemini-2.5` → `gemini-2.5-pro`

## Use Cases

### 1. Educational Tutoring

Perfect for homework help platforms where you want to guide learning without giving away answers:

```python
# Student asks: "What is the quadratic formula?"
# Instead of giving the formula directly, VETTING guides:
# "Great question! Let's think about this step by step. 
# What do you know about quadratic equations? What form do they take?"
```

### 2. Assessment Integrity

Maintain assessment integrity while still providing help:

```python
# During an exam, student asks for direct answer
# VETTING detects this violates policy and provides guidance instead:
# "I can't give you the direct answer, but I can help you think through 
# the problem. What approach would you take to solve this type of question?"
```

### 3. Content Safety

Prevent harmful or inappropriate responses while maintaining helpful interaction:

```python
# User asks about dangerous activities
# VETTING detects safety concern and responds appropriately:
# "[REQUIRES_ATTENTION] I understand you're curious, but I can't provide 
# information that could be harmful. Instead, let me suggest some safe 
# alternatives..."
```

### 4. Corporate Training

Ensure training materials adhere to company policies and learning objectives:

```python
# Training scenario with specific learning outcomes
# VETTING ensures responses align with corporate training goals
# while preventing disclosure of confidential information
```

## Best Practices

### 1. Configuration Management

- Use environment variables for API keys and basic settings
- Use configuration files for complex setups
- Validate configurations before use
- Keep verification model parameters more conservative (lower temperature)

### 2. Cost Management

- Enable cost tracking in production
- Monitor usage patterns and optimize model selection
- Use cheaper models for verification when possible
- Set up cost alerts for production systems

### 3. Educational Applications

- Design clear learning objectives for context items
- Use specific key concepts to avoid revealing
- Set appropriate maximum attempts (2-3 for homework, 1 for assessments)
- Always include explanations in answer keys for better verification

### 4. Error Handling

- Always validate inputs before processing
- Implement proper retry logic for provider failures
- Log verification failures for analysis
- Have fallback responses for system errors

### 5. Production Deployment

- Use connection pooling for high-throughput applications
- Implement proper monitoring and alerting
- Cache provider instances to avoid recreation overhead
- Set up log aggregation for debugging

## Examples

### 🎮 Interactive Examples

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1iB9QXe5YjW2S0ELZunrcm6ZnMCBKdI7m?usp=sharing) **Try live examples in your browser!**

### 📁 Local Examples

The `vetting_python/examples/` directory contains comprehensive examples:

- `basic_usage.py` - Getting started examples
- `advanced_usage.py` - Complex scenarios and custom providers
- `integration_patterns.py` - Web API and platform integration examples

Run the examples:

```bash
cd vetting_python/examples
python basic_usage.py
python advanced_usage.py
python integration_patterns.py
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
git clone https://github.com/your-org/vetting-python.git
cd vetting-python
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
black vetting_python/
isort vetting_python/
mypy vetting_python/
```

## Research Citation

If you use VETTING in your research, please cite our paper (citation will be updated upon publication):

```bibtex
@misc{vetting2025,
  title={VETTING: Verification and Evaluation Tool for Targeting Invalid Narrative Generation},
  author={VETTING Research Team},
  year={2025},
  note={Available at: https://github.com/hichipli/vetting-python}
}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📚 Documentation: [README.md](https://github.com/hichipli/vetting-python#readme)
- 🐛 Issues: [GitHub Issues](https://github.com/hichipli/vetting-python/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/hichipli/vetting-python/discussions)
- 🌐 Research Lab: [VIABLE Lab](https://www.viablelab.org/)
- 📧 Contact: [Contact Form](https://www.viablelab.org/contact) or hli3@ufl.edu

## Changelog

### v0.1.0 (2025-07-31) - 🎉 PUBLISHED TO PYPI

- ✅ **Published to PyPI**: [vetting-python](https://pypi.org/project/vetting-python/)
- ✅ **Installation**: `pip install vetting-python`
- ✅ Dual-LLM architecture implementation
- ✅ OpenAI, Claude, and Gemini provider support
- ✅ Educational vetting capabilities
- ✅ Cost tracking and monitoring
- ✅ Comprehensive configuration system
- ✅ Safety feature integration
- ✅ Example applications and documentation
- ✅ Automated publishing workflow with GitHub Actions
- ✅ Security and contribution guidelines

---

Built with ❤️ for safer and more effective AI interactions in education and beyond.
