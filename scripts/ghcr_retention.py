"""GHCR retention pruner.

Deletes versions of an organisation-owned GHCR container package whose
tags are short-SHA-only (or untagged orphans) and whose ``created_at``
is older than the configured retention window.

Protected tags are *never* touched:

- ``latest``
- ``edge``
- Any tag matching the immutable-version regex ``IMMUTABLE_VERSION_RE``.
  This matches the PEP 440 shorthand we publish (e.g. ``0.9.0a1``,
  ``0.9.0b2``, ``1.0.0rc1``, ``1.0.0``) and the semver-strict
  spellings (``0.9.0-alpha.1`` etc.) — both flavours that
  ``.github/workflows/publish.yml`` emits on a release-tag push.

If any tag on a version is protected, the entire version is kept.

Documented in:
- ``docs/internal/release-cadence.md`` § Rule 7
- ``docs/docs/operators/deployment/install.md`` § Image retention

Tracked in issue #119.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

LOG = logging.getLogger("ghcr_retention")

# Matches the immutable version tags the publish workflow emits on a release.
#   PEP 440 shorthand: 0.9.0a1, 0.9.0b2, 1.0.0rc1, 1.0.0
#   Semver-strict:     0.9.0-alpha.1, 0.9.0-beta.2, 1.0.0-rc.1
IMMUTABLE_VERSION_RE = re.compile(
    r"^[0-9]+\.[0-9]+\.[0-9]+"
    r"(a[0-9]+|b[0-9]+|rc[0-9]+|-alpha\.[0-9]+|-beta\.[0-9]+|-rc\.[0-9]+)?$"
)

# Tags we never prune even when they appear standalone.
PROTECTED_ROLLING_TAGS = {"latest", "edge"}


def _gh_api(path: str, paginate: bool = False) -> Any:
    """Call ``gh api`` and return parsed JSON."""
    cmd: list[str] = ["gh", "api"]
    if paginate:
        cmd.append("--paginate")
    cmd.append(path)
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    # `--paginate` concatenates page bodies; for an endpoint that returns a
    # JSON array, gh emits them as separate top-level arrays joined by
    # newlines.  Parse each and flatten.
    if paginate:
        flat: list[Any] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parsed = json.loads(line)
            if isinstance(parsed, list):
                flat.extend(parsed)
            else:
                flat.append(parsed)
        return flat
    return json.loads(result.stdout)


def _gh_delete(path: str) -> None:
    """Call ``gh api -X DELETE``; raise on non-success."""
    cmd = ["gh", "api", "-X", "DELETE", path]
    subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603, S607


def _is_protected(tags: list[str]) -> tuple[bool, str | None]:
    """Return (protected?, reason) for a version's tag list."""
    for tag in tags:
        if tag in PROTECTED_ROLLING_TAGS:
            return True, f"protected rolling tag {tag!r}"
        if IMMUTABLE_VERSION_RE.match(tag):
            return True, f"immutable version tag {tag!r}"
    return False, None


def _list_versions(org: str, package: str) -> list[dict[str, Any]]:
    path = f"orgs/{org}/packages/container/{package}/versions?per_page=100"
    result = _gh_api(path, paginate=True)
    if not isinstance(result, list):
        raise RuntimeError(f"Expected list of versions; got {type(result).__name__}")
    return result


def _delete_version(org: str, package: str, version_id: int) -> None:
    path = f"orgs/{org}/packages/container/{package}/versions/{version_id}"
    _gh_delete(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--min-age-days", type=int, default=90)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be deleted but do not call the DELETE endpoint.",
    )
    parser.add_argument(
        "--summary-path",
        default=os.environ.get("GITHUB_STEP_SUMMARY"),
        help="Markdown summary destination (defaults to $GITHUB_STEP_SUMMARY when set).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    cutoff = datetime.now(UTC) - timedelta(days=args.min_age_days)
    LOG.info(
        "Pruning %s/%s versions created before %s (min age %d days)%s",
        args.org,
        args.package,
        cutoff.isoformat(),
        args.min_age_days,
        " [DRY RUN]" if args.dry_run else "",
    )

    try:
        versions = _list_versions(args.org, args.package)
    except subprocess.CalledProcessError as exc:
        LOG.error("Failed to list versions: %s", exc.stderr)
        return 2

    deleted: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    for v in versions:
        version_id = v["id"]
        created_at = datetime.fromisoformat(v["created_at"].replace("Z", "+00:00"))
        tags = v.get("metadata", {}).get("container", {}).get("tags", []) or []
        protected, reason = _is_protected(tags)
        too_young = created_at > cutoff

        if protected:
            kept.append({"id": version_id, "tags": tags, "reason": reason})
            continue
        if too_young:
            kept.append({
                "id": version_id,
                "tags": tags,
                "reason": f"younger than {args.min_age_days}d (created {created_at.isoformat()})",
            })
            continue

        LOG.info(
            "%s version id=%s tags=%s created=%s",
            "WOULD DELETE" if args.dry_run else "Deleting",
            version_id,
            tags,
            created_at.isoformat(),
        )
        if not args.dry_run:
            try:
                _delete_version(args.org, args.package, version_id)
            except subprocess.CalledProcessError as exc:
                LOG.error(
                    "Delete failed for version id=%s: %s",
                    version_id,
                    exc.stderr,
                )
                continue
        deleted.append({"id": version_id, "tags": tags, "created": created_at.isoformat()})

    LOG.info(
        "Done. %d version(s) %s; %d kept.",
        len(deleted),
        "would-be-deleted" if args.dry_run else "deleted",
        len(kept),
    )

    if args.summary_path:
        try:
            with open(args.summary_path, "a", encoding="utf-8") as fh:  # noqa: PTH123
                fh.write(f"## GHCR retention — `{args.org}/{args.package}`\n\n")
                fh.write(
                    f"- Cutoff: {cutoff.isoformat()} ({args.min_age_days}d window)\n"
                    f"- Dry run: **{args.dry_run}**\n"
                    f"- Deleted: **{len(deleted)}**\n"
                    f"- Kept: **{len(kept)}**\n\n"
                )
                if deleted:
                    fh.write(
                        "### "
                        f"{'Would delete' if args.dry_run else 'Deleted'}\n\n"
                        "| Version id | Tags | Created |\n|---|---|---|\n"
                    )
                    for d in deleted:
                        tags_str = ", ".join(f"`{t}`" for t in d["tags"]) or "_(none)_"
                        fh.write(f"| {d['id']} | {tags_str} | {d['created']} |\n")
                    fh.write("\n")
        except OSError as exc:
            LOG.warning("Could not write step summary: %s", exc)

    return 0


if __name__ == "__main__":
    sys.exit(main())
