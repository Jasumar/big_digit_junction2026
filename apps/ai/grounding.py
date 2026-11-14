"""Check that the numbers in a model answer come from the tool results.

    check(text, results) -> (ok, unknown_numbers)

Amounts and percentages are extracted from the text (English "1,234.50" / "€1,234" and
Finnish "1 234,50 €" / "12,5 %") and compared with every number found in the results'
`data` and `args`. A number is grounded when it matches a result number within the
rounding it was written with (0 decimals: +-0.5, 2 decimals: +-0.005, ...), or within
1 percentage point for percentages. Signs are ignored ("down 12%" matches -12.3).
Bare integers 0-12 (counts, months), years and dates are not checked.
"""
import math
import re

SPACES = " \u00a0\u202f"
NUMBER = re.compile(
    r"(?<![\d.,])("
    r"\d{1,3}(?:[" + SPACES + r"]\d{3})+(?:[.,]\d+)?"   # 1 234,50
    r"|\d{1,3}(?:,\d{3})+(?:\.\d+)?"                     # 1,234.50
    r"|\d{1,3}(?:\.\d{3})+(?:,\d+)?"                     # 1.234,50
    r"|\d+(?:[.,]\d+)?"                                  # 1234.5 / 12,5
    r")(?!\d)")
DATE_OR_TIME = re.compile(
    r"\d{4}-\d{1,2}-\d{1,2}|(?<![\d.,€$])\d{1,2}\.\d{1,2}\.(?:\d{2,4})?(?!\d)"
    r"|\d{1,2}/\d{1,2}/\d{2,4}|(?<!\d)\d{1,2}:\d{2}(?::\d{2})?")
PERCENT_AFTER = re.compile(r"\s*(?:%|per\s?cent|percent|prosent|procent)", re.I)
CURRENCY_AFTER = re.compile(r"\s*(?:€|eur\b|euro)", re.I)
CURRENCY_BEFORE = re.compile(r"(?:[€$]|\beur)\s*$", re.I)
EPS = 1e-9


def _candidates(token):
    """Possible (value, decimals) readings of a number token; ambiguous ones have two."""
    spaced = any(c in token for c in SPACES)
    s = re.sub("[" + SPACES + "]", "", token)
    if "," in s and "." in s:
        decimal = "," if s.rfind(",") > s.rfind(".") else "."
    elif spaced:
        decimal = "," if "," in s else "."
    else:
        sep = "," if "," in s else "." if "." in s else None
        if sep is None:
            return [(float(s), 0)]
        head, _, tail = s.partition(sep)
        if s.count(sep) > 1:
            return [(float(s.replace(sep, "")), 0)]
        if len(tail) == 3 and 1 <= len(head) <= 3 and head != "0":
            return [(float(head + tail), 0), (float(head + "." + tail), 3)]
        decimal = sep
    thousands = "." if decimal == "," else ","
    s = s.replace(thousands, "").replace(decimal, ".")
    return [(float(s), len(s.split(".")[1]) if "." in s else 0)]


def extract(text):
    """-> [(as_written, kind, candidates)], kind in {"percent", "amount", "bare"}."""
    text = DATE_OR_TIME.sub(" ", text)
    found = []
    for m in NUMBER.finditer(text):
        token = m.group(1)
        if PERCENT_AFTER.match(text, m.end()):
            kind = "percent"
        elif CURRENCY_AFTER.match(text, m.end()) or CURRENCY_BEFORE.search(text[:m.start()]):
            kind = "amount"
        else:
            kind = "bare"
        cands = _candidates(token)
        if kind == "bare":
            value, decimals = cands[0]
            if decimals == 0 and len(cands) == 1:
                grouped = not token.isdigit()
                if value <= 12 or (not grouped and len(token) == 4 and 1900 <= value <= 2100):
                    continue
        found.append((token, kind, cands))
    return found


def result_numbers(results):
    """Every number in the results' data and args, recursively (bools excluded)."""
    numbers = []

    def walk(value):
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            if math.isfinite(value):
                numbers.append(abs(float(value)))
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)

    for result in results or []:
        if isinstance(result, dict):
            walk(result.get("data"))
            walk(result.get("args"))
    return numbers


def _grounded(kind, cands, numbers):
    for value, decimals in cands:
        tolerance = 1.0 if kind == "percent" else 0.5 * 10 ** -decimals
        if any(abs(abs(value) - n) <= tolerance + EPS for n in numbers):
            return True
    return False


def check(text, results):
    """-> (ok, unknown_numbers): numbers in `text` not found in `results`, as written."""
    numbers = result_numbers(results)
    unknown = []
    for token, kind, cands in extract(text or ""):
        if not _grounded(kind, cands, numbers) and token not in unknown:
            unknown.append(token)
    return not unknown, unknown
