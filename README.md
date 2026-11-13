# Junction 2026 — Project Name TBD

Scaffold for **Junction 2026** (S-pankki). Working idea: a client asks a question or
gives a command, a locally hosted AI model answers with insights, backed by
calculations over the client's own data.

Status: **working MVP** — an S-pankki money coach over the hackathon transaction data,
with a rule-based AI stub ready to be swapped for a real provider. Choices made while
building it: `docs/tasks/Decisions.md`.

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

Each directory has a README with its intent, setup and conventions.

## Run

```bash
bash scripts/test.sh                       # tests on fixture data, no install
python3 apps/bank-backend/server.py        # http://localhost:8000 (mobile-first UI)
```

No dependencies: Python 3.10+ standard library, plain JS in the browser. With no
database present the server builds a small fixture (6 customers). For the full
dataset (5,100 customers, 3.6M transactions) get the CSVs from
`hackjunction/Junction-2026-S-pankki` (the large one is Git LFS) and run:

```bash
python3 packages/cloud/seed.py --csv-dir <folder with the CSVs>   # ~80 s, 500 MB, gitignored
```

Env: `PORT`, `AI_PROVIDER` (only `stub` so far), `SPANKKI_DB` — see `.env.example`.

## Start

```bash
git clone <repo-url> && cd junction2026
cp .env.example .env                      # local config, never committed
cp preferences.example.md preferences.md  # optional, for your agent
bash scripts/check.sh                     # repo checks
```

Read: `docs/CHALLENGE.md` for the brief and judging criteria, `docs/CONTRIBUTING.md` for the workflow, `docs/MASTER_PLAN.md` for what we are
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
