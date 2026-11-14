# packages/contracts

The shapes the parts of the system agree on, one set per edge in the architecture.
Source of truth; a shared surface.

Owner: `TODO` (`docs/SYSTEM_MAP.md`)

- Depends on: nothing in this repo.
- Owns: request, response and error shapes for every edge below, and whatever makes
  them usable by both sides.
- Not its job: runtime behaviour, storage, UI.

## Edges

| Edge | Steps | Shapes | Status |
| --- | --- | --- | --- |
| frontend ↔ client | — | JS calls in `client.js`; answer rendered as-is | v0 |
| client ↔ bank-backend | 1, 7 | `COMMAND`, `ANSWER` (text, insights, visuals, trace) | v0 |
| bank-backend ↔ ai | 2, 6 | `PLAN` (requests or reply), then results in, `{text, insights}` out | v0 |
| bank-backend ↔ calculation | 3, 5 | `CALCULATION_REQUEST`, `CALCULATION_RESULT` (ok / rejected / failed) | v0 |
| calculation ↔ cloud | 4 | SQL over `packages/cloud/` tables | v0 |

## Changing it

Only with authority (see `docs/CONTRIBUTING.md` §Shared surfaces). Change once, update
every consumer in the same change, tell the team.

## Setup

`schemas.py`: JSON-Schema-style dicts (`COMMAND`, `PLAN`, `CALCULATION_REQUEST`,
`CALCULATION_RESULT`, `ANSWER`), `EXAMPLES`, and a small `validate()`; no dependencies.
Tests check every example against its schema. The frontend consumes the same shapes
as JSON.
