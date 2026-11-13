# packages/cloud

**Cloud** in the architecture (`docs/SYSTEM_MAP.md`). Where client financial data
lives. **Not scaffolded** — for the hackathon this is likely a mock dataset or a
stand-in for S-pankki's real systems; what it really is, and where it runs, is
undecided.

Owner: `TODO` (`docs/SYSTEM_MAP.md`)

- Flow step: **4** — the calculation tools read client data from here.
- Accessed by: `apps/bank-backend/calculation/` only. Nothing else reads it.
- Depends on: nothing in this repo.
- Owns: the shape of client data, how it is accessed, seed / mock data for a fresh
  start.
- Not its job: calculations, business logic, or shapes the contract does not describe.

## Rules

Shared surface: no silent changes to the data shape. One change at a time, say so in
the task file and to the team, and leave one documented command that gets a working
store (or mock) from nothing.

## Setup

`TODO`: create / seed / reset, once it is decided what "the cloud" is for the demo.
