"""The AI edge. The backend talks to a provider through exactly two calls.

    plan(text, tools, history)           -> PLAN      (step 2: what to calculate)
    compose(text, results, history)      -> {"text": str, "insights": [...]}   (step 6)

`tools` is the catalog from calculation.tools.describe_catalog() (name, description,
JSON-schema parameters), so a real model can use it directly for tool calling.
`results` is a list of CALCULATION_RESULT dicts (rejections included, ok=false).
A provider never sees raw transactions, only these results.

Optional multi-round call. A provider that has it is driven by the backend in a loop
instead of plan/compose (the stub has no `step` and keeps plan/compose):

    step(messages, tools) -> {"requests": [CALCULATION_REQUEST, ...]}
                          or {"final": {"text": str, "insights": [...]}}

`messages` is provider-neutral, oldest first: {"role": "user"|"coach", "text"} for the
conversation (the last "user" entry is the current question), then per round
{"role": "requests", "requests": [...]} (what the model asked for) followed by
{"role": "results", "results": [...]} (one CALCULATION_RESULT per request, in order,
rejections included with ok=false). Empty `tools` means no more calculations are
possible: the provider must return a "final" from what it has.

Select with env AI_PROVIDER (default "stub"); "llm" uses the OpenAI-compatible
provider with a request-local fallback to the stub.
"""
import logging
import os
import threading


def split_messages(messages):
    """-> (text, history, results): the current question, earlier turns, all results."""
    last_user = max(i for i, m in enumerate(messages) if m["role"] == "user")
    history = [m for m in messages[:last_user] if m["role"] in ("user", "coach")]
    results = [r for m in messages if m["role"] == "results" for r in m["results"]]
    return messages[last_user]["text"], history, results


class _FallbackProvider:
    """Keep fallback status local to each request thread."""

    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback
        self._state = threading.local()

    @property
    def name(self):
        return "stub (fallback)" if getattr(self._state, "failed", False) else "llm"

    def plan(self, text, tools, history=None):
        from ai.llm_provider import LLMError

        self._state.failed = False
        try:
            return self.primary.plan(text, tools, history)
        except Exception as exc:
            detail = str(exc) if isinstance(exc, LLMError) else type(exc).__name__
            logging.getLogger(__name__).warning("LLM plan failed: %s; using stub", detail)
            self._state.failed = True
            return self.fallback.plan(text, tools, history)

    def compose(self, text, results, history=None):
        from ai.llm_provider import LLMError

        if not getattr(self._state, "failed", False):
            try:
                return self.primary.compose(text, results, history)
            except Exception as exc:
                detail = str(exc) if isinstance(exc, LLMError) else type(exc).__name__
                logging.getLogger(__name__).warning("LLM compose failed: %s; using stub", detail)
                self._state.failed = True
        return self.fallback.compose(text, results, history)

    def step(self, messages, tools):
        from ai.llm_provider import LLMError

        if not any(m["role"] in ("requests", "results") for m in messages):
            self._state.failed = False
        if not getattr(self._state, "failed", False):
            try:
                return self.primary.step(messages, tools)
            except Exception as exc:
                detail = str(exc) if isinstance(exc, LLMError) else type(exc).__name__
                logging.getLogger(__name__).warning("LLM step failed: %s; using stub", detail)
                self._state.failed = True
        text, history, results = split_messages(messages)
        if results or not tools:
            return {"final": self.fallback.compose(text, results, history)}
        plan = self.fallback.plan(text, tools, history)
        if plan.get("requests"):
            return {"requests": plan["requests"]}
        return {"final": {"text": plan.get("reply") or "I can help with questions about "
                                                      "your spending.", "insights": []}}


def get_provider(name=None):
    name = name or os.environ.get("AI_PROVIDER", "stub")
    if name == "stub":
        from ai.stub_provider import Provider
        return Provider()
    if name == "llm":
        from ai.llm_provider import Provider
        from ai.stub_provider import Provider as StubProvider
        return _FallbackProvider(Provider(), StubProvider())
    raise ValueError("unknown AI_PROVIDER %r (known: stub, llm)" % name)
