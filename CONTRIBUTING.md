# Contributing to AI Platform

Thank you for your interest in contributing!

## DCO Sign-off (Required)

All commits must include a Developer Certificate of Origin (DCO) sign-off:

```bash
git commit -s -m "feat: add web search tool"
```

This adds `Signed-off-by: Your Name <email@example.com>` to your commit message, certifying that you wrote the code or have the right to submit it under the Apache 2.0 license.

## Branch Strategy

- `main` — protected; all changes via PR, requires at least one review and passing CI
- `feature/<name>` — new features
- `fix/<name>` — bug fixes  
- `docs/<name>` — documentation only

## Development Setup

```bash
git clone https://github.com/acmecorp/ai-platform
cd ai-platform
uv sync
docker compose -f infra/docker/docker-compose.yml up -d
uv run pytest
```

## Pull Request Process

1. Open an issue first for non-trivial changes.
2. Fork and create a branch from `main`.
3. Write tests that cover your change.
4. Run the full test suite: `uv run pytest`
5. Run linting: `uv run ruff check . && uv run ruff format .`
6. Run type checking: `uv run mypy packages/core/src`
7. Commit with `-s` (DCO sign-off).
8. Open a PR against `main`. Fill out the PR template.
9. Address review feedback.

## Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

Signed-off-by: Your Name <email@example.com>
```

Types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `perf`

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be kind.

## Security Issues

Do **not** open public issues for security vulnerabilities. See [SECURITY.md](SECURITY.md).
