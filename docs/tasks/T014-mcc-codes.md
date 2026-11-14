# T014 — Merchant Category Code reference data and subcategories

**Owner:** `TODO` **Status:** review
**Branch:** `task/t014-mcc-codes`

## Goal

The Merchant Category Code (MCC) reference list is part of our data, like the other
CSVs, and the coach can split categories by it — e.g. taxis vs. public transport vs.
fuel inside Transportation — and the T011 life signals stay consistent with it.

## What changed

- **Data:** `packages/cloud/fixture/mcc_codes.csv` — 981 codes from
  github.com/greggles/mcc-codes (Unlicense / public domain, downloaded 2026-11-14).
  `seed.py` loads it into a new `mcc_codes` table for both the sample and the full build
  (a copy in `--csv-dir` takes precedence); `store.mcc_names()` reads it; `store.info()`
  reports the count.
- **Subcategories:** `taxonomy.SUBCATEGORIES` maps all 36 codes in the S-pankki data to
  29 subcategory keys (taxi, public_transport, fuel, parking, restaurant, fast_food, bar,
  pharmacy, doctor, dentist, flights, hotels, …); `glossary.SUBCATEGORY_NAMES` names
  them in fi/sv/en.
- **Tools:** `explore_transactions` gains a `subcategory` filter and `group_by:
  "subcategory"`; results carry the official names (`mcc_names`) and a note that
  subcategory totals are minimums (about 5% of purchases, 12% of Transportation, have no
  MCC). Charts show localized subcategory names.
- **Coach:** the scope check no longer flags taxis, fuel, pharmacies etc.; coffee and
  tobacco stay unsupported (no code). Gemma's rules list the subcategories and ask it to
  say "at least".

## How this works with T011 (life signals)

T011 (`calculation/signals.py`) already used MCCs: rules such as "takes taxis" (4121),
"probably drives" (fuel and parking codes), "uses public transport" (4111), with its own
hand-written short names for the 36 codes. That module is unchanged except for its
`--report`, which now also lists codes missing from the reference table. New tests assert
that its codes are exactly the mapped subcategory codes, that every rule code exists in
the reference table, and that its taxi and public-transport rules use the same codes as
the subcategories — so the profile ("takes taxis") and an explicit question ("how much on
taxis?") can never disagree on what a taxi is.

## Allowed files

```text
packages/cloud/fixture/mcc_codes.csv (new), seed.py, store.py, taxonomy.py, glossary.py, README.md
apps/bank-backend/calculation/tools.py, signals.py (report only), README.md
apps/bank-backend/present.py, scope.py, tests/test_flow.py
apps/ai/llm_provider.py, README.md, eval/cases.json
docs/
```

**Shared surfaces touched:** stored-data shape gains the `mcc_codes` table (additive);
`explore_transactions` gains `subcategory` (additive). Consumers updated in the same
change.

## Acceptance criteria

- [x] `mcc_codes.csv` in `fixture/`; `seed.py` loads it for sample and full builds.
- [x] All 36 data codes in the reference table and mapped to a subcategory with names.
- [x] Taxi, fuel, public transport etc. answerable.
- [x] T011 signals consistent with the reference table and subcategories (tests).
- [x] Tests: 84 Python tests + UI text check.
- [x] No merchant-code warning is shown to users (team decision, Decisions #60); the
      model gives subcategory amounts plainly without claiming they include all.
- [x] Gemma, full data: "Paljonko olen käyttänyt takseihin viimeisen vuoden aikana?" →
      195 € (checked in SQL; 140 € of that customer's transport has no code, which the
      tool notes but users are not warned about). Coffee still gets the honest
      "no code for coffee" answer; life-signals profile and regression cases pass.
- [x] T011 `--report` on all 5,100 customers: "MCCs missing from the reference table: none".

## Verify

```bash
bash scripts/check.sh
bash scripts/test.sh
python3 packages/cloud/seed.py --full   # rebuild an existing database to get mcc_codes
```

## Notes

Decisions #57–60. Existing local databases need a rebuild (`seed.py --full`); without
the table the tools still work, only `mcc_names` comes back empty.
