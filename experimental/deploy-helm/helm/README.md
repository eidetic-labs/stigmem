# Helm Deploy Recipe

Kubernetes / enterprise deployment via Helm.

## Prerequisites

- Helm v3
- A Kubernetes cluster with a default StorageClass (for the PVC)
- `kubectl` configured for the target cluster

## Quick install

```bash
# From repo root — installs with defaults (SQLite, no auth, no ingress):
helm install stigmem experimental/deploy-helm/helm/stigmem --namespace stigmem --create-namespace

# Check status
kubectl -n stigmem get pods
kubectl -n stigmem logs deployment/stigmem

# Port-forward for local testing
kubectl -n stigmem port-forward svc/stigmem 8765:8765
curl http://localhost:8765/healthz
```

## Common overrides

### Enable OIDC auth

```yaml
# my-values.yaml
stigmem:
  authRequired: true
  oidcEnabled: true
  oidcIssuerUrl: "https://accounts.google.com"
  oidcAudience: "my-client-id"
  oidcAllowedDomains: "example.com"
```

### Ingress with TLS (cert-manager)

```yaml
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: stigmem.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: stigmem-tls
      hosts:
        - stigmem.example.com

stigmem:
  nodeUrl: "https://stigmem.example.com"
```

### libSQL / Turso backend

```bash
# Store token in a Secret
kubectl -n stigmem create secret generic stigmem-libsql \
  --from-literal=auth-token="<TURSO_TOKEN>"
```

```yaml
stigmem:
  storageBackend: libsql
  libsqlUrl: "libsql://<DB>.turso.io"

libsqlSecret:
  name: stigmem-libsql
  authTokenKey: auth-token
```

### Encryption at rest

```bash
kubectl -n stigmem create secret generic stigmem-encryption \
  --from-literal=passphrase="<STRONG_RANDOM_PASSPHRASE>"
```

```yaml
stigmem:
  atRestEncryption: "on"
  atRestKeyPassphraseEnv: "STIGMEM_DB_PASSPHRASE"

atRestEncryptionSecret:
  name: stigmem-encryption
  passphraseKey: passphrase
```

### Federation keypair

```bash
kubectl -n stigmem create secret generic stigmem-federation \
  --from-literal=pubkey="<BASE64URL_PUBKEY>" \
  --from-literal=privkey="<BASE64URL_PRIVKEY>"
```

```yaml
stigmem:
  federationEnabled: true
  federationPubkey: "<BASE64URL_PUBKEY>"

federationKeypairSecret:
  name: stigmem-federation
  pubkeyKey: pubkey
  privkeyKey: privkey
```

### Resource limits

```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

## Upgrade

```bash
helm upgrade stigmem experimental/deploy-helm/helm/stigmem -n stigmem -f my-values.yaml
```

## Uninstall (keeps PVC)

```bash
helm uninstall stigmem -n stigmem
# To also delete the PVC:
kubectl -n stigmem delete pvc stigmem
```

## Multi-instance federation

Deploy multiple Helm releases (one per node) with different `nodeUrl` values and
exchange federation invites. See docs.stigmem.dev/guides/federation.
