# apps/bank-backend

**S-pankki backend** in the architecture (`docs/SYSTEM_MAP.md`). The orchestrator: every
hop in the flow goes through it. **Not scaffolded** — stack and transport undecided.

Owner: `TODO` (`docs/SYSTEM_MAP.md`)

| Step | Direction | What |
| --- | --- | --- |
| 1 | client → bank | receive the user's command |
| 2 | bank → AI | forward the command to the local AI model |
| 3 | bank → calculation | send a calculation request — **approved or rejected here** |
| 5 | calculation → bank | calculation results (or a rejection / error response) |
| 6–7 | AI → bank | answer / insights from the model |
| 7 | bank → client | answer / insights back to the device |

- Contains: `calculation/` — the calculation tools. They live **inside** this app, not
  as a separate service (the diagram draws them apart; the code does not).
- Depends on: `packages/contracts/`, `packages/cloud/` (via `calculation/` only).
- Owns: request handling, the approval policy for calculation requests, calling the AI
  model, shaping the final answer.
- Not its job: the model itself (`apps/ai/`), the stored-data shape (`packages/cloud/`).

## Setup

`TODO`: install, run, build, test — mirrored in `README.md`.

## Conventions

`TODO`: how a request flows through this app, how approval is decided, how errors are
shaped.
