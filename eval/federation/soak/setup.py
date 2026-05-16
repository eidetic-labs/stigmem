"""Setup phase helpers for the federation soak harness."""

from __future__ import annotations

import base64
import shutil
import subprocess
import sys
import time

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from .constants import COMPOSE_FILE, ENV_FILE, NODES, REPO_ROOT

DOCKER_BIN = shutil.which("docker") or "docker"


def _generate_keypair() -> tuple[str, str]:
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    priv_b64 = (
        base64.urlsafe_b64encode(
            priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        )
        .decode()
        .rstrip("=")
    )
    pub_b64 = (
        base64.urlsafe_b64encode(pub.public_bytes(Encoding.Raw, PublicFormat.Raw))
        .decode()
        .rstrip("=")
    )
    return pub_b64, priv_b64


def ensure_keypairs() -> dict[str, str]:
    """Generate keypairs for all 3 nodes and write to .env (idempotent)."""
    if ENV_FILE.exists():
        env: dict[str, str] = {}
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
        if all(f"NODE_{letter}_PUBKEY" in env for letter in ("A", "B", "C")):
            print(f"  keypairs: loaded from {ENV_FILE}")
            return env

    lines: list[str] = []
    env = {}
    for letter in ("A", "B", "C"):
        pub, priv = _generate_keypair()
        lines += [f"NODE_{letter}_PUBKEY={pub}", f"NODE_{letter}_PRIVKEY={priv}"]
        env[f"NODE_{letter}_PUBKEY"] = pub
        env[f"NODE_{letter}_PRIVKEY"] = priv

    ENV_FILE.write_text("\n".join(lines) + "\n")
    print(f"  keypairs: generated → {ENV_FILE}")
    return env


def _docker_compose(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    cmd = [
        DOCKER_BIN,
        "compose",
        "-f",
        str(COMPOSE_FILE),
        "--env-file",
        str(ENV_FILE),
        *args,
    ]
    return subprocess.run(cmd, capture_output=False, check=check, cwd=str(REPO_ROOT))  # noqa: S603


def _docker_compose_quiet(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    cmd = [
        DOCKER_BIN,
        "compose",
        "-f",
        str(COMPOSE_FILE),
        "--env-file",
        str(ENV_FILE),
        *args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=check, cwd=str(REPO_ROOT))  # noqa: S603


def start_cluster() -> None:
    print("→ Starting 3-node eval federation cluster (build may take a moment)…")
    _docker_compose("up", "--build", "-d")


def wait_healthy(timeout_s: float = 120.0) -> None:
    print("→ Waiting for all 3 nodes to be healthy…")
    deadline = time.monotonic() + timeout_s
    for node in NODES:
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                r = httpx.get(f"{node['host_url']}/healthz", timeout=5.0)
                if r.status_code == 200:
                    print(f"  {node['name']}: healthy")
                    break
            except httpx.HTTPError as exc:
                last_error = exc
            time.sleep(2.0)
        else:
            if last_error is not None:
                print(f"  {node['name']}: last health check error: {last_error}", file=sys.stderr)
            raise RuntimeError(f"{node['name']} did not become healthy within {timeout_s:.0f} s")


def create_admin_key(container: str) -> str:
    """Create an admin API key (read+write+federate) via docker exec."""
    result = subprocess.run(  # noqa: S603
        [
            DOCKER_BIN,
            "exec",
            container,
            "python",
            "-c",
            (
                "from stigmem_node.auth import create_api_key; "
                "print(create_api_key('eval:admin', ['read','write','federate']))"
            ),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return result.stdout.strip()
