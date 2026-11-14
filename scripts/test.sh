#!/usr/bin/env bash
# Runs the Python tests (standard library only; uses the committed fixture data).
#   bash scripts/test.sh
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 -m unittest discover -s apps/bank-backend/tests -t apps/bank-backend -v
