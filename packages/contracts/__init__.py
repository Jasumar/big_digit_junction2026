"""Shapes on every edge of the system (docs/SYSTEM_MAP.md), as JSON-Schema-style dicts.

Python 3 standard library only. `validate(schema, value)` returns a list of problems
(empty = valid). The same shapes are what the frontend receives as JSON.
"""
from .schemas import (  # noqa: F401
    ANSWER, CALCULATION_REQUEST, CALCULATION_RESULT, COMMAND, EXAMPLES, PERIODS,
    PLAN, validate,
)
