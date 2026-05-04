"""conftest.py — add the adapter and SDK src directories to sys.path."""

import sys
from pathlib import Path

_HERE = Path(__file__).parent
_ADAPTER_ROOT = _HERE.parent

# src/stigmem_openclaw — importable as stigmem_openclaw (installed package layout)
sys.path.insert(0, str(_ADAPTER_ROOT / "src"))

# adapters/openclaw/ — allows `from adapter import ...` via the compat shim
sys.path.insert(0, str(_ADAPTER_ROOT))

# sdks/stigmem-py/src — import stigmem SDK without a pip install
_REPO_ROOT = _ADAPTER_ROOT.parent.parent  # openclaw/ -> adapters/ -> repo root
sys.path.insert(0, str(_REPO_ROOT / "sdks" / "stigmem-py" / "src"))
