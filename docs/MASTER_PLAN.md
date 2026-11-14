# MASTER_PLAN

What we build and who builds it. Architecture: `SYSTEM_MAP.md`. Workflow:
`CONTRIBUTING.md`. Architecture, stack, a working MVP with a real AI provider (Gemma on
Modal) and a draft demo story (`docs/DEMO.md`, kept local and gitignored for now) are in place. What is left: "Next up" below.

## Challenge

S-Bank: build a mobile-first AI financial coach that lets people chat with their own
money, built around the three spending baskets. Full brief, judging criteria and a
gap list against the MVP: [`CHALLENGE.md`](CHALLENGE.md).

## MVP scope

Proposed from the brief (`CHALLENGE.md`); confirm as a team.

- **Must have** (demo fails without it): chat with your own money on a phone-width
  UI; the three baskets; where did my money go; what kind of spender am I; safe to
  spend this week; what-if ("cut dining out by 20%"); a real AI provider behind the
  approval step. *All built (T001–T014).*
- **Built beyond the must-haves:** Finnish/Swedish/English UI and answers (T012), follow-up
  questions (T013), life signals (T011), MCC subcategories such as taxis (T014), a safety
  net against invented numbers and silent substitution (T010).
- **Should have, not built:** safe to save; open-data benchmarks (Statistics Finland);
  tested plain-language explanations of financial concepts.
- **Out of scope:** mortgage features (the data is loaded, no tool uses it), real login, multi-bank (PSD2) view, hosted cloud,
  native app.

## Demo

Draft 90-second story, checklist and fallback plan: `docs/DEMO.md` (local only for now,
gitignored; ask the team lead for a copy) — every question
in it was dry-run on Gemma with the full data. Confirm it as a team; it is the tiebreaker
for every "should we build this?" question.

## Milestones

| ID | Milestone | Exit criterion | Status |
| --- | --- | --- | --- |
| M0 | Scaffold | `bash scripts/check.sh` green; a fresh clone works | done |
| M1 | Walking skeleton | one command travels steps 1–7 (`SYSTEM_MAP.md` §Flow) through every module, stubs allowed | done (T007) |
| M2 | MVP | must-have scope works end to end | done (T008–T014) |
| M3 | Demo polish | the demo runs twice in a row, unattended | open — `DEMO.md` checklist |

## Tasks

Index of `docs/tasks/`. Keep it short; one owner per task.

| Task | Owner | Area | Depends on | Status |
| --- | --- | --- | --- | --- |
| [T001](tasks/T001-choose-stack.md) | `TODO` | all | — | merged |
| [T002](tasks/T002-contracts-v0.md) | `TODO` | contracts | T001 | merged |
| [T003](tasks/T003-cloud-mock-and-first-tool.md) | `TODO` | cloud, calculation | T002 | merged |
| [T004](tasks/T004-bank-backend-skeleton.md) | `TODO` | bank-backend | T002 | merged |
| [T005](tasks/T005-local-ai-spike.md) | `TODO` | ai | T001 | merged |
| [T006](tasks/T006-frontend-client-skeleton.md) | `TODO` | frontend, client | T002 | merged |
| [T007](tasks/T007-walking-skeleton.md) | `TODO` | all | T003–T006 | merged |
| [T008](tasks/T008-local-ai-modal.md) | `TODO` | ai | T007 | merged |
| [T009](tasks/T009-openrouter-provider.md) | `TODO` | ai | T008 | merged |
| [T010](tasks/T010-improve-ai-rules.md) | `TODO` | ai | T008 | merged |
| [T011](tasks/T011-inferred-life-signals.md) | `TODO` | calculation | T003 | merged |
| [T012](tasks/T012-ui-language.md) | `TODO` | frontend | T010 | merged |
| [T013](tasks/T013-follow-up-questions.md) | `TODO` | ai, frontend | T010 | merged |
| [T014](tasks/T014-mcc-codes.md) | `TODO` | cloud, calculation | T011 | merged |
| T015 (docs refresh + local demo plan) | `TODO` | docs | T014 | review |

Order: T001 first (everyone, short). Then T002. Then T003, T004, T005, T006 in
parallel — one person each. T007 joins them into M1. All seven were built together in
the MVP on branch `task/t000-first-mvp` (merged in PR #3).

**Next up** (no task files yet; create one before starting), most important first:

1. **Demo (M3):** confirm `DEMO.md` as a team, run it twice in a row, record a backup
   video, decide the demo laptop (Q8).
2. **Native check of Finnish/Swedish wording** (Q11): glossary, UI text, chips.
3. **Rotate the endpoint key** before the demo (`apps/ai/README.md` §Team access) and
   rerun `apps/ai/eval/run_eval.py` on Gemma (last full run was before T013/T014).
4. **Safe-to-save** tool — the brief names it next to safe-to-spend.
5. **Open-data benchmarks** from Statistics Finland (today: the dataset's own age bands).
6. **Missing tools** (the coach says it can't today): calendar months and custom date
   ranges, a list of individual transactions, monthly averages, year-over-year, balance
   history, share of income (shares are of spending today).
7. **Robustness:** Gemma sometimes says a subcategory total "includes all" purchases and
   once misdated the safe-to-spend week; the offline stub is English-only.
8. **Housekeeping:** decide on `feat/Verda` (CuriousGeorg1, WIP: grounding and provider
   tests — may overlap the T010 number check); owners can delete `feat/t009` and merged
   `task/…` branches; add a Node setup step to CI so the UI text check always runs.

## Open questions

| # | Question | Owner | Due |
| --- | --- | --- | --- |
| 1 | ~~Exact challenge brief and judging criteria?~~ Answered: `CHALLENGE.md` | — | done |
| 2 | ~~Stack and transport per app?~~ Answered by the MVP: Python stdlib backend, plain JS UI, HTTP between them, in-process AI and calculation (`tasks/Decisions.md` #1–4) | — | done |
| 3 | ~~Is `apps/client/` a real layer?~~ Answered: a thin JS module, not a process (#3) | — | done |
| 4 | ~~Which AI provider and model for the challenge?~~ Answered: Gemma 4 26B-A4B on Modal (vLLM, H100), OpenAI-compatible API with a key (T008; Gemma 3 27B until T016) | — | done |
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
| 2026-11-14 | Switch the model to Gemma 4 26B-A4B (same Modal app and URL); Gemma 3 27B stays selectable with `COACH_MODEL` | after three code fixes Gemma 4 passed 33/33 eval cases at 3.6 s median vs Gemma 3's 31/33 at 11.0 s | team (T016) |
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
- If Gemma is down, the offline stub answers — English only → switch the UI to EN, or
  play the backup video (`DEMO.md` §If something breaks).
- The endpoint key was shown in a chat transcript → rotate it before the demo.

Add risks as they appear, each with its fallback.
