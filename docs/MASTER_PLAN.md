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
| [T008](tasks/T008-local-ai-modal.md) | `TODO` | ai | T007 | review |

Order: T001 first (everyone, short). Then T002. Then T003, T004, T005, T006 in
parallel — one person each. T007 joins them into M1. All seven were built together in
the MVP on branch `task/t000-first-mvp` and await review.

**Next up** (no task files yet; create one before starting):

1. Gemma on Modal works end to end, incl. the browser UI (T008). Left: tidy Finnish
   wording (English archetype labels, "asuntolaina" for housing, € placement in English).
2. Safe-to-save tool.
3. MCC filter in `explore_transactions` (taxis, pharmacies…).
4. Open-data benchmarks from Statistics Finland.
5. Finnish/Swedish/English: string files for fixed text, category-name table, locale
   number/date formatting, glossary in the AI prompt (`apps/ai/README.md` §Language).
6. Agree the demo story below, then polish for it (M3). Idea: ask the same question in
   Finnish and in English and get native answers in both.

## Open questions

| # | Question | Owner | Due |
| --- | --- | --- | --- |
| 1 | ~~Exact challenge brief and judging criteria?~~ Answered: `CHALLENGE.md` | — | done |
| 2 | ~~Stack and transport per app?~~ Answered by the MVP: Python stdlib backend, plain JS UI, HTTP between them, in-process AI and calculation (`tasks/Decisions.md` #1–4) | — | done |
| 3 | ~~Is `apps/client/` a real layer?~~ Answered: a thin JS module, not a process (#3) | — | done |
| 4 | ~~Which AI provider and model for the challenge?~~ Answered: Gemma 3 27B on Modal (vLLM, H100), OpenAI-compatible API with a key (T008) | — | done |
| 5 | ~~What is "cloud" for the demo?~~ Answered: the data platform holding all client data (e.g. BigQuery, Azure, AWS); here, the S-pankki mock data. Local SQLite stands in. | — | done |
| 6 | ~~Who asks for a calculation, and what does "approved" check?~~ Answered: the model asks; the backend checks the catalog, the schema and that no customer id is supplied (#13) | — | done |
| 7 | ~~Which calculations does the demo need?~~ Answered for the MVP: seven tools (`apps/bank-backend/calculation/README.md`) | — | done |
| 8 | Where does the demo run (which laptop), and what is shown live vs scripted? | `TODO` | before demo |
| 9 | ~~Host the cloud for the demo?~~ Answered: keep the local SQLite stand-in for now | — | done |
| 11 | Finnish (and Swedish) names for the three baskets and key terms — confirm the draft glossary in `apps/ai/README.md` §Language | `TODO` — a Finnish speaker | before demo |
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
| 2026-11-14 | Challenge uses a hosted AI API; S-Bank may self-host in production, so the provider stays behind `apps/ai/provider.py` | speed for the challenge, swappable later | team |
| 2026-11-14 | One model answers in the user's language (Finnish/Swedish/English); no translation model; fixed UI text via string files, numbers formatted by code | simpler, faster, keeps tone; numbers stay exact | team |
| 2026-11-14 | AI for the challenge: Gemma 3 27B on Modal (vLLM, one H100), API-key protected; falls back to the stub if unreachable | open model we host ourselves, close to S-Bank self-hosting; team chose 27B | team |
| 2026-11-13 | The AI model never reads client data; it only sees results of backend-approved calculations | privacy, the core of the pitch | team |

## Risks

- A self-hosted model (S-Bank production) is weaker in Finnish → test Finnish quality
  first; consider a Finnish-trained open model before adding a translation step.
- The model emits malformed calculation requests → the backend rejects them (step 3)
  and the answer says so; never crash the demo.
- No real S-pankki data → mock data in `packages/cloud/` from day one.
- Demo laptop lacks the full database and silently runs on the 6-customer sample →
  start with `REQUIRE_FULL_DATA=1`; the UI also shows a banner on sample data.
- Gemma on Modal adds seconds per answer, cold starts take minutes, and it can be down →
  the provider falls back to the stub per call; warm it with `COACH_MIN_CONTAINERS=1`
  before the demo; the database is not the bottleneck (<5 ms per tool).
- GPU cost: an H100 bills while running → scale-to-zero after 10 min by default; only
  keep one warm during the demo.
- The stub only understands English keywords; Finnish questions get the help text →
  wire the real provider before showing Finnish.

Add risks as they appear, each with its fallback.
