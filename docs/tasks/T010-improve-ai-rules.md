# T010 — Measure and improve the coach's rules and wording

**Owner:** `TODO` **Status:** review
**Branch:** `task/t009-improve-ai-rules` (renumbered T010 after the OpenRouter task took T009)

## Goal

The Gemma coach follows clear rules (scope, no investment advice, privacy, prompt
injection, honesty), uses consistent Finnish/Swedish terms and money formats, and there
is a repeatable evaluation that shows whether a change made it better.

## Allowed files

```text
apps/ai/**                                  (prompts, glossary, eval)
apps/bank-backend/calculation/tools.py      (archetype_key, field notes in results)
apps/bank-backend/tests/test_llm_provider.py, tests/test_flow.py
apps/bank-backend/present.py, orchestrator.py   (charts in the answer language)
packages/cloud/glossary.py                      (moved from apps/ai/)
packages/contracts/schemas.py                   (optional `lang` on the answer)
apps/frontend/styles.css                        (chart labels wrap)
docs/
```

**Shared surfaces touched:** tool result shapes gain fields (`archetype_key`, `notes`,
`change_amount`, `typical_everyday_spend_per_day`) and the answer gains `lang` — all
additive; every consumer (charts, stub, frontend, tests) updated in the same change.

## Depends on

- Needs merged first: T008 (merged in PR #4)

## Acceptance criteria

- [x] `apps/ai/eval/` — 20 fixed questions (fi/en/sv, rule cases) with automatic checks:
      tool, language, number grounding, forbidden strings, foreign terms, money format.
- [x] Shared rule block in both prompts; glossary for baskets, categories, spender types.
- [x] Tool results explain confusing fields (safe per day, shares of spending).
- [x] Old vs new compared on Gemma with the same checks (results below).
- [x] Money format fixed in code per answer language (model reports `lang`).
- [x] Answer charts in the answer's language (labels, names, money/percent/date
      formats); checked in the browser with a Finnish question.
- [x] Tests: eval helpers, a stub run and money formatting, offline (25 tests).

## Verify

```bash
bash scripts/check.sh
bash scripts/test.sh
set -a; . ./.env; set +a; python3 apps/ai/eval/run_eval.py     # costs GPU time
```

## Results

Gemma 3 27B, customer CUST00001, same 20 questions and the same checks (2026-11-14):

| Version | Cases passed | Checks passed | Median answer |
| --- | --- | --- | --- |
| Old prompts (`main`) | 12 / 20 | 111 / 120 | 8.7 s |
| New rules + glossary | 17 / 20 | 117 / 120 | 8.0 s |
| + money formatting in code, field notes | 19 / 20 | 119 / 120 | 9.3 s |
| + thousands-separator fix (money cases re-run) | 6 / 6 | 36 / 36 | 9.1 s |

Fixed: cat poem written on request; another customer's request still ran a tool;
housing called "asuntolaina"; English money as "1 879 €"; Finnish terms in Swedish and
English answers; unrounded cents; model-computed differences.

Still seen when reading answers (not caught by checks): "safe per day" sometimes called
average daily spending in Finnish; Gemma does not always follow every rule — keep
running the evaluation after changes. One run per version: Gemma is not fully
deterministic, so ±1 case between runs is noise.

## Safety fixes (after probing 25 simple questions)

Probe on Gemma (CUST00001), before these fixes: 6 correct, 4 honest "can't", 15 broken —
silent substitution (6), invented facts (4), over-refusal (2), rent counted as a
purchase, a transfers bug, and no data date. Safety fixes in this branch: coverage +
notice, runtime number check, narrowed rules with a capability list, data date in prompt
and UI, transfers bug (Decisions #37–40). Eval grew to 30 cases with `notice` and
`must_any` checks. Logic fixes (rent in purchase/weekday analysis, one "late night"
definition, share of income) and new tools (date ranges, transaction list, one weekday,
monthly averages, year comparison, balance history) are next — not in this branch.

Evaluation after the safety fixes (Gemma, 30 cases incl. 10 gap/own-data cases):

| Step | Cases passed |
| --- | --- |
| Coverage + number check + narrowed rules | 24 / 30 (notices missing, false refusals, merchant ids) |
| + code-based scope check, merchant ids redacted | 29 / 30 (false "last month" refusal remained) |
| + unknown args dropped before approval, zero categories listed | 29 / 30 — the one fail is the eval's language heuristic on a short, correct Finnish answer |

Root causes found while fixing: Gemma adds arguments tools do not have (the strict
approval then rejected valid requests and the answer said "I can't"); Gemma's own
limitations are unreliable in both directions, so notices come from code
(`apps/bank-backend/scope.py`). Still seen on reading: the transport answer says the
category is "not reported" instead of "0 €"; answers to unsupported asks can be clumsy
but no longer mislead.

## Notes

Choices: `docs/tasks/Decisions.md` #32–36.
