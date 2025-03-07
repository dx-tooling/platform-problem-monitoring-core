# Platform Problem Monitoring Core - Release Management

This document outlines the release process for the Platform Problem Monitoring Core package, including version management, artifact creation, and publishing.

## Release Artifacts

Each release includes the following artifacts:

- **Source Distribution (.tar.gz)** - Contains the raw source code of the package
- **Wheel Distribution (.whl)** - A pre-built package that's ready to install

## Release Workflow

### Automated GitHub Actions Workflow

The release process uses a GitHub Actions workflow (`.github/workflows/release.yml`) that:

1. Builds Python packages (wheel and source distribution)
2. Creates a configuration templates archive
3. Creates a GitHub Release with auto-generated release notes
4. Attaches all artifacts to the release

The workflow is triggered whenever a tag with the format `v*.*.*` is pushed to the repository.

## Step-by-Step Release Process

### 1. Prepare for Release

Ensure all changes are committed, CI passes, and the code is ready for release:

```bash
# Pull latest changes
git checkout main
git pull origin main

# Run quality checks and tests
make ci-quality
make test-coverage
```

### 2. Update Version Number

Update the version in `pyproject.toml`:

```bash
# Option 1: Manual edit
# Edit pyproject.toml and change version = "x.y.z"

# Option 2: Using make command
make bump-version
```

The `bump-version` make command will:
1. Show current version
2. Prompt for new version
3. Update `pyproject.toml`

### 3. Commit Version Change

```bash
git add pyproject.toml
git commit -m "Bump version to x.y.z"
git push origin main
```

### 4. Create Release Tag

```bash
# Option 1: Manual tagging
git tag -a "vx.y.z" -m "Release vx.y.z"

# Option 2: Using make command
make release
```

The `release` make command will:
1. Run quality checks and tests
2. Create a new annotated git tag based on the version in pyproject.toml

### 5. Push Tag to Trigger Release

```bash
git push origin vx.y.z
```

This will trigger the GitHub Actions release workflow.

### 6. Verify Release

1. Go to the GitHub repository's Actions tab
2. Check that the release workflow completed successfully
3. Go to the Releases page to verify that the release was created with all artifacts

## Installation from Release Artifacts

The released package can be installed in two ways:

### 1. Using pip directly from GitHub (for applications)

```bash
pip install https://github.com/dx-tooling/platform-problem-monitoring-core/releases/download/vX.Y.Z/platform_problem_monitoring_core-X.Y.Z-py3-none-any.whl
```

### 2. For development or customization

1. Download both the wheel file and `additional_assets.zip` from the releases page
2. Extract the configuration templates
3. Follow the setup instructions in the README

## Versioning Scheme

This project follows [Semantic Versioning](https://semver.org/):

* **MAJOR version** (x.0.0) - Incompatible API changes
* **MINOR version** (0.x.0) - Add functionality in a backward compatible manner
* **PATCH version** (0.0.x) - Backward compatible bug fixes

## Release Notes Guidelines

When creating a new release:

1. Provide a summary of key changes
2. List new features
3. Document any breaking changes
4. Include any migration instructions
5. Acknowledge contributors

## Troubleshooting Release Issues

### Common Problems and Solutions

1. **Release workflow fails**
   - Check that all test dependencies are properly installed
   - Verify that tests pass locally

2. **Missing configuration files in the release**
   - Check the paths in the "Create configuration archive" step
   - Ensure all required files exist in the repository

3. **Wrong version number**
   - Check that the version in `pyproject.toml` matches the git tag
   - Ensure the tag follows the format `vX.Y.Z`
