# Operating Stigmem

This is the plain-English operating manual for a self-hosted Stigmem node. It is
written for the person on call: what to run, what to watch, and what to do when
something breaks.

The complete web docs live under [`docs/docs/operators/`](docs/docs/operators/).
Use this file as the repo-root entry point.

## Production Readiness

Before putting a node on the public internet or joining a federation:

- Run the supported v0.9.0a1 deployment path unless you are deliberately testing
  an experimental surface. Docker Compose is the supported default; Helm, Fly.io,
  PaaS recipes, Grafana dashboards, and non-SQLite storage backends are
  experimental.
- Store every secret in a secrets manager, not in Git, shell history, or checked
  in compose files.
- Enable TLS for all client traffic. For federation, enable mTLS and pin peer
  keys.
- Set API keys with expirations and rotate admin keys on a schedule.
- Back up the database before enabling federation or running migrations.
- Route node logs and `/metrics` into your normal monitoring stack.

## Run A Node

Start with the install and deployment docs:

- [Install](docs/docs/operators/deployment/install.md)
- [Release verification](docs/docs/operators/release-verification.md)
- [Deploy runbooks](docs/docs/operators/runbooks/deploy-runbooks.md)
- [Monitoring and debugging](docs/docs/operators/observability/monitoring.md)

At minimum, configure:

| Setting | Purpose |
|---|---|
| `STIGMEM_DB_PATH` | Persistent database location for the node. |
| `STIGMEM_AUTH_REQUIRED=true` | Requires callers to authenticate. |
| `STIGMEM_RATE_LIMIT_WRITE_PER_HOUR` / `STIGMEM_RATE_LIMIT_READ_PER_HOUR` | Prevents runaway clients from exhausting the node. |
| `STIGMEM_LOG_LEVEL=info` | Keeps production logs useful without debug-volume noise. |
| `STIGMEM_NODE_URL` | Public URL advertised to clients and peers. |

Use `/healthz` as the liveness/readiness probe and `/metrics` as the Prometheus
scrape target.

Before deploying a tagged release, verify its supply-chain evidence. The GHCR
node image is keyless-signed with Sigstore/cosign, carries an SPDX SBOM and
BuildKit provenance as OCI referrers, and records Rekor transparency-log
evidence through the keyless signing flow. npm and PyPI packages use registry
provenance via GitHub Actions OIDC. Use
[Release Verification](docs/docs/operators/release-verification.md) for the
commands and acceptance checks.

## Peer With Another Org

Federation is a trust relationship with another operator. Before enabling it:

1. Exchange node URLs and Ed25519 public keys out of band.
2. Enable federation and mTLS.
3. Register the peer and pin its public key.
4. Confirm facts from the peer land where expected.
5. Watch audit events and quarantine volume during the first pull cycles.

Detailed setup lives in
[Federation Peer Setup](docs/docs/operators/runbooks/federation-setup.md).

## Rotate Keys

Rotate keys deliberately and record the date. There are three operational key
classes:

| Key | Rotation impact |
|---|---|
| API keys | Revoke and recreate caller credentials; review audit activity for the retiring key. |
| Node federation keypair | Coordinate with peers so they can re-pin or refresh your manifest. |
| At-rest encryption passphrase | Stop the node and rekey the database with exclusive access. |

Use [Key Rotation](docs/docs/security/key-rotation.md) for the full procedure.
If a key has already expired and production traffic is blocked, use
[R-KEY-EXPIRY](docs/docs/operators/runbooks/r-key-expiry.md).

## Read The Audit Log

Use the audit log when an operator question starts with "who did what?" or "when
did this begin?"

Common checks:

```bash
# Recent audit events
curl -s "https://your-node.example.com/v1/audit/events?limit=50" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" | jq .

# Federation-focused events
curl -s "https://your-node.example.com/v1/federation/audit?limit=50" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" | jq .
```

Look for:

- Unexpected `admin_action` events.
- `peer_capability_violation`, `peer_replay_rejected`, or handshake failures.
- Sudden changes in `fact_write` volume by one principal or peer.
- `peer_hlc_anomaly` events.
- `manifest_rotation_failed`, `key_expiring_soon`, or `key_expired_blocked`.

See [Audit Log](docs/docs/security/audit-log.md) and
[Audit and Quotas](docs/docs/security/audit-and-quotas.md).

## Alerts To Set

At minimum, alert on:

| Alert | When to page |
|---|---|
| Node down | `/healthz` is not healthy for more than one minute. |
| High recall latency | 99th percentile recall latency stays above five seconds. |
| Federation pull errors | Pull errors from one peer spike repeatedly. |
| Peer capability violation | Any peer attempts an operation outside its granted capability. |
| Replay burst | More than five replay rejections from one peer in an hour. |
| HLC critical drift | One peer sends a timestamp more than 300 seconds outside the allowed future skew. |
| Manifest rotation failure | Any peer manifest/key rotation fails verification. |
| Key expired blocked | Any production operation is blocked by an expired key. |
| Quarantine backlog | More than 50 facts waiting or any fact older than 24 hours. |

Prometheus examples live in
[Monitoring and Debugging](docs/docs/operators/observability/monitoring.md).

## Recovery Runbooks

Critical federation alerts map to these runbooks:

| Runbook | Use when |
|---|---|
| [R-PEER-COMPROMISE](docs/docs/operators/runbooks/r-peer-compromise.md) | A peer violates capabilities, replays tokens, rotates suspiciously, or injects unexpected facts. |
| [R-WORM-DETECTED](docs/docs/operators/runbooks/r-worm-detected.md) | Agent-read and agent-write patterns suggest automated cross-peer spread. |
| [R-MANIFEST-FAILURE](docs/docs/operators/runbooks/r-manifest-failure.md) | Peer manifest or rotation verification fails. |
| [R-HLC-DRIFT](docs/docs/operators/runbooks/r-hlc-drift.md) | A peer sends timestamps outside allowed skew. |
| [R-KEY-EXPIRY](docs/docs/operators/runbooks/r-key-expiry.md) | Production traffic is blocked by an expired API, issuer, or federation key. |

Each runbook follows the same shape: identify, contain, investigate, recover,
and communicate.

## During An Incident

1. Preserve evidence first: export relevant audit events and current peer/key
   state before making changes.
2. Contain the blast radius: disable the peer, revoke the key, pause federation,
   or tighten quotas.
3. Investigate scope: identify affected peers, principals, scopes, and facts.
4. Recover carefully: retract bad facts, rotate keys, republish manifests, and
   re-enable only after verification.
5. Communicate with affected peer operators. If public trust is implicated,
   publish a short incident note naming impact, containment, and follow-up.

Keep incident notes in your own operations system. Do not store secrets or
customer data in GitHub issues.
