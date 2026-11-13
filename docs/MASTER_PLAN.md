# MASTER_PLAN

Single plan for the project. Owns **what** we build and **who** builds it. Architecture
detail lives in `SYSTEM_MAP.md`; workflow rules in `CONTRIBUTING.md`.

Status: scaffold — no challenge chosen, no scope fixed, no stack fixed. Sections below
are the skeleton to fill in on day one, not decisions.

## 1. Challenge

`TODO`: challenge name, organiser, one-paragraph problem statement, link to the brief.

## 2. MVP scope

Keep this ruthless: what the demo must do, nothing else.

**Must have** (demo fails without it)

- `TODO`

**Should have** (add if time allows)

- `TODO`

**Explicitly out of scope** (do not build, do not let agents build)

- `TODO`: authentication, admin panels, real-time sync, mobile app, … — list the
  tempting things we are saying no to, so nobody builds them by accident.

## 3. Demo goal

`TODO`: the 60–90 second story told on stage. Write it as a user walking through the
product, and name which parts are hard-coded, mocked, or live. Update it whenever
scope changes — it is the tiebreaker for every "should we build this?" question.

## 4. Milestones

| ID | Milestone | Goal | Exit criterion |
| --- | --- | --- | --- |
| M0 | Scaffold | repo, docs, workflow in place | `bash scripts/check.sh` green; `main` clones and runs |
| M1 | Walking skeleton | one thin end-to-end path through all modules | a request goes frontend → backend → db and back |
| M2 | MVP | must-have scope complete | demo goal works end to end |
| M3 | Demo polish | reliability, loading states, seed data, stage rehearsal | demo runs twice in a row without manual fixes |

`TODO`: put real times against M1–M3 relative to the event start.

## 5. Task ownership

Task files live in `docs/tasks/` (one file per task, template there). This table is
the index — keep it short.

| Task | Owner | Area | Depends on | Status |
| --- | --- | --- | --- | --- |
| `TODO` | `TODO` | `frontend` / `backend` / `contracts` / `db` | `TODO` | todo |

Rules:

- One owner per task. Shared ownership means nobody is responsible.
- A task that touches two areas is two tasks, unless it is explicitly a contract or
  schema change (those are one task owned by one person).
- Do not start a task whose dependency is not merged.

## 6. Open questions

| # | Question | Why it matters | Owner | Due |
| --- | --- | --- | --- | --- |
| 1 | Which challenge? | everything | `TODO` | day 1 |
| 2 | Stack (and who owns the setup)? | blocks all code | `TODO` | day 1 |
| 3 | Data sources / external APIs and their keys? | blocks backend | `TODO` | day 1 |
| 4 | Where does it run / how is it demoed? | blocks integration | `TODO` | day 1 |
| 5 | What is mocked vs real in the demo? | scope | `TODO` | day 1 |

## 7. Decision log

Append-only. One line per decision that others must not silently reverse.

| Date | Decision | Why | By |
| --- | --- | --- | --- |
| `TODO` | Monorepo with `apps/*` + `packages/*`, one branch/worktree per task | parallel work, few conflicts | scaffold |

## 8. Risks

`TODO`: e.g. an external API that may be rate-limited or unavailable on the day; a
dependency that needs approval; a demo that needs network. Name the fallback for each.
