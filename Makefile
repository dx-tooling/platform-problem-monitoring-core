.PHONY: install format format-check lint lint-fix type-check security-check quality ci-quality venv clean help activate-venv
.PHONY: format-check-files isort-check-files lint-files type-check-files security-check-files
.PHONY: test test-verbose test-coverage test-file update-deps
.PHONY: bump-version release

PYTHON = python3
PACKAGE = platform_problem_monitoring_core

# Detect if we're running in CI environment
ifeq ($(CI),true)
    # In CI, use commands directly (no venv prefix)
    CMD_PREFIX =
else
    # Locally, use commands from venv
    CMD_PREFIX = venv/bin/
endif

VENV_BIN = venv/bin

help:
	@echo "Available commands:"
	@echo "  make install        Install package and development dependencies"
	@echo "  make activate-venv  Instructions to activate the virtual environment"
	@echo "  make format         Format code with black and isort"
	@echo "  make format-check   Check if code is properly formatted without modifying files"
	@echo "  make lint           Run linters (ruff)"
	@echo "  make lint-fix       Run linters and auto-fix issues where possible"
	@echo "  make type-check     Run mypy type checking"
	@echo "  make security-check Run bandit security checks"
	@echo "  make quality        Run all code quality checks (with formatting)"
	@echo "  make ci-quality     Run all code quality checks (without modifying files)"
	@echo "  make test           Run tests"
	@echo "  make test-verbose   Run tests with verbose output"
	@echo "  make test-coverage  Run tests with coverage report"
	@echo "  make test-file      Run tests for a specific file (usage: make test-file file=path/to/test_file.py)"
	@echo "  make update-deps    Update all dependencies to their latest semver-compatible versions"
	@echo "  make bump-version   Update the version number in pyproject.toml"
	@echo "  make release        Create a new release tag (after running quality checks and tests)"
	@echo "  make clean          Remove build artifacts and cache directories"
	@echo "  make help           Show this help message"

venv:
	$(PYTHON) -m venv venv
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install -e ".[dev]"
	$(VENV_BIN)/pre-commit install

install: venv

# This doesn't actually activate, but shows how to activate
activate-venv:
	@echo "To activate the virtual environment, run:"
	@echo "  source venv/bin/activate"
	@echo ""
	@echo "After you're done, you can deactivate by running:"
	@echo "  deactivate"

format:
	$(CMD_PREFIX)black src
	$(CMD_PREFIX)isort src

format-check:
	$(CMD_PREFIX)black --check src
	$(CMD_PREFIX)isort --check src

# Pre-commit compatible targets that operate on specific files
format-check-files:
	$(CMD_PREFIX)black --check $(filter-out $@,$(MAKECMDGOALS))

isort-check-files:
	$(CMD_PREFIX)isort --check $(filter-out $@,$(MAKECMDGOALS))

lint:
	$(CMD_PREFIX)ruff check src

lint-fix:
	$(CMD_PREFIX)ruff check --fix src

lint-files:
	$(CMD_PREFIX)ruff check $(filter-out $@,$(MAKECMDGOALS))

type-check:
	$(CMD_PREFIX)mypy src

type-check-files:
	$(CMD_PREFIX)mypy $(filter-out $@,$(MAKECMDGOALS))

security-check:
	$(CMD_PREFIX)bandit -r src -x src/tests

security-check-files:
	if [[ "$(filter-out $@,$(MAKECMDGOALS))" == *"test_"* ]]; then \
		echo "Skipping security check for test file"; \
	else \
		$(CMD_PREFIX)bandit $(filter-out $@,$(MAKECMDGOALS)); \
	fi

# Dependency management
update-deps:
	$(CMD_PREFIX)pip install --upgrade -e ".[dev]"
	@echo "Dependencies updated to their latest semver-compatible versions"

# Test targets
test:
	$(CMD_PREFIX)pytest src/tests

test-verbose:
	$(CMD_PREFIX)pytest -v src/tests

test-coverage:
	$(CMD_PREFIX)pytest --cov=$(PACKAGE) --cov-report=term-missing --cov-report=xml src/tests

test-file:
	$(CMD_PREFIX)pytest $(file) -v

quality: format lint type-check security-check

ci-quality: format-check lint type-check security-check

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -f .coverage
	rm -f coverage.xml
	rm -f venv

# This allows passing filenames as arguments to make targets
%:
	@:

# Version Management
bump-version:
	@echo "Current version: $(shell grep -m 1 version pyproject.toml | cut -d '"' -f 2)"
	@read -p "New version: " new_version; \
	sed -i '' "s/version = \"[0-9]*\.[0-9]*\.[0-9]*\"/version = \"$$new_version\"/" pyproject.toml

# Creating a new release
release: ci-quality test-coverage
	@version=$$(grep -m 1 version pyproject.toml | cut -d '"' -f 2); \
	git tag -a "v$$version" -m "Release v$$version"; \
	echo "Created tag v$$version. Push with: git push origin v$$version"
