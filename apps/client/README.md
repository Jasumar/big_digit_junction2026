# apps/client

**Client device / Backend** in the architecture (`docs/SYSTEM_MAP.md`). The layer on
the user's device between the UI and the S-pankki backend. **Built as a thin JS module**
(`client.js`) the frontend imports from `/client/client.js`; not a separate process
(`docs/tasks/Decisions.md` #3).

Owner: `TODO` (`docs/SYSTEM_MAP.md`)

- Talks to: `apps/frontend/` (two-way) and `apps/bank-backend/`.
- Flow steps: **1** sends the user's command to the S-pankki backend; receives **7**
  (answer / insights) back.
- Depends on: `packages/contracts/` (UI ↔ client and client ↔ bank shapes).
- Owns: the user's session, calling the bank API, any on-device caching.
- Not its job: calculations, AI, or holding client financial data beyond what the
  answer needs.

## Setup

Nothing to install; served by the backend.

## Conventions

`createClient().command(customerId, text, history)` → POST `/api/command`;
`overview(id)`, `customers()`. Failures throw `CoachError` with a user-readable message
(timeout, backend down, backend error).
