#!/usr/bin/env bash
# Runs pytest in every project (no Ollama needed).
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/Scripts/python.exe"; [ -x "$PY" ] || PY="$ROOT/.venv/bin/python"; [ -x "$PY" ] || PY=python
FAILED=()
for p in "$ROOT"/[0-9][0-9]-*/; do
  echo; echo "===== $(basename "$p")"
  (cd "$p" && "$PY" -m pytest -q -W ignore) || FAILED+=("$(basename "$p")")
done
[ ${#FAILED[@]} -eq 0 ] && echo "All projects passed." || { echo "FAILED: ${FAILED[*]}"; exit 1; }
