"""Topology and threshold constants for the federation soak harness."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
EVAL_FED_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = EVAL_FED_DIR / ".env"
COMPOSE_FILE = EVAL_FED_DIR / "docker-compose.yml"
RESULTS_DIR = EVAL_FED_DIR.parent / "results"

NODES = [
    {
        "letter": "A",
        "name": "node-a",
        "host_url": "http://localhost:8780",
        "internal_url": "http://node-a:8765",
        "container": "eval-fed-node-a",
    },
    {
        "letter": "B",
        "name": "node-b",
        "host_url": "http://localhost:8781",
        "internal_url": "http://node-b:8765",
        "container": "eval-fed-node-b",
    },
    {
        "letter": "C",
        "name": "node-c",
        "host_url": "http://localhost:8782",
        "internal_url": "http://node-c:8765",
        "container": "eval-fed-node-c",
    },
]
NETWORK_NAME = "eval_fed_net"
LAG_WARN_MS = 2_000
LAG_FAIL_MS = 10_000
CONVERGENCE_WINDOW_S = 30.0
