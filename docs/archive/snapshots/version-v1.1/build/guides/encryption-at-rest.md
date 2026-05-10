---
id: encryption-at-rest
title: Encryption at Rest
sidebar_label: Encryption at Rest
description: How to enable SQLCipher or libSQL native encryption for the Stigmem reference node, including key management and key-rotation runbook.
audience: Integrator
---

# Encryption at Rest

*Audience: node operators running production deployments.*

---

Stigmem supports transparent encryption-at-rest as an opt-in operator feature. The default is **plaintext** (dev-friendly); encryption is a one-flag flip.

Both storage backends support encryption:

| Backend | Encryption mechanism |
|---|---|
| SQLite (default) | **SQLCipher** — AES-256 in CBC mode, page-level |
| libSQL / Turso | **Native libSQL encryption** — same AES-256 page-level approach |

---

## Quick start

### SQLite + SQLCipher

**1. Install the extras**

SQLCipher requires the native C library installed on the host, plus the Python wheel:

```bash
# macOS (Homebrew)
brew install sqlcipher
pip install 'stigmem-node[encryption,sqlcipher]'

# Ubuntu / Debian
apt-get install -y libsqlcipher-dev
pip install 'stigmem-node[encryption,sqlcipher]'

# Alpine (Docker)
apk add --no-cache sqlcipher-dev
pip install 'stigmem-node[encryption,sqlcipher]'
```

**2. Generate and store a passphrase**

Use your secrets manager to create a strong passphrase:

```bash
# Generate a 32-byte passphrase (base64 for readability)
openssl rand -base64 32
# → hN2rq8...
```

Inject it as an environment variable — **never commit it**:

```bash
# In your deployment environment (Fly.io, Docker secrets, Kubernetes secret, etc.)
MY_STIGMEM_PASSPHRASE=hN2rq8...
```

**3. Configure the node**

```bash
STIGMEM_STORAGE_BACKEND=sqlite
STIGMEM_DB_PATH=/app/data/stigmem.db
STIGMEM_AT_REST_ENCRYPTION=on
STIGMEM_AT_REST_KEY_PASSPHRASE_ENV=MY_STIGMEM_PASSPHRASE
```

`STIGMEM_AT_REST_KEY_PASSPHRASE_ENV` is the **name** of the environment variable
that holds the passphrase — not the passphrase itself. This indirection keeps
the passphrase out of the Stigmem config namespace.

**4. First boot**

On first start with a new database path, Stigmem creates an encrypted database and
runs migrations. Subsequent starts open the same encrypted file with the same key.

```bash
stigmem-node
# → Stigmem node ready — db=/app/data/stigmem.db auth=False federation=disabled
```

If the passphrase env var is missing or the key source is misconfigured, the node
refuses to start with a clear error:

```
RuntimeError: STIGMEM_AT_REST_ENCRYPTION=on but no key source is configured. ...
```

---

### libSQL (Turso) + native encryption

```bash
pip install 'stigmem-node[libsql,encryption]'

STIGMEM_STORAGE_BACKEND=libsql
STIGMEM_DB_PATH=/app/data/stigmem.db
STIGMEM_LIBSQL_URL=libsql://your-db.turso.io
STIGMEM_LIBSQL_AUTH_TOKEN=<from-secrets-manager>

STIGMEM_AT_REST_ENCRYPTION=on
STIGMEM_AT_REST_KEY_PASSPHRASE_ENV=MY_STIGMEM_PASSPHRASE
```

The encryption key is applied to the **local replica file**. The Turso cloud
primary uses server-side encryption independently.

---

## Key source options

Stigmem supports two key sources. Exactly one must be set when
`STIGMEM_AT_REST_ENCRYPTION=on`; the node refuses to start if both are empty
or both are set.

### Option A — passphrase (Argon2id derivation)

```bash
STIGMEM_AT_REST_KEY_PASSPHRASE_ENV=MY_PASSPHRASE_VAR
```

The value of `MY_PASSPHRASE_VAR` is stretched into a 32-byte AES key using
Argon2id (OWASP 2023 parameters: `t=3, m=64 MiB, p=4`). Requires
`argon2-cffi` (`pip install 'stigmem-node[encryption]'`).

**When to use:** secrets manager stores a human-readable passphrase (e.g. a
long random string from `openssl rand -base64 48`).

### Option B — raw hex key via KMS URI

```bash
STIGMEM_AT_REST_KEY_KMS_URI=env://MY_HEX_KEY_VAR
```

`MY_HEX_KEY_VAR` must contain exactly 64 hex characters (32 bytes). No KDF is
applied — the raw bytes are used directly as the AES key.

```bash
# Generate a 32-byte hex key
openssl rand -hex 32
# → a3f8c2...  (64 chars)
```

**When to use:** your secrets manager vends a pre-derived 32-byte key (e.g.
AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault). Future releases will
add `aws-kms://`, `gcp-kms://`, and Vault KMS URI schemes for envelope
encryption.

---

## Encrypting an existing (plaintext) database

Converting a live plaintext database to encrypted requires a one-time migration
using the SQLCipher CLI or the `sqlcipher3` Python REPL. **Stop the node first.**

```bash
# Stop the node, then:
sqlcipher plaintext.db "ATTACH DATABASE 'encrypted.db' AS enc KEY \"x'$(python3 -c \"
import os; from stigmem_node.storage.encryption import derive_key
pp = os.environ['MY_STIGMEM_PASSPHRASE']
print(derive_key(pp.encode()).hex())
\")'\";"
sqlcipher plaintext.db "SELECT sqlcipher_export('enc'); DETACH DATABASE enc;"
mv encrypted.db stigmem.db
```

Then restart the node with `STIGMEM_AT_REST_ENCRYPTION=on`.

:::warning
Never delete the plaintext database until you have verified the encrypted version
boots and passes a basic query round-trip.
:::

---

## Key rotation runbook

**Goal:** replace the encryption key without service interruption (requires
brief maintenance window).

**Steps:**

1. **Stop the node** to ensure no writes occur during the transition.

2. **Export the current database as plaintext** (SQLCipher REPL):
   ```bash
   CURRENT_KEY=$(python3 -c "
   import os; from stigmem_node.storage.encryption import derive_key
   print(derive_key(os.environ['OLD_PASSPHRASE'].encode()).hex())
   ")
   sqlcipher stigmem.db \
     "PRAGMA key = \"x'${CURRENT_KEY}'\";" \
     "ATTACH DATABASE 'plain_tmp.db' AS plain KEY '';" \
     "SELECT sqlcipher_export('plain');" \
     "DETACH DATABASE plain;"
   ```

3. **Re-encrypt with the new key**:
   ```bash
   NEW_KEY=$(python3 -c "
   import os; from stigmem_node.storage.encryption import derive_key
   print(derive_key(os.environ['NEW_PASSPHRASE'].encode()).hex())
   ")
   sqlcipher plain_tmp.db \
     "ATTACH DATABASE 'stigmem_new.db' AS enc KEY \"x'${NEW_KEY}'\";" \
     "SELECT sqlcipher_export('enc');" \
     "DETACH DATABASE enc;"
   mv stigmem_new.db stigmem.db
   rm plain_tmp.db
   ```

4. **Update the secret** in your secrets manager and redeploy with the new
   passphrase/key env var.

5. **Restart the node** — it opens the re-encrypted database with the new key.

---

## Running the conformance suite in encrypted mode

```bash
pip install 'stigmem-node[dev,encryption,sqlcipher]'
cd node
pytest --encrypt=on
```

`--encrypt=on` redirects all test fixtures to use encrypted SQLite storage with
a CI-only test passphrase. The full conformance suite passes without modification.

Note: federation tests (`test_federation.py`, `test_4node_federation.py`) use
direct database path fixtures that bypass encryption settings; run those tests
separately in plaintext mode.

---

## Security notes

- **Key material is never logged.** Exception messages from the key-loading code
  deliberately omit passphrase and key values.
- **Fixed KDF salt** — the Argon2id salt is a domain-separator constant. Security
  comes from the passphrase entropy, not salt randomness. This is appropriate for
  high-entropy operator secrets.
- **SQLCipher page-level encryption** — all pages including the schema are
  encrypted. An attacker with file access cannot determine table names, record
  counts, or any data without the key.
- **Snapshots are encrypted** — `stigmem snapshot create` produces snapshots
  encrypted with the same key. Store snapshot files with the same access controls
  as the database.
- **No key in config files** — `STIGMEM_AT_REST_KEY_PASSPHRASE_ENV` stores the
  **name** of the env var, not the value. The passphrase never passes through
  Stigmem's configuration namespace.
