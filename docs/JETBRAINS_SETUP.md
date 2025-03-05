# JetBrains IDE Setup Guide

This guide explains how to set up and use JetBrains IDEs (PyCharm, IntelliJ IDEA, etc.) with this project, particularly focusing on the code quality tools.

## Initial Setup

1. Open the project in your JetBrains IDE
2. Ensure you've installed the project dependencies:
   ```bash
   make install
   ```
3. The IDE should automatically detect the project structure and Python interpreter from the `.idea` directory settings

## Python SDK Setup

If the Python interpreter isn't automatically detected:

1. Go to `File > Project Structure`
2. Under Project Settings > Project, select the Python interpreter from your virtual environment
3. Make sure it's pointing to the `venv/bin/python` interpreter in your project directory

## Run Configurations

We've included several predefined run configurations to help you verify code quality:

- **Black Format**: Formats your code according to Black style
- **Ruff Lint**: Runs the Ruff linter to check for code issues
- **Ruff Lint Fix**: Runs the Ruff linter and automatically fixes issues where possible
- **Mypy Type Check**: Verifies type annotations
- **All Quality Checks**: Runs all quality checks at once
- **Make Lint Fix**: Runs make lint-fix to automatically fix linting issues

To run any of these:

1. Click on the run configuration dropdown in the top-right toolbar
2. Select the desired configuration
3. Click the run button (green triangle)

## Code Inspection

We've configured the IDE's inspection profiles to match our quality standards:

1. Type checking is enabled with strict mode
2. PEP 8 style checking is enabled
3. Python version compatibility checks are enabled

## External Tools Integration

### Black

Black auto-formatting is enabled in the editor:

1. The code will be auto-formatted on save
2. You can also press `Ctrl+Alt+L` (or `Cmd+Alt+L` on macOS) to format the current file

### Ruff

Ruff can both check for issues and fix them:

1. Run "Ruff Lint" to check for issues
2. Run "Ruff Lint Fix" to automatically fix issues where possible
3. From the terminal: `make lint` to check, `make lint-fix` to check and fix

### Keyboard Shortcuts

- **Reformat Code**: `Ctrl+Alt+L` (Windows/Linux) or `Cmd+Alt+L` (macOS)
- **Run Current Configuration**: `Shift+F10` (Windows/Linux) or `Ctrl+R` (macOS)
- **Debug Current Configuration**: `Shift+F9` (Windows/Linux) or `Ctrl+D` (macOS)

## Using the Terminal Tool Window

You can also run the Makefile commands directly from the Terminal tool window:

1. Open the Terminal tool window (`Alt+F12` or `View > Tool Windows > Terminal`)
2. Run commands like:
   ```bash
   make quality
   make lint
   make lint-fix
   make format
   ```

## Code Commits

When committing code, the pre-commit hooks will run automatically if you've installed them with:

```bash
pre-commit install
```

This helps catch issues before they're committed to the repository.

## Best Practices

1. **Enable Auto Import**: Under Settings > Editor > General > Auto Import, enable "Add unambiguous imports on the fly"
2. **Use Type Hints**: The IDE will show type hint errors as you type
3. **Run Type Checking Often**: Use the Mypy run configuration frequently to catch type issues
4. **Fix Linting Issues Automatically**: Use `make lint-fix` to automatically fix many common issues

## Troubleshooting

If you experience issues with the IDE:

1. **Invalidate Caches**: Try `File > Invalidate Caches and Restart`
2. **Sync Project with pyproject.toml**: Ensure the IDE settings match the `pyproject.toml` settings
3. **Check the Terminal**: Run commands directly in the terminal to see if errors are IDE-specific
