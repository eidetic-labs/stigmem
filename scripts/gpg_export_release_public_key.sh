#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <output.asc>" >&2
  exit 2
fi

if [ -z "${RELEASE_GPG_PRIVATE_KEY:-}" ]; then
  echo "::error::RELEASE_GPG_PRIVATE_KEY is required to export the release public key."
  exit 1
fi

output="$1"
GNUPGHOME="${GNUPGHOME:-${RUNNER_TEMP:-/tmp}/stigmem-release-gnupg}"
export GNUPGHOME
mkdir -p "$GNUPGHOME"
chmod 700 "$GNUPGHOME"
gpgconf --launch gpg-agent 2>/dev/null || true

printf '%s\n' "$RELEASE_GPG_PRIVATE_KEY" | gpg --batch --import

if [ -n "${RELEASE_GPG_KEY_FINGERPRINT:-}" ]; then
  gpg --batch --armor --export "$RELEASE_GPG_KEY_FINGERPRINT" > "$output"
else
  gpg --batch --armor --export > "$output"
fi

if [ ! -s "$output" ]; then
  echo "::error::No release public key was exported."
  exit 1
fi

echo "Exported release public key to $output"
