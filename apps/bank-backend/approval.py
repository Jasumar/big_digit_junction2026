"""Step 3: a calculation request is approved or rejected before anything runs.

Policy (v0): the tool must be in the catalog, args must match its schema exactly, and
the customer is always the session's customer, never anything the model supplied.
"""
from calculation.tools import TOOLS
from contracts import validate

MAX_REQUESTS_PER_COMMAND = 3


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
