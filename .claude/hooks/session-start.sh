#!/bin/bash
# SessionStart hook — installs backend (pip) and frontend (npm) dependencies so
# that tests, type-checks and the verification commands work in a fresh session.
#
# Runs synchronously: the session waits until deps are ready, which avoids the
# race where the agent tries to run pytest/vue-tsc before install finishes.
# Only meaningful in the remote (web) environment; skips locally.
set -euo pipefail

# Only run in Claude Code on the web; local machines manage their own env.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

echo "[session-start] installing backend deps…"
if command -v pip >/dev/null 2>&1; then
  pip install -q -r "$ROOT/backend/requirements.txt" || \
    echo "[session-start] WARN: some backend deps failed to install"
fi

echo "[session-start] installing frontend deps…"
if command -v npm >/dev/null 2>&1; then
  # npm install (not ci) so the cached container reuses node_modules across runs
  (cd "$ROOT/frontend" && npm install --no-audit --no-fund --silent) || \
    echo "[session-start] WARN: frontend deps failed to install"
fi

echo "[session-start] done."
