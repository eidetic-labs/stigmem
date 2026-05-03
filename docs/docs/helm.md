---
id: helm
title: Helm Deployment
sidebar_label: Helm
---

# Helm Deployment

**Audience:** platform engineers deploying Stigmem nodes on Kubernetes via Helm.

:::info Coming soon
Stigmem does not yet ship an official Helm chart. Docker Compose is the current supported deployment path — see [Deployment & Installation](./install).

This page will be completed when a Helm chart is published. If Kubernetes support is a priority for your team, open an issue at [github.com/Eidetic-Labs/stigmem](https://github.com/Eidetic-Labs/stigmem).
:::

---

## Planned chart structure

When the chart is released, it will expose the same environment variables documented in the [env var reference](./install#environment-variable-reference) as Helm values. The expected shape:

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

## Current alternative: Docker Compose

Until the Helm chart is available, you can run Stigmem on Kubernetes using a plain `Deployment` + `Service` manifest with the same environment variables. Refer to the [env var reference](./install#environment-variable-reference) for the full variable list.

For local and single-host deployments, use Docker Compose — see [Deployment & Installation](./install).
