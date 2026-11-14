# apps/bank-backend/calculation

**Calculation tools** in the architecture (`docs/SYSTEM_MAP.md`). A module inside the
S-pankki backend, not a separate service. Python, `tools.py`.

Owner: same as `apps/bank-backend/` unless `docs/SYSTEM_MAP.md` says otherwise.

- Flow steps: receives **3** (an already-approved calculation request), does **4**
  (calculates over client data in `packages/cloud/`), returns **5** (results or a
  response explaining why not).
- Owns: the set of calculations (each a named tool with typed input and output), and
  the only code path that reads client financial data.
- Not its job: deciding whether a request is allowed (the backend does that before
  calling in), talking to the AI model, or formatting answers for the user.

The AI model never sees raw client data, only what these tools return. Keep it that
way unless `docs/MASTER_PLAN.md` §Decision log says otherwise.

## Tools

`CATALOG` in `tools.py` is the source of truth (names, descriptions, JSON-schema
parameters); `describe_catalog()` is what the AI is shown. All read only the customer's
own transactions plus the peer benchmark table.

| Tool | Answers |
| --- | --- |
| `spending_breakdown` | where did my money go: categories, three buckets, change vs before |
| `spender_profile` | what kind of spender am I: archetype, traits, vs peers, and `signals` (see below) |
| `safe_to_spend` | what can I safely spend over N days |
| `savings_opportunities` | how could I save more: gaps to peers, top merchants, tips |
| `peer_comparison` | monthly spend per category vs age-band median |
| `simulate_change` | what if I cut/raise a category or basket by X%: monthly, yearly, horizon, savings rate |
| `explore_transactions` | free exploration: filter, group, aggregate; `subcategory` (taxi, fuel, pharmacy…) by merchant category code |

Add a tool: write the function, add it to `CATALOG`, add a visual in
`bank-backend/present.py` and wording in the AI provider.

## Life signals (`signals.py`)

`spender_profile` also returns `signals`: guesses about the customer's everyday life from
their card purchases, each `{key, label, evidence}`. They are not a tool of their own, and
the model never decides them; it only words them, as guesses ("looks like", "probably").

| Signal | Rule at 90 days (thresholds scale with the period) |
| --- | --- |
| `drives` | fuel 5541/5542 or parking 7523, at least 4 purchases |
| `public_transport` | 4111, at least 6 |
| `taxis` | 4121, at least 4 |
| `eats_out` | 5812 + 5814, at least 12 |
| `events` | 7832, 7922, 7999, at least 3 |
| `travels` | 4511, 4722, 7011, 7512, at least 2 |
| `invests` | `Invest Deposit` in at least 75% of the months |
| `regular_salary` | `Salary` in at least 75% of the months, median gap 25–35 days |

- Purchase counts are **minimums**: about 5% of purchases (12% in Transportation, 14% in
  Travel) carry no MCC and cannot be matched.
- Periods under 28 days give `signals: []`; a week of data says nothing reliable.
- **Never inferred:** health MCCs (5912, 8011, 8021, 8099), bars (5813), toy and hobby
  shops (5945). They still count in category and basket totals.
- `MCC_NAMES` lists all 36 codes in the data; a test fails on a code that is missing.
- Check the rules on a loaded database:
  `python3 apps/bank-backend/calculation/signals.py --report`.
