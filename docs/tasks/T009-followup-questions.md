# T009 — AI-suggested follow-up questions

**Owner:** `TODO` **Status:** review
**Branch:** `feat/questions`

## Goal

An answer can carry 0-3 tappable follow-up suggestions. Tapping one sends its text as
the next command, exactly like typing it — no new UI flow, no new endpoint. Covers the
brief's "ask what the customer wants to save on" kind of question (e.g. after savings
ideas, offer the top categories as one-tap choices) and open-ended next questions
(e.g. "How could I save more?" after a spending breakdown).

## Allowed files

```text
packages/contracts/schemas.py        (ANSWER.follow_ups — additive, optional field)
packages/contracts/README.md
apps/ai/stub_provider.py
apps/ai/llm_provider.py
apps/ai/README.md
apps/bank-backend/orchestrator.py
apps/bank-backend/tests/test_flow.py
apps/bank-backend/tests/test_llm_provider.py
apps/frontend/app.js
apps/frontend/styles.css
apps/frontend/README.md
docs/MASTER_PLAN.md
docs/tasks/T009-followup-questions.md
```

**Shared surfaces touched:** `packages/contracts/` (`ANSWER` gains an optional
`follow_ups` array; nothing existing changes shape or becomes required, so every
current producer/consumer keeps validating as-is). Authorized directly by the project
owner in session; every consumer doc updated in the same change (contracts, ai,
frontend READMEs above).

**Deliberately not touched:** `apps/bank-backend/calculation/tools.py` — a second
task is actively adding tools/capabilities there. This feature needed no new tool or
argument: every follow-up prompt is answerable by an existing tool (`simulate_change`
for a what-if, the existing intents for "how could I save more", etc). When new tools
land, give them `_followups_<tool>` (stub) / let the model suggest them (LLM prompt
already generic) — no contract change needed for that.

## Depends on

- Needs merged first: none
- Blocks: none

## Acceptance criteria

- [x] `ANSWER` accepts an optional `follow_ups: [{kind, label, prompt}]`, ≤3 items;
      existing answers without it still validate.
- [x] Stub provider proposes follow-ups for `spending_breakdown`, `spender_profile`,
      `safe_to_spend` (when tight), `savings_opportunities`, `peer_comparison`,
      `simulate_change`, using only existing tool capabilities.
- [x] LLM provider's compose schema/prompt can propose the same shape; malformed or
      missing `follow_ups` from the model never breaks the answer (filtered, default
      `[]`), consistent with existing insights handling.
- [x] Orchestrator passes `follow_ups` through untouched from the provider.
- [x] Frontend renders them as tappable chips under the insights; tapping sends the
      `prompt` through the normal `ask()` flow and disables that button.
- [x] Consumers updated: `packages/contracts/README.md`, `apps/ai/README.md`,
      `apps/frontend/README.md`.

## Verify

```bash
bash scripts/check.sh
bash scripts/test.sh
```

## Notes

- Kept `follow_ups` flat (no separate "question" + "options" nesting): each suggestion
  is independently clickable, matching the existing fixed `SUGGESTIONS` chip row the
  UI already had — same component, personalized per answer instead of static.
- No history wiring changes needed: a tapped follow-up's `prompt` becomes a normal
  user message and is self-explanatory on its own (e.g. "What if I cut Restaurants by
  20%?"), so the model does not need to recall exactly how it phrased the original
  question.
- Real personalization of *how* a cut is computed (e.g. "protect my hobbies budget")
  still routes through `simulate_change`/`savings_opportunities` as they exist today;
  it does not yet change the calculation itself. That would need new tool arguments,
  intentionally left to whoever is extending `calculation/tools.py` next.
