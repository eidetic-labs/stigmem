#!/usr/bin/env python3
"""Generate Ed25519 keypairs for the 4-node soak federation.

Usage:
    python soak/keys.py > soak/.env
    # Then: docker compose -f docker-compose.soak.yml --env-file soak/.env up -d

The .env file is consumed by docker-compose.soak.yml and by setup_peers.py.
"""

import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


def generate_keypair() -> tuple[str, str]:
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


def main() -> None:
    for name in ("A", "B", "C", "D"):
        pub, priv = generate_keypair()
        print(f"NODE_{name}_PUBKEY={pub}")
        print(f"NODE_{name}_PRIVKEY={priv}")


if __name__ == "__main__":
    main()
