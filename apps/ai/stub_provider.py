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
        "safely spend this week, where you could save, what-ifs like 'what if I cut "
        "restaurants by 20%?', and whether your finances could carry a big purchase like "
        "'could I afford a €20,000 car?'. "
        "Try one of those, or ask about a category like restaurants or groceries.")
GREETING = "Hi! I'm your money coach. "
THANKS = "You're welcome! Anything else about your money? "

# big purchases (T020): intent words and what is being bought, en/fi/sv
_BUY = r"afford|\bbuy|purchase|\bvaraa\b|\bosta|\bhankki|mahtu|\bråd\b|\bköp|klara"
_KINDS = (("home", r"\bhome|\bhouse|apartment|\bflat\b|\bcondo|asun|\btalo|kaksio|yksiö|"
                   r"\bkoti|bostad|\bhus\b|lägenhet|villa"),
          ("car", r"\bcar\b|\bauto|\bbil\b|\bbilen\b"))
_MONEY = re.compile(r"(?<![\d.,])(\d{1,3}(?:[ ,.\u00a0]\d{3})+|\d+(?:[.,]\d+)?)\s*"
                    r"(k\b|t\b|tuhat\w*|thousand|tusen)?")
_DOWN = re.compile(r"(down|käsiraha|omarahoitus|omaa rahaa|kontantinsats|insats)")
_YEARS = re.compile(r"(\d{1,2})[\s-]*(?:year|yr|vuo\w*|år)")
_PURCHASE_TWEAK = re.compile(r"down|käsiraha|omarahoitus|kontantinsats|insats|year loan|"
                             r"vuoden laina|laina-aika|års lån|interest|korko|ränta")


def _amounts(text):
    """[(value, start, end)] for money-looking numbers: '25 000 €', '€25,000', '300k'."""
    out = []
    for m in _MONEY.finditer(text.lower()):
        raw, mult = m.group(1), m.group(2)
        digits = re.sub(r"[ ,.\u00a0]", "", raw) if re.search(r"[ ,.\u00a0]\d{3}\b", raw) \
            else raw.replace(",", ".")
        try:
            v = float(digits)
        except ValueError:
            continue
        if mult:
            v *= 1000
        out.append((v, m.start(), m.end()))
    return out


def _purchase(text):
    """Args for purchase_affordability from one message, or None if it is not about one."""
    t = text.lower()
    kind = next((k for k, rx in _KINDS if re.search(rx, t)), None)
    if not (re.search(_BUY, t) and (kind or re.search(r"big purchase|iso hankinta|"
                                                      r"stort köp", t))):
        return None
    args = {"kind": kind or "other"}
    years = _YEARS.search(t)
    if years:
        args["loan_years"] = max(0, min(int(years.group(1)), 35))
    amounts = [(v, st, en) for v, st, en in _amounts(t)
               if not (years and st == years.start())]
    downs = [v for v, st, en in amounts if _next_to_down(t, st, en)]
    prices = [v for v, st, en in amounts if v >= 500 and v not in downs]
    if prices:  # the largest amount: "a 2024 car for 18 000 €" costs 18 000 €
        args["price"] = min(max(prices), 5000000.0)
        if downs and downs[0] < args["price"]:
            args["down_payment"] = downs[0]
    return args


def _next_to_down(t, start, end):
    """'40 000 down', 'put 40k down', 'käsiraha 40 000', 'insats på 40 000'."""
    return bool(_DOWN.search(t[end:end + 12]) or _DOWN.search(t[max(0, start - 16):start]))


def _purchase_followup(text, history):
    """'what if I put 40 000 down?' after a purchase question: earlier kind and price, the
    new value on top."""
    t = text.lower()
    if not _PURCHASE_TWEAK.search(t):
        return None
    earlier = None
    for h in reversed(history or []):
        if h.get("role") == "user":
            earlier = _purchase(h.get("text", ""))
            if earlier:
                break
    if not earlier or "price" not in earlier:
        return None
    args = dict(earlier)
    years = _YEARS.search(t)
    if years:
        args["loan_years"] = max(0, min(int(years.group(1)), 35))
    for v, start, end in _amounts(t):
        if v >= 100 and not (years and start == years.start()) and _DOWN.search(t):
            args["down_payment"] = min(v, args["price"])
            break
    return args


def eur(x):
    return ("-" if round(x) < 0 else "") + "€{:,.0f}".format(abs(x))


def _dedupe_follow_ups(items):
    """Keep order, drop exact-duplicate prompts (several tools can suggest the same one)."""
    seen, out = set(), []
    for f in items:
        if f["prompt"] not in seen:
            seen.add(f["prompt"])
            out.append(f)
    return out


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
    def plan(self, text, tools, history=None, context=None):
        t = text.lower()
        period = _period(text)
        p = {"period": period} if period else {}
        cat = _category(text)

        purchase = _purchase(text) or _purchase_followup(text, history)
        if purchase:
            return {"requests": [{"tool": "purchase_affordability", "args": purchase}]}
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
        if re.search(r"^\W*(hi|hello|hey|moi|hei|terve|hej|hallå)\b", t):
            return {"requests": [], "reply": GREETING + HELP}
        if re.search(r"\b(thanks|thank you|kiitos|tack)\b", t):
            return {"requests": [], "reply": THANKS}
        return {"requests": [], "reply": HELP}

    # ------------------------------------------------------------ step 6
    FOLLOW_UP_CAP = 3

    def compose(self, text, results, history=None, context=None):
        parts, insights, follow_ups = [], [], []
        for r in results:
            if not r["ok"]:
                parts.append("I couldn't run '%s': %s." % (r["tool"], r.get("error", "failed")))
                continue
            fn = getattr(self, "_" + r["tool"], None)
            if fn:
                t, ins = fn(r["data"])
                parts.append(t)
                insights += ins
            fu = getattr(self, "_followups_" + r["tool"], None)
            if fu:
                follow_ups += fu(r["data"])
        if not parts:
            parts.append(HELP)
        return {"text": " ".join(parts), "insights": insights, "lang": "en",
                "follow_ups": _dedupe_follow_ups(follow_ups)[:self.FOLLOW_UP_CAP]}

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
        for s in d.get("signals", []):  # guesses: hedged, with their evidence
            ev = s["evidence"]
            body = ("At least %d purchases, %s." % (ev["count"], eur(ev["amount_eur"]))
                    if "count" in ev else "%d of the last %d months." % (
                        ev.get("months_with_deposit", ev.get("months_with_salary", 0)),
                        ev["months"]))
            label = s["label"][:1].lower() + s["label"][1:]
            ins.append({"title": "Looks like: %s" % label, "body": body, "kind": "info"})
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
            text += " You already spend at or below your own usual, so these are gentle " \
                    "trims of your biggest extras."
        ins = []
        for i in d["ideas"]:
            gap = ("%s a month above your own usual. " % eur(i["above_usual_by"])
                   if i["above_usual_by"] else "")
            ins.append({"title": "%s: save ~%s/month" % (i["category"],
                                                          eur(i["potential_monthly"])),
                        "kind": "tip", "body": gap + i["tip"]})
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

    _VERDICT = {
        "fits": "On your last 12 months' numbers, this fits",
        "stretch": "On your last 12 months' numbers this could work, but it would be a stretch",
        "save_first": "Your monthly money could carry it, but your savings don't cover the "
                      "down payment and a safety buffer yet",
        "over_budget": "On your last 12 months' numbers, this doesn't fit your monthly "
                       "money right now",
    }
    _THING = {"home": "a home", "car": "a car", "other": "this purchase"}

    def _purchase_affordability(self, d):
        a = d["assumptions"]
        thing = self._THING[d["kind"]]
        if d["status"] == "range_only":
            if not d["max_price_estimate"]:
                text = ("Right now your savings above a safety buffer don't cover a down "
                        "payment for %s, so I can't show a price range yet." % thing)
            else:
                text = ("With your current savings and monthly money, %s up to about %s "
                        "would fit the same rules" % (thing, eur(d["max_price_estimate"])))
                text += (" (%d-year loan at %g%% interest)." % (a["loan_years"],
                                                                  a["interest_rate_pct"])
                         if a["loan_years"] else ", paid in cash.")
            return text + " What price do you have in mind?", []
        text = "%s: %s for %s." % (self._VERDICT[d["status"]], thing, eur(d["price"]))
        if d["monthly_payment"]:
            text += " The loan would cost about %s a month over %d years at %g%%." % (
                eur(d["monthly_payment"]), a["loan_years"], a["interest_rate_pct"])
        after = d["monthly_margin_after"]
        text += (" You'd have about %s left each month afterwards (now %s)." % (
            eur(after), eur(d["monthly_margin"])) if after >= 0 else
            " You'd be about %s short each month afterwards (now %s left over)." % (
            eur(-after), eur(d["monthly_margin"])))
        text += " This is an illustration from your own data, not a loan decision — the " \
                "choice is yours."
        ins = []
        if d["savings_gap"]:
            body = "%s more for the down payment and a %d-month buffer" % (
                eur(d["savings_gap"]), a["buffer_months"])
            body += (", about %d months at your current pace." % d["months_to_close_gap"]
                     if d["months_to_close_gap"] else ".")
            ins.append({"title": "Still to save", "kind": "warn", "body": body})
        if d["monthly_margin_after_stress"] is not None:
            m = d["monthly_margin_after_stress"]
            ins.append({"title": "If interest rose to %g%%" % a["stress_rate_pct"],
                        "kind": "good" if m >= 0 else "warn",
                        "body": ("You'd still have %s left each month." % eur(m)) if m >= 0
                        else "You'd be about %s short each month." % eur(-m)})
        if d["housing_cost_freed"]:
            ins.append({"title": "Rent you'd stop paying", "kind": "info",
                        "body": "About %s a month is counted as freed up." % eur(
                            d["housing_cost_freed"])})
        return text, ins[:3]

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

    # -------------------------------------------------------- follow-ups
    # By CuriousGeorg1 (feat/t009). English, like the rest of the stub; each prompt is
    # something the stub itself understands. The backend checks them (followups.clean).

    def _followups_spending_breakdown(self, d):
        out = []
        top = next((c for c in d["categories"] if c["amount"] > 0
                    and c["category"] not in ("Housing", "Utilities")), None)
        if top:
            out.append({"kind": "explore", "label": "Cut %s by 20%%?" % top["category"],
                        "prompt": "What if I cut %s by 20%%?" % top["category"]})
        out.append({"kind": "explore", "label": "How could I save more?",
                    "prompt": "How could I save more?"})
        return out

    def _followups_spender_profile(self, d):
        return [{"kind": "explore", "label": "How could I save more?",
                 "prompt": "How could I save more?"},
                {"kind": "explore", "label": "Spending more than before?",
                 "prompt": "Am I spending more than before?"}]

    def _followups_safe_to_spend(self, d):
        if d["status"] in ("tight", "very_tight"):
            return [{"kind": "explore", "label": "How could I save more?",
                     "prompt": "How could I save more?"}]
        return []

    def _followups_savings_opportunities(self, d):
        # where would they like to save? the top ideas as one-tap choices
        return [{"kind": "clarify", "label": "Cut back on %s" % i["category"],
                 "prompt": "What if I cut %s by 20%%?" % i["category"]}
                for i in d["ideas"][:2]]

    def _followups_purchase_affordability(self, d):
        thing = {"home": "home", "car": "car", "other": "big purchase"}[d["kind"]]
        if d["status"] == "range_only":
            return [{"kind": "explore", "label": "How could I save more?",
                     "prompt": "How could I save more?"}]
        out = [{"kind": "explore", "label": "What price could I afford?",
                "prompt": "How expensive a %s could I afford?" % thing}]
        if d["kind"] == "home" and d["assumptions"]["loan_years"] < 30:
            out.append({"kind": "clarify", "label": "With a 30-year loan?",
                        "prompt": "Could I afford a home for %s with a 30-year loan?"
                                  % eur(d["price"])})
        if d["status"] in ("save_first", "over_budget", "stretch"):
            out.append({"kind": "explore", "label": "How could I save more?",
                        "prompt": "How could I save more?"})
        return out

    def _followups_simulate_change(self, d):
        return [{"kind": "explore", "label": "How could I save more?",
                 "prompt": "How could I save more?"}]
