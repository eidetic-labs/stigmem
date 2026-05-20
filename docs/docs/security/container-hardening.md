---
title: Container Hardening
sidebar_label: Container Hardening
audience: Operator
---

# Container hardening

<p className="stigmem-meta"><span>3 min read</span><span>Operator</span><span>Spec-10-Hardening</span></p>

<div className="stigmem-lead">

**What this page is**

Stigmem's reference node image ships with a hardened container posture
as of pre-reset hardening (Spec-10-Hardening). This page describes
the controls baked into the image and how to verify them.

</div>

## What's included

<div className="stigmem-fields">

<div>
<dt>Control</dt>
<dt><span className="stigmem-fields__type">Implementation</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Non-root runtime</dt>
<dt><span className="stigmem-fields__type">UID/GID 65532</span></dt>
<dd>Baked into <code>node/Dockerfile</code>.</dd>
</div>

<div>
<dt>Minimal runtime image</dt>
<dt><span className="stigmem-fields__type">multi-stage</span></dt>
<dd>Only Python 3.11 slim + installed packages reach the final layer.</dd>
</div>

<div>
<dt>No build tools at runtime</dt>
<dt><span className="stigmem-fields__type">stripped</span></dt>
<dd><code>uv</code>, compiler, and pip are absent from the shipped image.</dd>
</div>

<div>
<dt>Read-only root filesystem</dt>
<dt><span className="stigmem-fields__type">enforced via Compose/Helm</span></dt>
<dd><code>/tmp</code> and <code>/run</code> are <code>tmpfs</code>.</dd>
</div>

<div>
<dt>All capabilities dropped</dt>
<dt><span className="stigmem-fields__type"><code>CAP_DROP ALL</code></span></dt>
<dd>No capabilities re-added in Compose/Helm.</dd>
</div>

<div>
<dt><code>no-new-privileges</code></dt>
<dt><span className="stigmem-fields__type">set in all recipes</span></dt>
<dd>Universal.</dd>
</div>

<div>
<dt>seccomp denylist</dt>
<dt><span className="stigmem-fields__type"><code>deploy/seccomp/stigmem-node.json</code></span></dt>
<dd>Extends Docker default by blocking additional container-escape syscalls.</dd>
</div>

<div>
<dt>SBOM</dt>
<dt><span className="stigmem-fields__type"><code>syft</code>-generated SPDX JSON</span></dt>
<dd>Attached to every published image as an OCI referrer.</dd>
</div>

<div>
<dt>Image signing</dt>
<dt><span className="stigmem-fields__type"><code>cosign</code> keyless (Sigstore)</span></dt>
<dd>Signature recorded in the Rekor transparency log.</dd>
</div>

</div>

## Image reference

```
ghcr.io/eidetic-labs/stigmem-node:<tag>
```

The hardened image is published for `linux/amd64` and `linux/arm64`.

:::tip For hardened production, pin to a digest
The `<tag>` placeholder above stands in for the tag you choose. For
supply-chain-conscious deployments use `@sha256:<digest>` instead — a
digest pin is tamper-evident and immune to tag reassignment. See the
[tag-selection guide](../operators/deployment/install#image-tags) for
the full breakdown.
:::

## Verifying the image signature

```bash
# Requires cosign ≥ 2.x
cosign verify \
  --certificate-identity-regexp "https://github.com/eidetic-labs/stigmem/.github/workflows/publish.yml" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  ghcr.io/eidetic-labs/stigmem-node:<tag>
```

A successful verification prints the signing certificate and Rekor log
entry.

## Verifying the SBOM

```bash
# Download the SBOM attached to a specific digest
cosign download sbom ghcr.io/eidetic-labs/stigmem-node@<digest> \
  | python3 -m json.tool | head -40

# Or pull it with oras (OCI referrers API)
oras discover --platform linux/amd64 \
  ghcr.io/eidetic-labs/stigmem-node:<tag>
```

## Running with the seccomp profile

### Docker / Compose

The profile is shipped at `deploy/seccomp/stigmem-node.json`. The
deploy Compose recipe loads it automatically:

```bash
docker compose -f deploy/compose/docker-compose.yml up -d
```

For a manual `docker run`:

```bash
docker run -d \
  --user 65532:65532 \
  --read-only \
  --tmpfs /tmp:mode=1777,size=64m \
  --tmpfs /run:mode=755,size=16m \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --security-opt seccomp=deploy/seccomp/stigmem-node.json \
  -v stigmem-data:/data \
  -e STIGMEM_DB_PATH=/data/stigmem.db \
  -p 8765:8765 \
  ghcr.io/eidetic-labs/stigmem-node:0.9.0a1
```

For audit-traceable production, replace `:0.9.0a1` with
`@sha256:<digest>` — see the
[tag-selection guide](../operators/deployment/install#image-tags).

:::note Kubernetes / Helm and Fly.io
Helm chart hardening defaults and Fly.io micro-VM guidance lived
alongside the v1.0 deploy recipes. Those recipes are deferred to
[`experimental/deploy-helm/`](https://github.com/eidetic-labs/stigmem/tree/main/experimental/deploy-helm)
and
[`experimental/deploy-fly/`](https://github.com/eidetic-labs/stigmem/tree/main/experimental/deploy-fly)
in v0.9.0a1 and are unsupported until they pass the
[ADR-008 reintroduction gates](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/008-experimental-gates.md).
The Docker and Docker Compose hardening guidance above is the
supported v0.9.0a1 surface.
:::

## Build reproducibility

The Dockerfile pins the `uv` version using Docker's `--from` copy
syntax:

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
```

For fully reproducible builds, pin the digest:

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:0.6.14@sha256:<digest> /uv /usr/local/bin/uv
```

And pin the base image tag in `node/Dockerfile` to a specific digest
as well.

## What the seccomp profile blocks

`deploy/seccomp/stigmem-node.json` uses a **denylist** strategy
(default ALLOW) and explicitly blocks the following syscall classes.

<div className="stigmem-grid">

<div><h4>Process injection</h4><p><code>ptrace</code>, <code>process_vm_readv</code>, <code>process_vm_writev</code>.</p></div>
<div><h4>Kernel module loading</h4><p><code>init_module</code>, <code>finit_module</code>, <code>delete_module</code>.</p></div>
<div><h4>kexec</h4><p><code>kexec_load</code>, <code>kexec_file_load</code>.</p></div>
<div><h4>Namespace manipulation</h4><p>Container escape vectors: <code>pivot_root</code>, <code>mount</code>, <code>umount2</code>, <code>unshare</code>, <code>setns</code>, <code>open_tree</code>, <code>move_mount</code>, <code>fsopen</code>, <code>fsconfig</code>, <code>fsmount</code>, <code>fspick</code>.</p></div>
<div><h4>eBPF</h4><p><code>bpf</code>, <code>perf_event_open</code>.</p></div>
<div><h4>Kernel time adjustment</h4><p><code>adjtimex</code>, <code>clock_adjtime</code>, <code>settimeofday</code>, <code>clock_settime</code>.</p></div>
<div><h4>Privileged I/O</h4><p><code>iopl</code>, <code>ioperm</code>.</p></div>
<div><h4>Key ring</h4><p><code>add_key</code>, <code>keyctl</code>, <code>request_key</code>.</p></div>
<div><h4>Misc dangerous</h4><p><code>reboot</code>, <code>syslog</code>, <code>chroot</code>, <code>acct</code>, <code>swapon</code>, <code>swapoff</code>, <code>userfaultfd</code>, <code>seccomp</code>, <code>quotactl</code>.</p></div>
<div><h4>io_uring</h4><p>CVE-2022-29582, CVE-2023-2598, CVE-2022-2586: <code>io_uring_setup</code>, <code>io_uring_enter</code>, <code>io_uring_register</code> — blocked because Python/uvicorn does not use io_uring and the interface has accumulated significant kernel exploit history.</p></div>
<div><h4>Shocker-class escape</h4><p>Host inode access via bind-mount: <code>open_by_handle_at</code>, <code>name_to_handle_at</code>.</p></div>
<div><h4>Cross-process disclosure</h4><p><code>kcmp</code>.</p></div>

</div>

<div className="stigmem-keypoint">

**The `clone`/`clone3` syscalls are NOT denied.**

Python's threading model requires them. Namespace-related misuse is
blocked by the missing <code>CAP_SYS_ADMIN</code> capability,
providing defense-in-depth.

</div>

## Known limitations

<div className="stigmem-grid">

<div><h4>Per-distro AppArmor profiles</h4><p>Out of scope for pre-reset hardening; community contributions welcome.</p></div>
<div><h4>Multi-arch matrix</h4><p>Covers <code>linux/amd64</code> and <code>linux/arm64</code> only.</p></div>
<div><h4>Helm <code>RuntimeDefault</code></h4><p><code>seccompProfile.type: RuntimeDefault</code> Helm default does not apply the stigmem-specific profile; operators who want the full denylist must load the JSON file as a <code>Localhost</code> profile.</p></div>

</div>
