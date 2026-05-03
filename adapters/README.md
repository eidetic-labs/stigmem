# Stigmem Adapter Suite

Each subdirectory is a standalone connector adapter that bridges Stigmem with a
third-party memory or reasoning backend.

| Adapter | Backend | Tests |
|---------|---------|-------|
| `cognee/` | Cognee knowledge graph | 24 |
| `gemini/` | Google Gemini function-calling | 17 |
| `letta/` | Letta agent memory | 20 |
| `openai-tools/` | OpenAI tool-call schema | 13 |
| `zep/` | Zep long-term memory | 22 |

---

## Running tests

### Per-adapter (recommended for development)

Run a single adapter's tests in isolation from its directory.  
The `--project ../../node` flag reuses the node project's virtual environment.

```bash
cd adapters/letta
uv run --project ../../node pytest tests/ -v

# Or any of the other adapters
cd adapters/gemini     && uv run --project ../../node pytest tests/ -v
cd adapters/openai-tools && uv run --project ../../node pytest tests/ -v
cd adapters/cognee     && uv run --project ../../node pytest tests/ -v
cd adapters/zep        && uv run --project ../../node pytest tests/ -v
```

### Repo-wide (all adapters in one shot)

From the repository root, run all adapter test suites together:

```bash
uv run pytest adapters/ -v
```

Expected output: **96 tests passed** across the five connector adapters (plus any
additional adapters in this directory).

> **How module-name collisions are avoided**
>
> Each adapter ships `tests/test_adapter.py` and `tests/conftest.py` with
> identical Python module names.  Three changes work together to prevent
> collection-time collisions:
>
> 1. An empty `__init__.py` at each adapter root (e.g. `adapters/letta/__init__.py`)
>    lets pytest compute unique package paths such as `letta.tests.conftest`
>    instead of the generic `tests.conftest`.
> 2. `--import-mode=importlib` in the root `pyproject.toml` `addopts` lets pytest
>    handle the `openai-tools` directory name (which contains a hyphen and is not
>    a valid Python identifier in normal import mode).
> 3. `adapters/conftest.py` provides a `pytest_collect_file` hook that clears
>    `sys.modules['adapter']` and promotes the correct adapter directory to the
>    front of `sys.path` before each test file is imported, preventing the shared
>    `adapter` module name from resolving to the wrong adapter's implementation.
