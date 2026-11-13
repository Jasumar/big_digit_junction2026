# apps/frontend

The user-facing application. **Status: not scaffolded** — stack not chosen yet.

Owner: `TODO` (see `docs/SYSTEM_MAP.md` §Module ownership)

## Responsibility

- Render the demo experience.
- Talk to the backend only through the shared contract in `packages/contracts/`.
- Own its own components, styling, and state management.

Not this app's job: business logic that the demo would show differently if it were
server-side, direct database access, or defining its own API shapes.

## Dependency rules

- May import: `packages/contracts`.
- Must not import: `apps/backend`, `packages/db`.

## Setup

`TODO`: install, dev server, build, and test commands — added when the stack is
chosen, and mirrored in the root `README.md` §Commands.

## Architecture

`TODO`: directory layout inside this app, state management approach, data-fetching
pattern, styling approach. Keep it to what a newcomer needs in the first ten minutes.

## Conventions

`TODO`: file naming, component structure, where API calls live, how to add a screen.

## Environment

Reads env vars from the repo-root `.env` (gitignored). Keys are declared in
`.env.example`. `TODO`: which keys this app needs.
