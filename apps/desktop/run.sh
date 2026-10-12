#!/usr/bin/env bash
# ==============================================================================
# ZETTA AI EMPLOYEE — DESKTOP LAUNCHER
# Starts the ZETTA FastAPI Bridge and opens the Desktop UI in standalone window mode.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${ROOT_DIR}"

echo "=================================================================="
echo "  ZETTA AI EMPLOYEE — DESKTOP UI OPERATING CONSOLE"
echo "=================================================================="
echo "Starting backend API gateway and static UI host..."

python3 core/zetta/cli.py ui "$@"
