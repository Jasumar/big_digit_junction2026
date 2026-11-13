# SYSTEM_MAP

Architecture and module boundaries. Keep this current — it is what stops two tasks
from editing the same files. **Every directory below owns its files and nothing
else.**

Status: scaffold. Nothing is implemented; responsibilities are intent, not code.

## Layers

```text
        ┌──────────────────────────────┐
        │  apps/frontend               │  user-facing app
        └──────────────┬───────────────┘
                       │ imports contracts only (never db, never backend internals)
        ┌──────────────▼───────────────┐
        │  packages/contracts          │  shared API shape — source of truth
        └──────────────▲───────────────┘
                       │ imports contracts
        ┌──────────────┴───────────────┐
        │  apps/backend                │  API, business logic
        └──────────────┬───────────────┘
                       │ imports db
        ┌──────────────▼───────────────┐
        │  packages/db                 │  schema, migrations, seed
        └──────────────────────────────┘
```

`TODO`: replace this sketch with the real runtime diagram (services, external APIs,
storage) once the architecture is decided. The dependency rules below are the part
that must stay true.

## Dependency rules

| Module | May depend on | Must never depend on |
| --- | --- | --- |
| `packages/contracts` | nothing in this repo | everything |
| `packages/db` | nothing in this repo (its own generated types are fine) | `apps/*`, `contracts` |
| `apps/backend` | `contracts`, `db` | `apps/frontend` |
| `apps/frontend` | `contracts` | `apps/backend`, `db` |

Two arrows are forbidden because they are what make parallel work expensive: the
frontend reaching into backend sources, and either app reaching into the other's
build output. If you think you need them, the contract is missing something.

## Module ownership

| Path | Responsibility | Owner | Notes |
| --- | --- | --- | --- |
| `apps/frontend/` | screens, state, API client | `TODO` | see its README |
| `apps/backend/` | HTTP surface, auth, business logic | `TODO` | see its README |
| `packages/contracts/` | request/response/error shapes | `TODO` | changes affect everyone |
| `packages/db/` | schema, migrations, seeds | `TODO` | shared state, one migration at a time |
| `docs/` | plan, map, rules, tasks | `TODO` | shared; small edits |
| `.github/`, `scripts/` | CI, repo checks | `TODO` | shared |

`TODO`: fill in the Owner column with names/handles before the event starts. An
unowned module is a module nobody is allowed to change without asking.

## Data flow

`TODO`: one paragraph or diagram per main user action: request path from frontend →
backend → db → response, including where external services are called. Nothing to
describe yet.

## Runtime / deployment

`TODO`: decided with the stack. Record where each app runs and how env vars are
supplied.

## Where things are decided

- Product scope and milestones: `docs/MASTER_PLAN.md`
- This file: architecture and boundaries
- Per-directory details: the README inside each directory
- Workflow: `docs/CONTRIBUTING.md`
