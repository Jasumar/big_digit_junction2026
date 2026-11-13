# packages/db

State that outlives a process. **Not scaffolded** — it is not yet decided whether we
store anything locally, remotely, or at all; the directory may end up thin or unused.
Fold it into another module rather than forcing a database in.

Owner: `TODO` (`docs/SYSTEM_MAP.md`)

- Depends on: nothing in this repo.
- Owns: the shape of stored data, how it is accessed, and seeds for a fresh start.
- Not its job: business logic, or shapes the contract does not describe.

## Rules

Shared surface: no silent changes. One change at a time, say so in the task file and to
the team, and leave one documented command that gets a working store from nothing.

## Setup

`TODO`: create / seed / reset, once it is decided what "the store" is.
