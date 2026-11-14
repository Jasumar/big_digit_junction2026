#!/usr/bin/env python3
"""Life signals: what a customer's transactions suggest about their everyday life (T011).

`tools.spender_profile` returns these as `signals` (it is not a tool of its own). The
module can still run alone: the `--report` command below needs nothing else.

    python3 apps/bank-backend/calculation/signals.py --report [--db PATH] [--period P]

Each signal is a guess with evidence: `{key, label, evidence}`. Evidence counts are lower
bounds ("at least"), because about 5% of purchases carry no MCC (12% in Transportation,
14% in Travel) and those rows cannot be matched to an MCC rule.

Never inferred: health (pharmacy, doctors, dentists, other medical), bars, and toy/hobby
shops (no "has children" guesses). Those purchases still count in category and basket
totals elsewhere; they just never become a statement about the person.

Reads data only through the read-only `cloud.store.Store`, like the calculation tools.
"""
import datetime as dt
import math
import os
import statistics
import sys
import time

# Every MCC in the S-pankki data (36 codes, checked on the full data 2026-11-14), with
# its standard ISO 18245 name. A code missing here fails test_signals.
MCC_NAMES = {
    "4111": "Commuter transport",
    "4121": "Taxis and limousines",
    "4511": "Airlines",
    "4722": "Travel agencies and tour operators",
    "5200": "Home supply warehouse stores",
    "5251": "Hardware stores",
    "5411": "Grocery stores and supermarkets",
    "5422": "Freezer and meat lockers, meat provisioners",
    "5451": "Dairy products stores",
    "5499": "Miscellaneous food stores",
    "5541": "Service stations",
    "5542": "Automated fuel dispensers",
    "5651": "Family clothing stores",
    "5691": "Men's and women's clothing stores",
    "5712": "Furniture and home furnishings stores",
    "5732": "Electronics stores",
    "5734": "Computer software stores",
    "5812": "Eating places and restaurants",
    "5813": "Drinking places (bars, taverns, nightclubs)",
    "5814": "Fast food restaurants",
    "5912": "Drug stores and pharmacies",
    "5941": "Sporting goods stores",
    "5942": "Book stores",
    "5945": "Hobby, toy and game shops",
    "5999": "Miscellaneous and specialty retail stores",
    "7011": "Hotels, motels and resorts",
    "7512": "Car rental agencies",
    "7523": "Parking lots and garages",
    "7832": "Motion picture theaters",
    "7922": "Theatrical producers and ticket agencies",
    "7991": "Tourist attractions and exhibits",
    "7996": "Amusement parks, carnivals and circuses",
    "7999": "Recreation services",
    "8011": "Doctors",
    "8021": "Dentists and orthodontists",
    "8099": "Medical services and health practitioners",
}

# Purchases at these never produce a signal, however many there are.
NEVER_INFER_MCC = frozenset({"5912", "8011", "8021", "8099", "5813", "5945"})

# (key, label, MCC codes, minimum purchases per 90 days). Thresholds scale with the period.
MCC_RULES = (
    ("drives", "Probably drives a car", ("5541", "5542", "7523"), 4),
    ("public_transport", "Uses public transport", ("4111",), 6),
    ("taxis", "Takes taxis", ("4121",), 4),
    ("eats_out", "Eats out often", ("5812", "5814"), 12),
    ("events", "Goes to events and the cinema", ("7832", "7922", "7999"), 3),
    ("travels", "Travels", ("4511", "4722", "7011", "7512"), 2),
)

# Share of the period's months that must have the payment.
INVEST_MONTH_SHARE = 0.75
SALARY_MONTH_SHARE = 0.75
SALARY_GAP_DAYS = (25, 35)

PERIOD_DAYS = {"last_30_days": 30, "last_90_days": 90, "last_12_months": 365}
MIN_DAYS = 28  # shorter windows give no signals
DAYS_PER_MONTH = 30.4


def _months(days):
    return max(1, int(round(days / DAYS_PER_MONTH)))


def _threshold(per_90_days, days):
    return max(1, int(round(per_90_days * days / 90.0)))


def signals_from_counts(counts, days):
    """Pure rules. `counts` comes from `customer_counts` (or a test):

    {"mcc": {code: {"n": int, "eur": float}},          # purchases, amount as positive EUR
     "months": {"Invest Deposit": int, "Salary": int},  # months with at least one
     "salary_gap_days": float | None}                   # median days between salaries
    """
    by_mcc = {k: v for k, v in (counts.get("mcc") or {}).items() if k not in NEVER_INFER_MCC}
    months = _months(days)
    out = []
    for key, label, codes, per_90 in MCC_RULES:
        hits = [c for c in codes if by_mcc.get(c, {}).get("n", 0) > 0]
        n = sum(by_mcc[c]["n"] for c in hits)
        if n >= _threshold(per_90, days):
            out.append({"key": key, "label": label, "evidence": {
                "count": n, "at_least": True,
                "amount_eur": round(sum(by_mcc[c]["eur"] for c in hits), 2),
                "mcc": sorted(hits), "period_days": days}})

    month_counts = counts.get("months") or {}
    inv = month_counts.get("Invest Deposit", 0)
    if inv >= max(2, math.ceil(INVEST_MONTH_SHARE * months)):
        out.append({"key": "invests", "label": "Invests regularly", "evidence": {
            "months_with_deposit": inv, "months": months, "period_days": days}})

    sal = month_counts.get("Salary", 0)
    gap = counts.get("salary_gap_days")
    lo, hi = SALARY_GAP_DAYS
    if (sal >= max(2, math.ceil(SALARY_MONTH_SHARE * months)) and gap is not None
            and lo <= gap <= hi):
        out.append({"key": "regular_salary", "label": "Has a regular monthly salary",
                    "evidence": {"months_with_salary": sal, "months": months,
                                 "median_gap_days": gap, "period_days": days}})
    return out


def period_range(store, customer_id, period):
    """-> (start_iso, end_iso, days), ending at the customer's latest transaction."""
    if period not in PERIOD_DAYS:
        raise ValueError("unknown period %r (use one of %s)" % (period, ", ".join(PERIOD_DAYS)))
    as_of = store.as_of(customer_id)
    if not as_of:
        raise ValueError("no transactions for this customer")
    end = dt.date.fromisoformat(as_of)
    days = PERIOD_DAYS[period]
    return (end - dt.timedelta(days=days - 1)).isoformat(), end.isoformat(), days


def customer_counts(store, customer_id, start, end):
    """The counts `signals_from_counts` needs, from two parameterised queries."""
    mcc = {r["mcc"]: {"n": r["n"], "eur": -r["amt"]} for r in store.rows(
        "SELECT mcc, COUNT(*) AS n, SUM(amount) AS amt FROM transactions"
        " WHERE customer_id = ? AND tx_date BETWEEN ? AND ? AND tx_type = 'purchase'"
        " AND mcc IS NOT NULL GROUP BY mcc", (customer_id, start, end))}
    rows = store.rows(
        "SELECT category, tx_date FROM transactions WHERE customer_id = ?"
        " AND tx_date BETWEEN ? AND ? AND category IN ('Salary', 'Invest Deposit')"
        " ORDER BY tx_date", (customer_id, start, end))
    months = {}
    for cat in ("Salary", "Invest Deposit"):
        months[cat] = len({r["tx_date"][:7] for r in rows if r["category"] == cat})
    sal = [dt.date.fromisoformat(r["tx_date"]) for r in rows if r["category"] == "Salary"]
    gaps = [(b - a).days for a, b in zip(sal, sal[1:])]
    return {"mcc": mcc, "months": months,
            "salary_gap_days": float(statistics.median(gaps)) if gaps else None}


def life_signals_between(store, customer_id, start, end, days):
    """Signals for an explicit window (what `spender_profile` uses). Windows shorter than
    MIN_DAYS give no signals: scaled to a week, one fuel purchase would read as "drives"."""
    if days < MIN_DAYS:
        return []
    return signals_from_counts(customer_counts(store, customer_id, start, end), days)


def life_signals(store, customer_id, period="last_90_days"):
    start, end, days = period_range(store, customer_id, period)
    return life_signals_between(store, customer_id, start, end, days)


def report(store, period="last_90_days", out=sys.stdout):
    """Run the rules on every customer; print each signal's share and the timing."""
    ids = [r["customer_id"] for r in store.rows(
        "SELECT DISTINCT customer_id FROM transactions ORDER BY customer_id")]
    keys = [r[0] for r in MCC_RULES] + ["invests", "regular_salary"]
    have = {k: 0 for k in keys}
    per_customer = []
    times = []
    for cid in ids:
        t0 = time.perf_counter()
        got = life_signals(store, cid, period)
        times.append((time.perf_counter() - t0) * 1000)
        per_customer.append(len(got))
        for s in got:
            have[s["key"]] += 1
    n = len(ids) or 1
    unknown = [r["mcc"] for r in store.rows(
        "SELECT DISTINCT mcc FROM transactions WHERE mcc IS NOT NULL") if r["mcc"] not in MCC_NAMES]
    times.sort()
    pick = lambda q: times[min(len(times) - 1, int(q * len(times)))] if times else 0.0
    info = store.info()
    print("data: %s (%d customers), period %s" % (info["source"], len(ids), period), file=out)
    print("%-18s %8s %7s  %s" % ("signal", "customers", "share", "flag"), file=out)
    flagged = 0
    for k in keys:
        share = have[k] / n
        flag = "too common (>90%)" if share > 0.90 else "too rare (<2%)" if share < 0.02 else ""
        flagged += bool(flag)
        print("%-18s %8d %6.1f%%  %s" % (k, have[k], 100 * share, flag), file=out)
    dist = {c: per_customer.count(c) for c in sorted(set(per_customer))}
    print("signals per customer: %s" % ", ".join("%d: %d" % kv for kv in dist.items()), file=out)
    print("time per customer: p50 %.2f ms, p95 %.2f ms" % (pick(0.5), pick(0.95)), file=out)
    print("unknown MCCs: %s" % (", ".join(sorted(unknown)) or "none"), file=out)
    return {"shares": {k: have[k] / n for k in keys}, "flagged": flagged,
            "p95_ms": pick(0.95), "unknown_mcc": unknown}


def _main(argv=None):
    import argparse
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.abspath(os.path.join(here, "..", "..", "..", "packages")))
    from cloud.store import Store

    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--report", action="store_true", help="signal shares over all customers")
    p.add_argument("--db", help="database path (default: SPANKKI_DB or the cloud default)")
    p.add_argument("--period", default="last_90_days", choices=sorted(PERIOD_DAYS))
    p.add_argument("--customer", help="print one customer's signals")
    a = p.parse_args(argv)
    store = Store(a.db)
    if a.customer:
        import json
        print(json.dumps(life_signals(store, a.customer, a.period), indent=2))
    elif a.report:
        report(store, a.period)
    else:
        p.print_help()


if __name__ == "__main__":
    _main()
