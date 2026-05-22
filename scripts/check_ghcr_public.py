#!/usr/bin/env python3
"""Verify the stigmem-node GHCR image is publicly pullable.

Surfaced as a CI gate after the 2026-05-10 dogfooding finding (issue #103):
the GHCR package was private at publish time, so adopters following the
README's `docker pull ghcr.io/eidetic-labs/stigmem-node:0.9.0a5` got
403 Forbidden. The fix is a one-time GitHub package-visibility flip,
but the regression mode is silent — if a future package is published
private by default and nobody notices, the same friction recurs.

This script probes the GHCR manifest endpoint anonymously (no auth
token, no Docker login). If the registry responds with 401/403, the
image is private and the script exits non-zero. Public images return
the manifest (200) — or a Bearer challenge that anonymous clients can
satisfy without credentials, depending on the registry's policy.

Run from CI on every push to main + on a daily cron, so a visibility
regression gets caught within 24 hours rather than at the next adopter
report.

Usage:
    python3 scripts/check_ghcr_public.py
    python3 scripts/check_ghcr_public.py --image ghcr.io/eidetic-labs/stigmem-node --tag latest

Exit codes:
    0  image is publicly pullable
    1  image is private or otherwise inaccessible anonymously
    2  network error (treated as warning; non-fatal on first attempt)
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request

DEFAULT_IMAGE = "ghcr.io/eidetic-labs/stigmem-node"
DEFAULT_TAG = "0.9.0a5"


def probe(image: str, tag: str) -> int:
    """Return 0 if image is anonymously pullable, 1 if private, 2 on network error."""
    # GHCR's anonymous-pull flow: first hit the token endpoint with no auth.
    # For public images, GHCR returns a token usable for the manifest fetch.
    # For private images, GHCR returns 401 (no token issued without credentials).
    registry, _, repo = image.partition("/")
    if registry != "ghcr.io":
        print(f"check_ghcr_public: registry {registry!r} not supported", file=sys.stderr)
        return 2

    token_url = f"https://ghcr.io/token?scope=repository:{repo}:pull&service=ghcr.io"
    try:
        req = urllib.request.Request(token_url)
        with urllib.request.urlopen(req, timeout=10) as r:
            if r.status != 200:
                print(
                    f"check_ghcr_public: token endpoint returned {r.status} "
                    f"(expected 200 for public image)",
                    file=sys.stderr,
                )
                return 1
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print(
                f"check_ghcr_public: FAIL — {image} is PRIVATE "
                f"(GHCR token endpoint returned {e.code}). "
                f"Adopters following the Docker quickstart cannot pull this image.",
                file=sys.stderr,
            )
            print(
                "Fix: https://github.com/orgs/eidetic-labs/packages/container/"
                f"{repo.split('/', 1)[1]}/settings → Change visibility → Public",
                file=sys.stderr,
            )
            return 1
        print(
            f"check_ghcr_public: unexpected HTTP {e.code} from token endpoint",
            file=sys.stderr,
        )
        return 2
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"check_ghcr_public: network error probing token endpoint: {e}", file=sys.stderr)
        return 2

    # Public-image confirmation: also probe the manifest endpoint anonymously
    # to make sure the registry actually serves it (not just that token issuance
    # succeeded).
    manifest_url = f"https://ghcr.io/v2/{repo}/manifests/{tag}"
    try:
        req = urllib.request.Request(manifest_url, method="HEAD")
        req.add_header("Accept", "application/vnd.docker.distribution.manifest.v2+json")
        # No Authorization header — anonymous probe.
        with urllib.request.urlopen(req, timeout=10) as r:
            if r.status == 200:
                print(
                    f"check_ghcr_public: OK — {image}:{tag} is anonymously pullable",
                    file=sys.stderr,
                )
                return 0
            print(
                f"check_ghcr_public: manifest endpoint returned {r.status} "
                f"(expected 200)",
                file=sys.stderr,
            )
            return 1
    except urllib.error.HTTPError as e:
        if e.code == 401:
            # Anonymous probe got challenged — we'd need the token from above.
            # Public images can technically still require this token roundtrip.
            # Treat 401 here as "needs token" rather than "private," since the
            # token endpoint above succeeded.
            print(
                f"check_ghcr_public: OK — {image}:{tag} requires the standard "
                "token roundtrip but the token endpoint serves anonymous "
                "callers (image is public)",
                file=sys.stderr,
            )
            return 0
        if e.code in (403, 404):
            print(
                f"check_ghcr_public: FAIL — manifest endpoint returned {e.code} "
                f"for {image}:{tag}",
                file=sys.stderr,
            )
            return 1
        print(
            f"check_ghcr_public: unexpected HTTP {e.code} from manifest endpoint",
            file=sys.stderr,
        )
        return 2
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"check_ghcr_public: network error probing manifest endpoint: {e}", file=sys.stderr)
        return 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--image", default=DEFAULT_IMAGE, help=f"image to probe (default: {DEFAULT_IMAGE})")
    parser.add_argument("--tag", default=DEFAULT_TAG, help=f"tag to probe (default: {DEFAULT_TAG})")
    args = parser.parse_args()
    return probe(args.image, args.tag)


if __name__ == "__main__":
    raise SystemExit(main())
