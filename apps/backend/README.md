# apps/backend

The API and server-side logic. **Status: not scaffolded** — stack not chosen yet.

Owner: `TODO` (see `docs/SYSTEM_MAP.md` §Module ownership)

## Responsibility

- Expose the HTTP API described by `packages/contracts/`.
- Business logic, validation at the boundary, and calls to external services.
- Access the database only through `packages/db/`.

Not this app's job: owning the schema (that is `packages/db/`), formatting for the UI,
or inventing response shapes the contract does not describe.

## Dependency rules

- May import: `packages/contracts`, `packages/db`.
- Must not import: `apps/frontend`.

## Setup

`TODO`: install, dev server, build, and test commands — added when the stack is
chosen, and mirrored in the root `README.md` §Commands.

## Architecture

`TODO`: how a request flows through this app (routing → handler → service → db),
where external services are called, how errors are mapped to contract error shapes.

## Conventions

`TODO`: where routes live, how to add an endpoint, validation approach, logging.

## Environment

Reads env vars from the repo-root `.env` (gitignored). Keys are declared in
`.env.example`. `TODO`: which keys this app needs, and which are required vs optional.
