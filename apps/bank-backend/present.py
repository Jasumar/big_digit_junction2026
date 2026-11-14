"""Builds the visuals for an answer from calculation results. Deterministic, no model.

Visual shapes: stats {items:[{label,value,sub?,tone?}]}, bars {title, items:[{label,value,
display,note?,tone?}], max?}, table {title, columns, rows}.

Labels, money, percentages and dates follow the answer language (en/fi/sv). Category,
basket and spender-type names come from packages/cloud/glossary.py, the same table the
AI prompts use.
"""
from cloud import glossary

LANGS = ("en", "fi", "sv")

# UI strings per language. Keys are English phrases; %s/%d placeholders stay the same.
T = {
    "Spent": {"fi": "Kulutit", "sv": "Spenderat"},
    "Income": {"fi": "Tulot", "sv": "Inkomster"},
    "%s to %s": {"fi": "%s–%s", "sv": "%s–%s"},
    "Three kinds of spending": {"fi": "Kolme menokoria", "sv": "Tre utgiftskorgar"},
    "By category": {"fi": "Kategorioittain", "sv": "Per kategori"},
    "Type": {"fi": "Tyyppi", "sv": "Typ"},
    "Monthly spend": {"fi": "Kulutus kuukaudessa", "sv": "Utgifter per månad"},
    "peers %s": {"fi": "ikätoverit %s", "sv": "jämnåriga %s"},
    "Kept of income": {"fi": "Tuloista jäi", "sv": "Kvar av inkomsten"},
    "Weekend share": {"fi": "Viikonloppujen osuus", "sv": "Andel på helger"},
    # life signals (calculation/signals.py); Finnish/Swedish wording is a draft (Q11)
    "What your spending suggests": {"fi": "Mitä kulutuksesi kertoo",
                                    "sv": "Vad dina utgifter visar"},
    "Evidence": {"fi": "Peruste", "sv": "Underlag"},
    "at least %d purchases, %s": {"fi": "vähintään %d ostoa, %s", "sv": "minst %d köp, %s"},
    "%d of %d months": {"fi": "%d / %d kuukautta", "sv": "%d av %d månader"},
    "Probably drives a car": {"fi": "Todennäköisesti ajaa autoa", "sv": "Kör troligen bil"},
    "Uses public transport": {"fi": "Käyttää julkista liikennettä", "sv": "Åker kollektivt"},
    "Takes taxis": {"fi": "Käyttää takseja", "sv": "Åker taxi"},
    "Eats out often": {"fi": "Syö usein ulkona", "sv": "Äter ofta ute"},
    "Goes to events and the cinema": {"fi": "Käy tapahtumissa ja elokuvissa",
                                      "sv": "Går på evenemang och bio"},
    "Travels": {"fi": "Matkustaa", "sv": "Reser"},
    "Invests regularly": {"fi": "Sijoittaa säännöllisesti", "sv": "Investerar regelbundet"},
    "Has a regular monthly salary": {"fi": "Saa säännöllistä kuukausipalkkaa",
                                     "sv": "Har regelbunden månadslön"},
    "Monthly spend vs peers (median)": {"fi": "Kuukausikulutus vs. ikätoverit (mediaani)",
                                        "sv": "Utgifter per månad vs. jämnåriga (median)"},
    "peers": {"fi": "ikätoverit", "sv": "jämnåriga"},
    "Balance now": {"fi": "Saldo nyt", "sv": "Saldo nu"},
    "Income expected": {"fi": "Odotetut tulot", "sv": "Väntade inkomster"},
    "Housing payment": {"fi": "Asumismaksu", "sv": "Boendekostnad"},
    "Expected essentials": {"fi": "Odotetut pakolliset menot", "sv": "Väntade nödvändiga utgifter"},
    "Reserve for surprises": {"fi": "Varaus yllätyksiin", "sv": "Reserv för överraskningar"},
    "Safety buffer": {"fi": "Turvapuskuri", "sv": "Säkerhetsbuffert"},
    "Safe to spend": {"fi": "Turvallisesti käytettävissä", "sv": "Tryggt att spendera"},
    "next %d days, until %s": {"fi": "seuraavat %d päivää, %s asti",
                               "sv": "kommande %d dagar, till %s"},
    "Per day": {"fi": "Päivässä", "sv": "Per dag"},
    "How it adds up": {"fi": "Näin summa muodostuu", "sv": "Så räknas det ut"},
    "Possible savings": {"fi": "Mahdollinen säästö", "sv": "Möjlig besparing"},
    "%s/mo": {"fi": "%s/kk", "sv": "%s/mån"},
    "%s a year": {"fi": "%s vuodessa", "sv": "%s per år"},
    "Where to start": {"fi": "Mistä aloittaa", "sv": "Var du kan börja"},
    "Category": {"fi": "Kategoria", "sv": "Kategori"},
    "You": {"fi": "Sinä", "sv": "Du"},
    "Peers": {"fi": "Ikätoverit", "sv": "Jämnåriga"},
    "Save": {"fi": "Säästö", "sv": "Spara"},
    "Monthly: you vs median of customers aged %s": {
        "fi": "Kuukaudessa: sinä vs. %s-vuotiaiden mediaani",
        "sv": "Per månad: du vs. median för %s år"},
    "Per month": {"fi": "Kuukaudessa", "sv": "Per månad"},
    "Extra per month": {"fi": "Lisää kuukaudessa", "sv": "Extra per månad"},
    "Per year": {"fi": "Vuodessa", "sv": "Per år"},
    "In %d months": {"fi": "%d kuukaudessa", "sv": "På %d månader"},
    "%s per month: now vs %s": {"fi": "%s kuukaudessa: nyt vs. %s",
                                "sv": "%s per månad: nu vs. %s"},
    "Now": {"fi": "Nyt", "sv": "Nu"},
    "After": {"fi": "Muutoksen jälkeen", "sv": "Efter"},
    "Nothing found": {"fi": "Ei osumia", "sv": "Inga träffar"},
    "Total": {"fi": "Yhteensä", "sv": "Totalt"},
    "%d transactions": {"fi": "%d tapahtumaa", "sv": "%d transaktioner"},
    "%d transactions, %s–%s": {"fi": "%d tapahtumaa, %s–%s", "sv": "%d transaktioner, %s–%s"},
    "sum": {"fi": "Summa", "sv": "Summa"}, "count": {"fi": "Määrä", "sv": "Antal"},
    "avg": {"fi": "Keskiarvo", "sv": "Medel"}, "max": {"fi": "Suurin", "sv": "Störst"},
    "%s by %s": {"fi": "%s: %s", "sv": "%s: %s"},
    "category": {"fi": "kategoria", "sv": "kategori"}, "merchant": {"fi": "kauppa", "sv": "butik"},
    "month": {"fi": "kuukausi", "sv": "månad"}, "day": {"fi": "päivä", "sv": "dag"},
    "weekday": {"fi": "viikonpäivä", "sv": "veckodag"},
    "hour_band": {"fi": "vuorokaudenaika", "sv": "tid på dygnet"},
    "bucket": {"fi": "menokori", "sv": "utgiftskorg"}, "none": {"fi": "yhteensä", "sv": "totalt"},
    "subcategory": {"fi": "alaluokka", "sv": "underkategori"},
}
WEEKDAYS = {"fi": dict(zip("Mon Tue Wed Thu Fri Sat Sun".split(),
                           "ma ti ke to pe la su".split())),
            "sv": dict(zip("Mon Tue Wed Thu Fri Sat Sun".split(),
                           "mån tis ons tor fre lör sön".split()))}
HOUR_BANDS = {"fi": {"night (22-6)": "yö (22–6)", "morning (6-12)": "aamu (6–12)",
                     "afternoon (12-18)": "iltapäivä (12–18)", "evening (18-22)": "ilta (18–22)"},
              "sv": {"night (22-6)": "natt (22–6)", "morning (6-12)": "morgon (6–12)",
                     "afternoon (12-18)": "eftermiddag (12–18)",
                     "evening (18-22)": "kväll (18–22)"}}


class Fmt:
    """Formatting for one answer language."""

    def __init__(self, lang):
        self.lang = lang if lang in LANGS else "en"

    def t(self, key):
        return T.get(key, {}).get(self.lang, key)

    def eur(self, x):
        n = "{:,.0f}".format(abs(x))
        sign = "-" if x < 0 else ""
        if self.lang == "en":
            return sign + "€" + n
        return sign + n.replace(",", " ") + " €"

    def pct(self, x, signed=False):
        s = ("%+.0f" if signed else "%.0f") % x
        return s + ("%" if self.lang == "en" else " %")

    def date(self, iso):
        if not iso:
            return iso
        y, m, d = iso.split("-")
        if self.lang == "en":  # "1 Oct 2025", like dates in English answer text
            return "%d %s %s" % (int(d), "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec"
                                 .split()[int(m) - 1], y)
        return "%d.%d.%s" % (int(d), int(m), y)

    def cat(self, name):
        return glossary.category(name, self.lang)

    def bucket(self, key):
        return glossary.bucket(key, self.lang)


def build(results, lang="en"):
    f = Fmt(lang)
    out = []
    for r in results:
        if r["ok"]:
            fn = globals().get("_" + r["tool"])
            if fn:
                out += fn(r["data"], f)
    return out


def _spending_breakdown(d, f):
    return [
        {"type": "stats", "items": [
            {"label": f.t("Spent"), "value": f.eur(d["total_spend"]),
             "sub": f.t("%s to %s") % (f.date(d["from"]), f.date(d["to"]))},
            {"label": f.t("Income"), "value": f.eur(d["income"])}]},
        {"type": "bars", "title": f.t("Three kinds of spending"),
         "items": [{"label": f.bucket(b["bucket"]), "value": b["amount"],
                    "display": f.eur(b["amount"]), "note": f.pct(b["share_pct"]),
                    "tone": b["bucket"]} for b in d["buckets"]]},
        {"type": "bars", "title": f.t("By category"),
         "items": [{"label": f.cat(c["category"]), "value": c["amount"],
                    "display": f.eur(c["amount"]),
                    "note": f.pct(c["change_pct"], signed=True)
                    if c["change_pct"] is not None else "",
                    "tone": c["bucket"]} for c in d["categories"] if c["amount"] > 0]},
    ]


def _spender_profile(d, f):
    archetype = glossary.archetype(d.get("archetype_key"), f.lang, d["archetype"])
    items = [{"label": f.t("Type"), "value": archetype},
             {"label": f.t("Monthly spend"), "value": f.eur(d["monthly_spend"]),
              "sub": f.t("peers %s") % f.eur(d["peer_monthly_spend_median"])
              if d["peer_monthly_spend_median"] else ""}]
    if d["savings_rate_pct"] is not None:
        items.append({"label": f.t("Kept of income"), "value": f.pct(d["savings_rate_pct"])})
    items.append({"label": f.t("Weekend share"), "value": f.pct(d["weekend_share_pct"])})
    peers = d["peer_bucket_median_monthly"]
    mine = d["monthly_by_bucket"]
    out = [{"type": "stats", "items": items},
           {"type": "bars", "title": f.t("Monthly spend vs peers (median)"),
            "items": [it for b in ("essentials", "necessities", "everyday") for it in (
                {"label": f.bucket(b), "value": mine[b], "display": f.eur(mine[b]),
                 "tone": b},
                {"label": "  " + f.t("peers"), "value": peers[b] or 0,
                 "display": f.eur(peers[b] or 0), "tone": "peer"})]}]
    rows = [[f.t(s["label"]), _signal_evidence(s["evidence"], f)] for s in d.get("signals", [])]
    if rows:
        out.append({"type": "table", "title": f.t("What your spending suggests"),
                    "columns": ["", f.t("Evidence")], "rows": rows})
    return out


def _signal_evidence(ev, f):
    """Evidence text for one life signal. Purchase counts are minimums (some purchases
    carry no merchant code), so they read 'at least'."""
    if "count" in ev:
        return f.t("at least %d purchases, %s") % (ev["count"], f.eur(ev["amount_eur"]))
    n = ev.get("months_with_deposit", ev.get("months_with_salary", 0))
    return f.t("%d of %d months") % (n, ev["months"])


def _safe_to_spend(d, f):
    rows = [[f.t("Balance now"), f.eur(d["balance"])]]
    if d["expected_income"]["amount"]:
        rows.append([f.t("Income expected"), "+" + f.eur(d["expected_income"]["amount"])])
    if d["housing_due"]["amount"]:
        rows.append([f.t("Housing payment"), "-" + f.eur(d["housing_due"]["amount"])])
    rows += [[f.t("Expected essentials"), "-" + f.eur(d["expected_essentials"])],
             [f.t("Reserve for surprises"), "-" + f.eur(d["reserve_for_surprises"])],
             [f.t("Safety buffer"), "-" + f.eur(d["buffer"])],
             [f.t("Safe to spend"), f.eur(d["safe_to_spend"])]]
    tone = {"comfortable": "good", "tight": "warn", "very_tight": "bad"}[d["status"]]
    return [{"type": "stats", "items": [
        {"label": f.t("Safe to spend"), "value": f.eur(d["safe_to_spend"]), "tone": tone,
         "sub": f.t("next %d days, until %s") % (d["horizon_days"], f.date(d["until"]))},
        {"label": f.t("Per day"), "value": f.eur(d["safe_per_day"])}]},
        {"type": "table", "title": f.t("How it adds up"), "columns": ["", "EUR"], "rows": rows}]


def _savings_opportunities(d, f):
    if not d["ideas"]:
        return []
    return [{"type": "stats", "items": [
        {"label": f.t("Possible savings"),
         "value": f.t("%s/mo") % f.eur(d["total_monthly_potential"]), "tone": "good",
         "sub": f.t("%s a year") % f.eur(d["yearly_potential"])}]},
        {"type": "table", "title": f.t("Where to start"),
         "columns": [f.t("Category"), f.t("You"), f.t("Peers"), f.t("Save")],
         "rows": [[f.cat(i["category"]), f.eur(i["monthly"]),
                   f.eur(i["peer_median"]) if i["peer_median"] is not None else "-",
                   f.eur(i["potential_monthly"])] for i in d["ideas"]]}]


def _peer_comparison(d, f):
    return [{"type": "bars",
             "title": f.t("Monthly: you vs median of customers aged %s")
             % d["peer_group"]["age_band"],
             "items": [it for c in d["categories"] for it in (
                 {"label": f.cat(c["category"]), "value": c["monthly"],
                  "display": f.eur(c["monthly"]), "tone": c["bucket"]},
                 {"label": "  " + f.t("peers"), "value": c["peer_median"] or 0,
                  "display": f.eur(c["peer_median"] or 0), "tone": "peer"})]}]


def _simulate_change(d, f):
    tgt = (f.cat(d["target"]["category"]) if d["target"].get("category")
           else f.bucket(d["target"]["bucket"]))
    saving = d["monthly_saving"]
    items = [{"label": f.t("Per month") if saving >= 0 else f.t("Extra per month"),
              "value": f.eur(abs(saving)), "tone": "good" if saving >= 0 else "warn"},
             {"label": f.t("Per year"), "value": f.eur(abs(d["yearly_saving"]))}]
    if d["months_ahead"] != 12:
        items.append({"label": f.t("In %d months") % d["months_ahead"],
                      "value": f.eur(abs(d["saving_over_horizon"]))})
    return [{"type": "stats", "items": items},
            {"type": "bars",
             "title": f.t("%s per month: now vs %s") % (tgt, f.pct(d["change_pct"], signed=True)),
             "items": [{"label": f.t("Now"), "value": d["baseline_monthly"],
                        "display": f.eur(d["baseline_monthly"]), "tone": "peer"},
                       {"label": f.t("After"), "value": d["new_monthly"],
                        "display": f.eur(d["new_monthly"]),
                        "tone": "good" if saving >= 0 else "warn"}]}]


BILLS = {"en": "Bills and transfers", "fi": "Laskut ja siirrot", "sv": "Räkningar och överföringar"}


def _group_label(g, group_by, f):
    label = g["label"]
    if label == "(bills and transfers)":
        return BILLS[f.lang]
    if group_by == "category":
        return f.cat(label)
    if group_by == "bucket":
        return f.bucket(g["key"])
    if group_by == "subcategory":
        return glossary.subcategory(g["key"], f.lang)
    if group_by == "weekday":
        return WEEKDAYS.get(f.lang, {}).get(label, label)
    if group_by == "hour_band":
        return HOUR_BANDS.get(f.lang, {}).get(label, label)
    if group_by == "day":
        return f.date(label)
    return label


def _explore_transactions(d, f):
    if not d["groups"]:
        return [{"type": "stats", "items": [{"label": f.t("Nothing found"),
                                             "value": f.eur(0)}]}]
    unit = (lambda v: str(int(v))) if d["metric"] == "count" else f.eur
    return [{"type": "stats", "items": [{"label": f.t("Total"), "value": f.eur(d["total"]),
                                         "sub": f.t("%d transactions, %s–%s") % (
                                             d["count"], f.date(d["from"]), f.date(d["to"]))}]},
            {"type": "bars", "title": f.t("%s by %s") % (f.t(d["metric"]), f.t(d["group_by"])),
             "items": [{"label": _group_label(g, d["group_by"], f), "value": g["value"],
                        "display": unit(g["value"]), "note": "%d×" % g["count"]}
                       for g in d["groups"]]}]
