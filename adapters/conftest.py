"""Top-level conftest for adapters/ — fixes sys.modules isolation between adapters.

Each adapter ships its own adapter.py and exposes it via `from adapter import X`.
When all adapters are collected in a single pytest session, the first adapter's
adapter.py gets cached in sys.modules['adapter'], causing ImportError for every
subsequent adapter that tries the same import.

The pytest_collect_file hook below clears that cache and re-orders sys.path so
the correct adapter.py is always imported first for each test file.
"""

import sys
from pathlib import Path


def pytest_collect_file(parent, file_path):
    """Ensure each adapter test file sees its own adapter.py."""
    if file_path.name != "test_adapter.py":
        return None

    # test_adapter.py lives at adapter_dir/tests/test_adapter.py
    adapter_dir = file_path.parent.parent
    if adapter_dir.parent.name != "adapters":
        return None

    adapter_str = str(adapter_dir)

    # Drop any cached 'adapter' module from a previous adapter's collection
    sys.modules.pop("adapter", None)

    # Promote this adapter's directory to the front of sys.path so the
    # subsequent module import resolves to the right adapter.py
    try:
        sys.path.remove(adapter_str)
    except ValueError:
        pass
    sys.path.insert(0, adapter_str)

    return None
