"""Calculation tools: the only code that reads client financial data.

Each tool is `fn(store, customer_id, args) -> dict` plus a parameter schema in CATALOG.
The backend (approval.py) validates args and supplies customer_id; tools never take a
customer id from the model. All SQL is parameterised; column names come from the
whitelists below, never from arguments.
"""
import datetime as dt
import statistics

from cloud.taxonomy import (
    BUCKET_LABELS, CATEGORY_BUCKET, EVERYDAY, ESSENTIALS, INCOME_CATEGORIES, NECESSITIES,
    SPEND_CATEGORIES, TRANSFER_CATEGORIES,
)
from contracts import PERIODS

DAYS_PER_MONTH = 30.4
_SPEND_IN = "(%s)" % ",".join("'%s'" % c for c in SPEND_CATEGORIES)  # constants, not input
_INCOME_IN = "(%s)" % ",".join("'%s'" % c for c in INCOME_CATEGORIES)
ALL_CATEGORIES = list(SPEND_CATEGORIES) + list(INCOME_CATEGORIES) + list(TRANSFER_CATEGORIES)


# ---------------------------------------------------------------- helpers

def _d(s):
    return dt.date.fromisoformat(s)


def resolve_period(period, as_of, first_date=None):
    """-> (start_iso, end_iso, days). End is inclusive and never after `as_of`."""
    end = _d(as_of)
    if period == "last_7_days":
        start = end - dt.timedelta(days=6)
    elif period == "last_30_days":
        start = end - dt.timedelta(days=29)
    elif period == "last_90_days":
        start = end - dt.timedelta(days=89)
    elif period == "last_12_months":
        start = end - dt.timedelta(days=364)
    elif period == "this_month":
        start = end.replace(day=1)
    elif period == "last_month":
        end = end.replace(day=1) - dt.timedelta(days=1)
        start = end.replace(day=1)
    elif period == "all":
        start = _d(first_date) if first_date else end - dt.timedelta(days=729)
    else:
        raise ValueError("unknown period %r" % period)
    return start.isoformat(), end.isoformat(), (end - start).days + 1


def _previous(start, days):
    end = _d(start) - dt.timedelta(days=1)
    return (end - dt.timedelta(days=days - 1)).isoformat(), end.isoformat()


def _ctx(store, customer_id, period):
    as_of = store.as_of(customer_id)
    if not as_of:
        raise ValueError("no transactions for this customer")
    first = store.one("SELECT MIN(tx_date) AS d FROM transactions WHERE customer_id = ?",
                      (customer_id,))["d"]
    start, end, days = resolve_period(period, as_of, first)
    start = max(start, first)
    days = (_d(end) - _d(start)).days + 1
    return {"as_of": as_of, "start": start, "end": end, "days": max(days, 1)}


def _spend_by_category(store, customer_id, start, end):
    rows = store.rows(
        "SELECT category, -SUM(amount) AS amt, COUNT(*) AS n FROM transactions"
        " WHERE customer_id = ? AND tx_date BETWEEN ? AND ? AND category IN " + _SPEND_IN +
        " GROUP BY category", (customer_id, start, end))
    return {r["category"]: r for r in rows}


def _income(store, customer_id, start, end):
    r = store.one("SELECT COALESCE(SUM(amount),0) AS s FROM transactions WHERE customer_id = ?"
                  " AND tx_date BETWEEN ? AND ? AND category IN " + _INCOME_IN,
                  (customer_id, start, end))
    return r["s"]


def _r(x, n=2):
    return round(float(x), n)


def _pct(part, whole):
    return _r(100.0 * part / whole, 1) if whole else 0.0


def _period_info(c, period):
    return {"period": period, "from": c["start"], "to": c["end"], "days": c["days"]}


def _next_recurring(dates, as_of):
    """Predict the next date of a recurring payment from its typical gap."""
    if len(dates) < 2:
        return None
    gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
    gap = max(int(statistics.median(gaps)), 1)
    nxt = dates[-1] + dt.timedelta(days=gap)
    while nxt <= as_of:
        nxt += dt.timedelta(days=gap)
    return nxt


def _bucket_totals(by_cat):
    out = {b: 0.0 for b in BUCKET_LABELS}
    for cat, r in by_cat.items():
        out[CATEGORY_BUCKET[cat]] += r["amt"]
    return out


# ---------------------------------------------------------------- tools

def spending_breakdown(store, customer_id, args):
    period = args.get("period", "last_30_days")
    c = _ctx(store, customer_id, period)
    cur = _spend_by_category(store, customer_id, c["start"], c["end"])
    pstart, pend = _previous(c["start"], c["days"])
    prev = _spend_by_category(store, customer_id, pstart, pend)
    total = sum(r["amt"] for r in cur.values())
    prev_total = sum(r["amt"] for r in prev.values())
    buckets = _bucket_totals(cur)
    categories = []
    for cat, r in sorted(cur.items(), key=lambda kv: -kv[1]["amt"]):
        p = prev.get(cat, {"amt": 0.0})["amt"]
        categories.append({
            "category": cat, "bucket": CATEGORY_BUCKET[cat], "amount": _r(r["amt"]),
            "share_pct": _pct(r["amt"], total), "transactions": r["n"],
            "previous_amount": _r(p),
            "change_pct": _pct(r["amt"] - p, p) if p else None})
    return {
        **_period_info(c, period),
        "total_spend": _r(total), "previous_total_spend": _r(prev_total),
        "change_pct": _pct(total - prev_total, prev_total) if prev_total else None,
        "income": _r(_income(store, customer_id, c["start"], c["end"])),
        "buckets": [{"bucket": b, "label": BUCKET_LABELS[b], "amount": _r(v),
                     "share_pct": _pct(v, total)} for b, v in buckets.items()],
        "categories": categories,
    }


def spender_profile(store, customer_id, args):
    period = args.get("period", "last_90_days")
    c = _ctx(store, customer_id, period)
    cust = store.customer(customer_id)
    agg = store.one(
        "SELECT COALESCE(-SUM(amount),0) AS total, COUNT(*) AS n,"
        " COALESCE(-SUM(CASE WHEN weekday >= 5 THEN amount END),0) AS weekend,"
        " COALESCE(-SUM(CASE WHEN hour >= 22 OR hour < 5 THEN amount END),0) AS late,"
        " COALESCE(-AVG(amount),0) AS avg_amt, COUNT(DISTINCT merchant_id) AS merchants"
        " FROM transactions WHERE customer_id = ? AND tx_date BETWEEN ? AND ?"
        " AND category IN " + _SPEND_IN + " AND tx_type = 'purchase'",
        (customer_id, c["start"], c["end"]))
    cur = _spend_by_category(store, customer_id, c["start"], c["end"])
    total = sum(r["amt"] for r in cur.values())
    buckets = _bucket_totals(cur)
    income = _income(store, customer_id, c["start"], c["end"])
    months = c["days"] / DAYS_PER_MONTH
    shares = {b: (v / total if total else 0.0) for b, v in buckets.items()}
    social = sum(cur.get(k, {"amt": 0})["amt"] for k in ("Restaurants", "Entertainment",
                                                         "Lifestyle"))
    purchase_total = agg["total"]
    weekend_share = agg["weekend"] / purchase_total if purchase_total else 0.0
    late_share = agg["late"] / purchase_total if purchase_total else 0.0
    savings_rate = (income - total) / income if income else None
    peer = store.peer(cust["age_band"], "total")
    peer_buckets = {b: store.peer(cust["age_band"], "bucket:" + b) for b in BUCKET_LABELS}

    traits = []
    if savings_rate is not None:
        traits.append("You keep %.0f%% of your income after spending." % (100 * savings_rate)
                      if savings_rate >= 0 else
                      "You spent %.0f%% more than you earned in this period."
                      % (-100 * savings_rate))
    traits.append("%.0f%% of your spending is regular essentials, %.0f%% everyday spending."
                  % (100 * shares[ESSENTIALS], 100 * shares[EVERYDAY]))
    if weekend_share > 0.35:
        traits.append("%.0f%% of card spending lands on weekends." % (100 * weekend_share))
    if late_share > 0.10:
        traits.append("%.0f%% of card spending happens late at night." % (100 * late_share))

    if shares[ESSENTIALS] >= 0.65:
        archetype, why = "Squeezed by essentials", "Fixed costs take most of your money."
    elif total and social / total >= 0.30:
        archetype, why = "Social spender", "Eating out, fun and shopping are a big slice."
    elif weekend_share >= 0.40:
        archetype, why = "Weekend splurger", "Your spending peaks on weekends."
    elif savings_rate is not None and savings_rate >= 0.15 and shares[EVERYDAY] <= 0.30:
        archetype, why = "Steady planner", "You spend predictably and keep a healthy margin."
    else:
        archetype, why = "Balanced spender", "A mix of essentials and everyday spending."

    return {
        **_period_info(c, period), "archetype": archetype, "why": why, "traits": traits,
        "total_spend": _r(total), "monthly_spend": _r(total / months),
        "income": _r(income), "savings_rate_pct": _r(100 * savings_rate, 1)
        if savings_rate is not None else None,
        "bucket_shares_pct": {b: _r(100 * s, 1) for b, s in shares.items()},
        "weekend_share_pct": _r(100 * weekend_share, 1),
        "late_night_share_pct": _r(100 * late_share, 1),
        "avg_purchase": _r(agg["avg_amt"]), "purchases": agg["n"],
        "purchases_per_week": _r(agg["n"] / (c["days"] / 7.0), 1),
        "distinct_merchants": agg["merchants"],
        "top_category": max(cur, key=lambda k: cur[k]["amt"]) if cur else None,
        "peer_group": {"age_band": cust["age_band"], "n": peer["n"] if peer else 0},
        "peer_monthly_spend_median": _r(peer["median_monthly"]) if peer else None,
        "peer_bucket_median_monthly": {b: _r(p["median_monthly"]) if p else None
                                       for b, p in peer_buckets.items()},
        "monthly_by_bucket": {b: _r(v / months) for b, v in buckets.items()},
    }


def safe_to_spend(store, customer_id, args):
    horizon = int(args.get("horizon_days", 7))
    as_of_s = store.as_of(customer_id)
    if not as_of_s:
        raise ValueError("no transactions for this customer")
    as_of = _d(as_of_s)
    first = _d(store.one("SELECT MIN(tx_date) AS d FROM transactions WHERE customer_id = ?",
                         (customer_id,))["d"])
    look_start = max(first, as_of - dt.timedelta(days=89))
    look_days = (as_of - look_start).days + 1
    end = as_of + dt.timedelta(days=horizon)
    balance = store.one("SELECT balance_after AS b FROM transactions WHERE customer_id = ?"
                        " ORDER BY tx_ts DESC, id DESC LIMIT 1", (customer_id,))["b"]
    by_cat = _spend_by_category(store, customer_id, look_start.isoformat(), as_of_s)

    def per_day(cats):
        return sum(by_cat.get(k, {"amt": 0})["amt"] for k in cats) / look_days

    variable = per_day(("Groceries", "Transportation", "Utilities")) * horizon
    reserve = per_day(("Health", "Home & Tech")) * horizon
    typical_everyday = per_day(("Restaurants", "Entertainment", "Lifestyle", "Travel")) * horizon
    monthly_spend = sum(r["amt"] for r in by_cat.values()) / look_days * DAYS_PER_MONTH
    buffer = max(50.0, 0.05 * monthly_spend)

    def recurring(category, sign):
        rows = store.rows(
            "SELECT tx_date, amount FROM transactions WHERE customer_id = ? AND category = ?"
            " AND tx_date >= ? ORDER BY tx_date",
            (customer_id, category, (as_of - dt.timedelta(days=240)).isoformat()))
        if not rows:
            return None
        dates = [_d(r["tx_date"]) for r in rows]
        recent = [abs(r["amount"]) for r in rows[-3:]]
        nxt = _next_recurring(dates, as_of)
        return {"date": nxt, "amount": statistics.fmean(recent)} if nxt else None

    housing = recurring("Housing", -1)
    salary = recurring("Salary", 1)
    housing_due = housing["amount"] if housing and housing["date"] <= end else 0.0
    income_in = salary["amount"] if salary and salary["date"] <= end else 0.0

    safe = max(0.0, balance + income_in - housing_due - variable - reserve - buffer)
    if safe >= typical_everyday:
        status = "comfortable"
    elif safe >= 0.5 * typical_everyday:
        status = "tight"
    else:
        status = "very_tight"
    return {
        "as_of": as_of_s, "until": end.isoformat(), "horizon_days": horizon,
        "balance": _r(balance),
        "expected_income": {"amount": _r(income_in),
                            "next_date": salary["date"].isoformat() if salary else None},
        "housing_due": {"amount": _r(housing_due),
                        "next_date": housing["date"].isoformat() if housing else None},
        "expected_essentials": _r(variable), "reserve_for_surprises": _r(reserve),
        "buffer": _r(buffer), "safe_to_spend": _r(safe),
        "safe_per_day": _r(safe / horizon), "typical_everyday_spend": _r(typical_everyday),
        "status": status,
    }


_TIPS = {
    "Restaurants": "Plan two or three meals out instead of grabbing food on impulse.",
    "Entertainment": "Review subscriptions and pick one or two outings to keep.",
    "Lifestyle": "Wait 48 hours before non-essential shopping purchases.",
    "Travel": "Book trips earlier and compare dates; set a trip budget up front.",
    "Groceries": "Plan the week's meals and shop with a list; fewer small top-up trips.",
    "Transportation": "Check whether a monthly pass or carpooling beats paying per trip.",
}
_CANDIDATES = ("Groceries", "Transportation", "Restaurants", "Entertainment", "Lifestyle",
               "Travel")


def _benchmark_rows(store, customer_id, c, cust):
    cur = _spend_by_category(store, customer_id, c["start"], c["end"])
    months = c["days"] / DAYS_PER_MONTH
    rows = []
    for cat in SPEND_CATEGORIES:
        mine = cur.get(cat, {"amt": 0.0})["amt"] / months
        p = store.peer(cust["age_band"], cat)
        rows.append({
            "category": cat, "bucket": CATEGORY_BUCKET[cat], "monthly": _r(mine),
            "peer_median": _r(p["median_monthly"]) if p else None,
            "peer_average": _r(p["avg_monthly"]) if p else None,
            "diff_vs_median": _r(mine - p["median_monthly"]) if p else None,
            "diff_pct": _pct(mine - p["median_monthly"], p["median_monthly"])
            if p and p["median_monthly"] else None})
    return rows


def peer_comparison(store, customer_id, args):
    period = args.get("period", "last_90_days")
    c = _ctx(store, customer_id, period)
    cust = store.customer(customer_id)
    rows = _benchmark_rows(store, customer_id, c, cust)
    peer_total = store.peer(cust["age_band"], "total")
    mine_total = sum(r["monthly"] for r in rows)
    return {
        **_period_info(c, period),
        "peer_group": {"age_band": cust["age_band"], "n": peer_total["n"] if peer_total else 0,
                       "description": "customers aged %s" % cust["age_band"]},
        "monthly_spend": _r(mine_total),
        "peer_median_monthly_spend": _r(peer_total["median_monthly"]) if peer_total else None,
        "categories": rows,
    }


def savings_opportunities(store, customer_id, args):
    period = args.get("period", "last_90_days")
    c = _ctx(store, customer_id, period)
    cust = store.customer(customer_id)
    months = c["days"] / DAYS_PER_MONTH
    bench = {r["category"]: r for r in _benchmark_rows(store, customer_id, c, cust)}
    income = _income(store, customer_id, c["start"], c["end"])
    spend = sum(r["monthly"] for r in bench.values())

    ideas = []
    for cat in _CANDIDATES:
        r = bench[cat]
        excess = max(0.0, r["diff_vs_median"] or 0.0)
        ideas.append({"category": cat, "monthly": r["monthly"], "peer_median": r["peer_median"],
                      "above_peers_by": _r(excess), "potential_monthly": _r(0.5 * excess)})
    ideas.sort(key=lambda i: -i["potential_monthly"])
    ideas = [i for i in ideas if i["potential_monthly"] >= 5][:3]
    basis = "peer_gap"
    if not ideas:  # already at or below peers: suggest a gentle trim of the biggest discretionary
        basis = "gentle_trim"
        for cat in sorted(("Restaurants", "Entertainment", "Lifestyle", "Travel"),
                          key=lambda k: -bench[k]["monthly"])[:2]:
            if bench[cat]["monthly"] > 0:
                ideas.append({"category": cat, "monthly": bench[cat]["monthly"],
                              "peer_median": bench[cat]["peer_median"], "above_peers_by": 0.0,
                              "potential_monthly": _r(0.1 * bench[cat]["monthly"])})
    for i in ideas:
        merchants = store.rows(
            "SELECT merchant_id, -SUM(amount) AS amt, COUNT(*) AS n FROM transactions"
            " WHERE customer_id = ? AND tx_date BETWEEN ? AND ? AND category = ?"
            " AND merchant_id IS NOT NULL GROUP BY merchant_id ORDER BY amt DESC LIMIT 3",
            (customer_id, c["start"], c["end"], i["category"]))
        i["top_merchants"] = [{"merchant_id": m["merchant_id"],
                               "monthly": _r(m["amt"] / months), "visits": m["n"]}
                              for m in merchants]
        i["tip"] = _TIPS[i["category"]]
    total_potential = sum(i["potential_monthly"] for i in ideas)
    return {
        **_period_info(c, period), "basis": basis,
        "peer_group": {"age_band": cust["age_band"]},
        "monthly_spend": _r(spend),
        "monthly_income": _r(income / months),
        "savings_rate_pct": _r(100 * (income - spend * months) / income, 1) if income else None,
        "ideas": ideas, "total_monthly_potential": _r(total_potential),
        "yearly_potential": _r(12 * total_potential),
    }


_HOUR_BAND = ("CASE WHEN hour < 6 THEN 'night (0-6)' WHEN hour < 12 THEN 'morning (6-12)'"
              " WHEN hour < 18 THEN 'afternoon (12-18)' ELSE 'evening (18-24)' END")
_WEEKDAY = ("CASE weekday WHEN 0 THEN 'Mon' WHEN 1 THEN 'Tue' WHEN 2 THEN 'Wed'"
            " WHEN 3 THEN 'Thu' WHEN 4 THEN 'Fri' WHEN 5 THEN 'Sat' ELSE 'Sun' END")
_BUCKET_CASE = "CASE category %s ELSE 'other' END" % " ".join(
    "WHEN '%s' THEN '%s'" % (k, v) for k, v in CATEGORY_BUCKET.items())
_GROUP_EXPR = {
    "none": "'total'", "category": "category", "merchant": "COALESCE(merchant_id,'(no merchant)')",
    "month": "substr(tx_date,1,7)", "day": "tx_date", "weekday": _WEEKDAY,
    "hour_band": _HOUR_BAND, "bucket": _BUCKET_CASE,
}
_CHRONO = ("month", "day")
_HOUR_RANGE = {"night": (0, 5), "morning": (6, 11), "afternoon": (12, 17), "evening": (18, 23)}


def explore_transactions(store, customer_id, args):
    period = args.get("period", "last_90_days")
    c = _ctx(store, customer_id, period)
    group_by = args.get("group_by", "category")
    metric = args.get("metric", "sum")
    direction = args.get("direction", "spend")
    limit = int(args.get("limit", 10))
    where = ["customer_id = ?", "tx_date BETWEEN ? AND ?"]
    params = [customer_id, c["start"], c["end"]]
    if direction == "spend":
        where.append("category IN " + _SPEND_IN)
    elif direction == "income":
        where.append("category IN " + _INCOME_IN)
    if args.get("category"):
        where.append("category = ?")
        params.append(args["category"])
    if args.get("bucket"):
        cats = [k for k, v in CATEGORY_BUCKET.items() if v == args["bucket"]]
        where.append("category IN (%s)" % ",".join("?" * len(cats)))
        params += cats
    if args.get("merchant_id"):
        where.append("merchant_id = ?")
        params.append(args["merchant_id"])
    if "min_amount" in args:
        where.append("ABS(amount) >= ?")
        params.append(float(args["min_amount"]))
    if "max_amount" in args:
        where.append("ABS(amount) <= ?")
        params.append(float(args["max_amount"]))
    if args.get("day_type") == "weekend":
        where.append("weekday >= 5")
    elif args.get("day_type") == "weekday":
        where.append("weekday < 5")
    if args.get("time_of_day"):
        lo, hi = _HOUR_RANGE[args["time_of_day"]]
        where.append("hour BETWEEN ? AND ?")
        params += [lo, hi]

    value = {"sum": "SUM(ABS(amount))", "count": "COUNT(*)", "avg": "AVG(ABS(amount))",
             "max": "MAX(ABS(amount))"}[metric]
    order = "key ASC" if group_by in _CHRONO else (
        "value %s" % ("ASC" if args.get("order") == "asc" else "DESC"))
    rows = store.rows(
        "SELECT %s AS key, %s AS value, COUNT(*) AS n FROM transactions WHERE %s"
        " GROUP BY key ORDER BY %s LIMIT ?" % (
            _GROUP_EXPR[group_by], value, " AND ".join(where), order),
        params + [limit])
    if group_by in _CHRONO and len(rows) == limit:  # keep the most recent periods
        tail = store.rows(
            "SELECT * FROM (SELECT %s AS key, %s AS value, COUNT(*) AS n FROM transactions"
            " WHERE %s GROUP BY key ORDER BY key DESC LIMIT ?) ORDER BY key ASC" % (
                _GROUP_EXPR[group_by], value, " AND ".join(where)), params + [limit])
        rows = tail
    tot = store.one("SELECT COALESCE(SUM(ABS(amount)),0) AS total, COUNT(*) AS n"
                    " FROM transactions WHERE %s" % " AND ".join(where), params)
    labels = BUCKET_LABELS
    return {
        **_period_info(c, period), "group_by": group_by, "metric": metric,
        "direction": direction,
        "filters": {k: args[k] for k in ("category", "bucket", "merchant_id", "min_amount",
                                         "max_amount", "day_type", "time_of_day") if k in args},
        "groups": [{"key": r["key"], "label": labels.get(r["key"], r["key"]),
                    "value": _r(r["value"]), "count": r["n"]} for r in rows],
        "total": _r(tot["total"]), "count": tot["n"],
    }


# ---------------------------------------------------------------- catalog

_PERIOD = {"type": "string", "enum": PERIODS}


def _params(**props):
    return {"type": "object", "additionalProperties": False, "properties": props}


CATALOG = [
    {"name": "spending_breakdown", "fn": spending_breakdown,
     "description": "Where the money went: spending by category and by the three buckets "
                    "(regular essentials, unexpected necessities, everyday spending), with "
                    "change versus the previous period.",
     "parameters": _params(period=_PERIOD)},
    {"name": "spender_profile", "fn": spender_profile,
     "description": "What kind of spender the customer is: archetype, traits, savings rate, "
                    "weekend and late-night habits, compared to peers of the same age.",
     "parameters": _params(period=_PERIOD)},
    {"name": "safe_to_spend", "fn": safe_to_spend,
     "description": "How much can safely be spent over the next days: balance plus expected "
                    "income minus upcoming housing, expected essentials, a reserve for "
                    "surprises and a buffer.",
     "parameters": _params(horizon_days={"type": "integer", "minimum": 1, "maximum": 31})},
    {"name": "savings_opportunities", "fn": savings_opportunities,
     "description": "Where the customer could save more: categories above the peer median, "
                    "top merchants, concrete tips and the monthly and yearly potential.",
     "parameters": _params(period=_PERIOD)},
    {"name": "peer_comparison", "fn": peer_comparison,
     "description": "Monthly spending per category versus the median of customers of the "
                    "same age band.",
     "parameters": _params(period=_PERIOD)},
    {"name": "explore_transactions", "fn": explore_transactions,
     "description": "Free-form exploration of the customer's own transactions: filter by "
                    "category, bucket, merchant, amount, weekday/weekend and time of day, "
                    "then group (category, merchant, month, day, weekday, hour_band, bucket, "
                    "none) and aggregate (sum, count, avg, max).",
     "parameters": _params(
         period=_PERIOD,
         category={"type": "string", "enum": ALL_CATEGORIES},
         bucket={"type": "string", "enum": list(BUCKET_LABELS)},
         merchant_id={"type": "string", "maxLength": 32},
         min_amount={"type": "number", "minimum": 0, "maximum": 1000000},
         max_amount={"type": "number", "minimum": 0, "maximum": 1000000},
         day_type={"type": "string", "enum": ["weekday", "weekend"]},
         time_of_day={"type": "string", "enum": list(_HOUR_RANGE)},
         direction={"type": "string", "enum": ["spend", "income", "all"]},
         group_by={"type": "string", "enum": list(_GROUP_EXPR)},
         metric={"type": "string", "enum": ["sum", "count", "avg", "max"]},
         order={"type": "string", "enum": ["asc", "desc"]},
         limit={"type": "integer", "minimum": 1, "maximum": 36})},
]
TOOLS = {t["name"]: t for t in CATALOG}


def describe_catalog():
    """Tool descriptions without the Python callables: what the AI model is shown."""
    return [{"name": t["name"], "description": t["description"],
             "parameters": t["parameters"]} for t in CATALOG]


def run(name, store, customer_id, args):
    return TOOLS[name]["fn"](store, customer_id, args)
