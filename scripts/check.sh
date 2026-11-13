#!/usr/bin/env bash
# Repo hygiene checks. Runs everywhere with only bash + git — no runtime, no install.
# CI runs this exact script, so a green run here means green there.
#
#   bash scripts/check.sh
#
# Exit code 0 = all checks passed, 1 = at least one failure.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

fail=0
ok()   { printf '  ok    %s\n' "$1"; }
bad()  { printf '  FAIL  %s\n' "$1"; fail=1; }

echo "Repository checks"

# --- 1. required structure --------------------------------------------------
echo "structure"
for p in \
  README.md AGENTS.md .gitignore .env.example preferences.example.md \
  docs/CHALLENGE.md docs/MASTER_PLAN.md docs/SYSTEM_MAP.md docs/CONTRIBUTING.md \
  docs/tasks/TEMPLATE.md docs/tasks/README.md \
  apps/frontend/README.md apps/client/README.md \
  apps/bank-backend/README.md apps/bank-backend/calculation/README.md \
  apps/ai/README.md \
  packages/contracts/README.md packages/cloud/README.md \
  .github/workflows; do
  if [ -e "$p" ]; then ok "$p"; else bad "missing: $p"; fi
done

# --- 2. nothing forbidden is tracked ---------------------------------------
echo "tracked files"
tracked="$(git ls-files)"
forbidden=0
while IFS= read -r f; do
  [ -n "$f" ] || continue
  case "$f" in
    .env|*/.env|.env.local|*/.env.local)
      bad "secret file tracked: $f"; forbidden=1 ;;
    preferences.md|*/preferences.md)
      bad "local preferences tracked: $f"; forbidden=1 ;;
    node_modules/*|*/node_modules/*)
      bad "dependencies tracked: $f"; forbidden=1 ;;
    .worktrees/*|*/.worktrees/*)
      bad "worktree tracked: $f"; forbidden=1 ;;
    .venv/*|*/.venv/*|build/*|*/build/*|dist/*|*/dist/*)
      bad "build output tracked: $f"; forbidden=1 ;;
  esac
done <<< "$tracked"
[ "$forbidden" -eq 0 ] && ok "no .env, preferences.md, node_modules, .worktrees or build output"

# --- 3. relative markdown links resolve ------------------------------------
echo "docs links"
linkfail=0
while IFS= read -r f; do
  [ -n "$f" ] || continue
  base="$(dirname "$f")"
  while IFS= read -r raw; do
    [ -n "$raw" ] || continue
    target="${raw#](}"
    target="${target%)}"
    case "$target" in
      http://*|https://*|mailto:*|'#'*) continue ;;
    esac
    target="${target%%#*}"          # drop anchor
    target="${target%%\?*}"         # drop query
    [ -n "$target" ] || continue
    case "$target" in
      /*) resolved=".${target}" ;;
      *)  resolved="$base/$target" ;;
    esac
    if [ ! -e "$resolved" ]; then
      bad "$f -> $raw (resolved: $resolved)"
      linkfail=1
    fi
  done < <(grep -oE '\]\([^)[:space:]]+\)' "$f" 2>/dev/null || true)
done <<< "$(git ls-files '*.md')"
[ "$linkfail" -eq 0 ] && ok "all relative markdown links resolve"

# --- 4. yaml sanity: no tabs, no CRLF --------------------------------------
echo "yaml"
yamlfail=0
while IFS= read -r f; do
  [ -n "$f" ] || continue
  if grep -q $'\t' "$f" 2>/dev/null; then bad "tab character (illegal in YAML): $f"; yamlfail=1; fi
  if grep -q $'\r' "$f" 2>/dev/null; then bad "CRLF line endings: $f"; yamlfail=1; fi
done <<< "$(git ls-files '*.yml' '*.yaml')"
[ "$yamlfail" -eq 0 ] && ok "workflow files are tab-free with LF endings"

# --- 5. worktrees live where the docs say ---------------------------------
echo "worktrees"
stray="$(git worktree list --porcelain | grep -E '^worktree ' | awk '{print $2}' \
          | grep -v "^$(pwd)$" | grep -v "/.worktrees/" || true)"
if [ -n "$stray" ]; then
  printf '  note  worktrees outside .worktrees/ (allowed, but unconventional):\n%s\n' "$stray"
else
  ok "no worktrees outside .worktrees/"
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "PASS"
else
  echo "FAIL"
fi
exit "$fail"
