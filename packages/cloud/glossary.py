"""Names per language for baskets, categories and spender types. Shared by the AI
prompts (apps/ai/llm_provider.py) and the charts (apps/bank-backend/present.py), so the
text and the charts always use the same words. Next to taxonomy.py because both describe
what the data means.

Tool results carry English labels and stable keys (category names, bucket keys,
`archetype_key`); the model is told to translate them with this table instead of
inventing its own words. Finnish/Swedish wording: draft, to be confirmed by a native
speaker (docs/MASTER_PLAN.md question 11).
"""

BUCKETS = {
    "essentials": {"en": "regular essentials", "fi": "pakolliset säännölliset menot",
                   "sv": "nödvändiga fasta utgifter"},
    "necessities": {"en": "unexpected necessities", "fi": "pakolliset yllättävät menot",
                    "sv": "nödvändiga oväntade utgifter"},
    "everyday": {"en": "everyday spending", "fi": "arjen pikkukulut",
                 "sv": "vardagsutgifter"},
}

CATEGORIES = {  # long forms explain the category to the model; charts use SHORT below
    "Housing": {"fi": "asuminen (vuokra tai vastike)", "sv": "boende (hyra eller avgift)"},
    "Utilities": {"fi": "asumisen laskut (sähkö, vesi, netti)", "sv": "boenderäkningar (el, vatten, internet)"},
    "Groceries": {"fi": "ruokaostokset", "sv": "matinköp"},
    "Transportation": {"fi": "liikkuminen", "sv": "transport"},
    "Health": {"fi": "terveys", "sv": "hälsa"},
    "Home & Tech": {"fi": "koti ja elektroniikka", "sv": "hem och elektronik"},
    "Restaurants": {"fi": "ravintolat ja kahvilat", "sv": "restauranger och kaféer"},
    "Entertainment": {"fi": "viihde", "sv": "nöjen"},
    "Lifestyle": {"fi": "vaatteet ja ostokset", "sv": "kläder och shopping"},
    "Travel": {"fi": "matkailu", "sv": "resor"},
}

# Short chart labels where the prompt form is long
SHORT = {"Housing": {"fi": "Asuminen", "sv": "Boende"},
         "Utilities": {"fi": "Asumisen laskut", "sv": "Boenderäkningar"}}

# Subcategory names (keys in taxonomy.SUBCATEGORIES): (en, fi, sv)
SUBCATEGORY_NAMES = {
    "taxi": ("Taxis", "Taksit", "Taxi"),
    "public_transport": ("Public transport", "Joukkoliikenne", "Kollektivtrafik"),
    "fuel": ("Fuel", "Polttoaine", "Bränsle"),
    "parking": ("Parking", "Pysäköinti", "Parkering"),
    "restaurant": ("Restaurants", "Ravintolat", "Restauranger"),
    "fast_food": ("Fast food", "Pikaruoka", "Snabbmat"),
    "bar": ("Bars", "Baarit", "Barer"),
    "supermarket": ("Supermarkets", "Ruokakaupat", "Livsmedelsbutiker"),
    "convenience_store": ("Convenience stores", "Lähikaupat ja erikoisliikkeet", "Närbutiker"),
    "meat_and_dairy": ("Meat and dairy shops", "Liha- ja maitokaupat", "Kött- och mejeributiker"),
    "pharmacy": ("Pharmacies", "Apteekit", "Apotek"),
    "doctor": ("Doctors and health services", "Lääkärit ja terveyspalvelut", "Läkare och vård"),
    "dentist": ("Dentists", "Hammaslääkärit", "Tandläkare"),
    "electronics": ("Electronics", "Elektroniikka", "Elektronik"),
    "furniture": ("Furniture", "Huonekalut", "Möbler"),
    "hardware_store": ("Hardware and home supply", "Rauta- ja kodintarvikkeet", "Järn- och hemvaror"),
    "clothing": ("Clothing", "Vaatteet", "Kläder"),
    "sporting_goods": ("Sporting goods", "Urheiluvälineet", "Sportartiklar"),
    "books": ("Books", "Kirjat", "Böcker"),
    "toys_and_hobbies": ("Toys and hobbies", "Lelut ja harrastukset", "Leksaker och hobby"),
    "other_shops": ("Other shops", "Muut kaupat", "Övriga butiker"),
    "cinema": ("Cinema", "Elokuvat", "Bio"),
    "events_and_tickets": ("Events and tickets", "Tapahtumat ja liput", "Evenemang och biljetter"),
    "attractions": ("Attractions and amusement parks", "Nähtävyydet ja huvipuistot", "Sevärdheter och nöjesparker"),
    "recreation": ("Recreation", "Vapaa-aika", "Fritid"),
    "flights": ("Flights", "Lennot", "Flyg"),
    "hotels": ("Hotels", "Hotellit", "Hotell"),
    "car_rental": ("Car rental", "Autonvuokraus", "Biluthyrning"),
    "travel_agency": ("Travel agencies", "Matkatoimistot", "Resebyråer"),
    "unknown": ("No merchant code", "Ei kauppakoodia", "Ingen butikskod"),
}

ARCHETYPES = {
    "squeezed": {"en": "Squeezed by essentials", "fi": "Pakollisten menojen puristuksessa",
                 "sv": "Pressad av nödvändiga utgifter"},
    "social": {"en": "Social spender", "fi": "Sosiaalinen kuluttaja", "sv": "Social konsument"},
    "weekend": {"en": "Weekend splurger", "fi": "Viikonlopputuhlaaja",
                "sv": "Helgslösare"},
    "planner": {"en": "Steady planner", "fi": "Vakaa suunnittelija", "sv": "Stabil planerare"},
    "balanced": {"en": "Balanced spender", "fi": "Tasapainoinen kuluttaja",
                 "sv": "Balanserad konsument"},
}


def prompt_table():
    """Compact glossary text for the system prompt."""
    lines = ["Baskets (key: English | Finnish | Swedish):"]
    lines += ["- %s: %s | %s | %s" % (k, v["en"], v["fi"], v["sv"]) for k, v in BUCKETS.items()]
    lines.append("Categories (data name: Finnish | Swedish):")
    lines += ["- %s: %s | %s" % (k, v["fi"], v["sv"]) for k, v in CATEGORIES.items()]
    lines.append("Subcategories (key: English | Finnish | Swedish):")
    lines += ["- %s: %s | %s | %s" % ((k,) + v) for k, v in SUBCATEGORY_NAMES.items()
              if k != "unknown"]
    lines.append("Spender types (archetype_key: English | Finnish | Swedish):")
    lines += ["- %s: %s | %s | %s" % (k, v["en"], v["fi"], v["sv"])
              for k, v in ARCHETYPES.items()]
    return "\n".join(lines)


def category(name, lang):
    """Chart label for a data category in a language (falls back to the data name)."""
    if lang not in ("fi", "sv"):
        return name
    short = SHORT.get(name, {}).get(lang)
    if short:
        return short
    text = CATEGORIES.get(name, {}).get(lang, name)
    return text[:1].upper() + text[1:]


def bucket(key, lang):
    text = BUCKETS.get(key, {}).get(lang if lang in ("fi", "sv") else "en", key)
    return text[:1].upper() + text[1:]


def archetype(key, lang, fallback=""):
    return ARCHETYPES.get(key, {}).get(lang if lang in ("fi", "sv", "en") else "en", fallback)


def subcategory(key, lang):
    names = SUBCATEGORY_NAMES.get(key)
    if not names:
        return key
    return names[{"en": 0, "fi": 1, "sv": 2}.get(lang, 0)]
