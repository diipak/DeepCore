#!/bin/bash
set -eo pipefail

# Resolve script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Source environment variables if .env exists
if [ -f "$PROJECT_ROOT/.env" ]; then
  set -a
  source "$PROJECT_ROOT/.env"
  set +a
fi

LOG_DIR="${HOME}/.deepcore2/logs"
mkdir -p "$LOG_DIR" 2>/dev/null || true

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🎬 Starting DeepCore automated YouTube playlist sync..."

# Execute sync using project virtual environment
"$PROJECT_ROOT/.venv/bin/python" -m deepcore2.cli sync youtube

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Automated YouTube playlist sync completed."
