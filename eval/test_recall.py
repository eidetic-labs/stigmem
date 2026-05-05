"""Pytest entry-point for the recall benchmark (400 probes).

Run via:
    pytest eval/test_recall.py -v

Or as part of make eval-fast.

CI blocking rules (spec §2 from research-memo):
- Primary metric: nDCG@10
- Regression threshold: 3% relative drop vs baseline.json
- Two-consecutive-run rule: CI blocks only after two consecutive regressions
  (tracked via eval/results/consecutive_failures.txt).
"""

from __future__ import annotations

import json
import pathlib
from datetime import UTC, datetime

import pytest

from eval.harness.recall import run
from eval.harness.utils import load_baseline, load_probes

RESULTS_DIR = pathlib.Path(__file__).parent / "results"
CONSECUTIVE_FAILURES_FILE = RESULTS_DIR / "consecutive_failures.txt"


def _get_consecutive_failures() -> int:
    try:
        return int(CONSECUTIVE_FAILURES_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def _set_consecutive_failures(n: int) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    CONSECUTIVE_FAILURES_FILE.write_text(str(n))


def test_recall_probe_count(recall_probes):
    """400 labeled probes present in corpus."""
    assert len(recall_probes) == 400


def test_recall_probe_classes(recall_probes):
    """All required probe classes are present (100 each for main classes)."""
    from collections import Counter
    classes = Counter(p["class"] for p in recall_probes)
    assert classes["entity_lookup"] == 100
    assert classes["relation_lookup"] == 100
    assert classes["paraphrase"] == 100
    assert classes["adversarial_ood"] == 100


def test_recall_ttl_probes(recall_probes):
    """At least 10 TTL-expiring probes exercise the confidence-decay sweeper."""
    ttl = [p for p in recall_probes if p.get("subclass") == "ttl_expiring"]
    assert len(ttl) == 10


def test_recall_benchmark(eval_node, git_sha):
    """Run recall benchmark; check nDCG@10 regression vs baseline.json.

    CI blocking is gated on two consecutive failures (not a single regression).
    """
    report = run(client=eval_node)

    # Save JSON artifact
    RESULTS_DIR.mkdir(exist_ok=True)
    artifact_path = RESULTS_DIR / f"ci-{git_sha}.json"
    artifact_path.write_text(json.dumps(report, indent=2))

    # Write markdown summary
    _write_markdown_summary(report, git_sha)

    ndcg = report["nDCG@10"]
    rec5 = report["Recall@5"]
    regression = report.get("regression", {})
    regression_triggered = regression.get("triggered", False)

    if regression_triggered:
        consecutive = _get_consecutive_failures() + 1
        _set_consecutive_failures(consecutive)
        delta_pct = regression.get("delta_pct", 0.0)
        msg = (
            f"nDCG@10 regression: {delta_pct:.2f}% drop "
            f"(run {consecutive}/2 needed to block CI). "
            f"Current={ndcg:.4f}, Baseline={regression.get('baseline_ndcg', '?'):.4f}"
        )
        if consecutive >= 2:
            pytest.fail(f"CI BLOCKED after 2 consecutive regressions: {msg}")
        else:
            pytest.xfail(f"First regression detected (not yet blocking): {msg}")
    else:
        # Reset consecutive failure counter on success
        _set_consecutive_failures(0)

    print(f"\n=== Recall Benchmark ===")
    print(f"nDCG@10: {ndcg:.4f}")
    print(f"Recall@5: {rec5:.4f}")
    print(f"Probe count: {report['probe_count']}")
    print(f"Elapsed: {report['elapsed_s']:.1f}s")
    if "note" in regression:
        print(f"Note: {regression['note']}")


def _write_markdown_summary(report: dict, git_sha: str) -> None:
    ndcg = report["nDCG@10"]
    rec5 = report["Recall@5"]
    regression = report.get("regression", {})
    lines = [
        f"# Recall Benchmark — {git_sha}",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| nDCG@10 | {ndcg:.4f} |",
        f"| Recall@5 | {rec5:.4f} |",
        f"| Probe count | {report['probe_count']} |",
        f"| Elapsed | {report['elapsed_s']:.1f}s |",
        f"| Corpus SHA | {report['corpus_sha']} |",
        f"| Server version | {report['server_version']} |",
        "",
    ]
    if regression.get("triggered"):
        lines.append(f"> **Regression detected**: {regression.get('delta_pct', 0):.2f}% nDCG@10 drop")
    elif "note" in regression:
        lines.append(f"> {regression['note']}")
    else:
        lines.append(f"> Regression check passed (baseline nDCG@10: {regression.get('baseline_ndcg', '?')})")

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / f"ci-{git_sha}.md").write_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Helper fixture: git sha for artifact naming
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def git_sha() -> str:
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        return "local"
