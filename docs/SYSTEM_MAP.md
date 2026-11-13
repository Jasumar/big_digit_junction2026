# SYSTEM_MAP

Who owns what and what depends on what. Nothing here commits to a stack.

## Modules

| Path | What it is | Owner |
| --- | --- | --- |
| `apps/frontend/` | what a user sees and does | `TODO` |
| `apps/backend/` | server-side logic, external calls | `TODO` |
| `packages/contracts/` | shapes both apps agree on | `TODO` |
| `packages/db/` | state outside the process: storage, access, seeds — location and form undecided, may be remote or thin | `TODO` |

An unowned module is one nobody may change without asking.

## Dependencies

```text
frontend ──┐
           ├──> contracts        (shapes only, no runtime)
backend ───┘
    │
    └──> db                   (if it exists; may be absent, remote, or in-process)
```

- `contracts` depends on nothing in this repo.
- `db` depends on nothing in this repo.
- Neither app owns the other's shapes or storage.

`TODO`: replace with the real runtime picture once the architecture is decided. The
arrows are the part that must stay true.

## Shared surfaces

Things more than one module or task depends on. Cross-cutting; changing one is a
coordinated act, not a local edit (rules: `docs/CONTRIBUTING.md` §Shared surfaces).

| Surface | Touched by |
| --- | --- |
| `packages/contracts/` | frontend, backend |
| `packages/db/` | backend, anything reading stored data |
| `.env.example`, config keys | both apps, CI |
| `scripts/`, `.github/` | everyone |
| root docs and `AGENTS.md` | everyone |

## Undecided

`TODO`: runtime/deployment shape, external services, how data is stored, where each
app runs, what is mocked. Each gets a line here when decided — and a line in
`docs/MASTER_PLAN.md` §Decision log.
