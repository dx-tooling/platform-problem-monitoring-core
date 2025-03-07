# Development

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/dx-tooling/platform-problem-monitoring-core.git
   cd platform-problem-monitoring-core
   ```

2. **Install development dependencies:**
   ```bash
   make install
   ```
   This creates a virtual environment, installs the package and all development dependencies, and sets up pre-commit hooks.

3. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

## Code Quality Tools

This project uses a unified approach to code quality with all tools configured in `pyproject.toml` and executed via:

1. **Pre-commit hooks** - Run automatically before each commit
2. **Make commands** - Run manually or in CI

Available make commands:

```bash
  make install        Install package and development dependencies
  make activate-venv  Instructions to activate the virtual environment
  make format         Format code with black and isort
  make format-check   Check if code is properly formatted without modifying files
  make lint           Run linters (ruff)
  make lint-fix       Run linters and auto-fix issues where possible
  make type-check     Run mypy type checking
  make security-check Run bandit security checks
  make quality        Run all code quality checks (with formatting)
  make ci-quality     Run all code quality checks (without modifying files)
  make test           Run tests
  make test-verbose   Run tests with verbose output
  make test-coverage  Run tests with coverage report
  make test-file      Run tests for a specific file (usage: make test-file file=path/to/test_file.py)
  make update-deps    Update all dependencies to their latest semver-compatible versions
  make bump-version   Update the version number in pyproject.toml
  make release        Create a new release tag (after running quality checks and tests)
  make clean          Remove build artifacts and cache directories
```

The pre-commit hooks are configured to use the same Makefile targets, ensuring consistency between local development and CI environments.
