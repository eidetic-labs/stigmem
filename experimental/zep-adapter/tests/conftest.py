"""conftest.py - add workspace source directories to sys.path."""

import sys
from pathlib import Path

_HERE = Path(__file__).parent
_ROOT = _HERE.parents[2]

sys.path.insert(0, str(_HERE.parent / "src"))
sys.path.insert(0, str(_ROOT / "sdks/stigmem-py/src"))
sys.path.insert(0, str(_ROOT / "node/src"))
