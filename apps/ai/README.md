# apps/ai

**Local AI model** in the architecture (`docs/SYSTEM_MAP.md`). Turns a client command
plus calculation results into an answer and insights. The default is an offline,
English-only rule-based stub; an OpenAI-compatible hosted provider is also available.

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

Stub needs nothing (`AI_PROVIDER=stub`, the default). To use a hosted model, set:

```sh
export AI_PROVIDER=llm
export LLM_BASE_URL="<provider OpenAI-compatible base URL>"
export LLM_MODEL="<provider model ID>"
export LLM_API_KEY="<provider API key>"
export LLM_TIMEOUT_S=15
python3 apps/bank-backend/server.py
```

The base URL must end before `/chat/completions`. Select a model supporting Chat
Completions, function calling, and `response_format: json_object`:

| Provider | Base URL and model |
| --- | --- |
| Google AI Studio / Gemini | Use the OpenAI-compatible base URL from [Google's documentation](https://ai.google.dev/gemini-api/docs/openai) and a supported Gemini model ID. |
| Verda | Use your Verda OpenAI-compatible inference base URL and supported model ID. |
| Claude | Use Anthropic's OpenAI-compatible base URL and model ID from [its documentation](https://platform.claude.com/docs/en/api/openai-sdk). Its compatibility endpoint rejects `json_object`, so **compose is not compatible with this implementation**; it will fall back to the stub. A compatible proxy or a separately implemented native provider would be needed. |

Use the API key for the chosen endpoint, not a model name or a browser subscription.
Configuration is read from the environment, not directly from `.env`; do not commit
keys. Each API call has a 15-second default timeout. Request failures and invalid model
responses are logged without the question, result, or key, and the stub answers with
provider `stub (fallback)`. Malformed composition JSON instead returns a short safe
message and is logged. The fallback stub understands English only. A tool-based answer
can require two API calls; the client currently times out after 30 seconds, so set
`LLM_TIMEOUT_S` lower if slow requests should have time to fall back within that limit.

The model sees the question, conversation history and tool results, so these may still
contain sensitive information even without raw database rows or `customer_id` fields.
Use synthetic data for this demo; review provider data-handling terms before real
banking data. The backend validates proposed tools and builds charts itself. The prompt
(`prompt.py`) tells the model to take every number from tool results, and
`grounding.py` checks the answer: amounts and percentages not found in the results
trigger one retry naming them, then a templated answer from the stub's `compose`.
Dates, small integers (0-12) and years are not checked, and a matching number can
still be misattributed, so test model output before relying on it.

## Language

Most S-Bank customers write Finnish; Finland is bilingual, so Swedish matters too.
Approach (`docs/tasks/Decisions.md` #24):

- **One model, answering in the user's language.** No separate translation model:
  translating English output doubles latency and cost, adds a failure point and makes
  the coaching tone stiff. Large API models write good Finnish and Swedish.
- **The model writes words; locale formatting is planned.** Today the model may format
  numbers in its text; charts are built by the backend. Verify numerical accuracy.
- **Glossary in the prompt** so the three baskets and key terms are always named the
  same way. Draft, to be confirmed by a Finnish speaker (`docs/MASTER_PLAN.md` Q11):
  pakolliset säännölliset menot · pakolliset yllättävät menot · arjen pikkukulut.
- **Self-hosted later:** smaller open models are weaker in Finnish than large API
  models — test Finnish quality first. Finnish-trained open models exist (e.g. Poro,
  Viking from Silo AI / TurkuNLP; check their current state). Only add a translation
  step if the chosen model is clearly worse in Finnish than English.
- **The stub is English-only**: Finnish questions fall through to the help text. Test
  the selected model's Finnish and Swedish quality before the demo.

## Conventions

`stub_provider.py`: intents in `plan`, wording in `_<tool>` methods of `compose`.
