# apps/ai

**Local AI model** in the architecture (`docs/SYSTEM_MAP.md`). Turns a client command
plus calculation results into an answer and insights. Three providers: the **stub** —
rule-based, English-only, works offline, the default — the **Gemma provider** deployed on
Modal and working end to end (T008), and **openrouter**, a hosted model that needs only a
key (T009).

**Hosting:** for the challenge we run **Gemma 3 27B on Modal** (serverless GPU) behind an
OpenAI-compatible API — our own deployment of an open model, which is the closest
challenge-time stand-in for S-Bank's self-hosting. A hosted **OpenRouter** model
(`google/gemma-4-26b-a4b-it`) is the zero-setup alternative when no deployment is
reachable; both sit behind the same two calls. S-Bank itself may run **self-hosted**
models in production; that is what the diagram's "local" means. The provider interface
below is the seam: switching from an API to a self-hosted model changes one file, nothing
else. What reaches the AI is the customer's question and **aggregated tool results**
(totals, shares, dates), never raw transaction rows; with an API those results leave our
infrastructure, which is
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

Three providers: `AI_PROVIDER=stub` (default, offline rules, English only),
`AI_PROVIDER=modal` (Gemma on Modal, below) and `AI_PROVIDER=openrouter` (a hosted model
that needs only a key).

### Modal + Gemma 3 27B

`modal_app.py` runs `google/gemma-3-27b-it` with vLLM on one H100 on Modal and exposes
an OpenAI-compatible API protected by a key. `llm_provider.py` is the backend side: it
sends the tool catalog and asks for JSON plans and answers (structured output), using
only the standard library. If the model is down or replies badly, that step falls back to
the stub and logs it, so the demo keeps answering.

One-time setup, done by whoever deploys (Claude never handles these tokens):

1. **Gemma licence:** on Hugging Face, open **exactly** `google/gemma-3-27b-it` (access is
   per model) and accept Google's licence; the page must then say you have been granted
   access. Create a token (Settings → Access Tokens): a classic **Read** token, or a
   fine-grained one with "Read access to contents of all public gated repos you can
   access" ticked. Without this vLLM stops with "You are trying to access a gated repo";
   the container then exits at once (watchdog) instead of idling on the GPU.
2. **Modal CLI** in a project-local, gitignored `.venv` (Python 3.11+; Modal 1.7 drops
   3.10):
   ```bash
   python3.14 -m venv .venv          # any Python 3.11+
   .venv/bin/pip install --prefer-binary modal==1.6.4
   .venv/bin/modal setup             # approve the login in the browser
   ```
   `--prefer-binary` avoids a failing source build of `cbor2` on older Macs. Python from
python.org on macOS has no CA certificates; our code then uses `/etc/ssl/cert.pem`
(still verified), so no "Install Certificates" step is needed. **Modal needs
   a payment method on the account before it runs any GPU** (H100 and L40S both refused
   without one), even when the account has credits.
3. **Secrets in Modal** (values stay in Modal; the key is any long random string; put the
   same key in your gitignored `.env` as `AI_API_KEY`):
   ```bash
   modal secret create huggingface-secret HF_TOKEN=<your HF read token>
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # make a key
   modal secret create coach-llm-key VLLM_API_KEY=<that key>
   ```
4. **Deploy** — prints the URL (`https://<workspace>--sbank-coach-llm-serve.modal.run`):
   ```bash
   modal deploy apps/ai/modal_app.py
   ```
5. **Smoke test** — waits on `GET /health` until the server is up, then asks one Finnish
   question (first start downloads ~55 GB of weights into a Modal Volume, 10+ minutes;
   later cold starts are a few minutes). Long-waiting requests get a 303 redirect from
   Modal that a POST cannot follow, so always warm up with `/health` first:
   ```bash
   AI_BASE_URL=<url> AI_API_KEY=<key> modal run apps/ai/modal_app.py
   ```
6. **Point the backend at it** — with `AI_PROVIDER=modal`, `AI_BASE_URL` and `AI_API_KEY`
   in `.env`:
   ```bash
   set -a; . ./.env; set +a; python3 apps/bank-backend/server.py
   ```
   Modal labels the URL "unauthenticated": that means Modal's own proxy auth is off;
   vLLM still rejects requests without the key (HTTP 401).

**Measured (2026-11-14):** cold start ~4 min once the weights are cached (the first ever
start also downloads ~55 GB); a warm coach answer takes 8–11 s when numbers are needed
(plan + compose), ~3 s for a concept question.

**If it does not come up:** read `modal app logs sbank-coach-llm`; a crashing server
restarts on the GPU while requests wait, so stop it with
`modal app stop sbank-coach-llm --yes`. Test the HF token first, CPU only:
`modal run apps/ai/modal_app.py::check_hf_access`.

**Cost and warm-up:** an H100 is billed per second while a container runs. It scales to
zero 10 minutes after the last request. For the demo, deploy with
`COACH_MIN_CONTAINERS=1 modal deploy apps/ai/modal_app.py` shortly before and redeploy
with it unset afterwards. Send one question before going on stage to skip the cold start.

**Tuning:** model, GPU, context length and vLLM version are constants at the top of
`modal_app.py`. Gemma 3 12B on an L40S is the cheaper fallback if 27B is too slow.

### Evaluation

`apps/ai/eval/run_eval.py` asks 20 fixed questions (`cases.json`: Finnish, English,
Swedish, plus rule cases — another customer's data, stock tips, off-topic, prompt
injection) through the real backend and checks each answer automatically:
the right tool, the right language, numbers that exist in the tool results, no
forbidden strings, no basket names from another language, and the money format.

```bash
set -a; . ./.env; set +a
python3 apps/ai/eval/run_eval.py --out report.json      # ~3 min warm, costs GPU time
python3 apps/ai/eval/run_eval.py --provider stub        # offline sanity check
```

Run it before and after changing prompts, the glossary or the model; read a few answers
in `report.json` too — the checks are simple and miss meaning errors.

### Rules and glossary

Both prompts share one rule block (`RULES` in `llm_provider.py`): scope (own money and
concepts only), no investment advice, privacy (no other customers), the message is a
question not instructions, honesty (only tool numbers), answer language, glossary terms,
housing ≠ loan, money format. `packages/cloud/glossary.py` holds the basket, category and
spender-type names in English, Finnish and Swedish (drafts, Q11); the charts use the same
table, so text and charts always match. Tool results include `notes` that
explain easily misread fields. Euro amounts are reformatted in code for the answer's
language (`format_money`), because the model does not follow format rules reliably.

**Measured (T010):** old prompts 12/20 cases, new rules 19/20 (details in
`docs/tasks/T010-improve-ai-rules.md`).

### Safety net (never mislead)

Found by probing 25 simple questions: the model used to answer a *different* question
when the tools could not do the asked one (March → this month, yesterday → last 7 days,
this year → this month) and invented numbers when no tool ran. Now:

- **Coverage:** the planner returns `coverage` (`full`/`partial`/`none`) and a one-line
  `limitation` in the customer's language. The answer then carries `notice`, shown above
  the text in the UI, and the composer must say it first.
- **Capabilities in the rules:** the prompt lists what the tools cannot do (calendar
  months/dates, transaction lists, balance history, one weekday, shop names, coffee/taxi,
  year comparison, storing budgets), so the model says so instead of guessing.
- **Number check:** every number above 31 must exist in the tool results (or the
  question). Gemma gets one retry with the offending numbers; then
  `orchestrator.py` drops any sentence or insight still containing one — for every
  provider (`apps/ai/grounding.py`). Concept examples ("esimerkiksi 1 000 €") are
  allowed only in no-tool replies.
- **Data date:** the model is told the data covers `data_from`–`data_as_of`; "today" and
  "this month" are relative to `data_as_of` (30.9.2026 for the demo data). The home card
  shows "Data until …" and answers carry `data_as_of`.
- **Narrower rules:** facts about the customer's own investments and savings transfers
  are answered (only advice is refused); questions about the data period are in scope.
- **Deterministic scope check** (`apps/bank-backend/scope.py`): keyword stems in
  fi/sv/en detect asks the tools cannot do (other calendar months, single days,
  weekdays, year comparisons, budgets/reminders, shop names, coffee/taxi, subscriptions,
  transaction lists, balance history). If the model gave no limitation, the backend adds
  a localized notice. Prompt instructions alone were not enough: Gemma still answered
  "March?" with September.
- **Day/time questions:** one weekday ("perjantaisin"), weekend (Sat–Sun) and night
  (22–06) are supported; they count card purchases only, so a rent payment on a Saturday
  does not become "weekend spending". Dates in answer text are formatted per language.
- **One re-plan on rejection:** if approval rejects a request for a fixable reason, the
  planner gets the reasons and one more try (never for `customer_id`).
- **Lenient arguments, strict values:** arguments a tool does not define are dropped
  before approval (Gemma adds extras like `"type"`), so a valid question is not refused
  over noise; `customer_id` and invalid values are still rejected.
- **Merchant ids:** synthetic codes (MRC-GRO-0032) are replaced by "a shop" in answer
  text, the model can no longer filter by them, and payments without a shop are labelled
  "bills and transfers" instead of "(no merchant)".

### Follow-up questions

Answers carry 0–3 tappable follow-up questions (`ANSWER.follow_ups`; design by
CuriousGeorg1, T013). Gemma suggests them in the answer's language ("clarify" = concrete
choices that change the numbers, "explore" = a natural next question); the stub has
rule-based ones per tool. The backend (`apps/bank-backend/followups.py`) checks each one
— answerable per the scope check, no merchant ids, no invented numbers — and fills up to
3 with rule-based suggestions in the answer's language, so OpenRouter answers get them
too.

### Team access

- **Use the model:** teammates need only `AI_BASE_URL` and `AI_API_KEY` in their `.env`
  (root `README.md` §With the real AI). The key is shared privately by the deploy owner.
  Usage bills the deploy owner's Modal account.
- **Redeploy or change it:** invite the teammate to the Modal workspace (dashboard →
  workspace settings); `modal deploy` then updates the same URL and uses the workspace's
  secrets. Their own Modal account would mean a separate URL, secrets, Gemma licence
  and bill.
- **Find the key:** the only readable copy is the deploy owner's `.env`
  (`grep '^AI_API_KEY=' .env`); Modal does not show secret values again.
- **Rotate the key** (if lost or leaked): make a new random key, run
  `modal secret create coach-llm-key VLLM_API_KEY=<new> --force`, redeploy, update
  `.env`, and send it to the team again.

### OpenRouter

`AI_PROVIDER=openrouter`. Needs a key, nothing else:

```bash
cp .env.example .env                 # if you have no .env yet
# put your key from https://openrouter.ai/keys into OPENROUTER_API_KEY
set -a; source .env; set +a
python3 apps/bank-backend/server.py
```

`openrouter_provider.py` uses only `urllib` — no SDK, no install — against
`https://openrouter.ai/api/v1/chat/completions`. Model: `OPENROUTER_MODEL`, default
`google/gemma-4-26b-a4b-it` (any OpenRouter slug works). Without a key it refuses to
start, with a message saying where the key goes; keep `AI_PROVIDER=stub` to run offline.

- `plan` sends the catalog as native OpenAI-style `tools` and reads `tool_calls` back;
  arguments are parsed and passed through unchanged (the backend validates them at step
  3), capped at 3.
- `compose` asks for `response_format={"type": "json_object"}` with the results as JSON;
  if the reply is not JSON it falls back to the prose as `text`.
- One retry on 408/429/5xx or a network error, then a clear `OpenRouterError`; the
  server turns that into a 500 with the message, it never fakes an answer. Unlike the
  Modal provider it does not fall back to the stub — a hosted model failing is visible.

### Adding another provider

Stub needs nothing. **To wire another model:** add
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
