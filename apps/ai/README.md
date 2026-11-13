# apps/ai

**Local AI model** in the architecture (`docs/SYSTEM_MAP.md`). Turns a client command
plus calculation results into an answer and insights. **Stub only** — a rule-based provider
that works offline. Model, runtime and API are still to be chosen.

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

Stub needs nothing (`AI_PROVIDER=stub`, the default). **To wire a real model:** add
`apps/ai/<name>_provider.py` with a `Provider` class (`name`, `plan`, `compose`, see
`provider.py`) and register it in `get_provider`. `plan` receives the tool catalog in
JSON-schema form, so provider tool-calling maps onto it directly; return
`{"requests": [{"tool", "args"}]}` or `{"reply": ...}`. `compose` gets the results and
returns `{"text", "insights": [{title, body, kind}]}`. The backend validates every
request (step 3) and builds charts itself.

## Conventions

`stub_provider.py`: intents in `plan`, wording in `_<tool>` methods of `compose`.
