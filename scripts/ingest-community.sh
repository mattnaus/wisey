#!/usr/bin/env bash
# Weekly community re-ingestion for Wisey
# Logs to ~/wisey-community-ingest.log

set -euo pipefail

cd /Users/mattijsnaus/code/wisey
export PATH="/opt/homebrew/bin:/opt/homebrew/opt/postgresql@17/bin:$PATH"

echo "=== Community ingest started: $(date) ==="
uv run python -m wisey.ingest community --fresh
echo "=== Community ingest finished: $(date) ==="
