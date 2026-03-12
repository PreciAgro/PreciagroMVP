# Contributing to PreciAgro

Thank you for your interest in contributing to **PreciAgro**! This document outlines the process for submitting contributions, reporting issues, and collaborating with the team.

---

## Code of Conduct

We are committed to fostering a welcoming and inclusive environment. All contributors are expected to:
- Be respectful and considerate in discussions
- Provide constructive feedback
- Avoid discriminatory or harassing behavior

---

## How to Contribute

### 1. Reporting Issues

If you find a bug or have a feature request:
1. Check [existing issues](https://github.com/YOUR_ORG/preciagro/issues) to avoid duplicates
2. Open a new issue with a clear title and description
3. Include:
   - Steps to reproduce (for bugs)
   - Expected vs. actual behavior
   - Environment details (OS, Python version, Docker version)
   - Logs or screenshots (if applicable)

### 2. Proposing Features

Before starting work on a new feature:
1. Open a **discussion** or **issue** describing the feature
2. Wait for maintainer feedback and approval
3. Create a **design document** (if the feature is complex) in `/docs/architecture/`

### 3. Submitting Code Changes

#### Branch Naming Convention

Use descriptive branch names:
- `feature/short-description`  for new features
- `fix/issue-number-short-description`  for bug fixes
- `refactor/short-description`  for code improvements
- `docs/short-description`  for documentation updates

**Example:**
```bash
git checkout -b feature/add-soil-moisture-engine
```

#### Pull Request Process

1. **Fork the repository** (if external contributor)
2. **Create a feature branch** from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature
   ```

3. **Make your changes**:
   - Follow the [Code Style](#code-style) guidelines
   - Write or update tests for your changes
   - Update relevant documentation

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add soil moisture engine with API endpoints"
   ```
   - Use [Conventional Commits](https://www.conventionalcommits.org/) format:
     - `feat:` for new features
     - `fix:` for bug fixes
     - `refactor:` for code improvements
     - `docs:` for documentation changes
     - `test:` for test updates
     - `chore:` for maintenance tasks

5. **Push to your branch**:
   ```bash
   git push origin feature/your-feature
   ```

6. **Open a Pull Request (PR)**:
   - Target the `develop` branch
   - Provide a clear title and description
   - Reference related issues (e.g., `Closes #123`)
   - Ensure CI checks pass

7. **Address review feedback**:
   - Make requested changes in new commits
   - Respond to reviewer comments
   - Re-request review after updates

8. **Merge**:
   - Maintainers will merge approved PRs
   - Delete your feature branch after merge

---

## Code Style

### Python

We enforce strict code quality standards:

- **Formatter:** [Black](https://black.readthedocs.io/) (line length: 100)
- **Import Sorter:** [isort](https://pycqa.github.io/isort/) (profile: black)
- **Linter:** [Ruff](https://beta.ruff.rs/)
- **Type Checker:** [MyPy](http://mypy-lang.org/) (gradual adoption)

#### Run Before Committing

```bash
cd backend

# Format code
black app/ tests/ scripts/
isort app/ tests/ scripts/

# Lint
ruff check app/ tests/ scripts/

# Type check
mypy app/preciagro/

# Run tests
pytest
```

#### Pre-commit Hook (Recommended)

Install [pre-commit](https://pre-commit.com/):
```bash
pip install pre-commit
pre-commit install
```

This will automatically run formatters and linters on every commit.

---

## Testing

### Writing Tests

- Place tests in the appropriate directory:
  - Engine-specific tests: `backend/app/preciagro/packages/engines/<engine_name>/tests/`
  - Integration tests: `backend/tests/`
- Use `pytest` for all tests
- Aim for **>80% code coverage**

### Running Tests

```bash
cd backend

# Run all tests
pytest

# Run specific engine tests
pytest app/preciagro/packages/engines/crop_intelligence/tests/ -v

# With coverage report
pytest --cov=app/preciagro --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Test Guidelines

- Write **unit tests** for individual functions/classes
- Write **integration tests** for API endpoints and database interactions
- Use **fixtures** for reusable test data
- Mock external dependencies (APIs, S3, etc.)

---

## Documentation

### Updating Docs

- API changes  Update docstrings and OpenAPI specs
- New engines  Add entry to `backend/README.md` and engine matrix
- Architecture changes  Update `/docs/architecture/`
- Security changes  Update `/docs/architecture/SECURITY.md`

### Writing Style

- Use clear, concise language
- Include code examples where applicable
- Follow [Markdown Best Practices](https://www.markdownguide.org/basic-syntax/)

---

## Commit Message Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`  new feature
- `fix`  bug fix
- `refactor`  code improvement (no behavior change)
- `docs`  documentation update
- `test`  test updates
- `chore`  maintenance (dependencies, config, etc.)
- `perf`  performance improvement
- `ci`  CI/CD changes

**Examples:**
```
feat(crop-intelligence): add soil moisture prediction endpoint

- Implement regression model for soil moisture forecasting
- Add new API endpoint /api/v1/soil-moisture/predict
- Update engine matrix documentation

Closes #456
```

```
fix(temporal-logic): correct timezone handling in forecasts

- Fix incorrect UTC offset in seasonal forecasts
- Add timezone validation tests

Fixes #789
```

---

## CI/CD Pipeline

All PRs must pass CI checks:

1. **Code Quality**  Black, isort, Ruff
2. **Type Checking**  MyPy (soft fail for now)
3. **Security Scanning**  Bandit, pip-audit, Gitleaks
4. **Unit Tests**  per-engine test suites
5. **Integration Tests**  cross-engine scenarios
6. **Docker Build**  ensure images build successfully

View pipeline config: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

---

## Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backward-compatible features
- **PATCH** version for backward-compatible bug fixes

---

## License

By contributing, you agree that your contributions will be licensed under the same proprietary license as the project.

---

## Questions?

- Open a [GitHub Discussion](https://github.com/YOUR_ORG/preciagro/discussions)
- Contact maintainers via the project communication channels

---

**Thank you for contributing to PreciAgro!** 
