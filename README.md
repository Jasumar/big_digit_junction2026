# Junction 2026 — Project Name TBD

<!-- TODO: replace the title above once the challenge is picked. -->

Hackathon project scaffold for **Junction 2026**. The challenge, product scope, and
tech stack are **not decided yet**; this repository exists so that on the main
hackathon day everyone can start work in parallel with near-zero setup and minimal
merge conflicts.

Status: **scaffold only.** No application code, no chosen stack, no product decisions.
Everything marked `TODO` is an open decision, not a hint.

---

## Start here

| If you are… | Read |
| --- | --- |
| A human, first time in the repo | this file, then [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) |
| Picking up a task | [`docs/tasks/`](docs/tasks/README.md) and your task file |
| An AI agent | [`AGENTS.md`](AGENTS.md) first, always |
| Looking for the big picture | [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md), [`docs/SYSTEM_MAP.md`](docs/SYSTEM_MAP.md) |

Ownership map: [`docs/SYSTEM_MAP.md`](docs/SYSTEM_MAP.md) §Module ownership.

---

## Structure

```text
/
├── apps/
│   ├── frontend/        # user-facing app — see its README
│   └── backend/         # API + server-side logic — see its README
├── packages/
│   ├── contracts/       # shared API contract, source of truth
│   └── db/              # schema, migrations, seed data
├── docs/
│   ├── MASTER_PLAN.md   # MVP scope, milestones, ownership, demo goals
│   ├── SYSTEM_MAP.md    # architecture, module boundaries, dependencies
│   ├── CONTRIBUTING.md  # mandatory collaboration rules
│   └── tasks/           # one file per task (branch + worktree)
├── scripts/check.sh     # repo hygiene checks, also run by CI
├── .github/workflows/   # CI
├── AGENTS.md            # rules for AI agents (tracked)
├── preferences.example.md  # template for local agent preferences
├── .env.example         # template for local environment
└── README.md
```

`apps/*/` are deployables; `packages/*` are shared libraries consumed by the apps.
Nothing is implemented yet — each directory has a README with its intended
responsibility.

---

## Prerequisites

Tooling is deliberately not pinned yet (`TODO`: pick once the stack is chosen).

- Git **2.5+** (worktrees).
- `TODO`: runtime + package manager, with a single version file to commit
  (e.g. `.nvmrc` / `.python-version`), so everyone runs the same version.

---

## Setup

```bash
git clone <repo-url>
cd junction2026

cp .env.example .env          # local config; never committed
cp preferences.example.md preferences.md   # optional, local agent preferences

# optional: run the repo hygiene checks
bash scripts/check.sh
```

`TODO`: install deps / build commands, added here and in each app README when the
stack is chosen. Until then there is nothing to install.

---

## Commands

Every project-wide command must be defined in **exactly one** place and referenced
from here. `TODO`: fill this table in — do not leave a command here that does not
work.

| Task | Command | Where defined |
| --- | --- | --- |
| Repo hygiene checks | `bash scripts/check.sh` | `scripts/check.sh` |
| Lint | `TODO` | `TODO` |
| Type check | `TODO` | `TODO` |
| Test | `TODO` | `TODO` |
| Build | `TODO` | `TODO` |
| Run dev servers | `TODO` | app READMEs |

---

## Conventions (short version)

Full rules: [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md).

- **One task = one file in `docs/tasks/` = one branch = one worktree.**
  Worktrees live in `.worktrees/<branch>` (gitignored).
- Branch names: `task/<id>-<slug>`, e.g. `task/t003-upload-endpoint`.
- Merge into `main` often and small; never let a branch live for a whole day.
- The API contract in `packages/contracts/` is the **source of truth**. Changing it
  requires announcing it in the task file and updating consumers in the same PR.
- Stay inside your task's "allowed files". Shared files need coordination first.
- No secrets, no local config, no committed `.env` — see `.gitignore`.

---

## Open decisions

Tracked in [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md) §Open questions. Currently
open: challenge, product scope, stack, hosting, data sources, demo story.
