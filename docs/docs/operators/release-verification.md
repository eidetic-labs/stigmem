---
title: Release Verification
sidebar_label: Release Verification
description: Verify Stigmem release signatures, SBOMs, provenance, and Rekor transparency-log evidence before deployment.
audience: Operator
---

# Release Verification

<p className="stigmem-meta"><span>4 min read</span><span>Release engineer · Operator</span><span>Supply-chain gate</span></p>

<div className="stigmem-lead">

**What this page covers**

Verify a tagged Stigmem release before deploying. The release
workflow publishes package-manager provenance for npm and PyPI, and
attaches supply-chain evidence to the GHCR node image.

</div>

**The release workflow publishes:**

<div className="stigmem-grid">

<div><h4>Cosign signature</h4><p>Keyless Sigstore/cosign image signature.</p></div>
<div><h4>SPDX SBOM</h4><p>JSON SBOM as an OCI referrer.</p></div>
<div><h4>SBOM attestation</h4><p>SPDX JSON SBOM attestation.</p></div>
<div><h4>BuildKit provenance</h4><p>For the container build.</p></div>
<div><h4>GPG signatures</h4><p>Detached signatures attached to the GitHub release.</p></div>
<div><h4>Rekor entries</h4><p>Transparency-log entries created by the keyless signing flow.</p></div>

</div>

## Verify the GHCR image

Install `cosign` and a registry inspection tool such as `crane`, then verify by digest rather than mutable tag.

```bash
IMAGE=ghcr.io/eidetic-labs/stigmem-node
VERSION=0.9.0a2
DIGEST="$(crane digest "$IMAGE:$VERSION")"
REF="$IMAGE@$DIGEST"
```

Verify that the image signature was issued by GitHub Actions for this repository and release workflow:

```bash
cosign verify \
  --certificate-identity-regexp 'https://github.com/eidetic-labs/stigmem/.github/workflows/publish.yml@refs/tags/v.*' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  "$REF"
```

Verify the SBOM attestation:

```bash
cosign verify-attestation \
  --type spdxjson \
  --certificate-identity-regexp 'https://github.com/eidetic-labs/stigmem/.github/workflows/publish.yml@refs/tags/v.*' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  "$REF"
```

Verify the BuildKit provenance attestation:

```bash
cosign verify-attestation \
  --type slsaprovenance \
  --certificate-identity-regexp 'https://github.com/eidetic-labs/stigmem/.github/workflows/publish.yml@refs/tags/v.*' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  "$REF"
```

Retrieve the attached SBOM if you need to archive it with a change ticket or scan it with your own tooling:

```bash
cosign download sbom "$REF" > stigmem-node.spdx.json
```

## Check Rekor evidence

<div className="stigmem-keypoint">

**Keep the cosign output with your release approval record.**

It includes the certificate and transparency-log metadata needed to
trace the release event. If public Rekor is temporarily unavailable,
follow [R-REKOR-UNAVAILABLE](./runbooks/r-rekor-unavailable). **Do not
deploy a new production release until signature and attestation
verification succeeds.**

</div>

## Verify package provenance

For npm, install the exact package version from the GitHub release notes and verify the package provenance in npm points back to `eidetic-labs/stigmem`, `publish.yml`, and the release tag.

```bash
npm view @eidetic-labs/stigmem-ts@0.9.0-alpha.2 dist.integrity dist.tarball
```

For PyPI packages, use the exact versions from the release notes and verify that the PyPI project publishing metadata shows the GitHub Trusted Publisher for `eidetic-labs/stigmem` and `.github/workflows/publish.yml`.

```bash
python -m pip download --no-deps --dest /tmp/stigmem-release stigmem-py==0.9.0a2
python -m pip hash /tmp/stigmem-release/*
```

Store the resulting hashes in your own deployment record if you require environment-local package pinning.

## Verify GPG release signatures

The GitHub release may attach detached ASCII-armored GPG signatures for release
artifacts, plus `stigmem-release-signing-key.asc`. These signatures are created
and uploaded manually by the release maintainer after publication.

Import the release public key, download the artifact and matching `.asc`
signature, then verify:

```bash
gpg --import stigmem-release-signing-key.asc
gpg --verify stigmem-node-sbom.spdx.json.asc stigmem-node-sbom.spdx.json
gpg --verify stigmem-node-image-digest.txt.asc stigmem-node-image-digest.txt
gpg --verify <artifact>.asc <artifact>
```

Treat a failed GPG verification as a release-blocking integrity failure. Do not
mirror or deploy an artifact whose detached signature does not verify.

## Reproducibility expectations

<div className="stigmem-keypoint">

**The signed container provenance is the supported reproducibility evidence for the future stable-readiness line.**

It identifies the source repository, release tag, commit, workflow,
Dockerfile, and builder inputs used for the released image.

Arbitrary later rebuilds may not produce the same byte-for-byte image digest if upstream base image digests, package indexes, or toolchains have moved. Treat a digest mismatch from a later local rebuild as an investigation signal, then compare the signed provenance and SBOM before deployment.

</div>
