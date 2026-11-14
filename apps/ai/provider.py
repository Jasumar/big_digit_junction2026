"""The AI edge. The backend talks to a provider through exactly two calls.

    plan(text, tools, history)           -> PLAN      (step 2: what to calculate)
    compose(text, results, history)      -> {"text": str, "insights": [...]}   (step 6)

`tools` is the catalog from calculation.tools.describe_catalog() (name, description,
JSON-schema parameters), so a real model can use it directly for tool calling.
`results` is a list of CALCULATION_RESULT dicts (rejections included, ok=false).
A provider never sees raw transactions, only these results.

Select with env AI_PROVIDER:
    "stub"       default; offline rules, no key, answers instantly
    "modal"      Gemma on Modal via an OpenAI-compatible API (llm_provider.py)
    "openrouter" hosted model via OpenRouter (openrouter_provider.py; needs a key)
To add another provider, create apps/ai/<name>_provider.py exposing `Provider` (with a
`name` attribute) and register it in `get_provider`.
"""
import os


def get_provider(name=None):
    name = name or os.environ.get("AI_PROVIDER", "stub")
    if name == "stub":
        from ai.stub_provider import Provider
        return Provider()
    if name in ("modal", "llm"):
        from ai.llm_provider import Provider
        return Provider()
    if name == "openrouter":
        from ai.openrouter_provider import Provider
        return Provider()
    raise ValueError("unknown AI_PROVIDER %r (known: stub, modal, openrouter)" % name)
