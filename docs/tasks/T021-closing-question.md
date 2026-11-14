# T021 — Closing question at the end of every answer

**Owner:** `TODO` **Status:** in review
**Branch:** `task/t021-closing-question` (from `main`)

## Goal

Every answer ends with a question that keeps the conversation going: a specific one
when it fits ("Would you like to see your restaurant spending month by month?", "Do you
have savings elsewhere?"), otherwise "Is there anything else you'd like to know?".

## What changed

- **Contract:** `ANSWER.closing` (string, optional, max 300). Shared surface; the only
  consumers are the orchestrator (producer) and the frontend (renderer), both updated.
- **Gemma:** the compose schema requires `closing`; the prompt asks for a specific
  question (what would change the numbers, or one next look the tools can do), with no
  numbers and nothing from the CANNOT list; the answer text itself has no question.
- **Backend:** `apps/bank-backend/closing.py` validates the proposal (a single question
  of 8–160 characters, the answer's language, no unbacked numbers, no merchant ids,
  passes the scope check) or falls back to one of three general questions per language.
  A question ending the answer text is moved into `closing`. Stub and OpenRouter answers
  get the general one. `scope.guess_lang` knows a few more question words.
- **UI:** the closing question is shown last in the answer bubble (bold), above the
  follow-up buttons, and is added to the chat history so "yes" continues the thread.
- **Tests:** `TestClosingQuestion` (every answer has one and validates against the
  contract; valid proposals kept; budget/number/wrong-language/merchant-id proposals
  replaced; trailing question moved; general question in fi/sv/en).
- **Answer language:** when the backend can tell the question's language, it is the
  answer language (Gemma once wrote Swedish but labelled it English, so euros and basket
  names were formatted in English).
- **Repeats:** a closing question already asked in this chat is not asked again.
- **Eval:** new `closing` check on every case; language is detected over text + closing;
  `fi-peers` no longer bans "keskiarvo" (the refusal itself says "keskiarvoihin").

## Result

Live Gemma 4 evaluation (CUST00001, 2026-11-14): 36/36 cases, 277/277 checks, median
3.3 s. Closing questions are specific in most answers ("Would you like to look closer
at your entertainment spending?") and general for refusals and concepts. A first prompt
version with a concrete example made Gemma repeat that example in almost every answer;
the prompt now describes what to ask instead.

## Verify

`bash scripts/test.sh`, `bash scripts/check.sh`, `python3 apps/ai/eval/run_eval.py`.
