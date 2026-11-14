"""The S-pankki backend's flow (docs/SYSTEM_MAP.md steps 1-7) in one function."""
import approval
import present
from calculation import tools
from contracts import COMMAND, PLAN, validate


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

    # step 2: the model decides what to calculate
    plan = provider.plan(command["text"], tools.describe_catalog(), history)
    if validate(PLAN, plan):
        plan = {"requests": [], "reply": "Sorry, I couldn't understand that request."}
    requests = plan.get("requests", [])[:approval.MAX_REQUESTS_PER_COMMAND]

    results, trace = [], []
    for req in requests:
        # step 3: approve or reject
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
            trace.append({"tool": req["tool"], "approved": True, "note": "ok"})
        except Exception as e:  # a failing tool must not take the answer down
            results.append({"tool": req["tool"], "ok": False, "error": str(e)})
            trace.append({"tool": req["tool"], "approved": True, "note": "failed: %s" % e})

    # step 6: the model turns results into an answer and insights
    if requests:
        composed = provider.compose(command["text"], results, history)
    else:
        composed = {"text": plan.get("reply") or "I can help with questions about your "
                                                  "spending.", "insights": []}
    # step 7: answer goes back to the client
    return {"text": composed["text"], "insights": composed.get("insights", []),
            "visuals": present.build(results), "trace": trace,
            "provider": getattr(provider, "name", "unknown")}


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
