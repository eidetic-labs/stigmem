"""conftest.py — add the adapter and SDK directories to sys.path."""

import sys
from pathlib import Path

_HERE = Path(__file__).parent

sys.path.insert(0, str(_HERE.parent))  # stigmem/adapters/letta/

_REPO_ROOT = _HERE.parent.parent.parent.parent  # tests/ -> letta/ -> adapters/ -> stigmem/ -> root
sys.path.insert(0, str(_REPO_ROOT / "sdks" / "stigmem-py" / "src"))
