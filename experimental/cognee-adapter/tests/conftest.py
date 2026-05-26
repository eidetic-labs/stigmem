"""conftest.py - add the adapter package and SDK directories to sys.path."""

import sys
from pathlib import Path

_HERE = Path(__file__).parent

sys.path.insert(0, str(_HERE.parent / "src"))

_REPO_ROOT = _HERE.parent.parent.parent.parent  # tests/ -> cognee/ -> adapters/ -> stigmem/ -> root
sys.path.insert(0, str(_REPO_ROOT / "sdks" / "stigmem-py" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "node" / "src"))
