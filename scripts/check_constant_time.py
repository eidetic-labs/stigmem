#!/usr/bin/env python3
"""CT001: Static check — flag == / != comparisons on potentially-secret values.

Prevents regressions after the Phase 12 constant-time crypto audit (ACM-256).
All signature/MAC/digest comparisons should use hmac.compare_digest; this
script enforces that at the AST level.

Usage:
    python scripts/check_constant_time.py [paths...]

Exit codes:
    0 — clean
    1 — violations found

To suppress a false-positive on a specific line, add:
    # nosec CT001
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# Name fragments that indicate cryptographic secret material.
# Deliberately narrow — false positives are more harmful than false negatives.
_SECRET_FRAGMENTS: tuple[str, ...] = (
    "signature",   # e.g. token_sig, declaration_sig, sig_bytes, sig_b64
    "_sig",        # e.g. rot_sig, wrong_sig, declaration_sig (suffix match)
    "sig_",        # e.g. sig_bytes, sig_b64 (prefix match)
    "hmac",        # explicit HMAC values
    "digest",      # hash digests used as authenticators
    "key_hash",    # e.g. key_hash, key_hash_hex (stored API-key digest)
    "secret",      # generic secret strings
    "password",    # passwords / passphrases
    "passwd",      # password aliases
)

# Exact lowercase names that resemble secrets but are not secret material.
_SAFE_NAMES: frozenset[str] = frozenset(
    {
        "key_id",
        "previous_key_id",
        "new_key_id",
        "token_version",
        "token_kind",
        "status",
        "kind",
        "event_type",
        "signing_body",   # bytes payload to be signed, not a secret
    }
)


def _name_from_node(node: ast.expr) -> str | None:
    """Extract a simple name or subscript key string from an AST expression."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        s = node.slice
        if isinstance(s, ast.Constant) and isinstance(s.value, str):
            return s.value
    return None


def _is_secret_name(name: str) -> bool:
    nl = name.lower()
    if nl in _SAFE_NAMES:
        return False
    return any(frag in nl for frag in _SECRET_FRAGMENTS)


def check_file(path: Path) -> list[tuple[int, str]]:
    """Return (line_number, message) for each CT001 violation in *path*."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = source.splitlines()

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    violations: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if not any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops):
            continue

        lineno = node.lineno
        line_text = lines[lineno - 1] if lineno <= len(lines) else ""

        if "nosec CT001" in line_text:
            continue

        operands: list[ast.expr] = [node.left, *node.comparators]
        for operand in operands:
            name = _name_from_node(operand)
            if name and _is_secret_name(name):
                violations.append(
                    (
                        lineno,
                        f"CT001 non-constant-time == / != on '{name}' "
                        "— use hmac.compare_digest instead",
                    )
                )
                break  # one violation per comparison node

    return violations


def main(argv: list[str]) -> int:
    roots = argv[1:] if len(argv) > 1 else ["."]
    violations: list[tuple[Path, int, str]] = []

    for root_str in roots:
        root = Path(root_str)
        py_files = [root] if root.is_file() else sorted(root.rglob("*.py"))
        for py_file in py_files:
            for lineno, msg in check_file(py_file):
                violations.append((py_file, lineno, msg))

    for file_path, lineno, msg in violations:
        print(f"{file_path}:{lineno}: {msg}")

    if violations:
        print(
            f"\nCT001: {len(violations)} violation(s) found. "
            "Replace == / != with hmac.compare_digest, or add  # nosec CT001  "
            "if the comparison is demonstrably non-secret."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
