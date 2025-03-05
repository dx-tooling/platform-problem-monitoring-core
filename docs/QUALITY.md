# Code Quality Guidelines

This document describes the code quality tools and practices used in this project.

## Code Quality Tools

We use the following tools to maintain high code quality:

### Ruff

[Ruff](https://github.com/charliermarsh/ruff) is an extremely fast Python linter, written in Rust. It includes many checks from tools like flake8, isort, pycodestyle, and many plugins.

```bash
# Run Ruff
make lint
```

### Black

[Black](https://github.com/psf/black) is an uncompromising code formatter for Python. It applies a consistent style by reformatting your code.

```bash
# Format code with Black
make format
```

### isort

[isort](https://github.com/PyCQA/isort) sorts your imports alphabetically, and automatically separated into sections and by type.

```bash
# Run isort (included in format command)
make format
```

### mypy

[mypy](https://github.com/python/mypy) is an optional static type checker for Python. It helps catch common errors before runtime.

```bash
# Run mypy
make type-check
```

### Bandit

[Bandit](https://github.com/PyCQA/bandit) is a tool designed to find common security issues in Python code.

```bash
# Run security checks
make security-check
```

### pre-commit

[pre-commit](https://pre-commit.com/) runs these checks automatically before each commit, ensuring that only quality code enters the repository.

```bash
# Install pre-commit hooks
pre-commit install
```

## Running All Checks

You can run all quality checks at once:

```bash
make quality
```

## VS Code Integration

This project includes VS Code settings that integrate all these tools into your editor. With the proper extensions installed, you'll get:

- Real-time type checking
- Automatic formatting on save
- Inline error highlighting
- Code actions to fix issues

## Recommended VS Code Extensions

- Python (Microsoft)
- Pylance (Microsoft)
- Ruff (Astral Software)
- Even Better TOML (tamasfe)
- YAML (Red Hat)

## Code Style Guidelines

1. **Type Annotations**: All functions should have complete type annotations.
2. **Docstrings**: All public methods and functions should have Google-style docstrings.
3. **Line Length**: Maximum line length is 100 characters.
4. **Imports**: Imports should be sorted by isort with the Black profile.
5. **Naming**: Follow PEP8 naming conventions:
   - Classes: `PascalCase`
   - Functions, methods, variables: `snake_case`
   - Constants: `UPPER_SNAKE_CASE`
   - Private members: start with underscore `_private_method()`

## Continuous Integration

These quality checks are also run in CI to ensure that all code entering the main branch maintains the expected level of quality.
