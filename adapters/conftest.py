"""Top-level conftest for adapters/ test isolation.

Several adapters expose their implementation as ``from adapter import ...`` and
also keep tests under same-named ``tests/`` directories. During aggregate test
collection, pytest would otherwise reuse the first imported ``adapter`` module
for subsequent adapter suites. The hook below resets that shared import and
promotes the correct adapter directory on ``sys.path`` before each adapter test
module is imported.
"""

from contextlib import suppress
import sys


def pytest_collect_file(parent, file_path):
    """Ensure each adapter test file sees its own adapter.py."""
    if file_path.suffix != ".py" or not file_path.name.startswith("test_"):
        return None

    # adapter tests live at adapters/<adapter>/tests/test_*.py
    tests_dir = file_path.parent
    adapter_dir = tests_dir.parent
    if tests_dir.name != "tests" or adapter_dir.parent.name != "adapters":
        return None

    adapter_str = str(adapter_dir)

    # Drop any cached 'adapter' module from a previous adapter's collection
    sys.modules.pop("adapter", None)

    # Promote this adapter's directory to the front of sys.path so the
    # subsequent module import resolves to the right adapter.py
    with suppress(ValueError):
        sys.path.remove(adapter_str)
    sys.path.insert(0, adapter_str)

    return None
