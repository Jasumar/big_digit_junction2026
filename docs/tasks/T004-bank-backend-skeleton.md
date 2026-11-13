# T004 — S-pankki backend skeleton

**Owner:** `TODO` **Status:** todo
**Branch:** `task/t004-bank-backend-skeleton`

## Goal

`apps/bank-backend/` accepts a `Command` (step 1), forwards it to an AI client (step 2),
runs the approval check on any calculation request (step 3), calls the calculation
module (step 5), and returns an `Answer` (step 7). AI and calculation are stubs behind
the T002 contracts, so this works before T003 and T005 land.

## Allowed files

```text
apps/bank-backend/**   (except calculation/, owned by T003)
```

**Shared surfaces touched:** none.

## Depends on

- Needs merged first: T002
- Blocks: T007

## Acceptance criteria

- [ ] One documented command starts the backend.
- [ ] A command returns a stubbed `Answer` end to end.
- [ ] A calculation request that fails approval is rejected and the answer says so.
- [ ] Setup section in `apps/bank-backend/README.md` filled in.

## Verify

```bash
bash scripts/check.sh
# TODO: the backend's test / run commands once the stack exists
```

## Notes

The approval rule can be a simple allow-list of tool names for v0.
