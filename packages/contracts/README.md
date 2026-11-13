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
| frontend ↔ client | — | UI action, rendered answer | `TODO` |
| client ↔ bank-backend | 1, 7 | `Command`, `Answer` (text + insights) | `TODO` |
| bank-backend ↔ ai | 2, 7 | command to model, model answer / insights, calculation request from the model | `TODO` |
| bank-backend ↔ calculation | 3, 5 | `CalculationRequest`, `CalculationResult`, rejection | `TODO` |
| calculation ↔ cloud | 4 | client data shape — owned by `packages/cloud/` | `TODO` |

## Changing it

Only with authority (see `docs/CONTRIBUTING.md` §Shared surfaces). Change once, update
every consumer in the same change, tell the team.

## Setup

`TODO`: the mechanism — typed module, JSON Schema, spec file — and its commands.
