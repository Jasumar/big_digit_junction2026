# T017 — No data about other customers

**Owner:** `TODO` **Status:** in review
**Branch:** `task/t017-no-peer-data` (built on `task/t016-gemma-4`)

## Goal

Strict banking-sector governance: the coach never shares anything derived from other
customers — no medians, averages or age-group comparisons. It only uses the customer's
own data.

## What changed

- **Data:** `seed.py` no longer builds the `peer_benchmark` table (age-band medians and
  averages); `store.peer` is gone. Rebuild the local database with `seed.py` (`--full`).
- **Tools:** `peer_comparison` removed from the catalog; `spender_profile` lost its
  peer fields; `savings_opportunities` now compares each category with the customer's
  own monthly average over the 12 months before the period (`usual_monthly`,
  `above_usual_by`, basis `above_usual` or `gentle_trim`).
- **UI:** the profile chart shows the customer's own monthly spend by basket (no peer
  bars); the savings table column "Peers" became "Usual". The gray chart colour is now
  called `baseline`. The example question "Compare to others my age" became "Am I spending more than
  before?" (fi/sv/en).
- **Coach:** `scope.py` recognises comparisons with others (fi/sv/en: "ikäisiini",
  "keskivertosuomalainen", "others my age", "average customer", "jämnåriga", …) and adds
  a limitation: own data only, comparison with own earlier spending offered. The shared
  prompt rule forbids peer comparisons and outside figures. The "Compare to others my
  age" follow-up is gone, and `followups.clean` drops any such suggestion.
- **Tests** (`TestNoOtherCustomersData`): no peer tool or table, no tool result or chart
  in any language mentions peers/medians, savings use own history, peer questions are
  declined, no peer follow-ups. Eval: `fi-peers` now expects a notice and no medians;
  new `en-peers`.

## Verify

`bash scripts/test.sh`, `bash scripts/check.sh`, `python3 apps/ai/eval/run_eval.py`.
