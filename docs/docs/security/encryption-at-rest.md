---
title: Encryption at Rest
sidebar_label: Encryption at Rest
description: How to enable SQLCipher or libSQL native encryption for the Stigmem reference node, including key management and key-rotation runbook.
audience: Integrator
---

# Encryption at Rest

<p className="stigmem-meta"><span>5 min read</span><span>Operator</span><span>Opt-in</span></p>

<div className="stigmem-lead">

**What this page is**

Stigmem supports transparent encryption-at-rest as an opt-in operator
feature. The default is **plaintext** (dev-friendly); encryption is a
one-flag flip.

</div>

Both storage backends support encryption.

<div className="stigmem-fields">

<div>
<dt>Backend</dt>
<dt><span className="stigmem-fields__type">Mechanism</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>SQLite (default)</dt>
<dt><span className="stigmem-fields__type">SQLCipher</span></dt>
<dd>AES-256 in CBC mode, page-level.</dd>
</div>

<div>
<dt>libSQL / Turso</dt>
<dt><span className="stigmem-fields__type">native libSQL encryption</span></dt>
<dd>Same AES-256 page-level approach.</dd>
</div>

</div>

## Quick start

### SQLite + SQLCipher

#### 1 · Install the extras

SQLCipher requires the native C library installed on the host, plus
the Python wheel:

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

#### 2 · Generate and store a passphrase

```bash
# Generate a 32-byte passphrase (base64 for readability)
openssl rand -base64 32
# → hN2rq8...
```

Inject it as an environment variable — **never commit it**:

```bash
# In your deployment environment (Docker secrets, AWS Secrets Manager, Vault, etc.)
MY_STIGMEM_PASSPHRASE=hN2rq8...
```

#### 3 · Configure the node

```bash
STIGMEM_STORAGE_BACKEND=sqlite
STIGMEM_DB_PATH=/app/data/stigmem.db
STIGMEM_AT_REST_ENCRYPTION=on
STIGMEM_AT_REST_KEY_PASSPHRASE_ENV=MY_STIGMEM_PASSPHRASE
```

<div className="stigmem-keypoint">

**`STIGMEM_AT_REST_KEY_PASSPHRASE_ENV` is the *name* of the environment variable that holds the passphrase — not the passphrase itself.**

This indirection keeps the passphrase out of the Stigmem config
namespace.

</div>

#### 4 · First boot

On first start with a new database path, Stigmem creates an encrypted
database and runs migrations. Subsequent starts open the same
encrypted file with the same key.

```bash
stigmem-node
# → Stigmem node ready — db=/app/data/stigmem.db auth=False federation=disabled
```

If the passphrase env var is missing or the key source is
misconfigured, the node refuses to start with a clear error:

```
RuntimeError: STIGMEM_AT_REST_ENCRYPTION=on but no key source is configured. ...
```

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

The encryption key is applied to the **local replica file**. The
Turso cloud primary uses server-side encryption independently.

## Key source options

Stigmem supports two key sources. Exactly one must be set when
`STIGMEM_AT_REST_ENCRYPTION=on`; the node refuses to start if both
are empty or both are set.

<div className="stigmem-fields">

<div>
<dt>Option</dt>
<dt><span className="stigmem-fields__type">Env var</span></dt>
<dd>When to use</dd>
</div>

<div>
<dt>A · passphrase (Argon2id derivation)</dt>
<dt><span className="stigmem-fields__type"><code>STIGMEM_AT_REST_KEY_PASSPHRASE_ENV</code></span></dt>
<dd>Secrets manager stores a human-readable passphrase (e.g. a long random string from <code>openssl rand -base64 48</code>). Stretched into a 32-byte AES key using Argon2id (OWASP 2023 params: <code>t=3, m=64 MiB, p=4</code>). Requires <code>argon2-cffi</code>.</dd>
</div>

<div>
<dt>B · raw hex key via KMS URI</dt>
<dt><span className="stigmem-fields__type"><code>STIGMEM_AT_REST_KEY_KMS_URI=env://VAR</code></span></dt>
<dd>Your secrets manager vends a pre-derived 32-byte key (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault). Variable must contain exactly 64 hex characters (32 bytes). No KDF applied. Future releases will add <code>aws-kms://</code>, <code>gcp-kms://</code>, and Vault KMS URI schemes for envelope encryption.</dd>
</div>

</div>

```bash
# Generate a 32-byte hex key (Option B)
openssl rand -hex 32
# → a3f8c2...  (64 chars)
```

## Encrypting an existing (plaintext) database

Converting a live plaintext database to encrypted requires a one-time
migration using the SQLCipher CLI or the `sqlcipher3` Python REPL.

<div className="stigmem-keypoint">

**Stop the node first.**

</div>

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
Never delete the plaintext database until you have verified the
encrypted version boots and passes a basic query round-trip.
:::

## Key rotation runbook

**Goal:** replace the encryption key without service interruption
(requires brief maintenance window).

<ol className="stigmem-steps">
<li><strong>Stop the node</strong> to ensure no writes occur during the transition.</li>
<li><strong>Export the current database as plaintext</strong> (SQLCipher REPL). See command below.</li>
<li><strong>Re-encrypt with the new key.</strong> See command below.</li>
<li><strong>Update the secret</strong> in your secrets manager and redeploy with the new passphrase/key env var.</li>
<li><strong>Restart the node</strong> — it opens the re-encrypted database with the new key.</li>
</ol>

**Step 2 — export to plaintext:**

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

**Step 3 — re-encrypt with new key:**

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

## Running the conformance suite in encrypted mode

```bash
pip install 'stigmem-node[dev,encryption,sqlcipher]'
cd node
pytest --encrypt=on
```

`--encrypt=on` redirects all test fixtures to use encrypted SQLite
storage with a CI-only test passphrase. The full conformance suite
passes without modification.

<div className="stigmem-keypoint">

**Federation tests use direct database path fixtures that bypass encryption settings.**

Run <code>test_federation.py</code> and <code>test_4node_federation.py</code>
separately in plaintext mode.

</div>

## Security notes

<div className="stigmem-grid">

<div><h4>Key material is never logged</h4><p>Exception messages from the key-loading code deliberately omit passphrase and key values.</p></div>
<div><h4>Fixed KDF salt</h4><p>The Argon2id salt is a domain-separator constant. Security comes from passphrase entropy, not salt randomness. Appropriate for high-entropy operator secrets.</p></div>
<div><h4>Page-level encryption</h4><p>SQLCipher encrypts all pages including the schema. An attacker with file access cannot determine table names, record counts, or any data without the key.</p></div>
<div><h4>Snapshots are encrypted</h4><p><code>stigmem snapshot create</code> produces snapshots encrypted with the same key. Store snapshot files with the same access controls as the database.</p></div>
<div><h4>No key in config files</h4><p><code>STIGMEM_AT_REST_KEY_PASSPHRASE_ENV</code> stores the <em>name</em> of the env var, not the value. The passphrase never passes through Stigmem's configuration namespace.</p></div>

</div>
