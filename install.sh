#!/usr/bin/env bash
set -euo pipefail
RESEARCH_REPO="${EQUITY_DATA_REPO:-$(cd "$(dirname "$0")/.." && pwd)/stock_research}"
if [[ ! -f "$RESEARCH_REPO/scripts/manage_skills.py" ]]; then
  echo "Set EQUITY_DATA_REPO to the maintained stock_research checkout." >&2
  exit 1
fi
exec python3 "$RESEARCH_REPO/scripts/manage_skills.py" "$@"
