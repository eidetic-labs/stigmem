from __future__ import annotations


def test_cli_capability_issue_parser() -> None:
    """stigmem capability issue must parse args correctly (M-SEC-3)."""
    from stigmem_node.cli import _build_parser

    parser = _build_parser()

    args = parser.parse_args(
        [
            "capability",
            "issue",
            "--issuer",
            "https://example.org",
            "--subject",
            "https://example.org",
            "--verb",
            "write",
            "--object",
            "stigmem://facts",
        ]
    )
    assert args.issuer == "https://example.org"
    assert args.verb == "write"
    assert callable(args.func)


def test_cli_capability_verify_parser() -> None:
    """stigmem capability verify TOKEN must parse without error (M-SEC-3)."""
    from stigmem_node.cli import _build_parser

    parser = _build_parser()

    args = parser.parse_args(["capability", "verify", '{"token_version":1}'])
    assert args.token_json == '{"token_version":1}'
    assert callable(args.func)


def test_cli_capability_revoke_parser() -> None:
    """stigmem capability revoke TOKEN_ID must parse without error (M-SEC-3)."""
    from stigmem_node.cli import _build_parser

    parser = _build_parser()

    args = parser.parse_args(["capability", "revoke", "some-token-id", "--reason", "expired"])
    assert args.token_id == "some-token-id"
    assert args.reason == "expired"
    assert callable(args.func)


# ===========================================================================
# 19. POST /v1/federation/capability-tokens/verify endpoint
# ===========================================================================
