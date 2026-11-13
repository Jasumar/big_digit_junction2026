"""Builds the visuals for an answer from calculation results. Deterministic, no model.

Visual shapes: stats {items:[{label,value,sub?,tone?}]}, bars {title, items:[{label,value,
display,note?,tone?}], max?}, table {title, columns, rows}.
"""


def eur(x):
    return "€{:,.0f}".format(x)


def build(results):
    out = []
    for r in results:
        if r["ok"]:
            fn = globals().get("_" + r["tool"])
            if fn:
                out += fn(r["data"])
    return out


def _spending_breakdown(d):
    return [
        {"type": "stats", "items": [
            {"label": "Spent", "value": eur(d["total_spend"]),
             "sub": "%s to %s" % (d["from"], d["to"])},
            {"label": "Income", "value": eur(d["income"])}]},
        {"type": "bars", "title": "Three kinds of spending",
         "items": [{"label": b["label"], "value": b["amount"], "display": eur(b["amount"]),
                    "note": "%.0f%%" % b["share_pct"], "tone": b["bucket"]}
                   for b in d["buckets"]]},
        {"type": "bars", "title": "By category",
         "items": [{"label": c["category"], "value": c["amount"], "display": eur(c["amount"]),
                    "note": "%+.0f%%" % c["change_pct"] if c["change_pct"] is not None else "",
                    "tone": c["bucket"]} for c in d["categories"]]},
    ]


def _spender_profile(d):
    items = [{"label": "Type", "value": d["archetype"]},
             {"label": "Monthly spend", "value": eur(d["monthly_spend"]),
              "sub": "peers %s" % eur(d["peer_monthly_spend_median"])
              if d["peer_monthly_spend_median"] else ""}]
    if d["savings_rate_pct"] is not None:
        items.append({"label": "Kept of income", "value": "%.0f%%" % d["savings_rate_pct"]})
    items.append({"label": "Weekend share", "value": "%.0f%%" % d["weekend_share_pct"]})
    labels = {"essentials": "Regular essentials", "necessities": "Unexpected necessities",
              "everyday": "Everyday spending"}
    peers = d["peer_bucket_median_monthly"]
    mine = d["monthly_by_bucket"]
    return [{"type": "stats", "items": items},
            {"type": "bars", "title": "Monthly spend vs peers (median)",
             "items": [it for b in labels for it in (
                 {"label": labels[b], "value": mine[b], "display": eur(mine[b]), "tone": b},
                 {"label": "  peers", "value": peers[b] or 0,
                  "display": eur(peers[b] or 0), "tone": "peer"})]}]


def _safe_to_spend(d):
    rows = [["Balance now", eur(d["balance"])]]
    if d["expected_income"]["amount"]:
        rows.append(["Income expected", "+" + eur(d["expected_income"]["amount"])])
    if d["housing_due"]["amount"]:
        rows.append(["Housing payment", "-" + eur(d["housing_due"]["amount"])])
    rows += [["Expected essentials", "-" + eur(d["expected_essentials"])],
             ["Reserve for surprises", "-" + eur(d["reserve_for_surprises"])],
             ["Safety buffer", "-" + eur(d["buffer"])],
             ["Safe to spend", eur(d["safe_to_spend"])]]
    tone = {"comfortable": "good", "tight": "warn", "very_tight": "bad"}[d["status"]]
    return [{"type": "stats", "items": [
        {"label": "Safe to spend", "value": eur(d["safe_to_spend"]), "tone": tone,
         "sub": "next %d days, until %s" % (d["horizon_days"], d["until"])},
        {"label": "Per day", "value": eur(d["safe_per_day"])}]},
        {"type": "table", "title": "How it adds up", "columns": ["", "EUR"], "rows": rows}]


def _savings_opportunities(d):
    if not d["ideas"]:
        return []
    return [{"type": "stats", "items": [
        {"label": "Possible savings", "value": eur(d["total_monthly_potential"]) + "/mo",
         "tone": "good", "sub": "%s a year" % eur(d["yearly_potential"])}]},
        {"type": "table", "title": "Where to start",
         "columns": ["Category", "You", "Peers", "Save"],
         "rows": [[i["category"], eur(i["monthly"]),
                   eur(i["peer_median"]) if i["peer_median"] is not None else "-",
                   eur(i["potential_monthly"])] for i in d["ideas"]]}]


def _peer_comparison(d):
    return [{"type": "bars", "title": "Monthly: you vs median of %s" % d["peer_group"][
        "description"], "items": [it for c in d["categories"] for it in (
            {"label": c["category"], "value": c["monthly"], "display": eur(c["monthly"]),
             "tone": c["bucket"]},
            {"label": "  peers", "value": c["peer_median"] or 0,
             "display": eur(c["peer_median"] or 0), "tone": "peer"})]}]


def _explore_transactions(d):
    if not d["groups"]:
        return [{"type": "stats", "items": [{"label": "Nothing found", "value": "€0"}]}]
    unit = (lambda v: str(int(v))) if d["metric"] == "count" else eur
    return [{"type": "stats", "items": [{"label": "Total", "value": eur(d["total"]),
                                         "sub": "%d transactions" % d["count"]}]},
            {"type": "bars", "title": "%s by %s" % (d["metric"], d["group_by"]),
             "items": [{"label": g["label"], "value": g["value"], "display": unit(g["value"]),
                        "note": "%d×" % g["count"]} for g in d["groups"]]}]
