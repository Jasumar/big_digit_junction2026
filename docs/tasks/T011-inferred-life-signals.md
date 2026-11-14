# T011 — Life signals from transactions

**Owner:** `TODO` **Status:** review
**Branch:** `task/t011-inferred-life-signals`

## Goal

A standalone, tested module that infers what a customer's money says about their
everyday life, without asking: "you probably drive", "you commute by public transport",
"you eat out about twice a week", "you travel a few times a year", "you invest every
month". Each guess carries its evidence (count, amount, period). The rules are checked
against all 5,100 customers before anything reaches the AI.

Built in two steps on one branch: first standalone (module, tests, report on all 5,100
customers), then wired into `spender_profile` once the parallel tooling task (T010) had
merged. The signals are returned inside `spender_profile`, not as a new tool.

## Allowed files

Everything else needs agreement first.

```text
apps/bank-backend/calculation/signals.py      (new: MCC table, signal rules, report command)
apps/bank-backend/tests/test_signals.py       (new)
docs/MASTER_PLAN.md                           (index row only)
```

Wiring step (after T010 merged, 2026-11-14):

```text
apps/bank-backend/calculation/tools.py        (spender_profile returns `signals`; catalog text)
apps/bank-backend/calculation/README.md       (document the signals)
apps/bank-backend/present.py                  (evidence table, fi/sv strings)
apps/ai/stub_provider.py                      (signals as hedged insights)
apps/bank-backend/tests/test_flow.py          (tests)
```

**Shared surfaces touched:** none changed. `signals.py` reads data only through the existing
read-only `cloud.store.Store` (`rows`/`one`) and imports `cloud.taxonomy` without
changing either. `CATALOG` in `tools.py` is untouched, so the AI sees no change.

### Why a module in `calculation/`, not a new package

The ask was "standalone packages". Two rules point to a module instead:

- AGENTS.md §2: no new packages or top-level directories without agreement.
- `packages/cloud/README.md`: the client data is read by `apps/bank-backend/calculation/`
  only. A package elsewhere that reads transactions would break that privacy boundary,
  which is part of the pitch.

A new file in `calculation/` that nothing imports yet is just as standalone. It can be
built, tested and run on its own, and it lands with no merge conflicts. If the team still
wants `packages/<name>/`, that needs agreement first and a change to the cloud README's
"who reads the data" rule.

## Depends on

- Needs merged first: T003 (store, taxonomy, fixture), already on `main`.
- Runs alongside: the parallel tooling task (no shared files).
- Blocks: the wiring task (below).

## Design

1. **MCC table:** `MCC_NAMES`, all 36 codes in the full data with their standard
   (ISO 18245) names, e.g. 5411 grocery stores/supermarkets, 5541 service stations, 4111
   commuter transport, 4121 taxis. Written by hand in English; Finnish and Swedish labels
   come later.
2. **Pure rules:** `signals_from_counts(counts, months) -> list[dict]` takes per-MCC and
   per-category counts and amounts, with no database access, so unit tests need no data.
3. **Data access:** `customer_counts(store, customer_id, start, end)`, one grouped SQL
   query per customer, parameterised like `tools.py`.
4. **Entry point for later wiring:** `life_signals(store, customer_id, period)` returns
   `[{key, label, evidence}]`. It uses the same period names as the tools (`PERIODS`) and
   works out the dates itself, so `tools.py` is not imported (it is being changed).
5. **Report:** `python3 apps/bank-backend/calculation/signals.py --report` runs the rules
   on every customer in the loaded database. It prints, per signal, the share of
   customers who get it, and the p50/p95 time per customer. This is where thresholds are
   tuned.

### Signals (starting thresholds; tune with the report)

Default period `last_90_days`. Purchases only; MCC rules ignore rows without an MCC.

| Signal | Rule (start) |
| --- | --- |
| Drives a car | fuel 5541/5542 or parking 7523, at least 4 purchases |
| Uses public transport | 4111, at least 6 |
| Takes taxis | 4121, at least 4 |
| Eats out often | 5812 + 5814, at least 12 |
| Goes to events / cinema | 7832, 7922, 7999, at least 3 |
| Travels | 4511, 7011, 7512, 4722, at least 2 |
| Invests regularly | `Invest Deposit` in most months of the period |
| Regular salary | `Salary` every month, median gap 25–35 days |

**Evidence is a lower bound:** 12% of Transportation and 14% of Travel purchases have no
MCC, so the evidence says "at least N". Measured coverage on the full data (2026-11-14):
94.6% of purchases have an MCC. A purchase without an MCC never has a merchant ID either,
so the missing codes cannot be recovered.

**Never inferred:** health MCCs (5912, 8011, 8021, 8099), bars (5813), or toy/hobby shops
as a "has children" guess. Health is special-category data under GDPR; drinking and
family guesses are the creepy kind.

**A useful signal tells people apart:** the report flags any signal held by more than 90%
or fewer than 2% of customers. Tune the threshold, or drop the signal.

## Acceptance criteria

- [x] `test_signals.py` unit-tests `signals_from_counts` on hand-made counts: each signal
      fires just at its threshold, not one below, empty counts give `[]`, thresholds scale
      with the period (`TestRules`).
- [x] Health and bar MCCs, and toy shops, never produce a signal, however many purchases
      there are (`test_never_inferred_codes_make_no_signal`).
- [x] Every MCC in the loaded database is in `MCC_NAMES` (fixture in CI; the full data
      too, via `TestFullData`).
- [x] Fixture tests pin the expected signals for CUST00004, 05 and 06.
- [x] `--report` runs on the full database; output below. No signal is flagged for the
      default period.
- [x] p95 under 5 ms per customer on the full data (0.73 ms).
- [x] Wiring: `spender_profile` returns `signals` (`test_profile_signals`), too-short
      periods give `[]`, charts show them in en/fi/sv without English left in fi, the stub
      words them as "Looks like" (`test_profile_signals_reach_the_answer`). `spender_profile`
      p95 on the full data: 1.12 ms.

## Verify

```bash
bash scripts/check.sh
bash scripts/test.sh                                         # picks up test_signals.py
SPANKKI_DB=<path to full db> python3 -m unittest tests.test_signals.TestFullData   # from apps/bank-backend; skipped without the full data
python3 apps/bank-backend/calculation/signals.py --report    # needs the full DB (packages/cloud/README.md §Setup)
```

## Wiring (done)

`spender_profile` adds `signals` and a note telling the model to word them as guesses. The
tool-result `data` is an untyped object in `packages/contracts`, so no contract change was
needed. `present.py` shows an evidence table ("at least 12 purchases, €340"), the stub
adds "Looks like: …" insights, and windows under 28 days return `signals: []`. Left for
later: moving `MCC_NAMES` to `packages/cloud/taxonomy.py` (shared surface, needs
agreement), and Finnish/Swedish signal labels in `glossary.py` (today only in
`present.py`; the wording is a draft, Q11).

## Notes

Decided while drafting (2026-11-14), open to change by the owner:

- **Rules, not clustering.** Clustering would need a new table in `packages/cloud`
  (shared surface), and on synthetic data it may just recover the generator's personas.
- **The model does not infer.** Per Decisions #14 it only words what the rules found,
  once wired.
- **Not here:** location from postal code, rent vs mortgage, household size (one account
  per customer), and letting the customer dismiss a signal (needs stored per-customer
  state, which nothing has yet).

## Results (2026-11-14, full data, 5,100 customers)

`--report`, default period `last_90_days` (thresholds as in the table above):

| Signal | Customers | Share |
| --- | ---: | ---: |
| drives | 3,571 | 70.0% |
| public_transport | 799 | 15.7% |
| taxis | 584 | 11.5% |
| eats_out | 3,407 | 66.8% |
| events | 3,828 | 75.1% |
| travels | 1,821 | 35.7% |
| invests | 1,470 | 28.8% |
| regular_salary | 3,431 | 67.3% |

Signals per customer: 0 → 50, 1 → 287, 2 → 713, 3 → 1,208, 4 → 1,332, 5 → 971, 6 → 402,
7 → 117, 8 → 20. Time per customer: p50 0.22 ms, p95 0.73 ms. Unknown MCCs: none.

- **Thresholds are untuned.** None is flagged, so I left the starting values. `drives`,
  `eats_out` and `events` are held by two thirds or more of customers, which makes them
  weak at telling people apart; raising `events` (now 3 per 90 days) and `eats_out` is the
  first thing to try if the follow-up wants sharper labels. This is synthetic data, so do
  not read the shares as Finnish behaviour.
- **`regular_salary` is flagged on `last_12_months`** (98.7%, too common). The default
  period is unaffected; whoever wires it up should either keep the 90-day period or drop
  that signal for longer ones.
- **`regular_salary` is only 67% at 90 days.** Some customers' salary gaps fall outside
  25–35 days; not investigated.
- **Windows:** `scripts/test.sh` needs `python3`, which this machine lacks; I ran the same
  `unittest discover` command with `python`. Seven errors in `test_flow.py` and
  `test_llm_provider.py` (`tearDownClass` cannot delete a temp database that is still
  open, and `TestEvalRunner.test_checks`) occur on main too, without this task's files.
