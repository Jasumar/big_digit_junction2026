"""Rule-based stand-in for the AI model: keyword intent -> tool requests -> templated text.

Same interface as a real provider (see provider.py), so the whole flow works offline.
"""
import re

CATEGORY_WORDS = {
    "Groceries": ("grocer", "supermarket", "food shop"),
    "Restaurants": ("restaurant", "eating out", "dining", "takeaway", "cafe", "coffee",
                    "lunch", "dinner"),
    "Transportation": ("transport", "fuel", "petrol", "taxi", "bus", "train", "commut",
                       "car "),
    "Entertainment": ("entertainment", "cinema", "movie", "game", "concert", "streaming"),
    "Health": ("health", "pharmacy", "doctor", "dentist"),
    "Travel": ("travel", "hotel", "flight", "holiday", "vacation"),
    "Lifestyle": ("lifestyle", "shopping", "clothes", "clothing", "fashion"),
    "Home & Tech": ("electronics", "furniture", "home & tech", "tech", "gadget"),
    "Utilities": ("utilit", "electricity", "internet", "phone bill"),
    "Housing": ("housing", "rent", "mortgage"),
}
BUCKET_WORDS = {
    "everyday": ("everyday", "extras", "small purchases", "slips through"),
    "necessities": ("necessit", "unexpected", "surprise", "irregular"),
    "essentials": ("essential", "fixed cost", "regular bills"),
}
HELP = ("I can show where your money went, what kind of spender you are, what you can "
        "safely spend this week, how you compare with others, where you could save, and "
        "what-ifs like 'what if I cut restaurants by 20%?'. "
        "Try one of those, or ask about a category like restaurants or groceries.")


def eur(x):
    return "€{:,.0f}".format(x)


def _period(text):
    t = text.lower()
    if "last month" in t or "previous month" in t:
        return "last_month"
    if "this month" in t:
        return "this_month"
    if "week" in t or "7 days" in t:
        return "last_7_days"
    if "year" in t or "12 months" in t:
        return "last_12_months"
    if "90 days" in t or "quarter" in t or "3 months" in t or "three months" in t:
        return "last_90_days"
    return None


def _what_if(text):
    """'reduced dining out by 20%' -> simulate_change args, or None if not a what-if."""
    t = text.lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(%|percent|per cent)", t)
    change_words = re.search(r"reduc|cut|less|lower|stop|quit|half|more|increase|raise|"
                             r"drop|skip", t)
    if not (m or re.search(r"what if|if i\b", t)) or not change_words:
        return None
    if m:
        pct = float(m.group(1))
    elif "half" in t:
        pct = 50.0
    elif re.search(r"stop|quit|no more|skip", t):
        pct = 100.0
    else:
        pct = 20.0
    up = re.search(r"more|increase|raise", t) and not re.search(r"reduc|cut|less|lower", t)
    args = {"change_pct": pct if up else -min(pct, 100.0)}
    cat = _category(text)
    if cat:
        args["category"] = cat
    else:
        args["bucket"] = next((b for b, ws in BUCKET_WORDS.items()
                               if any(w in t for w in ws)), "everyday")
    h = re.search(r"(\d+)\s*(month|year)", t)
    if h:
        n = int(h.group(1)) * (12 if h.group(2) == "year" else 1)
        args["months_ahead"] = max(1, min(n, 60))
    return args


def _category(text):
    t = " " + text.lower() + " "
    for cat, words in CATEGORY_WORDS.items():
        if any(w in t for w in words):
            return cat
    return None


class Provider:
    name = "stub"

    # ------------------------------------------------------------ step 2
    def plan(self, text, tools, history=None):
        t = text.lower()
        period = _period(text)
        p = {"period": period} if period else {}
        cat = _category(text)

        what_if = _what_if(text)
        if what_if:
            return {"requests": [{"tool": "simulate_change", "args": what_if}]}
        if re.search(r"safe|afford|can i spend|how much (can|could) i (spend|afford)|budget for", t):
            days = 30 if "month" in t else 1 if ("today" in t or "tonight" in t) else 7
            return {"requests": [{"tool": "safe_to_spend", "args": {"horizon_days": days}}]}
        if re.search(r"kind of spender|type of spender|spender|my habits|profile|personality", t):
            return {"requests": [{"tool": "spender_profile", "args": p}]}
        if re.search(r"save|saving|cut (back|down)|reduce|cheaper|economi", t):
            return {"requests": [{"tool": "savings_opportunities", "args": p}]}
        if re.search(r"compare|average|others|peers|benchmark|typical|normal", t):
            return {"requests": [{"tool": "peer_comparison", "args": p}]}
        if re.search(r"weekend|night|late|morning|evening", t) and not cat:
            args = dict(p)
            if "weekend" in t:
                args["day_type"] = "weekend"
            for tod in ("night", "morning", "evening"):
                if tod in t or (tod == "night" and "late" in t):
                    args["time_of_day"] = tod
                    break
            args["group_by"] = "category"
            return {"requests": [{"tool": "explore_transactions", "args": args}]}
        if cat or re.search(r"merchant|biggest|largest|most|top|trend|over time|per month",
                            t):
            args = dict(p)
            if cat:
                args["category"] = cat
            if re.search(r"trend|over time|per month|monthly|each month", t):
                args["group_by"] = "month"
                args["limit"] = 12
            elif re.search(r"merchant|shop|store|where|top|most|biggest|largest", t):
                args["group_by"] = "merchant" if cat else "category"
                args["limit"] = 5
            else:
                args["group_by"] = "month"
                args["limit"] = 6
            return {"requests": [{"tool": "explore_transactions", "args": args}]}
        if re.search(r"where|money go|spend|spent|spending|breakdown|categor|essential|"
                     r"necessit|everyday|expens", t):
            return {"requests": [{"tool": "spending_breakdown", "args": p}]}
        return {"requests": [], "reply": HELP}

    # ------------------------------------------------------------ step 6
    def compose(self, text, results, history=None):
        parts, insights = [], []
        for r in results:
            if not r["ok"]:
                parts.append("I couldn't run '%s': %s." % (r["tool"], r.get("error", "failed")))
                continue
            fn = getattr(self, "_" + r["tool"], None)
            if fn:
                t, ins = fn(r["data"])
                parts.append(t)
                insights += ins
        if not parts:
            parts.append(HELP)
        return {"text": " ".join(parts), "insights": insights}

    def _spending_breakdown(self, d):
        top = d["categories"][0] if d["categories"] else None
        b = {x["bucket"]: x for x in d["buckets"]}
        text = "In the period %s to %s you spent %s" % (d["from"], d["to"], eur(d["total_spend"]))
        if d["change_pct"] is not None:
            text += " (%+.0f%% vs the period before)" % d["change_pct"]
        text += ". Regular essentials took %s, unexpected necessities %s and everyday " \
                "spending %s." % (eur(b["essentials"]["amount"]),
                                  eur(b["necessities"]["amount"]),
                                  eur(b["everyday"]["amount"]))
        ins = []
        if top:
            ins.append({"title": "Biggest cost: %s" % top["category"], "kind": "info",
                        "body": "%s, %.0f%% of your spending." % (eur(top["amount"]),
                                                                 top["share_pct"])})
        movers = [c for c in d["categories"] if c["change_pct"] is not None
                  and abs(c["amount"] - c["previous_amount"]) >= 50]
        if movers:
            m = max(movers, key=lambda c: abs(c["amount"] - c["previous_amount"]))
            up = m["amount"] > m["previous_amount"]
            ins.append({"title": "%s %s" % (m["category"], "went up" if up else "went down"),
                        "kind": "warn" if up else "good",
                        "body": "%s now vs %s before (%+.0f%%)." % (
                            eur(m["amount"]), eur(m["previous_amount"]), m["change_pct"])})
        return text, ins

    def _spender_profile(self, d):
        text = "Your spender type: %s. %s" % (d["archetype"], d["why"])
        if d["savings_rate_pct"] is not None:
            text += " You kept about %.0f%% of your income." % d["savings_rate_pct"]
        ins = [{"title": t, "body": "", "kind": "info"} for t in d["traits"]]
        pm = d.get("peer_monthly_spend_median")
        if pm:
            diff = d["monthly_spend"] - pm
            ins.append({"title": "Versus people your age", "kind": "good" if diff <= 0 else "warn",
                        "body": "You spend %s a month, %s %s the median of %s." % (
                            eur(d["monthly_spend"]), eur(abs(diff)),
                            "below" if diff <= 0 else "above", eur(pm))})
        return text, ins

    def _safe_to_spend(self, d):
        text = ("You can safely spend about %s over the next %d days (about %s a day), "
                "after rent, essentials and a safety buffer." % (
                    eur(d["safe_to_spend"]), d["horizon_days"], eur(d["safe_per_day"])))
        ins = []
        if d["housing_due"]["amount"]:
            ins.append({"title": "Housing payment coming", "kind": "warn",
                        "body": "About %s around %s is already set aside." % (
                            eur(d["housing_due"]["amount"]), d["housing_due"]["next_date"])})
        if d["expected_income"]["amount"]:
            ins.append({"title": "Income expected", "kind": "good",
                        "body": "About %s around %s." % (
                            eur(d["expected_income"]["amount"]),
                            d["expected_income"]["next_date"])})
        elif d["expected_income"]["next_date"]:
            ins.append({"title": "Next income", "kind": "info",
                        "body": "Expected around %s, after this window." %
                                d["expected_income"]["next_date"]})
        label = {"comfortable": ("good", "You have room above your usual everyday spending."),
                 "tight": ("warn", "Tighter than your usual everyday spending."),
                 "very_tight": ("warn", "Much tighter than usual; hold back on extras.")}
        kind, msg = label[d["status"]]
        ins.append({"title": "Status: %s" % d["status"].replace("_", " "), "kind": kind,
                    "body": "%s You usually spend %s on everyday things in this time." % (
                        msg, eur(d["typical_everyday_spend"]))})
        return text, ins

    def _savings_opportunities(self, d):
        if not d["ideas"]:
            return "I didn't find an obvious place to save in this period.", []
        text = "You could free up around %s a month (%s a year)." % (
            eur(d["total_monthly_potential"]), eur(d["yearly_potential"]))
        if d["basis"] == "gentle_trim":
            text += " You already spend less than most people your age, so these are gentle " \
                    "trims of your biggest extras."
        ins = []
        for i in d["ideas"]:
            gap = ("%s above the median for your age group. " % eur(i["above_peers_by"])
                   if i["above_peers_by"] else "")
            ins.append({"title": "%s: save ~%s/month" % (i["category"],
                                                          eur(i["potential_monthly"])),
                        "kind": "tip", "body": gap + i["tip"]})
        return text, ins

    def _peer_comparison(self, d):
        diff = d["monthly_spend"] - (d["peer_median_monthly_spend"] or 0)
        text = "You spend %s a month; the median for %s is %s." % (
            eur(d["monthly_spend"]), d["peer_group"]["description"],
            eur(d["peer_median_monthly_spend"] or 0))
        rows = [c for c in d["categories"] if c["diff_pct"] is not None
                and abs(c["diff_vs_median"]) >= 30]
        rows.sort(key=lambda c: -abs(c["diff_vs_median"]))
        ins = [{"title": "%s %s peers" % (c["category"], "above" if c["diff_vs_median"] > 0
                                           else "below"),
                "kind": "warn" if c["diff_vs_median"] > 0 else "good",
                "body": "%s a month vs median %s (%+.0f%%)." % (
                    eur(c["monthly"]), eur(c["peer_median"]), c["diff_pct"])}
               for c in rows[:3]]
        if d["peer_median_monthly_spend"]:
            text += " That is %s %s the median." % (eur(abs(diff)),
                                                    "below" if diff <= 0 else "above")
        return text, ins

    def _simulate_change(self, d):
        tgt = d["target"].get("category") or d["target"]["label"].lower()
        verb = "cut" if d["change_pct"] < 0 else "increase"
        saving = d["monthly_saving"]
        text = ("If you %s %s by %.0f%%, you'd spend %s a month instead of %s" % (
            verb, tgt, abs(d["change_pct"]), eur(d["new_monthly"]), eur(d["baseline_monthly"])))
        if saving >= 0:
            text += " — that frees up %s a month, %s a year" % (eur(saving),
                                                              eur(d["yearly_saving"]))
            if d["months_ahead"] != 12:
                text += ", %s over %d months" % (eur(d["saving_over_horizon"]),
                                                d["months_ahead"])
        else:
            text += " — %s more a month, %s a year" % (eur(-saving), eur(-d["yearly_saving"]))
        text += "."
        ins = []
        if d["purchases_change_per_month"]:
            ins.append({"title": "In everyday terms", "kind": "tip",
                        "body": "About %.0f %s purchases a month (you make %.0f now)." % (
                            abs(d["purchases_change_per_month"]),
                            "fewer" if d["purchases_change_per_month"] < 0 else "more",
                            d["purchases_per_month"])})
        if d["savings_rate_pct_now"] is not None:
            better = d["savings_rate_pct_after"] >= d["savings_rate_pct_now"]
            ins.append({"title": "Savings rate", "kind": "good" if better else "warn",
                        "body": "You'd keep %.0f%% of your income instead of %.0f%%." % (
                            d["savings_rate_pct_after"], d["savings_rate_pct_now"])})
        ins.append({"title": "How this is worked out", "kind": "info",
                    "body": "Based on your average for %s to %s. %s" % (
                        d["from"], d["to"], d["note"])})
        return text, ins

    def _explore_transactions(self, d):
        flt = ", ".join("%s=%s" % kv for kv in d["filters"].items()) or "all spending"
        if not d["count"]:
            return "I found no matching transactions for %s between %s and %s." % (
                flt, d["from"], d["to"]), []
        text = "For %s (%s to %s) the total is %s across %d transactions." % (
            flt, d["from"], d["to"], eur(d["total"]), d["count"])
        ins = []
        if d["groups"] and d["group_by"] != "none":
            top = max(d["groups"], key=lambda g: g["value"])
            ins.append({"title": "Highest: %s" % top["label"], "kind": "info",
                        "body": "%s over %d transactions." % (eur(top["value"]), top["count"])})
        return text, ins
