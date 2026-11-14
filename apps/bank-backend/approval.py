"""Step 3: a calculation request is approved or rejected before anything runs.

Policy: the tool must be in the catalog, args must match its schema, and the customer is
always the session's customer, never anything the model supplied. `clean()` first drops
arguments the tool does not define (they would have no effect; Gemma adds e.g.
"type": "category"), except customer_id, which is always rejected, and unwraps a value
sent as a one-item list. Values are then validated strictly.
"""
from calculation.tools import TOOLS
from contracts import validate

MAX_REQUESTS_PER_COMMAND = 3


def clean(request):
    """-> (request with unknown args dropped, list of dropped names)."""
    name = request.get("tool")
    args = request.get("args") or {}
    if name not in TOOLS:
        return request, []
    known = TOOLS[name]["parameters"].get("properties", {})
    dropped = [k for k in args if k not in known and k != "customer_id"]
    kept = {}
    for k, v in args.items():
        if k not in known and k != "customer_id":
            continue
        # Gemma sometimes wraps one value in a list: {"category": ["Invest Deposit"]}
        if (isinstance(v, list) and len(v) == 1 and k in known
                and known[k].get("type") != "array"):
            v = v[0]
        kept[k] = v
    return dict(request, args=kept), dropped


def check(request, session_customer_id):
    """-> (approved, reason). `request` is a CalculationRequest dict."""
    name = request.get("tool")
    args = request.get("args", {})
    if name not in TOOLS:
        return False, "unknown tool '%s'" % name
    if "customer_id" in args:
        return False, "customer_id is set by the bank, not by the request"
    problems = validate(TOOLS[name]["parameters"], args, "args")
    if problems:
        return False, "; ".join(problems[:3])
    if not session_customer_id:
        return False, "no customer in session"
    return True, "ok"
