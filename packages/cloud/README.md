# packages/cloud

**Cloud** in the architecture (`docs/SYSTEM_MAP.md`): the data platform that holds all
client data — in a real bank something like GCP (BigQuery), Azure or AWS. In this project
it holds the **mock data provided by S-pankki**.

For now that platform is stood in for by a **local SQLite file** built from the
hackathon CSVs (`docs/tasks/Decisions.md` #5). Moving to a hosted platform means
replacing `store.py` and `seed.py`, and porting the SQL in
`apps/bank-backend/calculation/tools.py` (written in SQLite's dialect, mostly
portable). For now we keep the local stand-in (`docs/MASTER_PLAN.md` question 9).

Owner: `TODO` (`docs/SYSTEM_MAP.md`)

- Flow step: **4** — the calculation tools read client data from here.
- Accessed by: `apps/bank-backend/calculation/` only. Nothing else reads it.
- Depends on: nothing in this repo.
- Owns: the shape of client data, how it is accessed, seed / mock data for a fresh
  start.
- Not its job: calculations, business logic, or shapes the contract does not describe.

## Rules

Shared surface: no silent changes to the data shape. One change at a time, say so in
the task file and to the team, and leave one documented command that gets a working
store (or mock) from nothing.

## Setup

```bash
python3 packages/cloud/seed.py                    # committed 6-customer fixture
python3 packages/cloud/seed.py --csv-dir <dir>    # full dataset, ~80 s, ~500 MB
```
Output `packages/cloud/data/s_pankki.sqlite` (gitignored). `taxonomy.py` defines which
categories are spending and the three buckets; `store.py` is the read-only access
(open with `mode=ro`); tables: `customers`, `transactions`, `peer_benchmark`, `meta`.

The server checks which data is loaded (`meta.source`: `fixture` or `full`), warns on
the sample, and refuses to start on it with `REQUIRE_FULL_DATA=1` (Decisions #22).

## Data notes

What we learned from profiling the S-pankki CSVs (source:
`hackjunction/Junction-2026-S-pankki`; the transactions file is ~363 MB via Git LFS).

- **Size:** 3,626,755 transactions, 5,100 customers, 2024-10-01 – 2026-09-30.
  **One bank account per customer.** Ages 18–90, most 30–59.
- **Files start with a UTF-8 BOM** — read with `utf-8-sig`.
- **`tx_timestamp` looks like `03OCT24:09:04:04`**; `seed.py` converts it to ISO and
  derives `hour` and `weekday`. **Postal codes are text** (leading zeros matter).
- **Categories and types:** Groceries, Restaurants, Transportation, Entertainment,
  Health, Home & Tech, Lifestyle, Travel are `purchase`; Housing is `housing_payment`,
  Utilities `utilities_payment`; Salary, Other Income are income; Salary Sweep, Invest
  Deposit, Invest Withdraw are transfers. Bucket mapping: `taxonomy.py`.
- **Merchants are synthetic ids** (`MRC-GRO-0035`); 45–90 per category, no names.
- **MCC codes refine categories:** e.g. taxis are MCC 4121 (59k rows inside
  Transportation). 75k Transportation rows have no MCC. No tool filters by MCC yet.
- **Recurring patterns:** salary and housing roughly
  monthly, utilities several small payments a month — `safe_to_spend` predicts the next
  date from the median gap.
- **Mortgage files** (`mtg_*.csv`) are not loaded (Decisions #6).

## Performance

Measured on the full database (200 random customers, each tool's default arguments):
every tool answers in **under 3 ms median, under 5 ms at the 95th percentile**
(`safe_to_spend` is the slowest). Queries use the `(customer_id, tx_date)` index. Seeding
takes ~80 s and produces ~500 MB. The database is not a bottleneck: an AI provider call
will take seconds.

## Hosting later

We keep the local stand-in for now (team decision). Notes for when it moves:

- **SQLite is enough while** there is one backend process, read-only data and no real
  users: in-process, no network, cannot be corrupted read-only.
- **Move to a managed PostgreSQL when** several backend instances share data, data
  arrives continuously (new transactions, a PSD2 multi-bank feed), or per-customer
  access control, audit, backups and failover are needed. It adds ~1 ms of network per
  query in-region (≈5–20 ms per question) — chosen for safety and scale, not speed.
- **Suggestion (unverified, check before choosing):** Google Cloud in `europe-north1`
  (Finland), Cloud SQL for PostgreSQL as the serving store, the backend on Cloud Run in
  the same region. Data stays in Finland. Use BigQuery only beside it for analytics
  (peer benchmarks, Statistics Finland joins), not for serving chat queries — it has
  ~1 s per-query latency and bills a minimum per query.
- **What can override that:** whichever cloud S-Bank already uses — matching it helps
  the "potential to integrate into S-mobiili" criterion. Ask the S-Bank IT/AI mentor
  (`docs/MASTER_PLAN.md` question 10).
- **Migration scope:** `store.py`, `seed.py`, and the SQL in
  `apps/bank-backend/calculation/tools.py` (small fixes for Postgres; a bigger port for
  BigQuery).
