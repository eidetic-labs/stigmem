---
title: Helm Deployment
sidebar_label: Helm
audience: Operator
---

# Helm Deployment

**Audience:** platform engineers deploying Stigmem nodes on Kubernetes via Helm.

The Helm chart ships in [`experimental/deploy-helm/helm/stigmem/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/deploy-helm/helm/stigmem)
in the main repository. Install it directly from that path:

```bash
# Quick install with defaults (SQLite, no auth, no ingress):
helm install stigmem experimental/deploy-helm/helm/stigmem --namespace stigmem --create-namespace
```

See the **[Helm recipe README](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/deploy-helm/helm/README.md)**
for full instructions: ingress, TLS, libSQL/Turso, encryption at rest, federation keypair secrets,
and multi-instance federation.

---

## Chart values

The chart exposes all `STIGMEM_*` env vars as Helm values. The expected shape:

```yaml
# values.yaml (preview — subject to change)
image:
  repository: ghcr.io/eidetic-labs/stigmem-node
  tag: latest
  pullPolicy: IfNotPresent

replicaCount: 1

service:
  type: ClusterIP
  port: 8765

persistence:
  enabled: true
  storageClass: ""
  size: 1Gi
  # Mount path corresponds to STIGMEM_DB_PATH
  mountPath: /data

stigmem:
  # Core
  nodeUrl: "http://stigmem:8765"
  logLevel: "info"
  authRequired: false
  dbPath: "/data/stigmem.db"

  # Federation (spec §6)
  federationEnabled: false
  federationPullIntervalS: 30
  federationPushEnabled: false
  federationNonceWindowS: 300
  federationAllowTeam: false
  # Ed25519 keypair — supply via secretRef in production
  federationPubkey: ""
  federationPrivkey: ""

  # Decay (spec §15)
  decayTtlSeconds: 0
  decayMinConfidence: 0.0

  # Attestation & security (spec §18)
  attestationRequired: false
  sourceAttestationMode: "warn"

  # OIDC bridge (spec §B3)
  oidcEnabled: false
  oidcIssuerUrl: ""
  oidcAudience: ""
  oidcTokenTtlHours: 8
  oidcAllowedDomains: ""

  # Performance
  asyncJobThreshold: 100000

# Supply federation keypairs via a pre-existing Secret
# to avoid embedding private keys in values.yaml.
federationKeypairSecret:
  name: ""        # name of the Secret
  pubkeyKey: ""   # key holding the base64url public key
  privkeyKey: ""  # key holding the base64url private key
```

:::caution Keypair management
Never embed `STIGMEM_FEDERATION_PRIVKEY` directly in a `values.yaml` file committed to source control. Use a Kubernetes Secret (referenced via `federationKeypairSecret`) or a secrets manager (Vault, AWS Secrets Manager, etc.).
:::

---

## Other deployment options

| Recipe | Guide |
|---|---|
| Fly.io | [`deploy/fly/`](https://github.com/Eidetic-Labs/stigmem/tree/main/deploy/fly) |
| Docker Compose | [`deploy/compose/`](https://github.com/Eidetic-Labs/stigmem/tree/main/deploy/compose) |
| systemd / bare-metal | [`deploy/systemd/`](https://github.com/Eidetic-Labs/stigmem/tree/main/deploy/systemd) |
| Render / Railway / App Runner / Cloud Run | [`deploy/paas/`](https://github.com/Eidetic-Labs/stigmem/tree/main/deploy/paas) |

See the top-level [`deploy/README.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/deploy/README.md)
decision tree for help picking the right recipe.

For local and single-host deployments, see [Deployment & Installation](./install).
