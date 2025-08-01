# Makefile for VETTING Python framework development

.PHONY: help install dev-install test lint format type-check clean build upload docs

# Default target
help:
	@echo "VETTING Python Framework - Development Commands"
	@echo "================================================"
	@echo ""
	@echo "Setup:"
	@echo "  install      Install package in production mode"
	@echo "  dev-install  Install package in development mode with all dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  format       Format code with black and isort"
	@echo "  lint         Run linting checks"
	@echo "  type-check   Run type checking with mypy"
	@echo "  test         Run tests with pytest"
	@echo "  test-cov     Run tests with coverage reporting"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  clean        Clean build artifacts"
	@echo "  build        Build distribution packages"
	@echo "  upload       Upload to PyPI (requires authentication)"
	@echo "  upload-test  Upload to TestPyPI (requires authentication)"
	@echo ""
	@echo "Documentation:"
	@echo "  docs         Build documentation"
	@echo "  docs-serve   Serve documentation locally"
	@echo ""
	@echo "Examples:"
	@echo "  examples     Run example scripts"
	@echo "  example-basic Run basic usage example"

# Installation targets
install:
	pip install .

dev-install:
	pip install -e ".[dev,yaml,docs]"
	pre-commit install

# Code quality targets
format:
	black vetting_python/ tests/
	isort vetting_python/ tests/

lint:
	black --check vetting_python/ tests/
	isort --check-only vetting_python/ tests/
	flake8 vetting_python/ tests/

type-check:
	mypy vetting_python/

test:
	pytest tests/

test-cov:
	pytest tests/ --cov=vetting_python --cov-report=html --cov-report=term

# Build and deploy targets
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

build: clean
	python -m build

upload: build
	python -m twine upload dist/*

upload-test: build
	python -m twine upload --repository testpypi dist/*

# Documentation targets
docs:
	@echo "Documentation building not yet implemented"
	@echo "TODO: Set up Sphinx documentation"

docs-serve:
	@echo "Documentation serving not yet implemented"

# Example targets
examples:
	@echo "Running all examples..."
	@echo "Note: Make sure you have API keys configured"
	cd vetting_python/examples && python basic_usage.py
	cd vetting_python/examples && python advanced_usage.py
	cd vetting_python/examples && python integration_patterns.py

example-basic:
	@echo "Running basic usage example..."
	cd vetting_python/examples && python basic_usage.py

# Development setup verification
check-env:
	@echo "Checking development environment..."
	@python -c "import vetting_python; print(f'VETTING version: {vetting_python.__version__}')"
	@python -c "import sys; print(f'Python version: {sys.version}')"
	@echo "Environment check complete"

# Quick development cycle
dev: format type-check test
	@echo "Development checks completed successfully!"

# Release preparation
pre-release: clean format type-check test build
	@echo "Pre-release checks completed!"
	@echo "Ready for release. Run 'make upload' to deploy to PyPI."

# Help target (shown by default)
info:
	@echo "VETTING Python Framework Development Environment"
	@echo "=============================================="
	@echo ""
	@echo "Project Structure:"
	@echo "  vetting_python/     - Main package source code"
	@echo "  vetting_python/examples/ - Usage examples"
	@echo "  tests/             - Test suite"
	@echo "  docs/              - Documentation source"
	@echo ""
	@echo "Key Files:"
	@echo "  pyproject.toml     - Package configuration"
	@echo "  README.md          - Project documentation"
	@echo "  CHANGELOG.md       - Version history"
	@echo ""
	@echo "Run 'make help' for available commands."