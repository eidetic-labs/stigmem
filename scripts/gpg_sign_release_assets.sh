#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: $0 <file> [<file> ...]" >&2
  exit 2
fi

if [ -z "${RELEASE_GPG_PRIVATE_KEY:-}" ]; then
  echo "::error::RELEASE_GPG_PRIVATE_KEY is required for release asset signing."
  exit 1
fi

GNUPGHOME="${GNUPGHOME:-${RUNNER_TEMP:-/tmp}/stigmem-release-gnupg}"
export GNUPGHOME
mkdir -p "$GNUPGHOME"
chmod 700 "$GNUPGHOME"
gpgconf --launch gpg-agent 2>/dev/null || true

printf '%s\n' "$RELEASE_GPG_PRIVATE_KEY" | gpg --batch --import

if [ -n "${RELEASE_GPG_KEY_FINGERPRINT:-}" ]; then
  if ! gpg --batch --list-secret-keys --with-colons "$RELEASE_GPG_KEY_FINGERPRINT" \
    | grep -q '^sec:'; then
    echo "::error::Imported release GPG key does not match RELEASE_GPG_KEY_FINGERPRINT."
    exit 1
  fi
fi

sign_args=(--batch --yes --armor --detach-sign)
if [ -n "${RELEASE_GPG_PASSPHRASE:-}" ]; then
  sign_args+=(--pinentry-mode loopback --passphrase "$RELEASE_GPG_PASSPHRASE")
fi

for file in "$@"; do
  if [ ! -f "$file" ]; then
    echo "::error::Release asset not found: $file"
    exit 1
  fi
  gpg "${sign_args[@]}" "$file"
  echo "Signed $file -> $file.asc"
done
