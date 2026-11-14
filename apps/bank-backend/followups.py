"""Follow-up questions: 0-3 tappable next questions under an answer.

Idea and first version by CuriousGeorg1 (branch feat/t009). Tapping one sends its
`prompt` as the next command, exactly as if the customer had typed it.

Two sources, in this order:
- the AI provider's suggestions (Gemma; see apps/ai/llm_provider.py);
- `fallback()`: rule-based ones from the calculation results, in the answer's language,
  filling up to 3 slots (Gemma often gives one vague suggestion; OpenRouter gives none).

Every suggestion then goes through `clean()`: it must be answerable (the scope check
would not attach a "can't do that" notice to it), must not quote merchant ids or numbers
the tools did not produce, and duplicates and the question just asked are dropped.
"""
from ai.grounding import unbacked
from cloud import glossary
from present import Fmt
import scope

CAP = 3

# (label, prompt) templates per language; {cat} is the localized category name
T = {
    "save": {"en": ("How could I save more?", "How could I save more?"),
             "fi": ("Miten voisin säästää enemmän?", "Miten voisin säästää enemmän?"),
             "sv": ("Hur kan jag spara mer?", "Hur kan jag spara mer?")},
    "cut": {"en": ("Cut {cat} by 20%?", "What if I cut {cat} by 20%?"),
            "fi": ("{Cat} −20 %?", "Mitä jos vähentäisin kategoriaa {Cat} 20 %?"),
            "sv": ("{Cat} −20 %?", "Vad händer om jag minskar {cat} med 20 %?")},
    "where": {"en": ("Where did my money go?", "Where did my money go this month?"),
              "fi": ("Mihin rahat menivät?", "Mihin rahani menivät tässä kuussa?"),
              "sv": ("Vart tog pengarna vägen?", "Vart tog mina pengar vägen den här månaden?")},
    "safe": {"en": ("Safe to spend this week?", "What can I safely spend this week?"),
             "fi": ("Turvallinen kulutus tällä viikolla?",
                    "Paljonko voin turvallisesti kuluttaa tällä viikolla?"),
             "sv": ("Tryggt att spendera i veckan?",
                    "Hur mycket kan jag tryggt spendera den här veckan?")},
    # big purchases (T020); {thing} per kind below, {price} formatted for the language
    "range": {"en": ("What price could I afford?", "How expensive a {thing} could I afford?"),
              "fi": ("Mikä hinta mahtuisi?", "Minkä hintainen {thing} mahtuisi lukuihini?"),
              "sv": ("Vilket pris klarar jag?", "Hur dyr {thing} skulle mina siffror klara?")},
    "longer": {"en": ("With a 30-year loan?",
                      "Could I afford a {thing} for {price} with a 30-year loan?"),
               "fi": ("30 vuoden lainalla?",
                      "Voisinko ostaa {thing_obj} hintaan {price} 30 vuoden lainalla?"),
               "sv": ("Med 30 års lån?",
                      "Har jag råd med {thing_obj} för {price} med 30 års lån?")},
}
THING = {"home": {"en": ("home", "home"), "fi": ("asunto", "asunnon"),
                  "sv": ("bostad", "en bostad")},
         "car": {"en": ("car", "car"), "fi": ("auto", "auton"), "sv": ("bil", "en bil")},
         "other": {"en": ("big purchase", "big purchase"), "fi": ("iso hankinta", "ison hankinnan"),
                   "sv": ("stort köp", "ett stort köp")}}


def _purchase_fu(key, lang, kind, price=None, fu_kind="explore"):
    lang = lang if lang in ("en", "fi", "sv") else "en"
    label, prompt = T[key][lang]
    thing, thing_obj = THING[kind][lang]
    prompt = prompt.replace("{thing_obj}", thing_obj).replace("{thing}", thing)
    if price is not None:
        prompt = prompt.replace("{price}", Fmt(lang).eur(price))
    return {"kind": fu_kind, "label": label, "prompt": prompt}


def _fu(key, lang, kind="explore", cat=None):
    lang = lang if lang in ("en", "fi", "sv") else "en"
    label, prompt = T[key][lang]
    if cat:
        name = glossary.category(cat, lang)
        lower = name if lang == "en" else name[:1].lower() + name[1:]
        label = label.replace("{Cat}", name).replace("{cat}", lower)
        prompt = prompt.replace("{Cat}", name).replace("{cat}", lower)
    return {"kind": kind, "label": label, "prompt": prompt}


def fallback(results, lang):
    """Rule-based suggestions from the results (same rules as the first version)."""
    out = []
    for r in results:
        if not r.get("ok"):
            continue
        tool, d = r["tool"], r["data"]
        if tool == "spending_breakdown":
            top = next((c for c in d["categories"] if c["amount"] > 0
                        and c["category"] not in ("Housing", "Utilities")), None)
            if top:
                out.append(_fu("cut", lang, cat=top["category"]))
            out.append(_fu("save", lang))
        elif tool == "spender_profile":
            out += [_fu("save", lang), _fu("where", lang)]
        elif tool == "safe_to_spend":
            out.append(_fu("save", lang) if d["status"] in ("tight", "very_tight")
                       else _fu("where", lang))
        elif tool == "savings_opportunities":
            # where would they like to save? the top ideas as one-tap choices
            out += [_fu("cut", lang, "clarify", i["category"]) for i in d["ideas"][:2]]
        elif tool == "purchase_affordability":
            if d["status"] != "range_only":
                out.append(_purchase_fu("range", lang, d["kind"]))
                if d["kind"] == "home" and d["assumptions"]["loan_years"] < 30:
                    out.append(_purchase_fu("longer", lang, d["kind"], d["price"], "clarify"))
            if d["status"] != "fits":
                out.append(_fu("save", lang))
        elif tool in ("simulate_change", "explore_transactions"):
            out += [_fu("save", lang), _fu("safe", lang)]
    return out


def clean(items, question, lang, data_as_of, known):
    """Keep only valid, answerable, honest suggestions; dedupe; at most CAP."""
    out, seen = [], {(question or "").strip().lower()}
    for f in items or []:
        if not isinstance(f, dict):
            continue
        label = str(f.get("label", "")).strip()[:80]
        prompt = str(f.get("prompt", "")).strip()[:200]
        if not label or not prompt or prompt.lower() in seen:
            continue
        if scope.limitation(prompt, lang, data_as_of):  # would get a "can't" notice
            continue
        if scope.MERCHANT_ID.search(label + " " + prompt):
            continue
        if unbacked(label + " " + prompt, known, lang):
            continue
        seen.add(prompt.lower())
        out.append({"kind": f.get("kind") if f.get("kind") in ("clarify", "explore")
                    else "explore", "label": label, "prompt": prompt})
        if len(out) == CAP:
            break
    return out
