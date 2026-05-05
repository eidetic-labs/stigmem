#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PNPM_SHIM_DIR=""

python_adapter_tests=(
  adapters/cognee/tests
  adapters/gemini/tests
  adapters/letta/tests
  adapters/obsidian/tests
  adapters/openai-tools/tests
  adapters/openclaw/tests
  adapters/zep/tests
)

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

ensure_pnpm() {
  if command -v pnpm >/dev/null 2>&1; then
    return
  fi
  need_cmd corepack
  if [[ -z "${PNPM_SHIM_DIR}" ]]; then
    PNPM_SHIM_DIR="$(mktemp -d)"
    cat >"${PNPM_SHIM_DIR}/pnpm" <<'EOF'
#!/usr/bin/env bash
exec corepack pnpm "$@"
EOF
    chmod +x "${PNPM_SHIM_DIR}/pnpm"
    export PATH="${PNPM_SHIM_DIR}:${PATH}"
  fi
}

pnpm_cmd() {
  ensure_pnpm
  pnpm "$@"
}

run_python() {
  need_cmd uv
  cd "$ROOT_DIR"
  if [[ "${CHECK_SKIP_PYTHON_SYNC:-0}" != "1" ]]; then
    uv sync --all-packages
  fi

  uv run python scripts/check_ruff_baseline.py
  uv run python scripts/check_mypy_baseline.py
  uv run pytest node/tests/ sdks/stigmem-py/tests/ -q --tb=short

  for test_dir in "${python_adapter_tests[@]}"; do
    uv run pytest "$test_dir" -q --tb=short
  done

  uv run pip-audit --progress-spinner off
  uv run bandit -r node/src/ sdks/stigmem-py/src/ -c pyproject.toml -q
  uv run python scripts/check_constant_time.py node/src/ sdks/stigmem-py/src/
}

run_node() {
  need_cmd node
  cd "$ROOT_DIR"
  if [[ "${CHECK_SKIP_NODE_INSTALL:-0}" != "1" ]]; then
    pnpm_cmd install --frozen-lockfile
  fi

  pnpm_cmd build
  pnpm_cmd type-check
  pnpm_cmd --filter stigmem-ts test
  pnpm_cmd audit --audit-level=moderate

  (
    cd "$ROOT_DIR/sdks/stigmem-ts"
    pnpm_cmd exec esbuild src/index.ts \
      --bundle \
      --platform=node \
      --format=cjs \
      --outfile=dist/smoke.cjs \
      --log-level=warning
    node -e "const s = require('./dist/smoke.cjs'); console.log('esbuild smoke OK — exports:', Object.keys(s).join(', '))"
  )
}

run_go() {
  need_cmd go
  cd "$ROOT_DIR/sdks/stigmem-go"
  go test ./...
}

run_docs() {
  need_cmd npm
  cd "$ROOT_DIR/docs"
  if [[ "${CHECK_SKIP_DOCS_INSTALL:-0}" != "1" ]]; then
    npm ci
  fi
  npm run build
}

run_obsidian() {
  need_cmd npm
  cd "$ROOT_DIR/adapters/obsidian-plugin"
  if [[ "${CHECK_SKIP_OBSIDIAN_INSTALL:-0}" != "1" ]]; then
    npm ci
  fi
  npm run build
}

usage() {
  cat <<'EOF'
Usage: scripts/check.sh [all|python|node|contract|go|docs|obsidian]

Runs the fast repository gates locally. "all" is the PR-equivalent bundle.
EOF
}

run_contract() {
  need_cmd uv
  need_cmd node
  cd "$ROOT_DIR"

  if [[ "${CHECK_SKIP_PYTHON_SYNC:-0}" != "1" ]]; then
    uv sync --all-packages
  fi

  uv run python scripts/export_openapi.py --check

  if [[ "${CHECK_SKIP_NODE_INSTALL:-0}" != "1" ]]; then
    pnpm_cmd install --frozen-lockfile
  fi

  local generated_tmp
  generated_tmp="$(mktemp)"
  (
    cd "$ROOT_DIR/sdks/stigmem-ts"
    pnpm_cmd exec openapi-typescript ../../docs/openapi/stigmem.json -o "$generated_tmp" --root-types
  )
  diff -u "$ROOT_DIR/sdks/stigmem-ts/src/generated.ts" "$generated_tmp"
  rm -f "$generated_tmp"
}

case "${1:-all}" in
  all)
    run_python
    run_node
    run_contract
    run_go
    run_docs
    run_obsidian
    ;;
  python)
    run_python
    ;;
  node)
    run_node
    ;;
  contract)
    run_contract
    ;;
  go)
    run_go
    ;;
  docs)
    run_docs
    ;;
  obsidian)
    run_obsidian
    ;;
  *)
    usage
    exit 1
    ;;
esac
