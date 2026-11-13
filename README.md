# Junction 2026 — Project Name TBD

Scaffold for **Junction 2026**. Challenge, scope and stack are **not decided**; this
repo exists so work can start in parallel on day one with almost no setup.

Status: scaffold only. No code, no stack, no product decisions. Every `TODO` is an
open question, not a hint.

## Structure

```text
apps/frontend/       user-facing app
apps/backend/        server-side logic
packages/contracts/  shared shapes between apps
packages/db/         whatever holds state outside the process (may be remote, may be thin)
docs/                plan, map, rules, tasks
scripts/check.sh     repo checks, also run by CI
```

Each directory has a README with its intent and an empty Setup section.

## Start

```bash
git clone <repo-url> && cd junction2026
cp .env.example .env                      # local config, never committed
cp preferences.example.md preferences.md  # optional, for your agent
bash scripts/check.sh                     # repo checks
```

Read: `docs/CONTRIBUTING.md` for the workflow, `docs/MASTER_PLAN.md` for what we are
building, `docs/SYSTEM_MAP.md` for who owns what. Agents: `AGENTS.md` first.

## Conventions

- One task = one file in `docs/tasks/` = one branch = one worktree in `.worktrees/`.
- Branch names: `task/t001-<slug>`.
- Merge small and often; a branch that lives a day is too big.
- Anything more than one part of the system depends on is a **shared surface**. Do not
  change one silently — see `docs/CONTRIBUTING.md` §Shared surfaces.
- No secrets, no `.env`, no local config in git.

## Open

Challenge, MVP scope, stack, where it runs, what is mocked. See
`docs/MASTER_PLAN.md` §Open questions.
