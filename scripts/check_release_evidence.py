#!/usr/bin/env python3
"""Validate Phase C release-evidence wiring.

This check keeps supply-chain documentation and publish workflow behavior in
lockstep: release evidence is only useful when operators can verify it.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PUBLISH_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "publish.yml"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
RELEASE_DOC = REPO_ROOT / "docs" / "docs" / "operators" / "release-verification.md"
OPERATING_DOC = REPO_ROOT / "OPERATING.md"
SIDEBARS = REPO_ROOT / "docs" / "sidebars.js"

PUBLISH_REQUIREMENTS = {
    "keyless signing permission": "id-token: write",
    "cosign install": "sigstore/cosign-installer",
    "image signature": "cosign sign --yes",
    "SBOM generation": "stigmem-node-sbom.spdx.json",
    "SBOM attestation": "cosign attest --yes",
    "SPDX attestation type": "--type spdxjson",
    "BuildKit provenance": "provenance: mode=max",
    "npm provenance": "npm publish --provenance",
    "PyPI Trusted Publisher": "use_oidc: true",
    "release-page verification link": "docs.stigmem.dev/operators/release-verification",
}

DOC_REQUIREMENTS = {
    "cosign signature verification": "cosign verify",
    "cosign attestation verification": "cosign verify-attestation",
    "SBOM retrieval": "cosign download sbom",
    "BuildKit provenance": "BuildKit provenance",
    "Rekor": "Rekor",
    "npm provenance": "npm",
    "PyPI Trusted Publisher": "Trusted Publisher",
    "reproducibility scope": (
        "Arbitrary later rebuilds may not produce the same byte-for-byte image digest"
    ),
}


def _read(path: Path) -> str:
    try:
        return path.read_text()
    except OSError as exc:
        raise RuntimeError(f"unable to read {path.relative_to(REPO_ROOT)}: {exc}") from exc


def _missing(label: str, text: str, requirements: dict[str, str]) -> list[str]:
    return [
        f"{label}: missing {name!r} marker {marker!r}"
        for name, marker in requirements.items()
        if marker not in text
    ]


def main() -> int:
    failures: list[str] = []

    try:
        publish = _read(PUBLISH_WORKFLOW)
        release_doc = _read(RELEASE_DOC)
        operating_doc = _read(OPERATING_DOC)
        sidebars = _read(SIDEBARS)
        ci = _read(CI_WORKFLOW)
    except RuntimeError as exc:
        print(f"release-evidence: {exc}", file=sys.stderr)
        return 2

    failures.extend(_missing("publish.yml", publish, PUBLISH_REQUIREMENTS))
    failures.extend(_missing("release-verification.md", release_doc, DOC_REQUIREMENTS))

    if "docs/docs/operators/release-verification.md" not in operating_doc:
        failures.append("OPERATING.md: missing release verification link")
    if "operators/release-verification" not in sidebars:
        failures.append(
            "docs/sidebars.js: release verification page is not in the operator sidebar"
        )
    if "python scripts/check_release_evidence.py" not in ci:
        failures.append("ci.yml: security-evidence job does not run check_release_evidence.py")
    if "'scripts/check_release_evidence.py'" not in ci:
        failures.append(
            "ci.yml: detect-changes security_evidence filter misses check_release_evidence.py"
        )
    if "'.github/workflows/publish.yml'" not in ci:
        failures.append("ci.yml: detect-changes security_evidence filter misses publish.yml")

    if failures:
        print("release-evidence: FAIL", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("release-evidence: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
