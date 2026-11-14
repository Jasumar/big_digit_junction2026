# T011 — Life signals from transactions, standalone (not wired to the AI yet)

**Owner:** `TODO` **Status:** todo
**Branch:** `task/t011-inferred-life-signals`

## Goal

A standalone, tested module that infers what a customer's money says about their
everyday life, without asking: "you probably drive", "you commute by public transport",
"you eat out about twice a week", "you travel a few times a year", "you invest every
month". Each guess carries its evidence (count, amount, period). The rules are checked
against all 5,100 customers before anything reaches the AI.

This task does **not** touch the tools the AI can call. Another task is changing the
calculation tools right now. Wiring the signals into `spender_profile`, the visuals and
the stub provider is the follow-up task (see "Next task" below), started once that work
has merged.

## Allowed files

Everything else needs agreement first.

```text
apps/bank-backend/calculation/signals.py      (new: MCC table, signal rules, report command)
apps/bank-backend/tests/test_signals.py       (new)
```

Deliberately **not** allowed: `calculation/tools.py`, `calculation/README.md`,
`present.py`, `apps/ai/*`, `tests/test_flow.py`. These are where the parallel tooling
work is, or they belong to the wiring task. Documentation stays in the `signals.py`
docstring until then.

**Shared surfaces touched:** none. `signals.py` reads data only through the existing
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

- [ ] `test_signals.py` unit-tests `signals_from_counts` on hand-made counts: each signal
      fires just at its threshold, not one below, and empty counts give `[]`.
- [ ] A test proves health and bar MCCs never produce a signal, however many purchases
      there are.
- [ ] A test asserts every MCC in the loaded database is in `MCC_NAMES` (fixture in CI;
      the full data when it is loaded).
- [ ] Fixture tests pin the expected signals for at least two of CUST00001–06.
- [ ] `--report` runs on the full database. Its output (signal shares, timing) is pasted
      into this file's Notes with the date, and the thresholds are tuned until no signal
      is flagged.
- [ ] p95 under 5 ms per customer on the full data, matching the existing tools.
- [ ] `git diff main --stat` shows only the two allowed files and this task file.

## Verify

```bash
bash scripts/check.sh
bash scripts/test.sh                                         # picks up test_signals.py
python3 apps/bank-backend/calculation/signals.py --report    # needs the full DB (packages/cloud/README.md §Setup)
```

## Next task (wiring), not part of this one

Create it once the parallel tooling task has merged, and number it then:
`spender_profile` adds `signals: life_signals(...)`, `present.py` shows them with their
evidence, the stub answer words them as guesses ("looks like…"), and `test_flow.py`
covers them. The tool-result `data` is an untyped object in `packages/contracts`, so no
contract change is needed. The calculation README documents the signals then. Decide at
that point whether `MCC_NAMES` moves to `packages/cloud/taxonomy.py`, a shared surface
that would need agreement.

## Notes

Decided while drafting (2026-11-14), open to change by the owner:

- **Rules, not clustering.** Clustering would need a new table in `packages/cloud`
  (shared surface), and on synthetic data it may just recover the generator's personas.
- **The model does not infer.** Per Decisions #14 it only words what the rules found,
  once wired.
- **Not here:** location from postal code, rent vs mortgage, household size (one account
  per customer), and letting the customer dismiss a signal (needs stored per-customer
  state, which nothing has yet).
