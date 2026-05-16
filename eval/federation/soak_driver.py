#!/usr/bin/env python3
"""Federation soak workload driver — eval/ harness.

Usage:
  python eval/federation/soak_driver.py [--duration 3600] [--smoke] [--no-teardown]

The implementation is split into phase modules under
``eval/federation/soak/``; this file remains the stable CLI entrypoint.
"""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

main = import_module("eval.federation.soak.cli").main


if __name__ == "__main__":
    sys.exit(main())
