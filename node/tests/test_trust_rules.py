"""Phase 4c coverage: trust_rules unit tests.

Covers ``stigmem_node.trust_rules`` — operator-configured auto-trust rules
loaded from YAML (file-based) and the ``quarantine_rules`` table (db-based).

Targets:
- ``_load_yaml_rules`` (happy / not-found / invalid YAML / non-dict)
- ``_rule_matches`` (org_uri + scope matching, including null scope wildcard)
- ``evaluate_auto_rules`` (DB precedence, file fallback, no-match → None)
- ``_evaluate_db_rules`` (always/never/non-matching/exception swallowed)
"""

from __future__ import annotations

from pathlib import Path

import pytest

import stigmem_node.settings as settings_module
from stigmem_node.trust_rules import (
    _evaluate_db_rules,
    _load_yaml_rules,
    _rule_matches,
    evaluate_auto_rules,
)

# ---------------------------------------------------------------------------
# _load_yaml_rules
# ---------------------------------------------------------------------------


def test_load_yaml_rules_happy_path(tmp_path: Path) -> None:
    p = tmp_path / "rules.yaml"
    p.write_text(
        "always_trust:\n"
        "  - org_uri: stigmem://org-a\n"
        "    scope: null\n"
        "never_trust: []\n"
    )
    out = _load_yaml_rules(str(p))
    assert isinstance(out, dict)
    assert "always_trust" in out


def test_load_yaml_rules_file_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.yaml"
    assert _load_yaml_rules(str(missing)) == {}


def test_load_yaml_rules_invalid_yaml(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    # Unclosed string / unterminated mapping triggers a YAMLError.
    p.write_text("foo: [bar, baz\n  - oops:\n")
    assert _load_yaml_rules(str(p)) == {}


def test_load_yaml_rules_non_dict_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "list.yaml"
    p.write_text("- a\n- b\n- c\n")
    assert _load_yaml_rules(str(p)) == {}


# ---------------------------------------------------------------------------
# _rule_matches
# ---------------------------------------------------------------------------


def test_rule_matches_exact_org_and_scope() -> None:
    rule = {"org_uri": "stigmem://org-a", "scope": "public"}
    assert _rule_matches(rule, "stigmem://org-a", "public") is True


def test_rule_matches_null_scope_is_wildcard() -> None:
    rule = {"org_uri": "stigmem://org-a", "scope": None}
    assert _rule_matches(rule, "stigmem://org-a", "anything") is True


def test_rule_matches_non_matching_scope_returns_false() -> None:
    rule = {"org_uri": "stigmem://org-a", "scope": "private"}
    assert _rule_matches(rule, "stigmem://org-a", "public") is False


def test_rule_matches_mismatched_org_returns_false() -> None:
    rule = {"org_uri": "stigmem://org-a", "scope": None}
    assert _rule_matches(rule, "stigmem://org-other", "public") is False


# ---------------------------------------------------------------------------
# evaluate_auto_rules — file-based
# ---------------------------------------------------------------------------


@pytest.fixture()
def _isolated_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure trust_rules_file starts empty for each test in this section."""
    monkeypatch.setattr(settings_module.settings, "trust_rules_file", "", raising=False)


def test_evaluate_auto_rules_no_file_returns_none(
    _isolated_settings: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No DB rules either — patch _evaluate_db_rules to return None.
    monkeypatch.setattr(
        "stigmem_node.trust_rules._evaluate_db_rules", lambda _u, _s: None
    )
    assert evaluate_auto_rules("stigmem://org-a", "public") is None


def test_evaluate_auto_rules_file_always_trust(
    _isolated_settings: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = tmp_path / "rules.yaml"
    p.write_text(
        "always_trust:\n"
        "  - org_uri: stigmem://org-a\n"
        "    scope: null\n"
    )
    monkeypatch.setattr(settings_module.settings, "trust_rules_file", str(p))
    monkeypatch.setattr(
        "stigmem_node.trust_rules._evaluate_db_rules", lambda _u, _s: None
    )
    assert evaluate_auto_rules("stigmem://org-a", "public") == 1.0


def test_evaluate_auto_rules_file_never_trust(
    _isolated_settings: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = tmp_path / "rules.yaml"
    p.write_text(
        "never_trust:\n"
        "  - org_uri: stigmem://org-bad\n"
        "    scope: public\n"
    )
    monkeypatch.setattr(settings_module.settings, "trust_rules_file", str(p))
    monkeypatch.setattr(
        "stigmem_node.trust_rules._evaluate_db_rules", lambda _u, _s: None
    )
    assert evaluate_auto_rules("stigmem://org-bad", "public") == 0.0


def test_evaluate_auto_rules_file_no_matching_rule(
    _isolated_settings: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = tmp_path / "rules.yaml"
    p.write_text(
        "always_trust:\n"
        "  - org_uri: stigmem://org-a\n"
        "    scope: private\n"
        "never_trust:\n"
        "  - org_uri: stigmem://org-b\n"
        "    scope: secret\n"
    )
    monkeypatch.setattr(settings_module.settings, "trust_rules_file", str(p))
    monkeypatch.setattr(
        "stigmem_node.trust_rules._evaluate_db_rules", lambda _u, _s: None
    )
    # Different org / scope combination — no rule applies.
    assert evaluate_auto_rules("stigmem://org-c", "public") is None


def test_evaluate_auto_rules_db_precedence_over_file(
    _isolated_settings: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the DB rule says always_trust, the file is never consulted."""
    p = tmp_path / "rules.yaml"
    p.write_text(
        "never_trust:\n"
        "  - org_uri: stigmem://org-a\n"
        "    scope: null\n"
    )
    monkeypatch.setattr(settings_module.settings, "trust_rules_file", str(p))
    monkeypatch.setattr(
        "stigmem_node.trust_rules._evaluate_db_rules", lambda _u, _s: 1.0
    )
    assert evaluate_auto_rules("stigmem://org-a", "public") == 1.0


# ---------------------------------------------------------------------------
# _evaluate_db_rules — using a tmp DB
# ---------------------------------------------------------------------------


@pytest.fixture()
def _patched_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> str:
    """Apply migrations on a fresh sqlite DB and patch the global db settings to it."""
    import stigmem_node.db as db_mod
    from stigmem_node.db import apply_migrations
    from stigmem_node.settings import Settings

    db_file = str(tmp_path / "db.sqlite")
    apply_migrations(db_path=db_file)
    test_settings = Settings(db_path=db_file)
    monkeypatch.setattr(db_mod, "settings", test_settings, raising=False)
    monkeypatch.setattr(settings_module, "settings", test_settings, raising=False)
    return db_file


def _insert_quarantine_rule(
    db_file: str,
    *,
    rule_type: str,
    org_uri: str,
    scope: str | None,
) -> None:
    import sqlite3
    import time
    import uuid

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """INSERT INTO quarantine_rules (id, rule_type, org_uri, scope, entity_pat,
                                          reason, created_by, created_at, tenant_id)
           VALUES (?, ?, ?, ?, NULL, NULL, 'test', ?, NULL)""",
        (
            str(uuid.uuid4()),
            rule_type,
            org_uri,
            scope,
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        ),
    )
    conn.commit()
    conn.close()


def test_evaluate_db_rules_table_missing_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the DB cannot be opened / the table is missing, _evaluate_db_rules
    must swallow the exception and return None (graceful)."""
    import sqlite3

    import stigmem_node.db as db_mod

    # Construct a dummy db() context that raises on .execute() to simulate
    # a missing-table error without standing up a fresh DB.
    class _BadConn:
        def execute(self, *_a: object, **_kw: object) -> sqlite3.Cursor:
            raise sqlite3.OperationalError("no such table: quarantine_rules")

    from collections.abc import Iterator
    from contextlib import contextmanager

    @contextmanager
    def _bad_db() -> Iterator[_BadConn]:
        yield _BadConn()

    monkeypatch.setattr(db_mod, "db", _bad_db)
    # Re-import inside the function to pick up the patch (trust_rules imports lazily).
    assert _evaluate_db_rules("stigmem://org-a", "public") is None


def test_evaluate_db_rules_always_trust_match(_patched_db: str) -> None:
    _insert_quarantine_rule(
        _patched_db, rule_type="always_trust", org_uri="stigmem://org-x", scope=None
    )
    assert _evaluate_db_rules("stigmem://org-x", "public") == 1.0


def test_evaluate_db_rules_never_trust_match(_patched_db: str) -> None:
    _insert_quarantine_rule(
        _patched_db, rule_type="never_trust", org_uri="stigmem://org-y", scope="public"
    )
    assert _evaluate_db_rules("stigmem://org-y", "public") == 0.0


def test_evaluate_db_rules_wrong_scope_falls_through(_patched_db: str) -> None:
    """A rule whose scope doesn't match the query should be skipped; with
    only that one row in the table, the result is None."""
    _insert_quarantine_rule(
        _patched_db, rule_type="always_trust", org_uri="stigmem://org-z", scope="private"
    )
    assert _evaluate_db_rules("stigmem://org-z", "public") is None
