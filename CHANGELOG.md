# Changelog

All notable changes to the VETTING Python framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial planning for future features

## [0.1.0] - 2025-07-31

### Added
- **Core Framework**: Complete implementation of the dual-LLM VETTING architecture
- **Provider Support**: OpenAI, Anthropic Claude, and Google Gemini API integration
- **Educational Features**: Specialized support for tutoring and homework help scenarios
- **Configuration System**: Comprehensive configuration management with environment variables, JSON/YAML files, and programmatic setup
- **Cost Tracking**: Built-in cost monitoring and analysis across providers and models
- **Safety Features**: Safety prefix detection and content filtering
- **Validation System**: Comprehensive input validation and error handling
- **Examples**: Basic usage, advanced scenarios, and integration patterns
- **Documentation**: Complete README with API reference and best practices

### Features
- **VettingFramework**: Main orchestration class for dual-LLM processing
- **VettingConfig**: Flexible configuration object with builder pattern support
- **Multiple Providers**: OpenAI, Claude, and Gemini with automatic retry and error handling
- **Educational Vetting**: Context-aware verification for learning scenarios
- **Multi-turn Conversations**: Support for long conversations with context management
- **Batch Processing**: Efficient handling of multiple requests
- **Custom Providers**: Extensible provider interface for custom implementations
- **Production Ready**: Monitoring, logging, and error handling for production deployments

### Technical Details
- **Python**: Supports Python 3.8+
- **Async/Await**: Full asynchronous support for high-performance applications
- **Type Safety**: Comprehensive type hints and mypy compatibility
- **Testing**: Unit tests and integration test examples
- **Code Quality**: Black formatting, isort imports, and comprehensive linting

### Documentation
- Complete API reference with examples
- Detailed configuration guide
- Best practices for production deployment
- Educational use case examples
- Integration patterns for web applications

### Examples
- `basic_usage.py`: Getting started with chat and vetting modes
- `advanced_usage.py`: Complex educational scenarios and custom providers  
- `integration_patterns.py`: Web API and platform integration examples

### Architecture
- **Chat-Layer (LLM-A)**: User-facing conversational model
- **Verification-Layer (LLM-B)**: Policy enforcement model with confidential prompts
- **Feedback Loop**: Iterative refinement when verification fails
- **Architectural Isolation**: Complete separation of user interaction and policy enforcement

### Use Cases
- Educational tutoring and homework help
- Assessment integrity maintenance
- Content safety and moderation
- Corporate training with policy compliance
- Research applications requiring verifiable AI behavior

[Unreleased]: https://github.com/hichipli/vetting-python/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/hichipli/vetting-python/releases/tag/v0.1.0