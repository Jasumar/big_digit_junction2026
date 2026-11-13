# T001 — Choose stack and transport for every part

**Owner:** `TODO` **Status:** todo
**Branch:** `docs/t001-choose-stack`

## Goal

Every module in `docs/SYSTEM_MAP.md` has a chosen language/framework, and every edge a
chosen transport (HTTP, in-process call, …). Decided together, written down, so T002–T006
can start in parallel without guessing.

## Allowed files

```text
docs/MASTER_PLAN.md   (Decision log, Open questions 2–3)
docs/SYSTEM_MAP.md    (Undecided section)
```

**Shared surfaces touched:** `docs/` — whole team agrees in one short meeting.

## Depends on

- Needs merged first: none
- Blocks: T002, T005 (and through T002 everything else)

## Acceptance criteria

- [ ] Decision log has one line per module: stack, and who owns setup.
- [ ] Decision log has the transport for each edge in `SYSTEM_MAP.md` §Flow.
- [ ] Open question 3 (is `apps/client/` a real layer?) answered; if not, a follow-up
      task to fold it into `apps/frontend/` is listed in §Tasks.

## Verify

```bash
bash scripts/check.sh
```

## Notes

Pick what the team already knows. No code in this task.
