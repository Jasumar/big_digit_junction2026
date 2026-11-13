# Junction 2026 — Project Name TBD

Scaffold for **Junction 2026** (S-pankki). Working idea: a client asks a question or
gives a command, a locally hosted AI model answers with insights, backed by
calculations over the client's own data. Scope and stack are **not decided**; this
repo exists so work can start in parallel with almost no setup.

Status: architecture decided (`docs/SYSTEM_MAP.md`), skeleton only. No code, no
stack. Every `TODO` is an open question, not a hint.

## Structure

```text
apps/frontend/                   UI / Frontend
apps/client/                     Client device / Backend (between UI and bank)
apps/bank-backend/               S-pankki backend: orchestrates every hop
apps/bank-backend/calculation/   calculation tools (inside the backend)
apps/ai/                         Local AI model: answers and insights
packages/contracts/              shapes on every edge
packages/cloud/                  client data the calculations read
docs/                            plan, map, rules, tasks
scripts/check.sh                 repo checks, also run by CI
```

Flow: UI → client → S-pankki backend → local AI model; the backend runs approved
calculations over cloud data and the answer travels back the same way. Full picture
and numbered steps: `docs/SYSTEM_MAP.md`.

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

MVP scope, stack, which model, where it runs, what is mocked. See
`docs/MASTER_PLAN.md` §Open questions.
