"""Closing question: every answer ends by keeping the conversation going (T021).

The provider may propose one ("Would you like to see restaurants month by month?"). It is
kept only if it is a short question in the answer's language that the coach could
actually follow up on: no numbers the tools did not produce, no merchant ids, nothing the
scope check would refuse. Otherwise, or when the provider gave none (stub, OpenRouter),
a friendly general question in the answer's language is used. If the answer text itself
ends with a question, that question is moved here so the answer never asks twice.
"""
import re

from ai.grounding import unbacked
import scope

GENERIC = {
    "fi": ["Haluatko tietää vielä jotain muuta rahoistasi?",
           "Voinko auttaa vielä jossain muussa?",
           "Haluatko katsoa jotain tarkemmin?"],
    "sv": ["Vill du veta något mer om din ekonomi?",
           "Kan jag hjälpa dig med något annat?",
           "Vill du titta närmare på något?"],
    "en": ["Is there anything else you'd like to know?",
           "Can I help you with anything else?",
           "Would you like to look at anything in more detail?"],
}
MAX_LEN = 160
_LAST_QUESTION = re.compile(r"(?:^|(?<=[.!?…])\s+)([^.!?…]*\?)\s*$")


def generic(lang, question=""):
    """A general closing question; varies with the question so it does not repeat."""
    options = GENERIC.get(lang, GENERIC["en"])
    return options[sum(map(ord, question or "")) % len(options)]


def valid(text, lang, question, data_as_of, known):
    t = (text or "").strip()
    if not (8 <= len(t) <= MAX_LEN) or not t.endswith("?") or t.count("?") > 1:
        return False
    if t.lower() == (question or "").strip().lower():
        return False
    if scope.guess_lang(t) not in (None, lang):
        return False
    if lang == "en" and re.search(r"[åäö]", t.lower()):  # Finnish/Swedish letters
        return False
    if scope.MERCHANT_ID.search(t) or unbacked(t, known, lang):
        return False
    return not scope.limitation(t, lang, data_as_of)  # never offer what we cannot do


def finish(answer, proposed, question, data_as_of, known, history=None):
    """Return (text, closing): the answer text without a trailing question, and the
    closing question to show after the charts."""
    lang = answer.get("lang", "en")
    text = (answer.get("text") or "").rstrip()
    m = _LAST_QUESTION.search(text)
    if m and text[:m.start(1)].strip():  # the text ends with its own question: move it
        asked = m.group(1).strip()
        text = text[:m.start(1)].rstrip()
        if not (proposed or "").strip() or not valid(proposed, lang, question, data_as_of, known):
            proposed = asked
    said = " ".join(h.get("text", "") for h in history or []
                    if isinstance(h, dict) and h.get("role") != "user").lower()
    for cand in (proposed,):
        if valid(cand, lang, question, data_as_of, known) and cand.strip().lower() not in said:
            return text, cand.strip()
    options = [g for g in GENERIC.get(lang, GENERIC["en"]) if g.lower() not in said]
    return text, (options[sum(map(ord, question or "")) % len(options)] if options
                  else generic(lang, question))
