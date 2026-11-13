# packages/contracts

The API contract — **the single source of truth** for what the frontend sends and the
backend returns. **Status: not scaffolded** — the mechanism is decided with the stack.

Owner: `TODO` (see `docs/SYSTEM_MAP.md` §Module ownership)

## Responsibility

- Define requests, responses, and error shapes for every endpoint.
- Provide those definitions to both apps, so neither has a private copy.

Not this app's job: runtime behaviour, database queries, or UI concerns. If it needs a
framework to run, it probably belongs in an app.

## Rules

1. **Change here first.** The contract changes in its own commit, before consumers.
2. **Update every consumer in the same change.** A merged contract change with a
   broken consumer is a broken `main`.
3. **Announce it.** Contract changes break work in flight; say so in the channel.
4. **Never hand-copy types** across the app boundary — import from this package.

## Depends on

Nothing in this repo. It must stay dependency-light and free of app imports.

## Shape of a change

`TODO`: once decided, document the workflow here — e.g. edit the schema/spec, run the
generation command, commit both the source and the generated output (or state
explicitly that output is generated at build time and gitignored).

## Setup

`TODO`: generation/lint/test commands for the contract itself.
