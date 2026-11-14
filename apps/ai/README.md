# apps/ai

**Local AI model** in the architecture (`docs/SYSTEM_MAP.md`). Turns a client command
plus calculation results into an answer and insights. The default is the stub — a
rule-based, English-only provider that works offline — plus the **Gemma provider**,
deployed on Modal and working end to end (T008).

**Hosting:** for the challenge we run **Gemma 3 27B on Modal** (serverless GPU) behind an
OpenAI-compatible API — our own deployment of an open model, which is the closest
challenge-time stand-in for S-Bank's self-hosting. S-Bank itself may run **self-hosted** models in production; that is what the
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

Two providers: `AI_PROVIDER=stub` (default, offline rules, English only) and
`AI_PROVIDER=modal` (Gemma on Modal, below).

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
