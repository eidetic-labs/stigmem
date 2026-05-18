from __future__ import annotations

import logging
import uuid

import pytest
from conftest import FedNode, generate_keypair, make_peer_token, sign_declaration

from stigmem_node.auth import create_api_key
from stigmem_node.db import db as node_db
from stigmem_node.routes._federation_impl import peer_pubkey_fingerprint

logger = logging.getLogger(__name__)


class TestPeerRegistration:
    """Exercises the HTTP peer-registration route and declaration_sig verification."""

    def _build_declaration(
        self,
        node_id: str,
        node_url: str,
        pub_b64: str,
        priv_b64: str,
        allowed_scopes: list[str] | None = None,
        signed_at: str = "2026-05-02T00:00:00Z",
    ) -> dict:
        """Build a valid PeerDeclaration body per spec §6.1."""
        scopes = allowed_scopes or ["public"]
        # signed_fields must NOT include declaration_sig (spec §6.1 "above fields")
        fields_to_sign = {
            "allowed_scopes": scopes,
            "federation_pubkey": pub_b64,
            "node_id": node_id,
            "node_url": node_url,
            "signed_at": signed_at,
        }
        sig = sign_declaration(priv_b64, fields_to_sign)
        return {
            "node_id": node_id,
            "node_url": node_url,
            "federation_pubkey": pub_b64,
            "allowed_scopes": scopes,
            "declaration_sig": sig,
            "signed_at": signed_at,
        }

    def _mock_well_known(self, monkeypatch: pytest.MonkeyPatch, peer_pub: str) -> None:
        """Mock the well-known fetch that register_peer performs."""
        import httpx as _httpx

        class _MockAsyncClient:
            async def __aenter__(self) -> _MockAsyncClient:
                return self

            async def __aexit__(self, *args: object) -> None:
                pass

            async def get(self, url: str) -> _httpx.Response:
                return _httpx.Response(200, json={"federation_pubkey": peer_pub})

        monkeypatch.setattr(
            "stigmem_node.routes._federation_impl.httpx.AsyncClient",
            lambda **_: _MockAsyncClient(),
        )

    def test_valid_declaration_registers_as_pending_approval(
        self, fed_node: FedNode, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Valid declaration + matching well-known pubkey → pending operator approval."""

        peer_pub, peer_priv = generate_keypair()
        node_b_id = f"stigmem://test-b-reg-{uuid.uuid4()}"
        node_b_url = "http://test-b-reg"

        body = self._build_declaration(node_b_id, node_b_url, peer_pub, peer_priv)
        self._mock_well_known(monkeypatch, peer_pub)

        r = fed_node.client.post(
            "/v1/federation/peers",
            json=body,
            headers={"Authorization": f"Bearer {fed_node.federate_key}"},
        )

        assert r.status_code == 201, r.text
        data = r.json()
        assert data["status"] == "pending_approval", data
        assert data["verified_at"] is None

    def test_pending_peer_token_rejected_until_approved(
        self, fed_node: FedNode, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        peer_pub, peer_priv = generate_keypair()
        node_b_id = f"stigmem://test-b-pending-{uuid.uuid4()}"
        node_b_url = "http://test-b-pending"
        body = self._build_declaration(node_b_id, node_b_url, peer_pub, peer_priv)
        self._mock_well_known(monkeypatch, peer_pub)

        register = fed_node.client.post(
            "/v1/federation/peers",
            json=body,
            headers={"Authorization": f"Bearer {fed_node.federate_key}"},
        )
        assert register.status_code == 201, register.text
        token = make_peer_token(peer_priv, node_b_id, fed_node.node_id, ["public"])

        response = fed_node.client.get(
            "/v1/federation/facts",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "peer_not_approved"

    def test_approve_peer_requires_matching_fingerprint_and_writes_audit(
        self, fed_node: FedNode, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        peer_pub, peer_priv = generate_keypair()
        node_b_id = f"stigmem://test-b-approve-{uuid.uuid4()}"
        node_b_url = "http://test-b-approve"
        body = self._build_declaration(node_b_id, node_b_url, peer_pub, peer_priv)
        self._mock_well_known(monkeypatch, peer_pub)

        admin_key = create_api_key("agent:federation-admin", ["admin:federation"])
        register = fed_node.client.post(
            "/v1/federation/peers",
            json=body,
            headers={"Authorization": f"Bearer {fed_node.federate_key}"},
        )
        assert register.status_code == 201, register.text
        peer_id = register.json()["peer_id"]

        wrong = fed_node.client.post(
            f"/v1/federation/peers/{peer_id}/approve",
            json={"pubkey_fingerprint": "sha256:wrong"},
            headers={"Authorization": f"Bearer {admin_key}"},
        )
        assert wrong.status_code == 400

        approve = fed_node.client.post(
            f"/v1/federation/peers/{peer_id}/approve",
            json={"pubkey_fingerprint": peer_pubkey_fingerprint(peer_pub)},
            headers={"Authorization": f"Bearer {admin_key}"},
        )
        assert approve.status_code == 200, approve.text
        assert approve.json()["status"] == "active"

        token = make_peer_token(peer_priv, node_b_id, fed_node.node_id, ["public"])
        response = fed_node.client.get(
            "/v1/federation/facts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text

        with node_db() as conn:
            audit_events = [
                row["event_type"]
                for row in conn.execute(
                    "SELECT event_type FROM federation_audit WHERE peer_id = ?",
                    (peer_id,),
                ).fetchall()
            ]
        assert "peer_approval_failed" in audit_events
        assert "peer_approved" in audit_events

    def test_tampered_declaration_rejected(
        self, fed_node: FedNode, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Declaration where signature doesn't match payload → status rejected (§5.6 §6.1)."""

        peer_pub, peer_priv = generate_keypair()
        node_b_id = f"stigmem://test-b-tamper-{uuid.uuid4()}"
        node_b_url = "http://test-b-tamper"

        body = self._build_declaration(node_b_id, node_b_url, peer_pub, peer_priv)
        # Tamper: change allowed_scopes after signing → signature no longer valid
        body["allowed_scopes"] = ["company", "public"]
        self._mock_well_known(monkeypatch, peer_pub)

        r = fed_node.client.post(
            "/v1/federation/peers",
            json=body,
            headers={"Authorization": f"Bearer {fed_node.federate_key}"},
        )

        assert r.status_code == 201, r.text
        assert r.json()["status"] == "rejected"


# ---------------------------------------------------------------------------
# §11.1 — Split-Brain acceptance scenario
# ---------------------------------------------------------------------------
