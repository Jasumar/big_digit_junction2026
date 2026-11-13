# T002 — Contracts v0 for every edge

**Owner:** `TODO` **Status:** todo
**Branch:** `task/t002-contracts-v0`

## Goal

`packages/contracts/` defines the shapes for steps 1–7: `Command`, `Answer` (text +
insights), the bank ↔ AI messages, `CalculationRequest`, `CalculationResult` and its
rejection. Every other task builds against these.

## Allowed files

```text
packages/contracts/**
```

**Shared surfaces touched:** `packages/contracts/` — this task has authority to create
it. After merge, changes need the normal shared-surface process.

## Depends on

- Needs merged first: T001
- Blocks: T003, T004, T006

## Acceptance criteria

- [ ] One shape per row of the Edges table in `packages/contracts/README.md`, with an
      example value each.
- [ ] Error / rejection shape for step 3 and step 5.
- [ ] Setup section in the README filled in with the real commands.

## Verify

```bash
bash scripts/check.sh
# TODO: the contracts' own check (type check / schema validation) once T001 picks it
```

## Notes

Keep v0 minimal: only fields the demo path needs.
