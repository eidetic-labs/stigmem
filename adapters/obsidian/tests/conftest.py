"""conftest.py — add src and SDK directories to sys.path."""

import sys
from pathlib import Path

_HERE = Path(__file__).parent
_ADAPTER_ROOT = _HERE.parent
_REPO_ROOT = _ADAPTER_ROOT.parent.parent

sys.path.insert(0, str(_ADAPTER_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT / "sdks" / "stigmem-py" / "src"))
