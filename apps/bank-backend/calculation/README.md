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
| `spender_profile` | what kind of spender am I: archetype, traits, vs peers |
| `safe_to_spend` | what can I safely spend over N days |
| `savings_opportunities` | how could I save more: gaps to peers, top merchants, tips |
| `peer_comparison` | monthly spend per category vs age-band median |
| `simulate_change` | what if I cut/raise a category or basket by X%: monthly, yearly, horizon, savings rate |
| `explore_transactions` | free exploration: filter, group, aggregate |

Add a tool: write the function, add it to `CATALOG`, add a visual in
`bank-backend/present.py` and wording in the AI provider.
