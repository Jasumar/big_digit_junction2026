# T020 — Big purchases and a more conversational coach

**Owner:** `TODO` **Status:** in review
**Branch:** `task/t020-big-purchases` (from `main`)

## Goal

The coach can answer "could my finances carry a home / a car / another big purchase of
this size?" from the customer's own data. It never tells anyone to buy or not to buy and
never promises a loan: it says what their numbers show, names its assumptions and leaves
the decision to them. The chat also feels more like a conversation.

## Allowed files

Requested by the team lead (2026-11-14), who granted authority over the calculation tool
list and the docs listed below.

```text
apps/bank-backend/calculation/tools.py, present.py, scope.py, followups.py, tests/
apps/ai/llm_provider.py, openrouter_provider.py, stub_provider.py, eval/cases.json
apps/frontend/app.js, i18n.js
docs/tasks/T020-big-purchases.md
```

**Not yet edited (needs a team OK):** `docs/tasks/Decisions.md`, `docs/MASTER_PLAN.md`
(still lists mortgage features as out of scope; task index) and
`apps/bank-backend/calculation/README.md` (tool table). Proposed decision rows are under
Notes.

**Shared surfaces touched:** calculation tool list (new tool `purchase_affordability`;
consumers updated in the same change: approval reads the catalog, both AI prompts, the
stub, charts, follow-ups). No contract, data-shape or config change.

## What changed

- **Tool `purchase_affordability`** (`kind` home|car|other, optional `price`,
  `down_payment`, `loan_years`, `interest_rate_pct`, `running_costs_monthly`,
  `other_savings`, `replaces_housing`). From the customer's last 12 months: income,
  spending, monthly margin, balance, a 3-month essentials buffer; down payment, annuity
  loan payment, running costs, margin after the purchase, a 6% stress test for homes,
  savings gap and months to close it, and a `max_price_estimate` under the same rules.
  Without `price` it returns only the range. Status: `fits`, `stretch`, `save_first`,
  `over_budget` (with reason keys). Only this customer's data (T017).
- **Charts** (fi/sv/en): verdict, loan payment, money left each month; "how it adds up"
  per month; savings vs down payment and buffer.
- **Coach:** prompt rule 11 (never advise buying, never promise a loan, state
  assumptions, the decision is the customer's); planning hints for purchases and for
  follow-up turns that change one thing ("what if I put 40 000 down?"); compose style
  is chattier (warm, "you", may end with one question that would change the numbers);
  greetings get a warm reply instead of a refusal.
- **Offline stub:** purchase questions in fi/sv/en (price, down payment, loan years),
  follow-up turns reuse the earlier purchase from history, greeting/thanks replies,
  stale "compare with others" help text and follow-up removed.
- **Scope check:** "budget" and years ("a 2024 car") no longer trigger the
  "can't save budgets" / "can't compare years" notices in purchase questions.
- **Follow-ups:** "What price could I afford?", "With a 30-year loan?", "save more".
- **UI:** the chat opens with a greeting bubble; new chip "Could I afford a €20,000 car?".

## Verify

```bash
bash scripts/test.sh
bash scripts/check.sh
node apps/frontend/i18n.test.mjs   # Node 22+: scripts/test.sh skips it there
python3 apps/ai/eval/run_eval.py   # needs the Modal endpoint; new cases fi-car, en-home-range
```

## Notes

- Market assumptions (home 3.5% over 25 years, 10% down, 1.5%/year upkeep, 6% stress;
  car 6% over 5 years, 20% down, €200/month running costs; payment ≤ 30% of income
  comfortable, > 40% over budget) are drafts — confirm with an S-Bank mentor.
- Investments are not counted as available cash (their value is unknown) unless the
  customer states them as `other_savings`.
- The mortgage CSVs are still unused: their outcomes are other customers' data (T017).
- Not done: real loan offers, first-home (95%) rules, ASP savings, tax deductions.

Proposed rows for `Decisions.md`:

- **66** `purchase_affordability` from the customer's own last 12 months plus visible,
  overridable market assumptions (above); investments not counted as cash unless stated.
- **67** The coach never advises buying and never promises a loan (prompt rule 11,
  result notes, stub text).
- **68** More conversational coach: warm greetings, an optional closing question,
  follow-up turns reuse the earlier purchase, a greeting bubble in the UI.
- **69** The scope check skips the "budget" and calendar-year rules in purchase
  questions.
