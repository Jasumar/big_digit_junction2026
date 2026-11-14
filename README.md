# Junction 2026 — Project Name TBD

Scaffold for **Junction 2026** (S-pankki). Working idea: a client asks a question or
gives a command, a locally hosted AI model answers with insights, backed by
calculations over the client's own data.

Status: **working MVP** — a mobile-first S-pankki money coach over the full hackathon
transaction data. The AI is Gemma 4 26B-A4B on Modal (or OpenRouter, or an offline stub),
answering in Finnish, Swedish or English. Demo plan: `docs/DEMO.md` (local only for now, gitignored). Choices made while
building it: `docs/tasks/Decisions.md`.

## Structure

```text
apps/frontend/                   UI / Frontend
apps/client/                     Client device / Backend (between UI and bank)
apps/bank-backend/               S-pankki backend: orchestrates every hop
apps/bank-backend/calculation/   calculation tools (inside the backend)
apps/ai/                         Local AI model: answers and insights
packages/contracts/              shapes on every edge
packages/cloud/                  client data the calculations read
docs/                            plan, map, rules, tasks
scripts/check.sh                 repo checks, also run by CI
```

Flow: UI → client → S-pankki backend → local AI model; the backend runs approved
calculations over cloud data and the answer travels back the same way. Full picture
and numbered steps: `docs/SYSTEM_MAP.md`.

Each directory has a README with its intent, setup and conventions.

## Run

```bash
bash scripts/test.sh                       # tests on fixture data, no install
python3 apps/bank-backend/server.py        # http://localhost:8000 (mobile-first UI)
```

No dependencies: Python 3.10+ standard library, plain JS in the browser. With no
database present the server builds a small fixture (6 customers). For the full
dataset (all four CSVs: 5,100 customers, 3.6M transactions, 200 mortgage
applications) download it from `hackjunction/Junction-2026-S-pankki` and build:

```bash
python3 packages/cloud/fetch_data.py   # ~364 MB into packages/cloud/data/raw/, gitignored
python3 packages/cloud/seed.py --full  # ~70 s, ~500 MB database, gitignored
```

The raw data is too big for git (GitHub's limit is 100 MB per file), so every clone
fetches it once with the commands above.

### With the real AI (Gemma on Modal, or OpenRouter)

Two ways to run a real model; pick one. The prompt and answer paths are the same either
way — only which provider `AI_PROVIDER` names changes.

#### Modal + Gemma 4 26B-A4B (our deployment)

The model runs on our Modal deployment; you only need its URL and key, not a Modal or
Hugging Face account.

1. `cp .env.example .env`, then set `AI_PROVIDER=modal`, `AI_BASE_URL` (the deployment
   URL) and `AI_API_KEY`. **Ask the deploy owner for the key in a private message or
   password manager — never in git, issues or shared channels.**
2. Start with the env loaded:
   ```bash
   set -a; . ./.env; set +a; python3 apps/bank-backend/server.py
   ```
3. The first question after ~10 idle minutes waits for a cold start (~4 min); later
   answers take ~10 s. Every question bills GPU time to the deploy owner's Modal account.

Deploying or changing the model: `apps/ai/README.md` §Modal.

#### OpenRouter (no deployment of ours)

Set `AI_PROVIDER=openrouter` and put a key from https://openrouter.ai/keys into
`OPENROUTER_API_KEY`; `OPENROUTER_MODEL` defaults to `google/gemma-4-26b-a4b-it` (any
OpenRouter slug works). Nothing to deploy, no Modal account; each question bills the key
owner's OpenRouter account.

    set -a; . ./.env; set +a; AI_PROVIDER=openrouter python3 apps/bank-backend/server.py

Without a key the server refuses to start and says where the key goes. Either way the app
still works on the offline, English-only stub.

Env: `PORT`, `HOST`, `AI_PROVIDER` (`stub` | `modal` | `openrouter`), `AI_BASE_URL`, `AI_API_KEY`,
`AI_MODEL`, `AI_TIMEOUT`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `SPANKKI_DB`,
`REQUIRE_FULL_DATA` — see `.env.example`. On the sample data the server prints a warning
and the UI shows a
banner; for the demo start it with `REQUIRE_FULL_DATA=1` so it refuses to run without the
full dataset. `GET /api/health` reports which data is loaded.

## Deploy (Docker, Aiven Runtime)

The root `Dockerfile` builds one container that serves the API and the UI on port 8080.
The image contains the full database (it downloads the CSVs and seeds during the build);
the AI stays on an existing API (Modal or OpenRouter), so the container needs no GPU.

```bash
docker build -t spankki-coach .                           # full data, ~0.5 GB database
docker build -t spankki-coach --build-arg DATA=fixture .  # 6-customer sample, fast
docker run --rm -p 8080:8080 --env-file .env spankki-coach   # http://localhost:8080
```

Do not set `HOST` or `PORT` in the `.env` you pass to the container; the image sets
`HOST=0.0.0.0` and `PORT=8080`.

**Aiven Runtime** (https://aiven.io/docs/products/runtime) builds from this GitHub repo:

1. Connect the GitHub account to the Aiven organization (organization admin).
2. Create an application service: select the repository and branch `main`; Aiven finds
   `Dockerfile` at the root and reads port 8080 from `EXPOSE`. CLI equivalent:
   `-c application.source.build_path=. -c application.source.containerfile_path=Dockerfile`
   `-c 'application.ports=[{"name":"http","port":8080,"protocol":"HTTP"}]'`.
3. Environment variables: `AI_PROVIDER` (`modal` or `openrouter`) and its settings; store
   `AI_API_KEY` / `OPENROUTER_API_KEY` as **secrets**, never in the repo. Add
   `REQUIRE_FULL_DATA=1` so a sample-data image refuses to start.
4. Aiven gives an HTTPS URL and forwards it to port 8080. Check `GET /api/health`.
5. A push does not redeploy; use "Actions > Deploy latest commit".

The app has no login (Decisions #16): anyone with the URL can query the demo customers
and spend the AI key's budget.

## Start

```bash
git clone <repo-url> && cd junction2026
cp .env.example .env                      # local config, never committed
cp preferences.example.md preferences.md  # optional, for your agent
bash scripts/check.sh                     # repo checks
```

Read: `docs/CHALLENGE.md` for the brief and judging criteria, `docs/CONTRIBUTING.md` for the workflow, `docs/MASTER_PLAN.md` for what we are
building, `docs/SYSTEM_MAP.md` for who owns what. Agents: `AGENTS.md` first.

## Conventions

- One task = one file in `docs/tasks/` = one branch = one worktree in `.worktrees/`.
- Branch names: `task/t001-<slug>`.
- Merge small and often; a branch that lives a day is too big.
- Anything more than one part of the system depends on is a **shared surface**. Do not
  change one silently — see `docs/CONTRIBUTING.md` §Shared surfaces.
- No secrets, no `.env`, no local config in git.

## Open

MVP scope, stack, which model, where it runs, what is mocked. See
`docs/MASTER_PLAN.md` §Open questions.
