#!/usr/bin/env python3
"""ClawHub skill manifest validator.

Validates `adapters/openclaw/skill/SKILL.md` (the ClawHub catalog
manifest) against the conventions encoded in its own changelog history.
Every check here corresponds to a real regression we shipped and had to
fix out-of-cycle in v1.0.2–v1.0.5:

    v1.0.2 — bad `homepage` / `Documentation` URL (pointed to wrong page)
    v1.0.3 — wrong display name ("Clawhub Skill" instead of "Stigmem")
    v1.0.4 — wrong docs domain (missing `docs.` subdomain)
    v1.0.5 — missing `/en/latest/` ReadTheDocs path prefix

Each is statically detectable from the YAML frontmatter and body markdown.

Usage:
    python scripts/validate_clawhub_skill.py
    python scripts/validate_clawhub_skill.py --check-links     # also HEAD every URL
    python scripts/validate_clawhub_skill.py --check-pypi      # also resolve install pins

Exit codes:
    0 — every check passes
    1 — at least one validation error (details on stderr)
    2 — environmental error (missing PyYAML, missing file, etc.)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("error: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / "adapters/openclaw/skill/SKILL.md"

# ---------------------------------------------------------------------------
# Convention constants — the rules we keep regressing on
# ---------------------------------------------------------------------------

EXPECTED_TITLE = "Stigmem"
"""Display name for the skill on ClawHub. Hardcoded because the v1.0.3 regression
shipped 'Clawhub Skill' as the title — having the canonical value in code is
the cheapest guard against that recurring."""

DOCS_HOST_REQUIRED = "docs.stigmem.dev"
"""Canonical docs host. v1.0.4 shipped `stigmem.dev/...` (missing subdomain)."""

DOCS_PATH_PREFIX_REQUIRED = "/en/latest/"
"""Canonical ReadTheDocs path prefix. v1.0.5 shipped without this."""

KNOWN_STIGMEM_PACKAGES = {
    "stigmem",
    "stigmem-py",
    "stigmem-node",
    "stigmem-openclaw",
}
"""PyPI package names the skill may legitimately install. Catches typos
like `stigmem_py` (underscore) or `stigmem-py-sdk` (drift)."""

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

URL_RE = re.compile(r"https?://[^\s)>\"']+")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")


# ---------------------------------------------------------------------------
# Result accumulator
# ---------------------------------------------------------------------------

class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def ok(self) -> bool:
        return not self.errors

    def emit(self, verbose: bool) -> None:
        for w in self.warnings:
            print(f"::warning::{w}", file=sys.stderr)
        for e in self.errors:
            print(f"::error::{e}", file=sys.stderr)
        if self.ok():
            print(f"validate_clawhub_skill: OK ({len(self.warnings)} warning(s))")


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_skill(path: Path) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body_markdown) — raises if frontmatter missing."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing YAML frontmatter (must start with '---')")
    try:
        _, fm, body = text.split("---\n", 2)
    except ValueError as e:
        raise ValueError(f"{path}: malformed frontmatter delimiters") from e
    data = yaml.safe_load(fm)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: frontmatter is not a mapping")
    return data, body


# ---------------------------------------------------------------------------
# Schema checks
# ---------------------------------------------------------------------------

def _check_env_vars(env_vars: Any, r: Report) -> None:
    if not isinstance(env_vars, list):
        r.err("frontmatter.metadata.openclaw.envVars: must be a list")
        return
    for i, ev in enumerate(env_vars):
        if not isinstance(ev, dict):
            r.err(f"envVars[{i}]: must be a mapping")
            continue
        for k in ("name", "required", "description"):
            if k not in ev:
                r.err(f"envVars[{i}]: missing key '{k}'")


def _check_install_specs(install: Any, r: Report) -> None:
    if not isinstance(install, list) or not install:
        r.err("frontmatter.metadata.openclaw.install: must be a non-empty list")
        return
    for i, item in enumerate(install):
        if not isinstance(item, dict):
            r.err(f"install[{i}]: must be a mapping")
            continue
        for k in ("kind", "package"):
            if k not in item:
                r.err(f"install[{i}]: missing key '{k}'")


def check_schema(fm: dict[str, Any], r: Report) -> None:
    for key in ("name", "title", "description", "version", "metadata"):
        if key not in fm:
            r.err(f"frontmatter: missing required top-level key '{key}'")

    if "version" in fm and not SEMVER_RE.match(str(fm["version"])):
        r.err(f"frontmatter.version: '{fm['version']}' is not valid semver")

    meta = fm.get("metadata") or {}
    oc = (meta.get("openclaw") or {}) if isinstance(meta, dict) else {}
    if not isinstance(oc, dict):
        r.err("frontmatter.metadata.openclaw: must be a mapping")
        return

    for key in ("homepage", "clawhub", "primaryEnv", "envVars", "install"):
        if key not in oc:
            r.err(f"frontmatter.metadata.openclaw: missing required key '{key}'")

    _check_env_vars(oc.get("envVars") or [], r)
    _check_install_specs(oc.get("install") or [], r)


# ---------------------------------------------------------------------------
# Convention checks (the regression history)
# ---------------------------------------------------------------------------

def _check_homepage_conventions(homepage: str, r: Report) -> None:
    """v1.0.2 + v1.0.4 + v1.0.5: docs URL host/path requirements."""
    if not homepage or "stigmem.dev" not in homepage:
        return
    if DOCS_HOST_REQUIRED not in homepage:
        r.err(
            f"frontmatter.metadata.openclaw.homepage: '{homepage}' must use "
            f"'{DOCS_HOST_REQUIRED}' (v1.0.4 regression — docs subdomain dropped)"
        )
    if DOCS_PATH_PREFIX_REQUIRED not in homepage:
        r.err(
            f"frontmatter.metadata.openclaw.homepage: '{homepage}' missing "
            f"'{DOCS_PATH_PREFIX_REQUIRED}' (v1.0.5 regression — RTD path prefix)"
        )


def _check_clawhub_slug(clawhub: str, name: str, r: Report) -> None:
    """ClawHub slug must match the skill `name` (adopters install by name)."""
    if not (clawhub and name):
        return
    m = re.match(r"https?://clawhub\.ai/skills/([^/?#]+)", clawhub)
    if not m:
        r.err(
            f"frontmatter.metadata.openclaw.clawhub: '{clawhub}' is not a "
            "clawhub.ai/skills/<slug> URL"
        )
        return
    if m.group(1) != name:
        r.err(
            f"name/clawhub mismatch: name='{name}' but clawhub URL slug='{m.group(1)}'. "
            f"These must match — adopters install by name."
        )


def _check_install_packages_known(install: list[Any], r: Report) -> None:
    """Each install spec's package must be in KNOWN_STIGMEM_PACKAGES."""
    for i, item in enumerate(install):
        pkg_spec = str(item.get("package", ""))
        bare = re.split(r"[<>=!~ ]", pkg_spec, maxsplit=1)[0].strip()
        if bare and bare not in KNOWN_STIGMEM_PACKAGES:
            r.err(
                f"install[{i}].package: '{bare}' not in known stigmem packages "
                f"({sorted(KNOWN_STIGMEM_PACKAGES)}). Typo or drift?"
            )


def check_conventions(fm: dict[str, Any], r: Report) -> None:
    # v1.0.3: display title regression
    if fm.get("title") != EXPECTED_TITLE:
        r.err(
            f"frontmatter.title: '{fm.get('title')}' != '{EXPECTED_TITLE}' "
            f"(v1.0.3 regression — display name on ClawHub must be 'Stigmem')"
        )

    meta = fm.get("metadata") or {}
    oc = meta.get("openclaw") or {}
    if not isinstance(oc, dict):
        return

    _check_homepage_conventions(str(oc.get("homepage", "")), r)
    _check_clawhub_slug(str(oc.get("clawhub", "")), str(fm.get("name", "")), r)
    _check_install_packages_known(oc.get("install") or [], r)


# ---------------------------------------------------------------------------
# Body markdown checks
# ---------------------------------------------------------------------------

def check_body_links(body: str, r: Report) -> list[str]:
    """Return list of all URLs found in body for optional liveness check."""
    urls: list[str] = []
    for match in MD_LINK_RE.finditer(body):
        url = match.group(2)
        urls.append(url)
        if "stigmem.dev" in url and "docs.stigmem.dev" not in url and "/sponsors/" not in url:
            # Allow bare stigmem.dev for marketing landing, but flag docs paths
            if any(seg in url for seg in ("/docs/", "/guides/", "/concepts/", "/sdks/")):
                r.err(
                    f"body link '{url}': docs path on bare stigmem.dev — "
                    f"must use {DOCS_HOST_REQUIRED} (v1.0.4 regression)"
                )
        if "docs.stigmem.dev" in url and DOCS_PATH_PREFIX_REQUIRED not in url:
            r.err(
                f"body link '{url}': missing '{DOCS_PATH_PREFIX_REQUIRED}' "
                f"(v1.0.5 regression)"
            )
    return urls


# ---------------------------------------------------------------------------
# Optional: live URL liveness (skipped without --check-links)
# ---------------------------------------------------------------------------

def check_url_liveness(urls: list[str], r: Report) -> None:
    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "stigmem-clawhub-validator/1"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 400:
                    r.err(f"link liveness: {url} -> HTTP {resp.status}")
        except urllib.error.HTTPError as e:
            # Some sites 405 HEAD; retry with GET
            if e.code in (405, 403):
                try:
                    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "stigmem-clawhub-validator/1"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        if resp.status >= 400:
                            r.err(f"link liveness: {url} -> HTTP {resp.status}")
                except Exception as e2:
                    r.err(f"link liveness: {url} -> {e2}")
            else:
                r.err(f"link liveness: {url} -> HTTP {e.code}")
        except Exception as e:
            r.err(f"link liveness: {url} -> {e}")


# ---------------------------------------------------------------------------
# Optional: PyPI install-spec resolution (skipped without --check-pypi)
# ---------------------------------------------------------------------------

def check_pypi_install_specs(fm: dict[str, Any], r: Report) -> None:
    try:
        from packaging.specifiers import SpecifierSet
        from packaging.version import Version
    except ImportError:
        r.warn("--check-pypi requires `packaging` (pip install packaging); skipping pin resolution")
        return

    oc = (fm.get("metadata") or {}).get("openclaw") or {}
    for i, item in enumerate(oc.get("install") or []):
        pkg_spec = str(item.get("package", ""))
        m = re.match(r"^([a-zA-Z0-9_-]+)\s*(.*)$", pkg_spec)
        if not m:
            continue
        bare, spec_str = m.group(1), m.group(2).strip()
        if bare not in KNOWN_STIGMEM_PACKAGES:
            continue  # already errored in conventions
        url = f"https://pypi.org/pypi/{bare}/json"
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                meta = json.loads(resp.read())
        except Exception as e:
            r.warn(f"install[{i}] {bare}: PyPI lookup failed ({e}); skipping range check")
            continue
        try:
            spec = SpecifierSet(spec_str) if spec_str else SpecifierSet("")
        except Exception as e:
            r.err(f"install[{i}].package: invalid spec '{spec_str}': {e}")
            continue
        published = list(meta.get("releases", {}).keys())
        matching = [v for v in published if _safe_match(spec, v, Version)]
        if not matching:
            r.err(
                f"install[{i}].package: '{pkg_spec}' matches NO published version of {bare} on PyPI "
                f"(published: {sorted(published)[-5:]})"
            )


def _safe_match(spec: Any, v: str, Version: Any) -> bool:
    try:
        return spec.contains(Version(v), prereleases=True)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check-links", action="store_true", help="HEAD every URL (slow; for CI)")
    p.add_argument("--check-pypi", action="store_true", help="Resolve install pins against PyPI (network)")
    p.add_argument("--path", type=Path, default=SKILL_PATH, help="Path to SKILL.md")
    args = p.parse_args()

    if not args.path.exists():
        print(f"error: {args.path} does not exist", file=sys.stderr)
        return 2

    r = Report()
    try:
        fm, body = parse_skill(args.path)
    except Exception as e:
        print(f"::error::{e}", file=sys.stderr)
        return 1

    check_schema(fm, r)
    check_conventions(fm, r)
    body_urls = check_body_links(body, r)

    if args.check_links:
        # frontmatter URLs too
        fm_urls = []
        oc = (fm.get("metadata") or {}).get("openclaw") or {}
        for k in ("homepage", "clawhub"):
            v = oc.get(k)
            if v:
                fm_urls.append(str(v))
        check_url_liveness(fm_urls + body_urls, r)

    if args.check_pypi:
        check_pypi_install_specs(fm, r)

    r.emit(verbose=False)
    return 0 if r.ok() else 1


if __name__ == "__main__":
    sys.exit(main())
