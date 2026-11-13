# T006 — Frontend and client skeleton

**Owner:** `TODO` **Status:** todo
**Branch:** `task/t006-frontend-client-skeleton`

## Goal

A user can type a command in `apps/frontend/`, the client layer (`apps/client/`) sends
it as a `Command` (step 1), and the returned `Answer` and insights render on screen
(step 7). Works against a stubbed backend response until T004 is merged.

## Allowed files

```text
apps/frontend/**
apps/client/**
```

**Shared surfaces touched:** none.

## Depends on

- Needs merged first: T002 (and T001's answer on whether `apps/client/` is separate)
- Blocks: T007

## Acceptance criteria

- [ ] One documented command starts the UI.
- [ ] Command in, answer and insights out, against a stub.
- [ ] Loading and error states visible (backend down, rejected calculation).

## Verify

```bash
bash scripts/check.sh
# TODO: the frontend's test / build commands once the stack exists
```

## Notes
