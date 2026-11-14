# T003 — Mock client data and the first calculation tool

**Owner:** `TODO` **Status:** review (built in MVP, see Decisions.md)
**Branch:** `task/t003-cloud-mock-and-first-tool`

## Goal

`packages/cloud/` holds a mock dataset for a few fake clients, and
`apps/bank-backend/calculation/` has one working tool that takes a
`CalculationRequest`, reads that data (step 4) and returns a `CalculationResult`
(step 5).

## Allowed files

```text
packages/cloud/**
apps/bank-backend/calculation/**
```

**Shared surfaces touched:** `packages/cloud/` data shape — this task has authority to
create it.

## Depends on

- Needs merged first: T002
- Blocks: T007

## Acceptance criteria

- [ ] One command creates / resets the mock data; documented in `packages/cloud/README.md`.
- [ ] One tool (e.g. monthly spending by category — `TODO`: pick with the team) works
      on that data.
- [ ] Unknown client or bad input returns the rejection shape, not a crash.
- [ ] Tool listed in `apps/bank-backend/calculation/README.md` §Tools.

## Verify

```bash
bash scripts/check.sh
# TODO: the tool's test command once the stack exists
```

## Notes

Fake data only. Nothing that looks like a real person.
