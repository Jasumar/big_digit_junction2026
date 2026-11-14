# CHALLENGE

The S-Bank challenge at Junction 2026, as given by the organiser. This is the yardstick
for every scope question: if a feature does not move one of the judging criteria, it
waits. Plan: `MASTER_PLAN.md`. Data: <https://github.com/hackjunction/Junction-2026-S-pankki>.

## The ask

Explore how AI can turn personal banking data into a **trusted financial coach for
everyday life**. Let people **talk with their own money**: conversational, insightful,
personalised, instead of statements and transaction lists.

S-Bank: Finland's fourth-largest bank, 3.5 million customers. Its app **S-mobiili** is
used weekly by one in three Finnish adults and is among the top-rated finance apps. As
far as S-Bank knows, no Finnish bank yet lets customers chat with their own financial
data.

Build on the **large synthetic transaction dataset** modelled on real S-Bank data. The
experience should handle:

- simple questions — "How much did I spend on taxis last month?"
- deeper ones — "What kind of spender am I?", "What is safe for me to spend this week?"
- what-ifs — "How much could I save if I reduced dining out by 20%?"

## Pedagogical angle: three baskets

Everyone's spending falls into three baskets. Helping people see where their money
really goes counts for a lot.

1. **Mandatory and regular** — e.g. rent
2. **Mandatory and irregular** — e.g. a broken washing machine
3. **Everyday spending that slips through your fingers** — e.g. coffees

## What they value

- **MyData spirit:** users explore their own data freely, not fixed charts the bank
  picked for them.
- **Plain-language explanations** of financial concepts.
- **"What if" simulations.**
- **Guidance toward healthier habits**, e.g. safe-to-spend and safe-to-save.
- **Benchmarks against open population data** (e.g. Statistics Finland) — encouraged,
  not required.
- **Financial literacy, especially for young adults.**

**Output:** a mobile app, or a web app that can be embedded in a mobile app. Customers
are on mobile.

**Optional bonus:** multi-bank view. Under PSD2 a customer can let their bank fetch
accounts from other banks — how would the coach use the full financial picture? Not
required; the challenge is fully solvable with the provided and open data.

## Judging criteria (20% each)

| Criterion | What it means for us |
| --- | --- |
| Impact on financial literacy (incl. pedagogical angle) | the three baskets front and centre; explain, don't just report |
| Originality of AI integration | AI that reasons over the user's data, not a chatbot bolted on |
| Clarity of the mobile user experience | one-thumb, phone-first, answers readable at a glance |
| Feasibility | runs on the provided data; privacy story S-Bank can believe |
| Potential to integrate into S-mobiili | embeddable web view, bank-side backend, S-Bank look |

## Mentors and contact

- Carl-Edvard (Calle) Holmberg — Chief Innovation Officer, **main contact**
- A representative from S-Bank IT / AI development
- A data scientist (transaction data expert)
- 1–2 business representatives who own the customer problem

## Data

Four CSVs (data dictionary in the organiser's brief PDF; how we load them, and what
profiling found, in `packages/cloud/README.md`):

| File | Contents |
| --- | --- |
| `tx_junction_transactions.csv` | 3.6M transactions, 5,100 customers, Oct 2024 – Sep 2026 |
| `tx_customers_junction.csv` | customer id, postal code (text, leading zeros), age |
| `mtg_negotiation_history.csv` | mortgage application event history |
| `mtg_tx_customer_link_and_final_mtg_infio.csv` | links mortgage customers to transaction customers, final outcome |

All four are fetched by `python3 packages/cloud/fetch_data.py` and loaded by
`python3 packages/cloud/seed.py --full`.

## Where the MVP stands against the brief

As of the first MVP (`docs/tasks/Decisions.md`):

| Brief item | Status |
| --- | --- |
| Where did my money go / three baskets | done — `spending_breakdown` |
| What kind of spender am I | done — `spender_profile` |
| Safe to spend this week | done — `safe_to_spend` |
| Free exploration (MyData) | done — `explore_transactions` |
| Benchmarks | partly — peers from the dataset's own age bands, **no open data yet** |
| "Taxis last month" | partly — taxis are MCC 4121 inside `Transportation` (59k rows); no tool filters by MCC yet |
| What-if ("reduce dining out by 20%") | done — `simulate_change` (category or basket, ±%, horizon) |
| Safe to save | **missing** |
| Plain-language explanations of concepts | **missing** beyond answer text; depends on the real AI provider |
| Real conversational AI | done — Gemma 3 27B on Modal answers in Finnish and English (T008); stub as offline fallback |
| Finnish / Swedish | partly — Gemma answers in the user's language; UI, charts and stub are still English-only |
| Multi-bank view (bonus) | not started |
