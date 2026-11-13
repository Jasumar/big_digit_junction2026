# apps/backend

Server-side logic. **Not scaffolded** — stack and transport undecided.

Owner: `TODO` (`docs/SYSTEM_MAP.md`)

- Depends on: `packages/contracts/`, and `packages/db/` if data is stored.
- Owns: business logic, validation at the boundary, external service calls.
- Not its job: owning the stored-data shape, or shapes the contract does not describe.

## Setup

`TODO`: install, run, build, test — mirrored in `README.md`.

## Conventions

`TODO`: how a request flows through this app, where external calls live, how errors
are shaped.
