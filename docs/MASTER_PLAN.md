# MASTER_PLAN

What we build and who builds it. Architecture: `SYSTEM_MAP.md`. Workflow:
`CONTRIBUTING.md`. The architecture is decided (see Decision log); scope and stack are
not.

## Challenge

Organiser: S-pankki. `TODO`: challenge name, one-paragraph problem, link to the brief.

Working idea: a client asks a question or gives a command in the app; a locally hosted
AI model answers with insights, backed by calculations the bank backend approves and
runs over the client's own data. The model never reads client data directly.

## MVP scope

- **Must have** (demo fails without it): `TODO`
- **Should have**: `TODO`
- **Out of scope** — list the tempting things we are saying no to: `TODO`

## Demo

`TODO`: the 60–90s story, as a user walking through it, naming what is live and what is
faked. It is the tiebreaker for every "should we build this?" question.

## Milestones

| ID | Milestone | Exit criterion |
| --- | --- | --- |
| M0 | Scaffold | `bash scripts/check.sh` green; a fresh clone works |
| M1 | Walking skeleton | one command travels steps 1–7 (`SYSTEM_MAP.md` §Flow) through every module, stubs allowed |
| M2 | MVP | must-have scope works end to end |
| M3 | Demo polish | the demo runs twice in a row, unattended |

`TODO`: real times for M1–M3.

## Tasks

Index of `docs/tasks/`. Keep it short; one owner per task.

| Task | Owner | Area | Depends on | Status |
| --- | --- | --- | --- | --- |
| [T001](tasks/T001-choose-stack.md) | `TODO` | all | — | todo |
| [T002](tasks/T002-contracts-v0.md) | `TODO` | contracts | T001 | todo |
| [T003](tasks/T003-cloud-mock-and-first-tool.md) | `TODO` | cloud, calculation | T002 | todo |
| [T004](tasks/T004-bank-backend-skeleton.md) | `TODO` | bank-backend | T002 | todo |
| [T005](tasks/T005-local-ai-spike.md) | `TODO` | ai | T001 | todo |
| [T006](tasks/T006-frontend-client-skeleton.md) | `TODO` | frontend, client | T002 | todo |
| [T007](tasks/T007-walking-skeleton.md) | `TODO` | all | T003–T006 | todo |

Order: T001 first (everyone, short). Then T002. Then T003, T004, T005, T006 in
parallel — one person each. T007 joins them into M1.

## Open questions

| # | Question | Owner | Due |
| --- | --- | --- | --- |
| 1 | Exact challenge brief and judging criteria? | `TODO` | day 1 |
| 2 | Stack and transport per app, and who owns setup? (T001) | `TODO` | day 1 |
| 3 | Is `apps/client/` a real layer, or the data layer inside the frontend? | `TODO` | day 1 |
| 4 | Which model and runtime counts as "local", and what hardware runs it? (T005) | `TODO` | day 1 |
| 5 | What is "cloud" for the demo — mock data, a hosted DB, an S-pankki API? | `TODO` | day 1 |
| 6 | Who asks for a calculation: the model (tool call, step 2→3) or the backend up front? What does "approved" check? | `TODO` | day 1 |
| 7 | Which calculations does the demo need? | `TODO` | day 1 |
| 8 | Where does it run, and what is mocked in the demo? | `TODO` | day 1 |

## Decision log

Append-only. One line per decision others must not silently reverse.

| Date | Decision | Why | By |
| --- | --- | --- | --- |
| 2026-11-13 | Monorepo, one branch/worktree per task, shared surfaces need authority | parallel work, few conflicts | scaffold |
| 2026-11-13 | Architecture: UI → client → S-pankki backend ↔ local AI model; calculation tools inside the backend read cloud data (`SYSTEM_MAP.md`) | team diagram | team |
| 2026-11-13 | The AI model never reads client data; it only sees results of backend-approved calculations | privacy, the core of the pitch | team |

## Risks

- A local model is too slow or too weak on our hardware → fallback: a smaller model,
  or canned answers behind the same contract for the demo.
- The model emits malformed calculation requests → the backend rejects them (step 3)
  and the answer says so; never crash the demo.
- No real S-pankki data → mock data in `packages/cloud/` from day one.

`TODO`: add risks as they appear, each with its fallback.
