# MASTER_PLAN

What we build and who builds it. Architecture: `SYSTEM_MAP.md`. Workflow:
`CONTRIBUTING.md`. Architecture, stack and a working MVP are in place (see Decision log
and `tasks/Decisions.md`); the real AI provider and the demo story are not.

## Challenge

S-Bank: build a mobile-first AI financial coach that lets people chat with their own
money, built around the three spending baskets. Full brief, judging criteria and a
gap list against the MVP: [`CHALLENGE.md`](CHALLENGE.md).

## MVP scope

Proposed from the brief (`CHALLENGE.md`); confirm as a team.

- **Must have** (demo fails without it): chat with your own money on a phone-width
  UI; the three baskets; where did my money go; what kind of spender am I; safe to
  spend this week; what-if ("cut dining out by 20%"); a real AI provider behind the
  approval step. *Built, except the real AI provider.*
- **Should have:** safe to save; open-data benchmarks (Statistics Finland); MCC-level
  questions ("taxis last month"); plain-language explanations of financial concepts.
- **Out of scope:** mortgage features (the data is loaded, no tool uses it), real login, multi-bank (PSD2) view, hosted cloud,
  native app.

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
| [T001](tasks/T001-choose-stack.md) | `TODO` | all | — | review |
| [T002](tasks/T002-contracts-v0.md) | `TODO` | contracts | T001 | review |
| [T003](tasks/T003-cloud-mock-and-first-tool.md) | `TODO` | cloud, calculation | T002 | review |
| [T004](tasks/T004-bank-backend-skeleton.md) | `TODO` | bank-backend | T002 | review |
| [T005](tasks/T005-local-ai-spike.md) | `TODO` | ai | T001 | review |
| [T006](tasks/T006-frontend-client-skeleton.md) | `TODO` | frontend, client | T002 | review |
| [T007](tasks/T007-walking-skeleton.md) | `TODO` | all | T003–T006 | review |

Order: T001 first (everyone, short). Then T002. Then T003, T004, T005, T006 in
parallel — one person each. T007 joins them into M1. All seven were built together in
the MVP on branch `task/t000-first-mvp` and await review.

**Next up** (no task files yet; create one before starting):

1. Wire a real AI provider (`apps/ai/README.md` §Setup) — the biggest gap.
2. Safe-to-save tool.
3. MCC filter in `explore_transactions` (taxis, pharmacies…).
4. Open-data benchmarks from Statistics Finland.
5. Agree the demo story below, then polish for it (M3).

## Open questions

| # | Question | Owner | Due |
| --- | --- | --- | --- |
| 1 | ~~Exact challenge brief and judging criteria?~~ Answered: `CHALLENGE.md` | — | done |
| 2 | ~~Stack and transport per app?~~ Answered by the MVP: Python stdlib backend, plain JS UI, HTTP between them, in-process AI and calculation (`tasks/Decisions.md` #1–4) | — | done |
| 3 | ~~Is `apps/client/` a real layer?~~ Answered: a thin JS module, not a process (#3) | — | done |
| 4 | Which real model and runtime, and does "local" mean self-hosted or an API? | `TODO` | next |
| 5 | ~~What is "cloud" for the demo?~~ Answered: the data platform holding all client data (e.g. BigQuery, Azure, AWS); here, the S-pankki mock data. Local SQLite stands in. | — | done |
| 6 | ~~Who asks for a calculation, and what does "approved" check?~~ Answered: the model asks; the backend checks the catalog, the schema and that no customer id is supplied (#13) | — | done |
| 7 | ~~Which calculations does the demo need?~~ Answered for the MVP: seven tools (`apps/bank-backend/calculation/README.md`) | — | done |
| 8 | Where does the demo run (which laptop), and what is shown live vs scripted? | `TODO` | before demo |
| 9 | ~~Host the cloud for the demo?~~ Answered: keep the local SQLite stand-in for now | — | done |
| 10 | Which cloud does S-Bank use? Decides the provider if we host later (`packages/cloud/README.md` §Hosting later) | `TODO` — ask S-Bank IT/AI mentor | — |

## Decision log

Append-only. One line per decision others must not silently reverse.

| Date | Decision | Why | By |
| --- | --- | --- | --- |
| 2026-11-13 | Monorepo, one branch/worktree per task, shared surfaces need authority | parallel work, few conflicts | scaffold |
| 2026-11-13 | Architecture: UI → client → S-pankki backend ↔ local AI model; calculation tools inside the backend read cloud data (`SYSTEM_MAP.md`) | team diagram | team |
| 2026-11-13 | MVP built with stdlib Python, plain JS, SQLite, stub AI; smaller choices in `docs/tasks/Decisions.md` (#1–22) | ship something that runs | MVP build |
| 2026-11-13 | "Cloud" = the data platform that holds all client data (GCP BigQuery, Azure, AWS or similar). In this project it holds the S-pankki mock data. | team definition | team |
| 2026-11-13 | Keep the local SQLite stand-in for the cloud for now; hosted platform later | demo works offline, no accounts | team |
| 2026-11-13 | The AI model never reads client data; it only sees results of backend-approved calculations | privacy, the core of the pitch | team |

## Risks

- A local model is too slow or too weak on our hardware → fallback: a smaller model,
  or canned answers behind the same contract for the demo.
- The model emits malformed calculation requests → the backend rejects them (step 3)
  and the answer says so; never crash the demo.
- No real S-pankki data → mock data in `packages/cloud/` from day one.
- Demo laptop lacks the full database and silently runs on the 6-customer sample →
  start with `REQUIRE_FULL_DATA=1`; the UI also shows a banner on sample data.

- A real AI provider adds seconds per answer and can be down → keep `AI_PROVIDER=stub`
  as the offline fallback; the database is not the bottleneck (<5 ms per tool).
- The stub only understands keywords → script the demo questions, or wire the real
  provider first.

Add risks as they appear, each with its fallback.
