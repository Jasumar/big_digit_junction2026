#!/usr/bin/env python3
"""Evaluate the coach end to end on fixed questions (apps/ai/eval/cases.json).

    set -a; . ./.env; set +a                 # AI_PROVIDER=modal, AI_BASE_URL, AI_API_KEY
    python3 apps/ai/eval/run_eval.py         # all cases against the configured provider
    python3 apps/ai/eval/run_eval.py --provider stub --only fi-where,en-save
    python3 apps/ai/eval/run_eval.py --out report.json   # full answers for reading

Checks per case (all automatic, deliberately simple):
  tool      the first tool the AI asked for is one of the accepted ones ([] = none)
  lang      the answer is in the language of the question (word heuristic)
  ground    every number in the answer appears in the tool results (or the question)
  must_not  none of the forbidden strings appear
  terms     no basket names from another language (e.g. Finnish terms in Swedish)
  money     euro format of the language: English "€1,234", Finnish/Swedish "1 234 €"
  notice    (optional per case) the answer carries / does not carry a "can't fully" notice
  must_any  (optional per case) at least one of the given strings appears
  closing   the answer ends with a closing question in the case's language (T021)
Warm the model first (GET <AI_BASE_URL>/health) or the first case hits a cold start.
"""
import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "apps", "bank-backend"), os.path.join(ROOT, "packages"),
          os.path.join(ROOT, "apps")):
    if p not in sys.path:
        sys.path.insert(0, p)

import orchestrator  # noqa: E402
from ai.provider import get_provider  # noqa: E402
from calculation import tools  # noqa: E402
from cloud.store import Store  # noqa: E402

BASKET_NAMES = {  # inlined so the runner also works on older code without cloud/glossary.py
    "en": ["regular essentials", "unexpected necessities", "everyday spending"],
    "fi": ["pakolliset säännölliset menot", "pakolliset yllättävät menot", "arjen pikkukulut"],
    "sv": ["nödvändiga fasta utgifter", "nödvändiga oväntade utgifter", "vardagsutgifter"],
}
MONEY_WRONG = {"en": re.compile(r"\d\s?€"), "fi": re.compile(r"€\s?\d"),
               "sv": re.compile(r"€\s?\d")}

WORDS = {
    "fi": {"on", "ja", "sinun", "olet", "kuussa", "että", "voit", "noin", "euroa", "menot",
           "tämä", "rahasi", "kulutus", "säästä", "jos", "kuin", "mutta", "tai", "sinulla"},
    "sv": {"och", "är", "du", "din", "för", "att", "det", "har", "kan", "som", "en", "på",
           "dina", "pengar", "månad", "veckan", "inte", "med"},
    "en": {"the", "you", "your", "and", "is", "of", "to", "in", "this", "on", "for", "can",
           "spent", "with", "are", "that"},
}


def detect_lang(text):
    words = re.findall(r"[a-zåäöü]+", text.lower())
    scores = {k: sum(w in v for w in words) for k, v in WORDS.items()}
    return max(scores, key=scores.get) if any(scores.values()) else "?"


from ai.grounding import grounded, numbers_in, result_numbers  # noqa: E402,F401


def run_case(case, store, provider, customer_id):
    captured = {}
    real_run = tools.run

    def spy(name, st, cid, args):  # record results the AI saw, for the grounding check
        data = real_run(name, st, cid, args)
        captured.setdefault("results", []).append(data)
        return data

    tools.run = spy
    try:
        t0 = time.time()
        answer = orchestrator.handle_command({"customer_id": customer_id, "text": case["q"]},
                                             store, provider)
        secs = time.time() - t0
    finally:
        tools.run = real_run
    text = answer["text"] + " " + " ".join(i["title"] + " " + i["body"]
                                           for i in answer["insights"])
    used = [t["tool"] for t in answer["trace"]]
    checks = {}
    if case["tools"] == ["*"]:
        checks["tool"] = True
    elif case["tools"]:
        checks["tool"] = bool(used) and used[0] in case["tools"]
    else:
        checks["tool"] = not used
    lang = detect_lang(text + " " + (answer.get("closing") or ""))
    checks["lang"] = lang == case["lang"]
    known = result_numbers(captured.get("results", [])) + numbers_in(case["q"], case["lang"])
    known += result_numbers([store.as_of(customer_id), store.one(  # data dates are known
        "SELECT MIN(tx_date) AS d FROM transactions WHERE customer_id = ?", (customer_id,))["d"]])
    stray = [x for x in numbers_in(text, case["lang"]) if x > 31 and not grounded(x, known)]
    checks["ground"] = not stray
    hits = [s for s in case["must_not"] if s.lower() in text.lower()]
    checks["must_not"] = not hits
    foreign = [n for lg, names in BASKET_NAMES.items() if lg != case["lang"] for n in names
               if n in text.lower()]
    checks["terms"] = not foreign
    bad_money = MONEY_WRONG[case["lang"]].findall(text)
    checks["money"] = not bad_money
    close = answer.get("closing") or ""
    checks["closing"] = close.strip().endswith("?") and detect_lang(close) in (case["lang"], "?")
    if "notice" in case:  # must admit it can only partly answer
        checks["notice"] = bool(answer.get("notice")) == case["notice"]
    if case.get("must_any"):  # must mention at least one of these
        checks["must_any"] = any(m.lower() in text.lower() for m in case["must_any"])
    return {"id": case["id"], "q": case["q"], "tools_used": used, "lang_detected": lang,
            "ungrounded_numbers": stray, "forbidden_found": hits, "foreign_terms": foreign,
            "bad_money": bad_money, "seconds": round(secs, 1),
            "checks": checks, "passed": all(checks.values()),
            "text": answer["text"], "insights": answer["insights"], "closing": close}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--provider", help="stub or modal (default: AI_PROVIDER)")
    ap.add_argument("--only", help="comma-separated case ids")
    ap.add_argument("--db", help="SQLite path (default: SPANKKI_DB or the full database)")
    ap.add_argument("--out", help="write the full report as JSON")
    a = ap.parse_args()

    spec = json.load(open(os.path.join(HERE, "cases.json"), encoding="utf-8"))
    cases = spec["cases"]
    if a.only:
        wanted = set(a.only.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    store = Store(a.db)
    provider = get_provider(a.provider)
    print("provider=%s  db=%s  cases=%d\n" % (provider.name, store.path, len(cases)))
    print("%-20s %-5s %-5s %-6s %-8s %-5s %-5s %6s  %s" % (
        "case", "tool", "lang", "ground", "must_not", "terms", "money", "secs", "notes"))
    rows = []
    for c in cases:
        r = run_case(c, store, provider, spec["customer_id"])
        rows.append(r)
        notes = []
        if not r["checks"]["tool"]:
            notes.append("tools=%s" % r["tools_used"])
        if not r["checks"]["lang"]:
            notes.append("lang=%s" % r["lang_detected"])
        if r["ungrounded_numbers"]:
            notes.append("numbers=%s" % r["ungrounded_numbers"][:4])
        if r["forbidden_found"]:
            notes.append("found=%s" % r["forbidden_found"])
        if r["foreign_terms"]:
            notes.append("foreign=%s" % r["foreign_terms"][:2])
        if r["bad_money"]:
            notes.append("money=%s" % r["bad_money"][:2])
        for k in ("notice", "must_any"):
            if k in r["checks"] and not r["checks"][k]:
                notes.append("%s=FAIL" % k)
        if not r["checks"]["closing"]:
            notes.append("closing=%r" % r["closing"][:60])
        mark = lambda ok: "ok" if ok else "FAIL"  # noqa: E731
        print("%-20s %-5s %-5s %-6s %-8s %-5s %-5s %6.1f  %s" % (
            r["id"], mark(r["checks"]["tool"]), mark(r["checks"]["lang"]),
            mark(r["checks"]["ground"]), mark(r["checks"]["must_not"]),
            mark(r["checks"]["terms"]), mark(r["checks"]["money"]), r["seconds"],
            "; ".join(notes)))
    passed = sum(r["passed"] for r in rows)
    total_checks = sum(len(r["checks"]) for r in rows)
    ok_checks = sum(sum(r["checks"].values()) for r in rows)
    print("\npassed %d/%d cases, %d/%d checks, median %.1f s" % (
        passed, len(rows), ok_checks, total_checks,
        sorted(r["seconds"] for r in rows)[len(rows) // 2] if rows else 0))
    if a.out:
        json.dump({"provider": provider.name, "results": rows}, open(a.out, "w"),
                  ensure_ascii=False, indent=2)
        print("report:", a.out)
    return rows


if __name__ == "__main__":
    main()
