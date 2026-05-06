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

Expected output: roughly **159 adapter tests** across the connector suites in
this directory. The exact count may drift as adapters are added or expanded.

> **How module-name collisions are avoided**
>
> Several adapters ship `tests/test_*.py` files plus local `tests/conftest.py`
> helpers. Two repo-level choices keep aggregate collection working:
>
> 1. `--import-mode=importlib` in the root `pyproject.toml` makes pytest import
>    test modules by path instead of relying on package names. That avoids
>    collisions even for adapter directories such as `openai-tools/` whose names
>    are not valid Python identifiers.
> 2. `adapters/conftest.py` provides a `pytest_collect_file` hook that clears
>    `sys.modules['adapter']` and promotes the correct adapter directory to the
>    front of `sys.path` before each adapter test module is imported,
>    preventing the shared `adapter` module name from resolving to the wrong
>    adapter implementation.
