"""conftest.py — add the adapter directory to sys.path."""

import sys
from pathlib import Path

_HERE = Path(__file__).parent

sys.path.insert(0, str(_HERE.parent))  # stigmem/adapters/zep/
