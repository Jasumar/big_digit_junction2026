# SYSTEM_MAP

Who owns what, what talks to what, and in which order. The runtime picture below is
decided (`docs/MASTER_PLAN.md` §Decision log); the stack is not.

## Architecture

```text
            ┌──────────────────┐
            │  UI / Frontend   │  apps/frontend/
            └────────┬─────────┘
                     │ ▲  (two-way)
                     ▼ │
        ┌──────────────────────────┐
        │ Client device / Backend  │  apps/client/
        └──────┬───────────▲───────┘
   1. command  │           │ 7. answer / insights
               ▼           │
        ┌──────────────────┴───────┐  2. client command    ┌────────────────┐
        │     S-pankki backend     │ ────────────────────> │ Local AI model │  apps/ai/
        │   apps/bank-backend/     │ <──────────────────── │ 6. generate    │
        │                          │  7. answer / insights └────────────────┘
        │  ┌────────────────────┐  │
        │  │ Calculation tools  │  │  apps/bank-backend/calculation/
        │  │ 3. request in      │  │  (inside the backend, not a service)
        │  │   (approved/not)   │  │
        │  │ 5. results out     │  │
        │  └─────────┬──────────┘  │
        └────────────┼─────────────┘
                     │ 4. calculate client data
                     ▼
               ┌───────────┐
               │   Cloud   │  packages/cloud/
               └───────────┘
```

## Flow

| # | From → To | What |
| --- | --- | --- |
| 1 | client → bank-backend | user's command |
| 2 | bank-backend → ai | client command |
| 3 | bank-backend → calculation | calculation request; the backend approves or rejects it |
| 4 | calculation ↔ cloud | calculate over client data |
| 5 | calculation → bank-backend | results, or a response saying why not |
| 6 | ai | generate answer and insights from the command and results |
| 7 | ai → bank-backend → client | answer / insights, then on to the UI |

Read as intended, not as drawn (the diagram leaves these implicit — confirm in
`docs/MASTER_PLAN.md` §Open questions):

- Between 2 and 3 the model asks for a calculation; the backend decides whether it is
  allowed. The model never runs tools or reads client data itself.
- Between 5 and 6 the backend passes the results to the model.
- The diagram labels two hops "7"; both carry the same answer.

## Modules

| Path | Diagram box | Owner |
| --- | --- | --- |
| `apps/frontend/` | UI / Frontend | `TODO` |
| `apps/client/` | Client device / Backend | `TODO` |
| `apps/bank-backend/` | S-pankki backend | `TODO` |
| `apps/bank-backend/calculation/` | Calculation tools | as `apps/bank-backend/` |
| `apps/ai/` | Local AI model | `TODO` |
| `packages/cloud/` | Cloud (client data) | `TODO` |
| `packages/contracts/` | shapes on every edge | `TODO` |

An unowned module is one nobody may change without asking.

## Dependencies

Who may call whom at runtime. Anything not listed is not allowed.

```text
frontend      ──> client
client        ──> bank-backend
bank-backend  ──> ai
bank-backend  ──> calculation     (in-process)
calculation   ──> cloud

every app     ──> contracts       (shapes only, no runtime)
```

- `contracts` and `cloud` depend on nothing in this repo.
- Only `calculation` touches client data. The AI model sees only tool results.
- The frontend never skips the client; the client never skips the bank backend.

## Shared surfaces

Things more than one module or task depends on. Changing one is a coordinated act, not
a local edit (rules: `docs/CONTRIBUTING.md` §Shared surfaces).

| Surface | Touched by |
| --- | --- |
| `packages/contracts/` | every app |
| `packages/cloud/` data shape | calculation tools, seed / mock data |
| calculation tool list (names, inputs, outputs) | bank-backend, calculation, ai |
| `.env.example`, config keys | every app, CI |
| `scripts/`, `.github/` | everyone |
| root docs and `AGENTS.md` | everyone |

## Undecided

`TODO`: stack per app, transport between them, which model and runtime, what "cloud"
is for the demo, where each part runs, what is mocked. Each gets a line here when
decided — and a line in `docs/MASTER_PLAN.md` §Decision log.
