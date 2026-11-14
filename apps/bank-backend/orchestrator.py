"""The S-pankki backend's flow (docs/SYSTEM_MAP.md steps 1-7) in one function."""
import time

import approval
import present
from calculation import tools
from contracts import CALCULATION_REQUEST, COMMAND, PLAN, validate

MAX_ROUNDS = 3
TIME_LIMIT_S = 25


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

    if hasattr(provider, "step"):
        composed, results, trace = _run_rounds(command["text"], history, customer_id,
                                               store, provider)
    else:
        composed, results, trace = _plan_and_compose(command["text"], history, customer_id,
                                                     store, provider)
    # step 7: answer goes back to the client
    return {"text": composed["text"], "insights": composed.get("insights", []),
            "visuals": present.build(results), "trace": trace,
            "provider": getattr(provider, "name", "unknown")}


def _execute(requests, rnd, customer_id, store):
    """Steps 3-5 for one batch: every request is approved first, then run."""
    results, trace = [], []
    for req in requests:
        # step 3: approve or reject
        ok, reason = approval.check(req, customer_id)
        if not ok:
            results.append({"tool": req["tool"], "ok": False, "rejected": True,
                            "error": reason})
            trace.append({"tool": req["tool"], "approved": False, "note": reason,
                          "round": rnd})
            continue
        # steps 4-5: calculate over the customer's data, get results back
        try:
            data = tools.run(req["tool"], store, customer_id, req["args"])
            results.append({"tool": req["tool"], "ok": True, "data": data,
                            "args": req["args"]})
            trace.append({"tool": req["tool"], "approved": True, "note": "ok",
                          "round": rnd})
        except Exception as e:  # a failing tool must not take the answer down
            results.append({"tool": req["tool"], "ok": False, "error": str(e)})
            trace.append({"tool": req["tool"], "approved": True, "note": "failed: %s" % e,
                          "round": rnd})
    return results, trace


def _plan_and_compose(text, history, customer_id, store, provider):
    # step 2: the model decides what to calculate
    plan = provider.plan(text, tools.describe_catalog(), history)
    if validate(PLAN, plan):
        plan = {"requests": [], "reply": "Sorry, I couldn't understand that request."}
    requests = plan.get("requests", [])[:approval.MAX_REQUESTS_PER_COMMAND]
    results, trace = _execute(requests, 1, customer_id, store)
    # step 6: the model turns results into an answer and insights
    if requests:
        composed = provider.compose(text, results, history)
    else:
        composed = {"text": plan.get("reply") or "I can help with questions about your "
                                                  "spending.", "insights": []}
    return composed, results, trace


def _valid_final(out):
    final = out.get("final") if isinstance(out, dict) else None
    return (isinstance(final, dict) and isinstance(final.get("text"), str)
            and final["text"].strip() and isinstance(final.get("insights", []), list))


def _valid_requests(out):
    reqs = out.get("requests") if isinstance(out, dict) else None
    return (isinstance(reqs, list) and 0 < len(reqs)
            and not any(validate(CALCULATION_REQUEST, r) for r in reqs))


def _run_rounds(text, history, customer_id, store, provider):
    """Steps 2-6 as a loop: the model may ask for calculations in several rounds."""
    catalog = tools.describe_catalog()
    messages = [{"role": t["role"], "text": t["text"]} for t in history]
    messages.append({"role": "user", "text": text})
    results, trace, final = [], [], None
    started = time.monotonic()
    for rnd in range(1, MAX_ROUNDS + 1):
        if time.monotonic() - started >= TIME_LIMIT_S:
            break
        out = provider.step(messages, catalog)
        if _valid_final(out):
            final = out["final"]
            break
        if not _valid_requests(out):
            break
        requests = out["requests"][:approval.MAX_REQUESTS_PER_COMMAND]
        round_results, round_trace = _execute(requests, rnd, customer_id, store)
        results += round_results
        trace += round_trace
        messages.append({"role": "requests", "requests": requests})
        messages.append({"role": "results", "results": round_results})
    if final is None:  # a limit was hit (or the model went off script): wrap up
        out = provider.step(messages, [])
        final = out["final"] if _valid_final(out) else {
            "text": "Sorry, I couldn't finish that request.", "insights": []}
    return final, results, trace


def overview(customer_id, store):
    """Home-screen data. Goes through the same approval and tools as a command."""
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
    return out
