#!/usr/bin/env bash
# Monthly docs re-ingestion for Wisey
# Logs to ~/wisey-docs-ingest.log

set -euo pipefail

cd /Users/mattijsnaus/code/wisey
export PATH="/opt/homebrew/bin:/opt/homebrew/opt/postgresql@17/bin:$PATH"

echo "=== Docs ingest started: $(date) ==="
uv run python -m wisey.ingest docs --fresh
echo "=== Docs ingest finished: $(date) ==="
