.PHONY: install format lint lint-fix type-check security-check quality venv clean help activate-venv

PYTHON = python3
PACKAGE = platform_problem_monitoring_core
VENV_BIN = venv/bin

help:
	@echo "Available commands:"
	@echo "  make install        Install package and development dependencies"
	@echo "  make activate-venv  Instructions to activate the virtual environment"
	@echo "  make format         Format code with black and isort"
	@echo "  make lint           Run linters (ruff)"
	@echo "  make lint-fix       Run linters and auto-fix issues where possible"
	@echo "  make type-check     Run mypy type checking"
	@echo "  make security-check Run bandit security checks"
	@echo "  make quality        Run all code quality checks"
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
	$(VENV_BIN)/black src/$(PACKAGE)
	$(VENV_BIN)/isort src/$(PACKAGE)

lint:
	$(VENV_BIN)/ruff check src/$(PACKAGE)

lint-fix:
	$(VENV_BIN)/ruff check --fix src/$(PACKAGE)

type-check:
	$(VENV_BIN)/mypy src/$(PACKAGE)

security-check:
	$(VENV_BIN)/bandit -r src/$(PACKAGE)

quality: format lint type-check security-check

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete 