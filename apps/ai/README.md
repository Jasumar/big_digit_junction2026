# apps/ai

**Local AI model** in the architecture (`docs/SYSTEM_MAP.md`). Turns a client command
plus calculation results into an answer and insights. **Not scaffolded** — model,
runtime and hosting undecided.

"Local" means the model runs on infrastructure we control, so client data is not sent
to a third-party model API. What that means for the demo is an open question in
`docs/MASTER_PLAN.md`.

Owner: `TODO` (`docs/SYSTEM_MAP.md`)

- Talks to: `apps/bank-backend/` only (two-way).
- Flow steps: receives **2** (client command); does **6** (generate insights and
  answer); returns **7** to the backend.
- Depends on: `packages/contracts/` (bank ↔ AI shapes, calculation tool descriptions).
- Owns: model choice, prompts, how it asks for calculations, output format.
- Not its job: reading client data directly, executing calculations, or approving its
  own calculation requests.

## Setup

`TODO`: how to get the model and runtime locally, how to start it, hardware needed.

## Conventions

`TODO`: where prompts live, how tool calls are expressed, how to evaluate output.
