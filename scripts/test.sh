#!/usr/bin/env bash
# Runs the Python tests (standard library only; uses the committed fixture data) and the
# UI text checks (Node, no packages).
#   bash scripts/test.sh
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m unittest discover -s apps/bank-backend/tests -t apps/bank-backend -v
# UI text checks need Node 20.10+ (no packages; the frontend .js files are ES modules).
# Skipped with a note when Node is missing or too old.
if command -v node >/dev/null 2>&1 && \
   node --experimental-default-type=module -e "" >/dev/null 2>&1; then
  node --no-warnings --experimental-default-type=module apps/frontend/i18n.test.mjs
else
  echo "note: Node 20.10+ not found, skipped apps/frontend/i18n.test.mjs"
fi
