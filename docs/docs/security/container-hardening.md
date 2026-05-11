---
title: Container Hardening
sidebar_label: Container Hardening
audience: Operator
---

# Container hardening

Stigmem's reference node image ships with a hardened container posture as of **pre-reset hardening** (spec §22.6). This page describes the controls baked into the image and how to verify them.

## What's included

| Control | Implementation |
|---|---|
| Non-root runtime | UID/GID 65532 baked into `node/Dockerfile` |
| Minimal runtime image | Multi-stage build; only Python 3.11 slim + installed packages reach the final layer |
| No build tools at runtime | `uv`, compiler, and pip are absent from the shipped image |
| Read-only root filesystem | Enforced by Compose/Helm recipes; `/tmp` and `/run` are `tmpfs` |
| All capabilities dropped | `CAP_DROP ALL` in Compose/Helm; no capabilities re-added |
| `no-new-privileges` | Set in all deploy recipes |
| seccomp denylist | `deploy/seccomp/stigmem-node.json` — extends Docker default by blocking additional container-escape syscalls (`ptrace`, `bpf`, `kexec_load`, `mount`, `unshare`, etc.) |
| SBOM | `syft`-generated SPDX JSON attached to every published image as an OCI referrer |
| Image signing | `cosign` keyless (Sigstore) — signature recorded in the Rekor transparency log |

## Image reference

```
ghcr.io/eidetic-labs/stigmem-node:<tag>
```

The hardened image is published for `linux/amd64` and `linux/arm64`.

## Verifying the image signature

```bash
# Requires cosign ≥ 2.x
cosign verify \
  --certificate-identity-regexp "https://github.com/eidetic-labs/stigmem/.github/workflows/publish.yml" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  ghcr.io/eidetic-labs/stigmem-node:<tag>
```

A successful verification prints the signing certificate and Rekor log entry.

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

The profile is shipped at `deploy/seccomp/stigmem-node.json`. The deploy Compose recipe loads it automatically:

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
  ghcr.io/eidetic-labs/stigmem-node:latest
```

:::note Kubernetes / Helm and Fly.io
Helm chart hardening defaults and Fly.io micro-VM guidance lived alongside the v1.0 deploy recipes. Those recipes are deferred to [`experimental/deploy-helm/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/deploy-helm) and [`experimental/deploy-fly/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/deploy-fly) in v0.9.0a1 and are unsupported until they pass the [ADR-008 reintroduction gates](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/008-experimental-gates.md). The Docker and Docker Compose hardening guidance above is the supported v0.9.0a1 surface.
:::

## Build reproducibility

The Dockerfile pins the `uv` version using Docker's `--from` copy syntax:

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
```

For fully reproducible builds, pin the digest:

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:0.6.14@sha256:<digest> /uv /usr/local/bin/uv
```

And pin the base image tag in `node/Dockerfile` to a specific digest as well.

## What the seccomp profile blocks

`deploy/seccomp/stigmem-node.json` uses a **denylist** strategy (default ALLOW) and explicitly blocks:

- **Process injection**: `ptrace`, `process_vm_readv`, `process_vm_writev`
- **Kernel module loading**: `init_module`, `finit_module`, `delete_module`
- **kexec**: `kexec_load`, `kexec_file_load`
- **Namespace manipulation** (container escape vectors): `pivot_root`, `mount`, `umount2`, `unshare`, `setns`, `open_tree`, `move_mount`, `fsopen`, `fsconfig`, `fsmount`, `fspick`
- **eBPF**: `bpf`, `perf_event_open`
- **Kernel time adjustment**: `adjtimex`, `clock_adjtime`, `settimeofday`, `clock_settime`
- **Privileged I/O**: `iopl`, `ioperm`
- **Key ring**: `add_key`, `keyctl`, `request_key`
- **Misc dangerous**: `reboot`, `syslog`, `chroot`, `acct`, `swapon`, `swapoff`, `userfaultfd`, `seccomp`, `quotactl`
- **io_uring** (CVE-2022-29582, CVE-2023-2598, CVE-2022-2586): `io_uring_setup`, `io_uring_enter`, `io_uring_register` — blocked because Python/uvicorn does not use io_uring and the interface has accumulated significant kernel exploit history
- **Shocker-class container escape** (host inode access via bind-mount): `open_by_handle_at`, `name_to_handle_at`
- **Cross-process information disclosure**: `kcmp`

The `clone`/`clone3` syscalls are **not** denied because Python's threading model requires them. Namespace-related misuse is blocked by the missing `CAP_SYS_ADMIN` capability, providing defense-in-depth.

## Known limitations

- **Per-distro AppArmor profiles** are out of scope for pre-reset hardening; community contributions welcome.
- **Multi-arch matrix** covers `linux/amd64` and `linux/arm64` only.
- The `seccompProfile.type: RuntimeDefault` Helm default does not apply the stigmem-specific profile; operators who want the full denylist must load the JSON file as a `Localhost` profile.
