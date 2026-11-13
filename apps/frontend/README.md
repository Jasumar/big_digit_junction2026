# apps/frontend

**UI / Frontend** in the architecture (`docs/SYSTEM_MAP.md`). What the user sees and
does: type a question or command, see the answer and insights. **Not scaffolded** —
stack undecided.

Owner: `TODO` (`docs/SYSTEM_MAP.md`)

- Talks to: `apps/client/` only (two-way). Never calls the S-pankki backend, the AI
  model or the cloud directly.
- Depends on: `packages/contracts/` (UI ↔ client shapes).
- Owns: screens, styling, UI state, rendering answers and insights.
- Not its job: auth, session handling, server logic, or its own copy of shared shapes.

## Setup

`TODO`: install, dev, build, test — mirrored in `README.md`.

## Conventions

`TODO`: layout, state approach, how to add a screen.
