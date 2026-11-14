# T009 — OpenRouter as a second real provider

**Owner:** `TODO` **Status:** review
**Branch:** `task/t009-openrouter-provider`

## Goal

The coach can also answer with an OpenRouter-hosted model, selected by
`AI_PROVIDER=openrouter`, next to the existing stub and the Gemma-on-Modal provider.
Reaching a real model needs only an API key — no deployment, no GPU account — and choosing
one provider never breaks the others.

## Allowed files

```text
apps/ai/openrouter_provider.py          (new)
apps/ai/provider.py                     (register the name)
apps/bank-backend/server.py             (report a provider that refuses to start)
apps/bank-backend/tests/test_flow.py    (provider tests)
apps/ai/README.md, README.md, .env.example, docs/   (setup keys and notes)
```

**Shared surfaces touched:** `.env.example` (`OPENROUTER_*` keys), root `README.md`,
`apps/ai/README.md`, `apps/ai/provider.py`, `docs/MASTER_PLAN.md` — agreed with the repo
owner on 2026-11-14; the code using each key lands in the same change.

## Depends on

- Needs merged first: T008 (Modal provider, merged in PR #4) — T009 must not remove it
- Blocks: demo polish (M3)

## Acceptance criteria

- [x] `AI_PROVIDER=openrouter` plans with native OpenAI-style `tools` / `tool_calls` and
      composes with `response_format={"type": "json_object"}` (tests with a fake transport).
- [x] A missing key refuses to start with a message naming `OPENROUTER_API_KEY`; an API
      error is a clear error, never an invented answer.
- [x] `stub`, `modal` and `openrouter` all resolve through `get_provider`, and a missing
      key or URL for one does not stop the others (tests: `TestProviderSelection`).
- [x] The server exits with "refusing to start: …" instead of a traceback when the chosen
      provider cannot be built.
- [x] Live: `GET /api/health` reports `"provider": "openrouter"` and a real question
      answers over the full dataset (2026-11-14, 5 100 customers, model
      `google/gemma-4-26b-a4b-it`).

## Verify

```bash
bash scripts/check.sh
bash scripts/test.sh
set -a; source .env; set +a
AI_PROVIDER=openrouter python3 apps/bank-backend/server.py
curl -s http://localhost:8000/api/health | head -c 200
```

## Notes

`openrouter_provider.py` is deliberately separate from `llm_provider.py` rather than a
configuration of it: `llm_provider` asks for vLLM `json_schema` structured output on both
calls, while OpenRouter's tool calling is used for `plan`. Both stay behind the same
`Provider` interface from `provider.py`.

Difference to decide later: the Modal provider falls back to the stub on a failed call
(Decisions #26), the OpenRouter provider raises instead, because a hosted model failing
should be visible rather than silently answered by rules. Folding both onto one policy is
a follow-up, not part of this task.
