# MASTER_PLAN

What we build and who builds it. Architecture: `SYSTEM_MAP.md`. Workflow:
`CONTRIBUTING.md`. Nothing below is decided yet — this is the shape to fill in.

## Challenge

`TODO`: name, organiser, one-paragraph problem, link to the brief.

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
| M1 | Walking skeleton | one thin path through every module |
| M2 | MVP | must-have scope works end to end |
| M3 | Demo polish | the demo runs twice in a row, unattended |

`TODO`: real times for M1–M3.

## Tasks

Index of `docs/tasks/`. Keep it short; one owner per task.

| Task | Owner | Area | Depends on | Status |
| --- | --- | --- | --- | --- |
| `TODO` | `TODO` | | | todo |

## Open questions

| # | Question | Owner | Due |
| --- | --- | --- | --- |
| 1 | Which challenge? | `TODO` | day 1 |
| 2 | Stack, and who owns setup? | `TODO` | day 1 |
| 3 | Data: what is stored, where, and is it local at all? | `TODO` | day 1 |
| 4 | External APIs and their keys? | `TODO` | day 1 |
| 5 | Where does it run, and what is mocked in the demo? | `TODO` | day 1 |

## Decision log

Append-only. One line per decision others must not silently reverse.

| Date | Decision | Why | By |
| --- | --- | --- | --- |
| 2026-11-13 | Monorepo, one branch/worktree per task, shared surfaces need authority | parallel work, few conflicts | scaffold |

## Risks

`TODO`: name each risk and its fallback — an API that rate-limits on the day, a demo
that needs network, a dependency that needs approval.
