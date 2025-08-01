# Contributing to VETTING Python Framework

Thank you for your interest in contributing to the VETTING framework! This document provides guidelines for contributing to this project.

## 📋 Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please be respectful and professional in all interactions.

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- GitHub account

### Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/vetting-python.git
   cd vetting-python
   ```

3. **Set up development environment**:
   ```bash
   make dev-install
   ```

4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 📝 Development Workflow

### Making Changes

1. **Write your code** following the existing style
2. **Add tests** for new functionality
3. **Run quality checks**:
   ```bash
   make format      # Format code
   make lint        # Check linting
   make type-check  # Check types
   make test        # Run tests
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add: brief description of your changes"
   ```

### Commit Message Format

Use clear, descriptive commit messages:
- `Add: new feature or functionality`
- `Fix: bug fixes`
- `Update: changes to existing features`
- `Docs: documentation changes`
- `Test: adding or updating tests`

### Pull Request Process

1. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request** on GitHub with:
   - Clear title and description
   - Reference any related issues
   - Include screenshots if UI changes
   - Add tests for new features

3. **Code Review Process**:
   - All PRs require review from maintainers
   - Address any feedback promptly
   - Ensure all checks pass

## 🧪 Testing

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_specific.py
```

### Writing Tests

- Add tests for all new functionality
- Follow existing test patterns
- Use descriptive test names
- Include edge cases and error conditions

## 📚 Documentation

### Code Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings
- Include type hints for all parameters and return values

### README and Docs

- Update README.md if adding new features
- Add examples for new functionality
- Update CHANGELOG.md for significant changes

## 🔍 Code Style

### Python Style Guide

- Follow PEP 8
- Use Black for formatting (`make format`)
- Use isort for import sorting
- Maximum line length: 100 characters

### Type Hints

- Use type hints for all functions
- Import types from `typing` module when needed
- Run `make type-check` to verify types

## 🚫 What Not to Contribute

Please avoid:
- Breaking changes without discussion
- Changes to core architecture without approval
- Adding large dependencies without justification
- Changing version numbers (handled by maintainers)
- Modifying release workflows

## 🐛 Reporting Issues

### Bug Reports

Include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages/stack traces

### Feature Requests

Include:
- Clear description of the feature
- Use case and motivation
- Possible implementation approach
- Consider if it fits the project scope

## 📦 Release Process

**Note**: Only maintainers can create releases.

1. Version updates are handled by maintainers
2. Releases are created through GitHub releases
3. PyPI publishing is automated via GitHub Actions

## 🔒 Security

### Reporting Security Issues

**Do not report security issues publicly.** Instead:
- Email: hli3@ufl.edu
- Include detailed description
- Provide steps to reproduce if possible

### Security Best Practices

- Never commit API keys or secrets
- Use environment variables for sensitive data
- Follow secure coding practices

## 📞 Getting Help

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and discussions
- **Email**: hli3@ufl.edu for security issues or urgent matters

### Before Asking for Help

1. Check existing issues and discussions
2. Read the documentation
3. Try the examples in the repository

## 🎯 Contribution Areas

We welcome contributions in:

- **Core Framework**: Improvements to the dual-LLM architecture
- **Provider Support**: New LLM provider integrations
- **Educational Features**: Enhanced tutoring capabilities
- **Documentation**: Examples, guides, and API docs
- **Testing**: Unit tests, integration tests, examples
- **Performance**: Optimization and efficiency improvements

## 📋 Review Criteria

PRs are evaluated on:

- **Code Quality**: Clean, readable, well-documented code
- **Testing**: Adequate test coverage for new features
- **Documentation**: Clear documentation and examples
- **Compatibility**: Maintains backward compatibility
- **Performance**: No significant performance regressions
- **Security**: Follows security best practices

## 🎉 Recognition

Contributors will be:
- Listed in CHANGELOG.md for significant contributions
- Mentioned in release notes
- Added to a contributors section (future)

Thank you for contributing to the VETTING framework! Your contributions help make AI interactions safer and more effective for education and beyond.

---

**Questions?** Feel free to open a discussion or reach out to the maintainers!