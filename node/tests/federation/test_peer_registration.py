from __future__ import annotations

import logging
import uuid

import pytest
from conftest import FedNode, generate_keypair, sign_declaration

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

    def test_valid_declaration_registers_as_active(
        self, fed_node: FedNode, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Valid declaration + matching well-known pubkey → status active (§5.6)."""
        import httpx as _httpx

        peer_pub, peer_priv = generate_keypair()
        node_b_id = f"stigmem://test-b-reg-{uuid.uuid4()}"
        node_b_url = "http://test-b-reg"

        body = self._build_declaration(node_b_id, node_b_url, peer_pub, peer_priv)

        # Mock the well-known fetch that register_peer performs
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

        r = fed_node.client.post(
            "/v1/federation/peers",
            json=body,
            headers={"Authorization": f"Bearer {fed_node.federate_key}"},
        )

        assert r.status_code == 201, r.text
        data = r.json()
        assert data["status"] == "active", f"Expected active, got: {data}"
        assert data["verified_at"] is not None

    def test_tampered_declaration_rejected(
        self, fed_node: FedNode, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Declaration where signature doesn't match payload → status rejected (§5.6 §6.1)."""
        import httpx as _httpx

        peer_pub, peer_priv = generate_keypair()
        node_b_id = f"stigmem://test-b-tamper-{uuid.uuid4()}"
        node_b_url = "http://test-b-tamper"

        body = self._build_declaration(node_b_id, node_b_url, peer_pub, peer_priv)
        # Tamper: change allowed_scopes after signing → signature no longer valid
        body["allowed_scopes"] = ["company", "public"]

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
