# packages/db

Schema, migrations, and seed data. **Status: not scaffolded** — stack not chosen yet.

Owner: `TODO` (see `docs/SYSTEM_MAP.md` §Module ownership)

## Responsibility

- Own the schema and every migration.
- Provide a client/interface the backend uses; keep connection setup in one place.
- Provide seed data so a fresh checkout has something to demo.

## Rules

1. **One migration per change.** Never edit a migration that is already on `main`.
2. **Announce schema changes** in the task file and the channel — another task may be
   reading or writing the same tables.
3. **Clean checkout must work.** One documented command creates and seeds a database
   from nothing; run it yourself before merging.
4. **Destructive changes** (dropping columns, rewriting data) need a second pair of
   eyes even at hackathon speed.

## Depends on

Nothing in this repo. Apps depend on this, never the reverse.

## Setup

`TODO`: create / migrate / seed / reset commands — added when the stack is chosen, and
mirrored in the root `README.md` §Commands.

## Conventions

`TODO`: naming, how to add a table, where seeds live, how local data is reset.
Local database files are gitignored (`*.db`, `*.sqlite`, `data/`).
