# T007 — Walking skeleton (M1)

**Owner:** `TODO` **Status:** review (built in MVP, see Decisions.md)
**Branch:** `task/t007-walking-skeleton`

## Goal

Replace the stubs: one real command travels steps 1–7 through every module — UI,
client, bank backend, local AI model, calculation tool, mock cloud data — and the answer
appears in the UI.

## Allowed files

```text
apps/**            (wiring only; no new features)
README.md          (§Start: one way to run everything)
.env.example       (keys the wiring needs)
```

**Shared surfaces touched:** `README.md`, `.env.example` — tell the team.

## Depends on

- Needs merged first: T003, T004, T005, T006
- Blocks: M2 work

## Acceptance criteria

- [ ] From a fresh clone, the documented steps start every part.
- [ ] One sample question returns an answer that uses a real calculation result.
- [ ] Turning off the AI model gives a visible error, not a hang.

## Verify

```bash
bash scripts/check.sh
# TODO: the end-to-end run command
```

## Notes
