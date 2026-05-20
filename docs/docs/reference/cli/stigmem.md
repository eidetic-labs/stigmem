---
title: "stigmem"
sidebar_label: "stigmem"
sidebar_position: 1
description: "CLI reference for the stigmem command — capability tokens, federation, snapshots, decay, instructions, audit, identity, and CID backfill."
audience: Operator
---

# stigmem CLI

<p className="stigmem-meta"><span>6 min read</span><span>Operator · Admin</span><span>Auto-generated</span></p>

<div className="stigmem-lead">

**What this page covers**

The management CLI: capability tokens, federation, snapshots, decay,
instructions, audit, identity, and CID backfill.

</div>

<div className="stigmem-keypoint">

**Auto-generated from `stigmem --help`.**

Regenerate with `make gen-cli-docs`.

</div>

## `stigmem`

```
usage: stigmem [-h] COMMAND ...

Stigmem reference node CLI

positional arguments:
  COMMAND
    capability   capability token management (Spec-06-Capability-Tokens)
    migrate      database migration utilities
    plugins      inspect installed plugins (PR 4-INF.2)
    federation   federation management (Spec-05-Federation-Trust)
    snapshot     backup/restore with signed manifests (Phase 8)
    decay        decay sweeper — expire stale facts (Phase 6)
    instruction  instruction manifest tools (Spec-X1-Lazy-Instruction-
                 Discovery)
    audit        discovery audit reports (Spec-X1-Lazy-Instruction-Discovery)
    identity     node identity management (Spec-10-Hardening)
    backfill-cids
                 compute and persist CIDs for facts that pre-date CID backfill
                 (Spec-21-Content-Addressed-IDs)
    auth         API key management (Spec-06-Capability-Tokens)

options:
  -h, --help     show this help message and exit
```

**Command index:**

<div className="stigmem-fields">

<div>
<dt>Command</dt>
<dt><span className="stigmem-fields__type">Spec</span></dt>
<dd>Purpose</dd>
</div>

<div>
<dt><code>capability</code></dt>
<dt><span className="stigmem-fields__type">Spec-06</span></dt>
<dd>Capability token management.</dd>
</div>

<div>
<dt><code>migrate</code></dt>
<dt><span className="stigmem-fields__type">Spec-01</span></dt>
<dd>Database migration utilities.</dd>
</div>

<div>
<dt><code>plugins</code></dt>
<dt><span className="stigmem-fields__type">PR 4-INF.2</span></dt>
<dd>Inspect installed plugins.</dd>
</div>

<div>
<dt><code>federation</code></dt>
<dt><span className="stigmem-fields__type">Spec-05</span></dt>
<dd>Federation management.</dd>
</div>

<div>
<dt><code>snapshot</code></dt>
<dt><span className="stigmem-fields__type">Phase 8</span></dt>
<dd>Backup/restore with signed manifests.</dd>
</div>

<div>
<dt><code>decay</code></dt>
<dt><span className="stigmem-fields__type">Phase 6 / Spec-X9</span></dt>
<dd>Decay sweeper — expire stale facts.</dd>
</div>

<div>
<dt><code>instruction</code></dt>
<dt><span className="stigmem-fields__type">Spec-X1</span></dt>
<dd>Instruction manifest tools.</dd>
</div>

<div>
<dt><code>audit</code></dt>
<dt><span className="stigmem-fields__type">Spec-X1</span></dt>
<dd>Discovery audit reports.</dd>
</div>

<div>
<dt><code>identity</code></dt>
<dt><span className="stigmem-fields__type">Spec-10</span></dt>
<dd>Node identity management.</dd>
</div>

<div>
<dt><code>backfill-cids</code></dt>
<dt><span className="stigmem-fields__type">Spec-21</span></dt>
<dd>Compute and persist CIDs for legacy facts.</dd>
</div>

<div>
<dt><code>auth</code></dt>
<dt><span className="stigmem-fields__type">Spec-06</span></dt>
<dd>API key management.</dd>
</div>

</div>

### `stigmem capability`

```
usage: stigmem capability [-h] SUBCOMMAND ...

positional arguments:
  SUBCOMMAND
    issue     issue a new capability token
    verify    verify a capability token
    revoke    revoke a capability token by token_id
```

#### `stigmem capability issue`

```
usage: stigmem capability issue [-h] [--node-url URL] [--api-key KEY] [--json]
                                --issuer URI --subject URI --verb VERB
                                --object OBJECT [--ttl-seconds N]

options:
  --issuer URI     issuer entity URI
  --subject URI    subject entity URI
  --verb VERB      permission verb (e.g. read, write)
  --object OBJECT  object URI the token grants access to
  --ttl-seconds N  token lifetime in seconds (max: 7776000 / 90 days)
```

#### `stigmem capability verify`

```
usage: stigmem capability verify [-h] [--node-url URL] [--api-key KEY]
                                 [--json]
                                 TOKEN_JSON

positional arguments:
  TOKEN_JSON      capability token JSON string; pass '-' to read from stdin
```

#### `stigmem capability revoke`

```
usage: stigmem capability revoke [-h] [--node-url URL] [--api-key KEY]
                                 [--json] [--reason REASON]
                                 TOKEN_ID

positional arguments:
  TOKEN_ID         ID of the token to revoke

options:
  --reason REASON  human-readable reason for revocation
```

### `stigmem migrate`

```
usage: stigmem migrate [-h] SUBCOMMAND ...

positional arguments:
  SUBCOMMAND
    normalize-entities
                      populate entity_aliases from non-canonical entity/source
                      URIs in facts (Spec-01-Fact-Model)
```

#### `stigmem migrate normalize-entities`

```
usage: stigmem migrate normalize-entities [-h] [--dry-run] [--db PATH]

options:
  --dry-run   print aliases without inserting
  --db PATH   path to stigmem.db (default: STIGMEM_DB_PATH env or settings default)
```

### `stigmem plugins`

```
usage: stigmem plugins [-h] SUBCOMMAND ...

positional arguments:
  SUBCOMMAND
    list      list installed plugins
    describe  describe one installed plugin
```

#### `stigmem plugins list`

```
usage: stigmem plugins list [-h] [--json]
```

#### `stigmem plugins describe`

```
usage: stigmem plugins describe [-h] [--json] NAME

positional arguments:
  NAME        plugin name
```

### `stigmem federation`

```
usage: stigmem federation [-h] SUBCOMMAND ...

positional arguments:
  SUBCOMMAND
    register-peer
                 register this node as a peer with a remote node
                 (Spec-05-Federation-Trust)
    cursor-export
                 export replication cursor positions to a JSON checkpoint file
    cursor-import
                 restore replication cursors from a checkpoint file after DB
                 loss
```

#### `stigmem federation register-peer`

```
usage: stigmem federation register-peer [-h] --remote-url URL
                                        [--local-url URL]
                                        [--scopes SCOPE[,SCOPE]]
                                        [--api-key KEY]

options:
  --remote-url URL      base URL of the remote node (e.g. http://node-b:8765)
  --local-url URL       base URL of this node as seen by the remote
  --scopes              comma-separated scopes to share (default: "company,public")
  --api-key KEY         API key for the remote node (required when remote auth_required=true)
```

#### `stigmem federation cursor-export`

```
usage: stigmem federation cursor-export [-h] [--out FILE] [--db PATH]

options:
  --out FILE  output file path (default: stdout, use "-" for stdout)
  --db PATH   path to stigmem.db (default: STIGMEM_DB_PATH env or settings default)
```

#### `stigmem federation cursor-import`

```
usage: stigmem federation cursor-import [-h] [--force] [--db PATH] FILE

positional arguments:
  FILE        path to checkpoint JSON produced by cursor-export

options:
  --force     overwrite cursors that are already set (default: skip existing non-null cursors)
  --db PATH   path to stigmem.db (default: STIGMEM_DB_PATH env or settings default)
```

### `stigmem snapshot`

```
usage: stigmem snapshot [-h] SUBCOMMAND ...

positional arguments:
  SUBCOMMAND
    create    create a signed, content-addressed snapshot tarball
    restore   verify signature + hashes and restore a snapshot tarball
```

#### `stigmem snapshot create`

```
usage: stigmem snapshot create [-h] [--out PATH] [--sign-with KEY_FILE]
                               [--db PATH]

options:
  --out PATH            output path for the .tar.gz (default: auto-named stigmem-snapshot-<ts>-<hash>.tar.gz)
  --sign-with KEY_FILE  path to a file containing a raw base64url Ed25519 private key (32 bytes)
  --db PATH             path to stigmem.db
```

#### `stigmem snapshot restore`

```
usage: stigmem snapshot restore [-h] --from PATH [--trusted-keys PATH]
                                [--force-unverified] [--db PATH]

options:
  --from PATH          path to the .tar.gz snapshot to restore
  --trusted-keys PATH  JSON file listing trusted base64url Ed25519 public keys
  --force-unverified   restore even if signature or hash verification fails (NOT recommended)
  --db PATH            destination database path
```

<div className="stigmem-keypoint">

**`--force-unverified` is always logged at `WARNING` level.**

Audit your logs after any forced restore.

</div>

### `stigmem decay`

```
usage: stigmem decay [-h] SUBCOMMAND ...

positional arguments:
  SUBCOMMAND
    sweep     mark non-expiring or low-confidence facts as expired
```

#### `stigmem decay sweep`

```
usage: stigmem decay sweep [-h] [--ttl-seconds N] [--min-confidence F]
                           [--scope SCOPE] [--dry-run] [--db PATH]

options:
  --ttl-seconds N     expire non-expiring facts older than N seconds (0 = expire all)
  --min-confidence F  expire active facts with confidence below F (0.0–1.0)
  --scope SCOPE       restrict sweep to one scope (local/team/company/public)
  --dry-run           print what would be decayed without writing
  --db PATH           path to stigmem.db
```

### `stigmem instruction`

```
usage: stigmem instruction [-h] SUBCOMMAND ...

positional arguments:
  SUBCOMMAND
    manifest  manage instruction manifests
    migrate   migrate markdown instruction files to stigmem facts + publish manifest
```

#### `stigmem instruction manifest`

```
usage: stigmem instruction manifest [-h] SUBCOMMAND ...

positional arguments:
  SUBCOMMAND
    generate  generate a manifest JSON from a directory of markdown instruction files
```

#### `stigmem instruction manifest generate`

```
usage: stigmem instruction manifest generate [-h] --agent-id AGENT_ID
                                             [--deployment DEPLOYMENT]
                                             [--version VERSION] [--out FILE]
                                             PATH

positional arguments:
  PATH                  directory containing markdown instruction files

options:
  --agent-id AGENT_ID   agent UUID to embed in generated fact_uri values
  --deployment          deployment namespace for instruction: URIs (default: default)
  --version VERSION     manifest version string (default: v1)
  --out FILE            write JSON to FILE instead of stdout
```

#### `stigmem instruction migrate`

```
usage: stigmem instruction migrate [-h] (--role ROLE | --skill SKILL)
                                   --agent-id AGENT_ID
                                   [--deployment DEPLOYMENT]
                                   [--version VERSION] [--node-url URL]
                                   [--api-key KEY] [--db PATH] [--dry-run]
                                   [--yes]
                                   PATH

positional arguments:
  PATH                  markdown file or directory to migrate

options:
  --role ROLE / --skill SKILL  scope selector (mutually exclusive)
  --agent-id AGENT_ID          agent UUID owning the manifest
  --deployment                 deployment namespace (default: default)
  --version VERSION            fact version string (default: v1)
  --node-url URL               stigmem node base URL (default: http://127.0.0.1:8000)
  --api-key KEY                API key (or set STIGMEM_API_KEY env var)
  --db PATH                    path to stigmem.db for local idempotency checks
  --dry-run                    show diff without writing any facts or manifest
  --yes, -y                    skip confirmation prompt
```

### `stigmem audit`

```
usage: stigmem audit [-h] SUBCOMMAND ...

positional arguments:
  SUBCOMMAND
    discovery
              print discovery audit metrics: Recall@k, Hit@k, miss rate
```

#### `stigmem audit discovery`

```
usage: stigmem audit discovery [-h] --agent AGENT_ID_OR_ROLE [--since DATE]
                               [--db PATH] [--json]

options:
  --agent AGENT_ID_OR_ROLE  agent ID (UUID) or role substring to filter
  --since DATE              ISO 8601 date/datetime to start from (default: 7 days ago)
  --db PATH                 path to stigmem.db
  --json                    output as JSON
```

### `stigmem identity`

```
usage: stigmem identity [-h] SUBCOMMAND ...

positional arguments:
  SUBCOMMAND
    rotate-key
              rotate the node or issuer Ed25519 key with a dual-trust window
              (Spec-10-Hardening)
```

#### `stigmem identity rotate-key`

```
usage: stigmem identity rotate-key [-h] --kind KIND [--dry-run]
                                   [--dual-trust-days DAYS] [--db PATH]

options:
  --kind KIND             key type to rotate: node (federation identity) or
                          issuer (capability token signing)
  --dry-run               generate artefacts and print new key without writing
                          to TL or DB
  --dual-trust-days DAYS  days the retiring key stays in accept_set (default: 90; must be ≥ 90)
  --db PATH               path to stigmem.db
```

<div className="stigmem-keypoint">

**`--dual-trust-days` must be ≥ 90.**

The CLI enforces this minimum because 90 days is the maximum
capability token TTL per `Spec-06-Capability-Tokens`.

</div>

### `stigmem backfill-cids`

```
usage: stigmem backfill-cids [-h] [--db PATH] [--batch-size N] [--quiet]

options:
  --db PATH       path to stigmem.db (default: STIGMEM_DB_PATH env or settings default)
  --batch-size N  facts to process per transaction (default: 500)
  --quiet         suppress progress output
```

### `stigmem auth`

```
usage: stigmem auth [-h] SUBCOMMAND ...

positional arguments:
  SUBCOMMAND
    bootstrap-key
                 register a caller-provided admin API key on a fresh install
                 (refuses if api_keys is non-empty; system never generates the
                 key)
```

#### `stigmem auth bootstrap-key`

```
usage: stigmem auth bootstrap-key [-h] [--key VALUE] [--entity-uri URI]
                                  [--permissions LIST]

options:
  --key VALUE         raw API key value to register. Generate externally
                      (e.g., `openssl rand -hex 32`). Alternative:
                      STIGMEM_BOOTSTRAP_KEY env var.
  --entity-uri URI    entity URI to associate with the bootstrap key (default: agent:admin)
  --permissions LIST  comma-separated permissions for the bootstrap key (default: admin,write,read)
```

<div className="stigmem-keypoint">

**`bootstrap-key` refuses if `api_keys` is non-empty, and the system never generates the key.**

The caller MUST provide the value (e.g. via `openssl rand -hex 32`)
so it can be stored in their secrets manager before registration.

</div>
