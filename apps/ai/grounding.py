"""Are the numbers in an answer backed by the tool results? Used at runtime (the backend
removes unbacked sentences) and by the evaluation (apps/ai/eval/run_eval.py).

Deliberately simple: a number counts as backed if it is close to any number found in the
results (or its ×100 form, for shares), or appears in the customer's question. Numbers up
to 31 are ignored (days, counts, short periods).
"""
import re

_NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:[   ]\d{3})+|\d+)(?:([.,])(\d+))?")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_EXAMPLE = re.compile(r"esim|for example|e\.g\.|for instance|till exempel|t\.ex", re.I)


def numbers_in(text, lang="en"):
    out = []
    for m in _NUM.finditer(text or ""):
        whole = re.sub(r"[   ]", "", m.group(1))
        sep, frac = m.group(2), m.group(3)
        if sep == "," and frac and len(frac) == 3 and lang == "en":
            out.append(float(whole + frac))  # English thousands separator
        elif sep and frac:
            out.append(float(whole + "." + frac))
        else:
            out.append(float(whole))
    return out


def result_numbers(obj, acc=None):
    acc = [] if acc is None else acc
    if isinstance(obj, bool):
        return acc
    if isinstance(obj, (int, float)):
        acc.append(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            result_numbers(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            result_numbers(v, acc)
    elif isinstance(obj, str):  # dates like 2026-09-30, labels like 25-34
        acc += [float(x) for x in re.findall(r"\d+", obj)]
    return acc


def grounded(x, known):
    for v in known:
        for cand in (v, abs(v), v * 100, abs(v) * 100):
            if abs(x - cand) <= max(1.0, 0.015 * abs(cand)):
                return True
    return False


def unbacked(text, known, lang="en"):
    """Numbers in `text` above 31 that are not backed by `known`."""
    return [x for x in numbers_in(text, lang) if x > 31 and not grounded(x, known)]


def known_numbers(results, question="", lang="en", context=None):
    known = result_numbers([r.get("data") for r in results if r.get("ok")])
    known += numbers_in(question, lang)
    if context:
        known += result_numbers(context)
    return known


def strip_unbacked(answer, known, safe_text, allow_examples=False):
    """Drop sentences and insights with unbacked numbers. Returns (answer, removed)."""
    lang = answer.get("lang", "en")
    removed = []
    kept = []
    for s in _SENTENCE.split(answer.get("text", "")):
        bad = unbacked(s, known, lang)
        if bad and not (allow_examples and _EXAMPLE.search(s)):
            removed += bad
        else:
            kept.append(s)
    insights = []
    for i in answer.get("insights", []):
        bad = unbacked(i.get("title", "") + " " + i.get("body", ""), known, lang)
        if bad:
            removed += bad
        else:
            insights.append(i)
    text = " ".join(kept).strip() or safe_text
    return dict(answer, text=text, insights=insights), removed
