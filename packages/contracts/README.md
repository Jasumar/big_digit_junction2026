# packages/contracts

The shapes the parts of the system agree on. Source of truth; a shared surface.

Owner: `TODO` (`docs/SYSTEM_MAP.md`)

- Depends on: nothing in this repo.
- Owns: request, response and error shapes, and whatever makes them usable by both
  sides.
- Not its job: runtime behaviour, storage, UI.

## Changing it

Only with authority (see `docs/CONTRIBUTING.md` §Shared surfaces). Change once, update
every consumer in the same change, tell the team.

## Setup

`TODO`: the mechanism — typed module, generated client, spec file — and its commands.
