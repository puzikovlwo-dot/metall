#!/usr/bin/env bash
# regen_data.sh — Regenerate sales/plans/clients CSVs.
#
# Usage:  bash .claude/skills/metall-dashboard/scripts/regen_data.sh [--yes]
#
# Without --yes, asks for confirmation. With --yes, overwrites silently.
# Output files:
#   sales.csv     (deterministic — np.random.seed(42) in data_prep.py)
#   plans.csv
#   clients.csv

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$REPO_ROOT"

if [ ! -f data_prep.py ]; then
  echo "[ERROR] data_prep.py not found in $REPO_ROOT" >&2
  exit 1
fi

if [ "${1:-}" != "--yes" ]; then
  echo "This will overwrite: sales.csv, plans.csv, clients.csv"
  echo "  (deterministic — same files regenerated every time, unless you change the seed in data_prep.py)"
  read -r -p "Proceed? [y/N] " ans
  case "$ans" in
    y|Y|yes|YES) ;;
    *) echo "Aborted."; exit 0 ;;
  esac
fi

python data_prep.py
echo "[OK] data regenerated in $REPO_ROOT"
