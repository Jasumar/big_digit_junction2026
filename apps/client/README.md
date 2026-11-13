# apps/client

**Client device / Backend** in the architecture (`docs/SYSTEM_MAP.md`). The layer on
the user's device between the UI and the S-pankki backend. **Not scaffolded** — it is
not decided whether this is a separate process, a local server, or simply the data
layer inside the frontend app. If it ends up thin, fold it into `apps/frontend/` and
update `docs/SYSTEM_MAP.md`.

Owner: `TODO` (`docs/SYSTEM_MAP.md`)

- Talks to: `apps/frontend/` (two-way) and `apps/bank-backend/`.
- Flow steps: **1** sends the user's command to the S-pankki backend; receives **7**
  (answer / insights) back.
- Depends on: `packages/contracts/` (UI ↔ client and client ↔ bank shapes).
- Owns: the user's session, calling the bank API, any on-device caching.
- Not its job: calculations, AI, or holding client financial data beyond what the
  answer needs.

## Setup

`TODO`: install, run, build, test — mirrored in `README.md`.

## Conventions

`TODO`: how a command becomes a request, how errors reach the UI.
