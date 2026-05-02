# Contributing to AI Platform

Thank you for your interest in contributing! This guide covers everything you need to get started.

## Development Setup

```bash
# Prerequisites: Python 3.11+, uv, Docker, Node.js 20+, pnpm 9+

git clone https://github.com/acme/ai-platform.git
cd ai-platform

# Install Python dependencies
uv sync

# Install JS dependencies
pnpm install

# Start dev stack
docker compose -f infra/docker/docker-compose.yml up -d

# Run tests
uv run pytest
pnpm test
```

## Code Style

- **Python**: ruff for linting and formatting (`uv run ruff check . && uv run ruff format .`)
- **Mypy**: strict mode enabled; no `# type: ignore` without an explanatory comment
- **TypeScript**: ESLint + Prettier via Turborepo

Run all checks: `uv run ruff check . && uv run mypy packages/ apps/api/ && uv run pytest`

## Testing Requirements

- New public functions require unit tests
- New integrations require integration tests with mocked HTTP (use `respx`)
- Minimum coverage: 80% for new code

## Branch Strategy

- `main` — always releasable; protected; requires PR + 1 approval + CI green
- `dev` — integration branch for large feature work
- Feature branches: use `feat/`, `fix/`, or `chore/` prefixes

## Pull Request Process

1. Fork the repo and create a branch from `main` (for fixes) or `dev` (for features)
2. Make focused, small commits with conventional commit messages (`feat:`, `fix:`, `chore:`)
3. Fill in the PR template
4. Link the PR to the relevant issue
5. Sign off your commits with DCO: `git commit -s -m "feat: add thing"`
6. Wait for CI to pass and a maintainer review

## Developer Certificate of Origin (DCO)

All contributions must include a DCO sign-off. By signing off you certify that:

> I wrote this code and have the right to contribute it under the Apache 2.0 license.
> See https://developercertificate.org/ for the full text.

Sign off automatically with `git commit -s`.

## Adding a New Connector

1. Copy `packages/integrations/shopify/` as a template
2. Implement the `Connector` protocol in `src/{name}/connector.py`
3. Add tools in `src/{name}/tools.py`
4. Write integration tests with `respx` mocking
5. Add a README with auth setup instructions
6. Submit PR with the `integration` label

## Code of Conduct

This project follows the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md). Be kind.

## Good First Issues

Look for issues tagged [`good-first-issue`](https://github.com/acme/ai-platform/labels/good-first-issue) to get started.
