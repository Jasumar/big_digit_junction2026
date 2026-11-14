# T008 — Gemma on Modal as the AI provider

**Owner:** `TODO` **Status:** review
**Branch:** `task/t008-local-ai-modal`

## Goal

The coach answers with a real model: Gemma 3 27B served by vLLM on Modal, called by the
backend through the existing `plan` / `compose` interface, in the customer's language.

## Allowed files

```text
apps/ai/**
apps/bank-backend/tests/test_llm_provider.py
apps/client/client.js          (timeout only)
.env.example, docs/            (setup keys and notes)
```

**Shared surfaces touched:** `.env.example` (AI_* keys), docs — agreed with the team.

## Depends on

- Needs merged first: T007 (merged in PR #3)
- Blocks: demo polish (M3)

## Acceptance criteria

- [x] `modal_app.py` defines the vLLM server (checked by importing it with Modal 1.6.4).
- [x] `AI_PROVIDER=modal` sends the tool catalog, gets JSON plans/answers, and falls back
      to the stub when the server is down or replies badly (tests with a fake server).
- [x] Model requests still go through approval; the model never picks the customer.
- [x] Deployed on Modal; `modal run apps/ai/modal_app.py` answers in Finnish
      (2026-11-14: "Budjetointi on prosessi, jossa suunnitellaan…").
- [x] Brief questions answered end to end through the backend in Finnish and English
      (where did my money go, spender type, safe to spend, what-if −20 % dining out, how to
      save, a concept question), and in the browser UI ("Paljonko voin turvallisesti
      kuluttaa tällä viikolla?" answered in Finnish, no stub fallback).
- [x] Measured: cold start ~4 min (weights cached; first ever start also downloads ~55 GB);
      warm answers 8–11 s with numbers (two model calls), ~3 s for a concept question;
      raw model reply 3.6 s.

## Verify

```bash
bash scripts/check.sh
bash scripts/test.sh
modal deploy apps/ai/modal_app.py                                   # needs login + secrets
AI_BASE_URL=<url> AI_API_KEY=<key> modal run apps/ai/modal_app.py
```

## Notes

Deploy problems hit and fixed: Modal needs a payment method for any GPU; the HF token had
no access until the licence was accepted on the exact model page (check with
`modal run apps/ai/modal_app.py::check_hf_access`, CPU only); vLLM 0.31's FlashInfer
sampler needs `nvcc`, so it is turned off (`VLLM_USE_FLASHINFER_SAMPLER=0`); a crashing
server crash-loops on the GPU while requests wait, so stop the app
(`modal app stop sbank-coach-llm --yes`) if it does not come up.

Seen in answers: English archetype labels ("Squeezed by essentials") inside Finnish text,
Housing called "asuntolaina" (mortgage), and "€" placement in English. Tool data and the
prompt can fix these later.

Deployment needs a Hugging Face token with Gemma access and a Modal login; both are done
by a person, not an agent. Choices: `docs/tasks/Decisions.md` #25–28.
