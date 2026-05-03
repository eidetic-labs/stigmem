"""conftest.py — add the adapter and SDK src directories to sys.path."""

import sys
from pathlib import Path

_HERE = Path(__file__).parent

# stigmem/adapters/openclaw/ — import adapter without installing a package
sys.path.insert(0, str(_HERE.parent))

# sdks/stigmem-py/src — import stigmem SDK without a pip install
_REPO_ROOT = _HERE.parent.parent.parent.parent  # tests/ -> openclaw/ -> adapters/ -> stigmem/ -> root
sys.path.insert(0, str(_REPO_ROOT / "sdks" / "stigmem-py" / "src"))
