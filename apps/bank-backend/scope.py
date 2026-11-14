"""Deterministic check: does the question ask for something the tools cannot do?

The model is also told its limits, but it does not reliably admit them (it answered
"March?" with September). This keyword check runs on every question; when it fires and
the model did not already give a limitation, the backend adds a notice to the answer.
Finnish, Swedish and English; simple stems on purpose — a false notice is harmless, a
missing one misleads.
"""
import re

MONTHS = {  # month number -> stems
    1: ["tammikuu", "januari", "january"], 2: ["helmikuu", "februari", "february"],
    3: ["maaliskuu", " mars ", "march"], 4: ["huhtikuu", "april"],
    5: ["toukokuu", " maj ", " in may"], 6: ["kesäkuu", "juni", "june"],
    7: ["heinäkuu", "juli", "july"], 8: ["elokuu", "augusti", "august"],
    9: ["syyskuu", "september"], 10: ["lokakuu", "oktober", "october"],
    11: ["marraskuu", "november"], 12: ["joulukuu", "december"],
}

RULES = [  # (key, regex on lower-cased question)
    # banking secrecy (T017): the coach has no data about other customers, not even
    # aggregates, so any comparison with other people is declined
    ("others", r"ikäis|ikätover|samanikäi|muihin (asiakk|ihmis|suomal|ikä)|muut (asiakkaat|"
               r"ihmiset)|keskiverto|keskivert|keskimääräi\w* (suomalai|asiakas|ihmi|kotital)|"
               r"mediaani|vertaudun muihin|vertautu\w* muihin|"
               r"\bpeers?\b|others my age|people my age|my age group|other (people|customers|"
               r"users)|average (person|customer|finn|household|user)|compared? (to|with) "
               r"others|than others|median|"
               r"jämnårig|andra i min ålder|andra kunder|andra människor|genomsnittlig\w* "
               r"(kund|person|finländare|hushåll)|jämfört med andra"),
    ("date", r"\beilen\b|\byesterday\b|\bigår\b|\btoissapäivänä\b|\b\d{1,2}\.\s?\d{1,2}\.|"
             r"\b\d{1,2}\.\s?(päivä|tammi|helmi|maalis|huhti|touko|kesä|heinä|elo|syys|loka|"
             r"marras|joulu)"),
    ("year", r"(tänä vuonna|this year|i år).*(viime vuonna|last year|förra året)|"
             r"(viime vuonna|last year|förra året).*(tänä vuonna|this year|i år)|"
             r"\b20[12]\d\b"),
    ("store", r"budjet|budget|muistut|remind|påminn|tavoite|\bgoal\b|\bmål\b|aseta |set a |"
              r"sätt en "),
    ("shop", r"prisma|s-market|k-market|citymarket|lidl|alepa|\bsale\b|tokmanni|ikea|"
             r"gigantti|verkkokauppa|\balko\b|hesburger|mcdonald|starbucks|wolt|foodora|"
             r"\buber\b|\bbolt\b|netflix|spotify|amazon|zalando|\bica\b|\bcoop\b"),
    # taxis, fuel, pharmacies etc. are answerable since T014 (merchant category codes);
    # coffee and tobacco have no code of their own
    ("sub", r"kahvi|kaffe|coffee|tupak|tobacco|tobak"),
    ("subscr", r"tilau|subscript|prenumer|kuukausimaksu|kestotilaus"),
    ("list", r"viimeiset \d|viimeisimmät|last \d+ (purchase|transaction|payment)|"
             r"senaste \d|näytä (kaikki )?(ostok|tapahtum)|list (my|all)|show (my|all) "
             r"(purchases|transactions)|lista"),
    ("balance_hist", r"(saldo|balance).*(alimm|lowest|högst|highest|korkein|history|historia|"
                     r"kehity)"),
]

# Big-purchase questions (T020) are answerable: "within my budget" there is not a request
# to store a budget, and "a 2024 car" is not a calendar-year comparison.
PURCHASE = (r"afford|\bbuy|purchase|\bvaraa\b|\bosta|\bhankki|mahtu|\bråd\b|\bköp|klara")
PURCHASE_THING = (r"\bhome|\bhouse|apartment|\bflat\b|\bcondo|\bcar\b|asun|\btalo|kaksio|"
                  r"yksiö|\bauto|\bkoti|bostad|\bhus\b|lägenhet|villa|\bbil\b|\bbilen\b")
_PURCHASE_SKIPS = ("store", "year")


def is_purchase(question):
    q = (question or "").lower()
    return bool(re.search(PURCHASE, q) and re.search(PURCHASE_THING, q))


TEXT = {
    "others": {"fi": "Näen vain sinun omat tietosi – en vertaa sinua muihin asiakkaisiin, en edes keskiarvoina. Voin verrata kulutustasi omaan aiempaan kulutukseesi.",
               "sv": "Jag ser bara dina egna uppgifter – jag jämför dig inte med andra kunder, inte ens som genomsnitt. Jag kan jämföra dina utgifter med dina egna tidigare utgifter.",
               "en": "I only see your own data — I don't compare you with other customers, not even as averages. I can compare your spending with your own earlier spending."},
    "month": {"fi": "En voi valita tiettyä kalenterikuukautta; näytän lähimmän saatavilla olevan jakson.",
              "sv": "Jag kan inte välja en viss kalendermånad; jag visar närmaste tillgängliga period.",
              "en": "I can't pick a specific calendar month; I'm showing the closest available period."},
    "date": {"fi": "En voi näyttää yksittäistä päivää; näytän lähimmän saatavilla olevan jakson.",
             "sv": "Jag kan inte visa en enskild dag; jag visar närmaste tillgängliga period.",
             "en": "I can't show a single day; I'm showing the closest available period."},
    "weekday": {"fi": "En voi rajata yhteen viikonpäivään (vain arki vs. viikonloppu = la–su).",
                "sv": "Jag kan inte filtrera på en enskild veckodag (bara vardag vs. helg = lör–sön).",
                "en": "I can't filter one weekday (only weekdays vs. weekend = Sat–Sun)."},
    "year": {"fi": "En voi verrata kalenterivuosia; vertaan viimeistä 12 kuukautta edelliseen 12 kuukauteen.",
             "sv": "Jag kan inte jämföra kalenderår; jag jämför senaste 12 månader med de 12 före.",
             "en": "I can't compare calendar years; I compare the last 12 months with the 12 before."},
    "store": {"fi": "En voi tallentaa budjetteja, tavoitteita tai muistutuksia.",
              "sv": "Jag kan inte spara budgetar, mål eller påminnelser.",
              "en": "I can't save budgets, goals or reminders."},
    "shop": {"fi": "Tiedoissa ei ole kauppojen nimiä, joten en voi näyttää kulutusta tiettyyn kauppaan.",
             "sv": "Datan har inga butiksnamn, så jag kan inte visa utgifter i en viss butik.",
             "en": "The data has no shop names, so I can't show spending at a specific shop."},
    "sub": {"fi": "Kahville tai tupakalle ei ole omaa kauppakoodia; näytän lähimmän luokan (esim. ravintolat ja kahvilat).",
            "sv": "Kaffe och tobak har ingen egen butikskod; jag visar närmaste kategori (t.ex. restauranger och kaféer).",
            "en": "Coffee and tobacco have no merchant code of their own; I'm showing the closest category (e.g. restaurants and cafés)."},
    "subscr": {"fi": "En pysty tunnistamaan tilauksia tiedoista.",
               "sv": "Jag kan inte känna igen prenumerationer i datan.",
               "en": "I can't identify subscriptions in the data."},
    "list": {"fi": "En voi listata yksittäisiä tapahtumia; näytän yhteenvedon.",
             "sv": "Jag kan inte lista enskilda transaktioner; jag visar en sammanfattning.",
             "en": "I can't list individual transactions; I'm showing a summary."},
    "balance_hist": {"fi": "Saldohistoriaa ei ole saatavilla, vain nykyinen saldo.",
                     "sv": "Saldohistorik finns inte, bara nuvarande saldo.",
                     "en": "Balance history isn't available, only the current balance."},
}


def limitation(question, lang, data_as_of):
    """Localized limitation sentence if the question asks for something unsupported."""
    q = " " + (question or "").lower() + " "
    lang = lang if lang in ("fi", "sv", "en") else "en"
    if data_as_of:  # this month and last month are supported; other named months are not
        cur = int(data_as_of[5:7])
        ok = {cur, 12 if cur == 1 else cur - 1}
        for m, stems in MONTHS.items():
            if m not in ok and any(s in q for s in stems):
                return TEXT["month"][lang]
    purchase = is_purchase(question)
    for key, rx in RULES:
        if purchase and key in _PURCHASE_SKIPS:
            continue
        if re.search(rx, q):
            return TEXT[key][lang]
    return ""


MERCHANT_ID = re.compile(r"\bMRC-[A-Z]{3}-\d{4}\b")
SHOP_WORD = {"fi": "yksi kauppa", "sv": "en butik", "en": "a shop"}


def redact_merchants(answer):
    """Synthetic merchant ids mean nothing to a customer; never show them in text."""
    word = SHOP_WORD.get(answer.get("lang"), "a shop")
    fix = lambda s: MERCHANT_ID.sub(word, s or "")  # noqa: E731
    return dict(answer, text=fix(answer.get("text")),
                insights=[dict(i, title=fix(i.get("title")), body=fix(i.get("body")))
                          for i in answer.get("insights", [])])


def drop_foreign_terms(answer):
    """Remove bracketed glossary terms in another language, e.g. an English answer adding
    "(arjen pikkukulut / vardagsutgifter)"."""
    from cloud.glossary import BUCKETS
    lang = answer.get("lang", "en")
    foreign = [v[lg].lower() for v in BUCKETS.values() for lg in ("en", "fi", "sv") if lg != lang]
    def fix(s):
        def repl(m):
            return "" if any(t in m.group(0).lower() for t in foreign) else m.group(0)
        return re.sub(r"\s?\([^()]{0,120}\)", repl, s or "")
    return dict(answer, text=fix(answer.get("text")),
                insights=[dict(i, title=fix(i.get("title")), body=fix(i.get("body")))
                          for i in answer.get("insights", [])])


_LANG_WORDS = {
    "fi": {"paljonko", "mihin", "miten", "millainen", "mitä", "olen", "minun", "rahani",
           "kuussa", "viime", "tässä", "voin", "kulutin", "käytin", "jos", "eilen", "onko",
           "kuinka", "näytä", "minä", "vuonna", "kannattaa", "sijoittanut", "säästää",
           "haluatko", "voinko", "katsotaanko", "näytänkö", "kerronko", "muuta", "vielä"},
    "sv": {"hur", "mycket", "vart", "mina", "pengar", "jag", "kan", "den", "här", "månaden",
           "veckan", "vilken", "är", "spendera", "spara", "igår", "förra", "visa",
           "vill", "du", "något", "annat", "mer", "titta"},
    "en": {"how", "much", "what", "where", "did", "spend", "spent", "my", "money", "can",
           "this", "last", "month", "week", "the", "yesterday", "show", "could", "save",
           "would", "you", "like", "want", "see", "else", "anything"},
}


def guess_lang(text):
    """Language of a question by common words; None if unsure. The model's own guess was
    wrong at times (Gemma 4 marked an English question as Finnish)."""
    words = re.findall(r"[a-zåäö]+", (text or "").lower())
    scores = {k: sum(w in v for w in words) for k, v in _LANG_WORDS.items()}
    best = max(scores, key=scores.get)
    ranked = sorted(scores.values(), reverse=True)
    return best if ranked[0] >= 1 and ranked[0] > ranked[1] else None


def _term_map(lang):
    """Glossary terms of the other languages -> the answer language's term."""
    from cloud import glossary
    idx = {"en": 0, "fi": 1, "sv": 2}
    out = {}
    for key, names in glossary.BUCKETS.items():
        for lg in ("en", "fi", "sv"):
            if lg != lang and names[lg] != names[lang]:
                out[names[lg]] = names[lang]
    for cat, names in glossary.CATEGORIES.items():
        target = cat.lower() if lang == "en" else names[lang].split(" (")[0]
        for lg in ("fi", "sv"):
            if lg != lang:
                src = names[lg].split(" (")[0]
                if src.lower() != target.lower():
                    out[src] = target
    return out


def localize_terms(answer):
    """Replace basket/category names written in another language (Gemma 4 left Finnish
    "pakolliset säännölliset menot" in English and Swedish answers)."""
    lang = answer.get("lang", "en")
    terms = sorted(_term_map(lang).items(), key=lambda kv: -len(kv[0]))

    def fix(s):
        s = s or ""
        for src, dst in terms:
            def repl(m, dst=dst):
                return dst[:1].upper() + dst[1:] if m.group(0)[:1].isupper() else dst
            s = re.sub(r"(?<![\w])%s(?![\w])" % re.escape(src), repl, s, flags=re.I)
        return s
    return dict(answer, text=fix(answer.get("text")),
                insights=[dict(i, title=fix(i.get("title")), body=fix(i.get("body")))
                          for i in answer.get("insights", [])])
