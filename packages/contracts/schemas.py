"""Schemas, examples and a minimal validator (no third-party dependency)."""

PERIODS = ["last_7_days", "last_30_days", "last_90_days", "this_month", "last_month",
           "last_12_months", "all"]

# client -> bank-backend (step 1)
COMMAND = {
    "type": "object",
    "required": ["customer_id", "text"],
    "additionalProperties": False,
    "properties": {
        "customer_id": {"type": "string", "minLength": 1, "maxLength": 32},
        "text": {"type": "string", "minLength": 1, "maxLength": 500},
        "history": {  # optional earlier turns, oldest first
            "type": "array", "maxItems": 10,
            "items": {"type": "object", "required": ["role", "text"],
                      "properties": {"role": {"type": "string", "enum": ["user", "coach"]},
                                     "text": {"type": "string", "maxLength": 2000}}},
        },
    },
}

# ai -> bank-backend (step 2 reply): what the model wants calculated.
# The backend overrides/injects customer_id; the model never supplies it.
CALCULATION_REQUEST = {
    "type": "object",
    "required": ["tool", "args"],
    "additionalProperties": False,
    "properties": {
        "tool": {"type": "string", "minLength": 1, "maxLength": 64},
        "args": {"type": "object"},
    },
}

PLAN = {  # what AI.plan() returns
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "requests": {"type": "array", "maxItems": 3, "items": CALCULATION_REQUEST},
        "reply": {"type": "string", "maxLength": 2000},  # direct answer, no calculation
    },
}

# bank-backend -> ai (step 5 onward) and into the answer trace.
CALCULATION_RESULT = {
    "type": "object",
    "required": ["tool", "ok"],
    "additionalProperties": False,
    "properties": {
        "tool": {"type": "string"},
        "ok": {"type": "boolean"},
        "data": {"type": "object"},     # when ok
        "error": {"type": "string"},    # when not ok: rejected or failed
        "rejected": {"type": "boolean"},  # true: approval said no, nothing was run
        "args": {"type": "object"},
    },
}

# bank-backend -> client (step 7)
ANSWER = {
    "type": "object",
    "required": ["text", "insights", "visuals", "trace"],
    "additionalProperties": False,
    "properties": {
        "text": {"type": "string"},
        "insights": {
            "type": "array",
            "items": {"type": "object", "required": ["title", "body"],
                      "properties": {"title": {"type": "string"}, "body": {"type": "string"},
                                     "kind": {"type": "string",
                                              "enum": ["info", "good", "warn", "tip"]}}},
        },
        # Built by the backend from calculation results, never by the model.
        "visuals": {
            "type": "array",
            "items": {"type": "object", "required": ["type"],
                      "properties": {"type": {"type": "string",
                                              "enum": ["stats", "bars", "table"]}}},
        },
        "trace": {  # what happened at steps 2-5, for transparency
            "type": "array",
            "items": {"type": "object", "required": ["tool", "approved"],
                      "properties": {"tool": {"type": "string"},
                                     "approved": {"type": "boolean"},
                                     "note": {"type": "string"}}},
        },
        "provider": {"type": "string"},
    },
}

EXAMPLES = {
    "command": {"customer_id": "CUST00001", "text": "Where did my money go this month?"},
    "calculation_request": {"tool": "spending_breakdown", "args": {"period": "this_month"}},
    "calculation_result": {"tool": "spending_breakdown", "ok": True,
                           "data": {"total_spend": 1234.5}},
    "answer": {
        "text": "You spent EUR 1,234 this month.",
        "insights": [{"title": "Biggest cost", "body": "Housing", "kind": "info"}],
        "visuals": [{"type": "stats", "items": [{"label": "Spent", "value": "EUR 1,234"}]}],
        "trace": [{"tool": "spending_breakdown", "approved": True}],
        "provider": "stub",
    },
}


_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool,
          "integer": int, "number": (int, float)}


def validate(schema, value, path="$"):
    """Return a list of problem strings. Supports the keywords used above."""
    t = schema.get("type")
    if t:
        py = _TYPES[t]
        ok = isinstance(value, py) and not (t in ("integer", "number")
                                            and isinstance(value, bool))
        if t == "integer" and isinstance(value, float):
            ok = False
        if not ok:
            return ["%s: expected %s" % (path, t)]
    problems = []
    if "enum" in schema and value not in schema["enum"]:
        problems.append("%s: must be one of %s" % (path, schema["enum"]))
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            problems.append("%s: too short" % path)
        if len(value) > schema.get("maxLength", 10 ** 9):
            problems.append("%s: too long" % path)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            problems.append("%s: below %s" % (path, schema["minimum"]))
        if "maximum" in schema and value > schema["maximum"]:
            problems.append("%s: above %s" % (path, schema["maximum"]))
    if isinstance(value, list):
        if len(value) > schema.get("maxItems", 10 ** 9):
            problems.append("%s: too many items" % path)
        if "items" in schema:
            for i, v in enumerate(value):
                problems += validate(schema["items"], v, "%s[%d]" % (path, i))
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for k in schema.get("required", []):
            if k not in value:
                problems.append("%s: missing '%s'" % (path, k))
        for k, v in value.items():
            if k in props:
                problems += validate(props[k], v, "%s.%s" % (path, k))
            elif schema.get("additionalProperties") is False:
                problems.append("%s: unknown field '%s'" % (path, k))
    return problems
