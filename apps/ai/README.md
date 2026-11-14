# apps/ai

**Local AI model** in the architecture (`docs/SYSTEM_MAP.md`). Turns a client command
plus calculation results into an answer and insights. **Stub only** so far — a
rule-based, English-only provider that works offline.

**Hosting:** for the challenge we use a **hosted AI API** (provider still to be
chosen). S-Bank itself may run **self-hosted** models in production; that is what the
diagram's "local" means. The provider interface below is the seam: switching from an API
to a self-hosted model changes one file, nothing else. What reaches the AI is the
customer's question and **aggregated tool results** (totals, shares, dates), never raw
transaction rows; with an API those results leave our infrastructure, which is
acceptable here because the data is synthetic.

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

## Language

Most S-Bank customers write Finnish; Finland is bilingual, so Swedish matters too.
Approach (`docs/tasks/Decisions.md` #24):

- **One model, answering in the user's language.** No separate translation model:
  translating English output doubles latency and cost, adds a failure point and makes
  the coaching tone stiff. Large API models write good Finnish and Swedish.
- **The model writes words; code formats numbers and dates.** Amounts arrive from the
  tools as numbers and are formatted for the locale (`1 234,50 €`, `14.11.2026`), so
  translation can never garble a figure.
- **Glossary in the prompt** so the three baskets and key terms are always named the
  same way. Draft, to be confirmed by a Finnish speaker (`docs/MASTER_PLAN.md` Q11):
  pakolliset säännölliset menot · pakolliset yllättävät menot · arjen pikkukulut.
- **Self-hosted later:** smaller open models are weaker in Finnish than large API
  models — test Finnish quality first. Finnish-trained open models exist (e.g. Poro,
  Viking from Silo AI / TurkuNLP; check their current state). Only add a translation
  step if the chosen model is clearly worse in Finnish than English.
- **The stub is English-only**: Finnish questions fall through to the help text. A real
  provider fixes that.

## Conventions

`stub_provider.py`: intents in `plan`, wording in `_<tool>` methods of `compose`.
