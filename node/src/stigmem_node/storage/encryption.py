"""Key material loading and Argon2id derivation for encryption-at-rest.

Key material is cached per unique (passphrase_env, kms_uri) pair so Argon2id
runs at most once per process lifetime, not once per connection.

Security properties:
- Key material is never included in exception messages or log output.
- The cache holds derived keys in-process memory; no disk persistence.
- Fixed KDF salt is intentional: the passphrase is the secret, not the salt.
  This is appropriate for stretching high-entropy operator secrets, not for
  hashing low-entropy user passwords.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

# Domain-separator salt for Argon2id — 32 bytes, never changes after deployment.
_ARGON2_SALT: bytes = (
    b"stigmem-at-rest-v1" + b"\x00" * 14  # 18 + 14 = 32 bytes
)

_key_cache: dict[tuple[str, str], bytes] = {}


def load_key(settings: Any) -> bytes:
    """Return the 32-byte encryption key derived from *settings*.

    Sources are checked in priority order:
    1. ``at_rest_key_kms_uri``  (e.g. ``env://MY_HEX_KEY``)
    2. ``at_rest_key_passphrase_env`` → Argon2id derivation

    Raises ``RuntimeError`` if neither source is configured or loading fails.
    Key material is never surfaced in exception messages.
    """
    kms_uri: str = getattr(settings, "at_rest_key_kms_uri", "")
    passphrase_env: str = getattr(settings, "at_rest_key_passphrase_env", "")
    cache_key = (passphrase_env, kms_uri)

    if cache_key in _key_cache:
        return _key_cache[cache_key]

    if kms_uri:
        key = _load_from_kms_uri(kms_uri)
    elif passphrase_env:
        key = _derive_from_passphrase_env(passphrase_env)
    else:
        raise RuntimeError(
            "STIGMEM_AT_REST_ENCRYPTION=on but no key source is configured. "
            "Set STIGMEM_AT_REST_KEY_PASSPHRASE_ENV or STIGMEM_AT_REST_KEY_KMS_URI. "
            "The node refuses to start without a key source when encryption is enabled."
        )

    _key_cache[cache_key] = key
    return key


def _load_from_kms_uri(uri: str) -> bytes:
    """Load a raw 32-byte key from a KMS URI.

    Supported schemes:
    - ``env://VAR`` — read a 64-char hex-encoded 32-byte key from env var VAR.
    """
    if uri.startswith("env://"):
        var_name = uri[len("env://") :]
        raw = os.environ.get(var_name, "")
        if not raw:
            raise RuntimeError(
                f"STIGMEM_AT_REST_KEY_KMS_URI references env var '{var_name}' "
                "which is not set or is empty."
            )
        try:
            key = bytes.fromhex(raw.strip())
        except ValueError:
            raise RuntimeError(
                f"Env var '{var_name}' (KMS URI) must contain a 64-character "
                "hex-encoded 32-byte key. Check that the value is valid hex."
            ) from None
        if len(key) != 32:
            raise RuntimeError(
                f"Env var '{var_name}' (KMS URI) decoded to {len(key)} bytes; "
                "exactly 32 bytes (64 hex characters) are required."
            )
        return key

    raise RuntimeError(
        f"Unsupported KMS URI scheme — only 'env://' is supported in this release. Got: {uri!r}"
    )


def _derive_from_passphrase_env(env_var: str) -> bytes:
    passphrase = os.environ.get(env_var, "")
    if not passphrase:
        raise RuntimeError(
            f"STIGMEM_AT_REST_KEY_PASSPHRASE_ENV references env var '{env_var}' "
            "which is not set or is empty."
        )
    return derive_key(passphrase.encode())


def derive_key(passphrase: bytes) -> bytes:
    """Derive a 32-byte encryption key from *passphrase* using Argon2id.

    Parameters follow OWASP 2023 recommendations for key derivation:
    time_cost=3, memory_cost=64 MiB, parallelism=4.

    Requires ``argon2-cffi``; install with ``pip install 'stigmem-node[encryption]'``.
    """
    try:
        import argon2.low_level as _argon2
    except ImportError as exc:
        raise RuntimeError(
            "argon2-cffi is required for passphrase-based key derivation. "
            "Install it with: pip install 'stigmem-node[encryption]'"
        ) from exc

    derived: bytes = _argon2.hash_secret_raw(
        secret=passphrase,
        salt=_ARGON2_SALT,
        time_cost=3,
        memory_cost=65_536,
        parallelism=4,
        hash_len=32,
        type=_argon2.Type.ID,
    )
    return derived


def _reset_key_cache() -> None:
    """Clear the in-process key cache. For tests only."""
    _key_cache.clear()
