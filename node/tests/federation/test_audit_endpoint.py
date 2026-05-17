from __future__ import annotations

import json
import uuid

from conftest import FedNode

from stigmem_node.db import db as _db_ctx


class TestFederationAuditEndpoint:
    def test_filters_peer_and_paginates_entries(self, fed_node: FedNode) -> None:
        peer_id = f"peer-{uuid.uuid4()}"
        other_peer_id = f"peer-{uuid.uuid4()}"
        rows = [
            (
                str(uuid.uuid4()),
                peer_id,
                "replay_attempt",
                {"nonce": "n1"},
                "2026-05-03T00:00:01Z",
            ),
            (
                str(uuid.uuid4()),
                peer_id,
                "scope_violation",
                {"scope": "company"},
                "2026-05-03T00:00:02Z",
            ),
            (
                str(uuid.uuid4()),
                peer_id,
                "rejected_fact",
                {"reason": "source_not_owned"},
                "2026-05-03T00:00:03Z",
            ),
            (
                str(uuid.uuid4()),
                other_peer_id,
                "replay_attempt",
                {"nonce": "other"},
                "2026-05-03T00:00:04Z",
            ),
        ]

        with _db_ctx() as conn:
            for entry_id, row_peer_id, event_type, detail, ts in rows:
                conn.execute(
                    "INSERT INTO federation_audit (id, peer_id, event_type, detail, ts) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (entry_id, row_peer_id, event_type, json.dumps(detail), ts),
                )

        response = fed_node.client.get(
            f"/v1/federation/audit?peer_id={peer_id}&limit=2",
            headers={"Authorization": f"Bearer {fed_node.federate_key}"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["has_more"] is True
        assert body["cursor"] is not None
        assert [entry["peer_id"] for entry in body["entries"]] == [peer_id, peer_id]
        assert [entry["event_type"] for entry in body["entries"]] == [
            "rejected_fact",
            "scope_violation",
        ]
        assert body["entries"][0]["detail"] == {"reason": "source_not_owned"}

        filtered_response = fed_node.client.get(
            f"/v1/federation/audit?peer_id={peer_id}&event_type=scope_violation",
            headers={"Authorization": f"Bearer {fed_node.federate_key}"},
        )

        assert filtered_response.status_code == 200
        filtered_entries = filtered_response.json()["entries"]
        assert len(filtered_entries) == 1
        assert filtered_entries[0]["event_type"] == "scope_violation"
        assert filtered_entries[0]["detail"] == {"scope": "company"}
