# T013 — Follow-up questions (ported from feat/t009)

**Owner:** `TODO` (feature design and first version: CuriousGeorg1) **Status:** merged
**Branch:** `task/t013-follow-up-questions`

## Goal

An answer carries 0–3 tappable follow-up questions. Tapping one sends its prompt as the
next question, exactly like typing it. "Clarify" buttons offer concrete choices that
change the numbers (e.g. which category to save on); "explore" buttons offer a natural
next question.

## Where it comes from

CuriousGeorg1 built the feature on branch `feat/t009` (one commit, "t009"), on top of
`main` as it was after T008. Since then `main` gained the T010 rules and safety net,
OpenRouter (T009), life signals (T011) and the UI language switch (T012). Merging that
branch directly would have overwritten newer code (the orchestrator's answer fields,
the rewritten prompts) and added a second `T009-…` task file. So only the follow-up
questions were ported by hand onto current `main`; `feat/t009` itself is untouched.

Kept from feat/t009: the `FOLLOW_UP` contract and `ANSWER.follow_ups`, the Gemma prompt
and schema for suggestions, the stub's rule-based follow-ups per tool, the frontend
buttons (clarify styled differently, disabled after a tap), and four tests.

## What was added to make it work with the rest

- `apps/bank-backend/followups.py`: every suggestion is checked — it must be answerable
  (the T010 scope check would not attach a "can't" notice to it), must not quote
  merchant ids or numbers the tools did not produce, and duplicates and the question just
  asked are dropped.
- Rule-based follow-ups in the backend, in the answer's language (fi/sv/en, category
  names from `packages/cloud/glossary.py`), fill up to 3 slots after the provider's own
  suggestions: Gemma often gives one vague suggestion; OpenRouter gives none.
- Labels and prompts from Gemma get the same money/date formatting as answers.
- Rent and bills are never suggested as something to cut.

## Allowed files

```text
apps/bank-backend/followups.py (new), orchestrator.py, tests/test_flow.py
apps/ai/llm_provider.py, stub_provider.py, README.md
apps/bank-backend/tests/test_llm_provider.py
apps/frontend/app.js, styles.css, README.md
packages/contracts/schemas.py, __init__.py, README.md
docs/
```

**Shared surfaces touched:** `ANSWER` gains optional `follow_ups` (`FOLLOW_UP` items) —
additive; every consumer updated in the same change.

## Acceptance criteria

- [x] Answers carry 0–3 follow-ups; tapping one sends its prompt as the next question.
- [x] Follow-ups are in the answer's language and are all answerable (scope-checked).
- [x] Works for every provider: Gemma (own + filled), OpenRouter (rule-based), stub.
- [x] Tests: 76 Python tests (4 from feat/t009, adapted, + 5 new) + UI text check.
- [x] Browser + Gemma: Finnish savings question → "Viihde −20 %?" choice → tapped →
      Finnish what-if answer with its own follow-ups ("Entä jos vähentäisin 10 %?").
- [x] Regression: 11 evaluation cases on Gemma, 11/11 pass (answers ~1–2 s slower).

## Verify

```bash
bash scripts/check.sh
bash scripts/test.sh
```

## Notes

Decisions #54–56. `feat/t009` can be deleted by its owner once this is merged.
