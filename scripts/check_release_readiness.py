#!/usr/bin/env python3
"""Umbrella release-readiness gate.

This check answers a single question before a publish workflow tags an immutable
release: is the surrounding bookkeeping consistent with the code we are about to
ship?

It does two things existing gates (`check_version_consistency.py`,
`validate_version_surfaces.py`, `check_release_evidence.py`) do not:

1. **CHANGELOG presence and non-emptiness.** When run without `--tag`, asserts
   that `CHANGELOG.md` has a `## [Unreleased]` section with at least one
   non-empty bullet under any subsection — catches the "No unreleased changes"
   lie that lets feature commits land without a CHANGELOG entry. When run with
   `--tag vX.Y.Z`, asserts that a `## [X.Y.Z]` section exists and has body
   content (so a tag push cannot create a CHANGELOG-less release).

2. **Milestone is closed.** When run with `--tag vX.Y.Z`, asserts that a
   GitHub milestone with title matching the tag's version exists and has zero
   open issues. Requires `gh` CLI on PATH and authenticated for the target repo
   (defaults to `Eidetic-Labs/stigmem`; override with `--repo`). The milestone
   check is skipped if `--no-milestone-check` is passed or if `gh` is missing,
   so the gate still works in environments without GitHub credentials (CI
   passes `gh` in by default).

Exit code 0 if ready, 1 with a diagnostic if not. Intended to be wired into
`.github/workflows/publish.yml` immediately before the tag-gated publish jobs.

Discipline anchor: this gate exists because the v0.9.0a1/a2 release cycle and
the parallel Craik v0.2.0 / v0.3.0 cycles repeatedly surfaced two failure modes
that the existing per-artifact gates do not catch: CHANGELOG sections that
describe the wrong release, and milestones with open issues that should have
shipped in the tagged release.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

DEFAULT_REPO = "Eidetic-Labs/stigmem"

VERSION_TAG_RE = re.compile(r"^v(?P<version>\d+\.\d+\.\d+(?:[ab]\d+|rc\d+)?)$")


def _read_changelog() -> str:
    if not CHANGELOG.exists():
        print(f"FAIL: {CHANGELOG.relative_to(REPO_ROOT)} is missing", file=sys.stderr)
        sys.exit(1)
    return CHANGELOG.read_text()


def _extract_section(changelog: str, heading_pattern: str) -> str | None:
    """Return the body of the first `## <heading>` section, or None if missing.

    Body ends at the next `## ` heading or end of file. Leading/trailing blank
    lines are stripped.
    """
    lines = changelog.splitlines()
    in_section = False
    body: list[str] = []
    # Allow optional trailing content after the bracketed heading (date,
    # em-dash status, etc.). Common CHANGELOG patterns:
    #   `## [Unreleased]`
    #   `## [0.9.0a2] — 2026-05-18`
    #   `## [0.9.0a1] - 2026-05-08`
    head_re = re.compile(rf"^## {heading_pattern}(?:\s.*)?$", re.IGNORECASE)
    for line in lines:
        if head_re.match(line):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            body.append(line)
    if not in_section:
        return None
    return "\n".join(body).strip()


def _section_has_substantive_content(body: str) -> bool:
    """A section is substantive if it has at least one non-empty bullet.

    Empty placeholders like `_No unreleased changes._` or solitary "—" markers
    do not count.
    """
    if not body:
        return False
    placeholder_re = re.compile(
        r"^\s*[_*]?\s*(no unreleased changes|tbd|n/a|none)\b", re.IGNORECASE
    )
    bullet_re = re.compile(r"^\s*[-*]\s+\S")
    for line in body.splitlines():
        if placeholder_re.match(line):
            return False
        if bullet_re.match(line):
            return True
    return False


def _check_changelog_unreleased(changelog: str) -> list[str]:
    body = _extract_section(changelog, r"\[Unreleased\]")
    if body is None:
        return [
            "CHANGELOG.md is missing a `## [Unreleased]` section. Add one above "
            "the most recent versioned section."
        ]
    if not _section_has_substantive_content(body):
        return [
            "CHANGELOG.md `[Unreleased]` section is empty or contains only a "
            "placeholder. Document landed-but-unreleased changes before tagging."
        ]
    return []


def _check_changelog_for_version(changelog: str, version: str) -> list[str]:
    pattern = rf"\[{re.escape(version)}\]"
    body = _extract_section(changelog, pattern)
    if body is None:
        return [
            f"CHANGELOG.md is missing a `## [{version}]` section. Promote "
            "the `[Unreleased]` section to a `[<version>]` heading before tagging."
        ]
    if not _section_has_substantive_content(body):
        return [
            f"CHANGELOG.md `[{version}]` section has no substantive bullets. "
            "A tagged release must document what shipped."
        ]
    return []


def _run_gh_api(repo: str, path: str) -> tuple[bool, str]:
    if not shutil.which("gh"):
        return False, "gh CLI not on PATH"
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/{path}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return False, f"gh invocation failed: {exc}"
    if result.returncode != 0:
        return False, f"gh api error: {result.stderr.strip() or result.stdout.strip()}"
    return True, result.stdout


def _check_milestone(repo: str, version: str) -> list[str]:
    ok, payload = _run_gh_api(repo, "milestones?state=all&per_page=100")
    if not ok:
        return [
            f"could not query milestones for {repo}: {payload}. "
            "Re-run with `--no-milestone-check` to skip this gate locally."
        ]
    try:
        milestones = json.loads(payload)
    except json.JSONDecodeError as exc:
        return [f"could not parse milestones payload: {exc}"]
    target_titles = {f"v{version}", version}
    matches = [m for m in milestones if m.get("title") in target_titles]
    if not matches:
        return [
            f"no milestone with title matching {sorted(target_titles)} found on "
            f"{repo}. Create one (see CONTRIBUTING.md §PR-closes-issue and "
            "milestone discipline) or skip this gate with "
            "`--no-milestone-check`."
        ]
    failures: list[str] = []
    for milestone in matches:
        open_count = milestone.get("open_issues", 0)
        if open_count:
            number = milestone.get("number")
            url = milestone.get("html_url", "")
            failures.append(
                f"milestone {milestone['title']!r} (#{number}) has "
                f"{open_count} open issue(s) — close or move them before "
                f"tagging. {url}".rstrip()
            )
    return failures


def _print_failures(failures: Iterable[str]) -> None:
    for line in failures:
        print(f"FAIL: {line}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tag",
        help=(
            "Release tag being prepared (e.g. v0.9.0a3). When provided, "
            "switches CHANGELOG check to the versioned section and runs the "
            "milestone gate. Without --tag, only the `[Unreleased]` non-empty "
            "check runs."
        ),
    )
    parser.add_argument(
        "--repo",
        default=DEFAULT_REPO,
        help=f"GitHub repo for milestone lookup (default: {DEFAULT_REPO}).",
    )
    parser.add_argument(
        "--no-milestone-check",
        action="store_true",
        help="Skip the milestone gate. Useful for local checks without gh auth.",
    )
    args = parser.parse_args(argv)

    failures: list[str] = []
    changelog = _read_changelog()

    if args.tag:
        match = VERSION_TAG_RE.match(args.tag)
        if not match:
            print(
                f"FAIL: --tag {args.tag!r} does not match vMAJOR.MINOR.PATCH"
                "[aN|bN|rcN]",
                file=sys.stderr,
            )
            return 1
        version = match.group("version")
        failures.extend(_check_changelog_for_version(changelog, version))
        if not args.no_milestone_check:
            failures.extend(_check_milestone(args.repo, version))
    else:
        failures.extend(_check_changelog_unreleased(changelog))

    if failures:
        _print_failures(failures)
        return 1

    print("OK: release readiness checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
