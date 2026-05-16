"""Teardown phase helpers for the federation soak harness."""

from __future__ import annotations

from .setup import _docker_compose_quiet


def stop_cluster() -> None:
    print("→ Tearing down eval federation cluster…")
    _docker_compose_quiet("down", "-v", check=False)
