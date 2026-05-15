"""Capability-token CLI handlers."""

from __future__ import annotations

import argparse
import sys


def _cmd_capability_issue(args: argparse.Namespace) -> int:
    """Issue a capability token via the local node HTTP API."""
    import json

    import httpx

    payload = {
        "issuer": args.issuer,
        "subject": args.subject,
        "verb": args.verb,
        "object": args.object,
    }
    if args.ttl_seconds is not None:
        payload["ttl_seconds"] = args.ttl_seconds

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    try:
        resp = httpx.post(
            f"{args.node_url.rstrip('/')}/v1/federation/capability-tokens",
            json=payload,
            headers=headers,
            timeout=15.0,
        )
    except Exception as exc:
        print(f"error: cannot reach node at {args.node_url}: {exc}", file=sys.stderr)
        return 1

    if resp.status_code == 201:
        data = resp.json()
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(f"token_id:  {data['token_id']}")
            print(f"issuer:    {data['issuer']}")
            print(f"subject:   {data['subject']}")
            print(f"verb:      {data['verb']}")
            print(f"object:    {data['object']}")
            print(f"expiry:    {data['expiry']}")
            print(f"token_json: {data['token_json']}")
        return 0

    print(f"error: {resp.status_code}: {resp.text}", file=sys.stderr)
    return 1


def _cmd_capability_verify(args: argparse.Namespace) -> int:
    """Verify a capability token via the local node HTTP API."""
    import json

    import httpx

    token_json_str = args.token_json
    if token_json_str == "-":  # nosec B105 — "-" is stdin sentinel, not a password
        token_json_str = sys.stdin.read().strip()

    headers: dict[str, str] = {}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    try:
        resp = httpx.post(
            f"{args.node_url.rstrip('/')}/v1/federation/capability-tokens/verify",
            json={"token_json": token_json_str},
            headers=headers,
            timeout=15.0,
        )
    except Exception as exc:
        print(f"error: cannot reach node at {args.node_url}: {exc}", file=sys.stderr)
        return 1

    if resp.status_code == 200:
        data = resp.json()
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            valid = data.get("valid", False)
            print(f"valid: {valid}")
            if not valid:
                print(f"reason: {data.get('reason', 'unknown')}")
        return 0

    # Treat 422/400 as invalid (not an HTTP error — the token itself is invalid)
    if resp.status_code in (422, 400):
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        print(f"invalid: {detail}", file=sys.stderr)
        return 1

    print(f"error: {resp.status_code}: {resp.text}", file=sys.stderr)
    return 1


def _cmd_capability_revoke(args: argparse.Namespace) -> int:
    """Revoke a capability token via the local node HTTP API."""
    import json

    import httpx

    payload: dict[str, str] = {}
    if args.reason:
        payload["reason"] = args.reason

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    try:
        resp = httpx.post(
            f"{args.node_url.rstrip('/')}/v1/federation/capability-tokens/{args.token_id}/revoke",
            json=payload,
            headers=headers,
            timeout=15.0,
        )
    except Exception as exc:
        print(f"error: cannot reach node at {args.node_url}: {exc}", file=sys.stderr)
        return 1

    if resp.status_code == 200:
        data = resp.json()
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(f"revoked: {data['token_id']} at {data['revoked_at']}")
        return 0

    if resp.status_code == 404:
        print(f"error: token not found: {args.token_id}", file=sys.stderr)
        return 1
    if resp.status_code == 409:
        print(f"error: token already revoked: {args.token_id}", file=sys.stderr)
        return 1

    print(f"error: {resp.status_code}: {resp.text}", file=sys.stderr)
    return 1
