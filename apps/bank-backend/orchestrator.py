"""The S-pankki backend's flow (docs/SYSTEM_MAP.md steps 1-7) in one function."""
import sys

import approval
import present
import scope
from ai.grounding import known_numbers, strip_unbacked
from calculation import tools
from cloud import glossary
from contracts import COMMAND, PLAN, validate

SAFE_TEXT = {
    "en": "I couldn't verify the numbers for a written answer; the charts below show the "
          "calculated figures.",
    "fi": "En pystynyt varmistamaan lukuja kirjalliseen vastaukseen; alla olevat kaaviot "
          "näyttävät lasketut luvut.",
    "sv": "Jag kunde inte verifiera siffrorna för ett skriftligt svar; diagrammen nedan "
          "visar de beräknade siffrorna.",
}


class BadCommand(Exception):
    pass


def handle_command(command, store, provider):
    problems = validate(COMMAND, command)
    if problems:
        raise BadCommand("; ".join(problems))
    customer_id = command["customer_id"]
    if not store.customer(customer_id):
        raise BadCommand("unknown customer")
    history = command.get("history", [])
    as_of = store.as_of(customer_id)
    first = store.one("SELECT MIN(tx_date) AS d FROM transactions WHERE customer_id = ?",
                      (customer_id,))["d"]
    ui_lang = command.get("lang") or "en"
    context = {"data_from": first, "data_as_of": as_of, "ui_lang": ui_lang}

    # step 2: the model decides what to calculate
    plan = provider.plan(command["text"], tools.describe_catalog(), history, context)
    if validate(PLAN, plan):
        plan = {"requests": [], "reply": "Sorry, I couldn't understand that request."}
    requests = plan.get("requests", [])[:approval.MAX_REQUESTS_PER_COMMAND]

    results, trace = _run_requests(requests, store, customer_id)
    fixable = [r for r in results if r.get("rejected")
               and "customer_id" not in r.get("error", "")]
    if fixable:  # one re-plan with the rejection reasons (wrong values, wrong tool name)
        context["feedback"] = "; ".join("%s rejected: %s" % (r["tool"], r["error"])
                                        for r in fixable)
        replan = provider.plan(command["text"], tools.describe_catalog(), history, context)
        context.pop("feedback", None)
        if not validate(PLAN, replan) and replan.get("requests"):
            plan = replan
            requests = replan["requests"][:approval.MAX_REQUESTS_PER_COMMAND]
            results, trace = _run_requests(requests, store, customer_id)

    # Limits are decided in code: the model both missed real limits ("March?") and invented
    # false ones ("last month" refused). Its own limitation is used only for no-tool replies.
    limitation = scope.limitation(command["text"], plan.get("lang") or ui_lang, as_of)
    if not limitation and not requests and plan.get("coverage") == "none":
        limitation = (plan.get("limitation") or "").strip()
    context["limitation"] = limitation

    # step 6: the model turns results into an answer and insights
    if requests:
        composed = provider.compose(command["text"], results, history, context)
    else:
        composed = {"text": plan.get("reply") or "I can help with questions about your "
                                                  "spending.", "insights": [],
                    "lang": plan.get("lang")}
    lang = composed.get("lang") if composed.get("lang") in ("en", "fi", "sv") else ui_lang
    composed["lang"] = lang

    # safety net for every provider: no number may appear that the tools did not produce
    known = known_numbers(results, command["text"], lang, {"as_of": as_of, "from": first})
    composed, removed = strip_unbacked(composed, known, SAFE_TEXT[lang],
                                       allow_examples=not requests)
    if removed:
        sys.stderr.write("[guard] removed unbacked numbers %s\n" % removed[:5])
    composed = scope.redact_merchants(composed)
    composed = scope.drop_foreign_terms(composed)

    # step 7: answer goes back to the client
    answer = {"text": composed["text"], "insights": composed.get("insights", []),
              "visuals": present.build(results, lang), "trace": trace, "lang": lang,
              "data_as_of": as_of, "provider": getattr(provider, "name", "unknown")}
    if limitation:
        answer["notice"] = limitation
    return answer


def _run_requests(requests, store, customer_id):
    """Steps 3-5 for a list of requests -> (results, trace)."""
    results, trace = [], []
    for req in requests:
        # step 3: approve or reject (arguments the tool does not have are dropped first)
        req, dropped = approval.clean(req)
        ok, reason = approval.check(req, customer_id)
        if not ok:
            results.append({"tool": req["tool"], "ok": False, "rejected": True,
                            "error": reason})
            trace.append({"tool": req["tool"], "approved": False, "note": reason})
            continue
        # steps 4-5: calculate over the customer's data, get results back
        try:
            data = tools.run(req["tool"], store, customer_id, req["args"])
            results.append({"tool": req["tool"], "ok": True, "data": data,
                            "args": req["args"]})
            trace.append({"tool": req["tool"], "approved": True,
                          "note": "ok" if not dropped else "ok; ignored args: %s"
                          % ", ".join(dropped)})
        except Exception as e:  # a failing tool must not take the answer down
            results.append({"tool": req["tool"], "ok": False, "error": str(e)})
            trace.append({"tool": req["tool"], "approved": True, "note": "failed: %s" % e})

    return results, trace


def overview(customer_id, store, lang="en"):
    """Home-screen data. Goes through the same approval and tools as a command.
    `bucket_labels` are the basket names in `lang`, from the shared glossary."""
    cust = store.customer(customer_id)
    if not cust:
        raise BadCommand("unknown customer")
    out = {"customer": {"customer_id": customer_id, "age": cust["age"],
                        "postal_code": cust["postal_code"]}}
    for key, req in (("safe_to_spend", {"tool": "safe_to_spend", "args": {"horizon_days": 7}}),
                     ("breakdown", {"tool": "spending_breakdown",
                                    "args": {"period": "last_30_days"}})):
        ok, reason = approval.check(req, customer_id)
        out[key] = tools.run(req["tool"], store, customer_id, req["args"]) if ok else None
    lang = lang if lang in ("en", "fi", "sv") else "en"
    out["bucket_labels"] = {b: glossary.bucket(b, lang)
                            for b in ("essentials", "necessities", "everyday")}
    return out
