# packages/cloud

**Cloud** in the architecture (`docs/SYSTEM_MAP.md`). Where client financial data
lives. Here it is a **SQLite file** built from the hackathon CSVs (Decisions #5).

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
