# T016 — Gemma 4 26B-A4B as the coach model

**Owner:** `TODO` **Status:** in review
**Branch:** `task/t016-gemma-4`

## Goal

The coach runs on Gemma 4 26B-A4B instead of Gemma 3 27B, without losing answer quality,
and Gemma 3 stays one setting away.

## What changed

- **Deployment:** `apps/ai/modal_app.py` defaults to `google/gemma-4-26B-A4B-it` (same
  H100, vLLM 0.31.0, same served name `gemma`, same app `sbank-coach-llm` and URL, so
  `.env` is unchanged). `COACH_MODEL=google/gemma-3-27b-it` brings Gemma 3 back;
  `COACH_APP` deploys a second app for side-by-side comparison.
- **Fixes found by the evaluation** (in code, model-agnostic):
  1. `explore_transactions`: an explicit category wins over a contradicting `direction`
     (Gemma 4 asked for investments with `direction: "spend"` and got 0 €).
  2. `scope.guess_lang`: the backend guesses the question's language from common words;
     the orchestrator uses it for the limitation text and the Gemma prompt says which
     language to answer in (Gemma 4 once answered an English question in Finnish).
  3. `scope.localize_terms`: basket and category names in another language are replaced
     with the answer language's names (Finnish basket names in English/Swedish answers).
- Tests for all three in `apps/bank-backend/tests/test_flow.py` (`TestGemma4Fixes`).

## Evaluation (`apps/ai/eval/run_eval.py`, 33 cases, CUST00001, 2026-11-14)

| Model | Cases | Checks | Median answer |
| --- | --- | --- | --- |
| Gemma 3 27B | 31/33 | 217/219 | 11.0 s |
| Gemma 4 26B-A4B, before fixes | 28/33 | 212/219 | 3.8 s |
| Gemma 3 27B, with fixes | 32/33 | 218/219 | 9.4 s |
| Gemma 4 26B-A4B, with fixes | 33/33 | 219/219 | 3.6 s |
| Gemma 4 on the main app `sbank-coach-llm` after the switch | 33/33 | 219/219 | 3.5 s |

## Verify

`bash scripts/test.sh`, `bash scripts/check.sh`, then `python3 apps/ai/eval/run_eval.py`
against the deployment in `.env`.
