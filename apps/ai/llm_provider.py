"""AI provider backed by an OpenAI-compatible chat API — our Gemma on Modal (vLLM), or
any other server that speaks the same protocol. Standard library only.

Env:
    AI_BASE_URL   e.g. https://<workspace>--sbank-coach-llm-serve.modal.run (no /v1)
    AI_API_KEY    the VLLM_API_KEY stored in the Modal secret "coach-llm-key"
    AI_MODEL      served model name (default "gemma")
    AI_TIMEOUT    seconds per call (default 120; a cold start can take minutes)

Both calls ask for JSON matching a schema (vLLM structured output). If the server is
unreachable or the reply is unusable, that call falls back to the rule-based stub so the
app keeps answering; the fallback is logged to stderr.
"""
import json
import os
import ssl
import sys
import urllib.error
import urllib.request

from ai.stub_provider import Provider as StubProvider

GLOSSARY = {
    "fi": "pakolliset säännölliset menot (regular essentials), pakolliset yllättävät menot "
          "(unexpected necessities), arjen pikkukulut (everyday spending)",
}

PLAN_SYSTEM = """You are the planning step of S-Bank's money coach. A customer asks about \
their own finances. Decide which calculation tools the bank should run. You never see raw \
transactions; the bank runs the tools and checks every request.

Rules:
- Reply with JSON only: {{"requests": [{{"tool": ..., "args": {{...}}}}], "reply": "..."}}.
- Use 1-3 requests when numbers are needed. Use only the tools and argument names below; \
leave out arguments you do not need. Never send customer_id.
- Periods: "this week"=last_7_days, "this month"=this_month, "last month"=last_month, \
default last_30_days for "recently", last_90_days for habits and savings.
- What-if questions ("if I cut X by 20%") -> simulate_change with change_pct=-20.
- Taxis, coffee etc. are not categories: map to the closest category (Transportation, \
Restaurants).
- If no numbers are needed (greeting, explaining a financial concept), return no requests \
and put a short, plain-language answer in "reply", in the customer's language.

Tools:
{tools}"""

COMPOSE_SYSTEM = """You are S-Bank's friendly money coach. Explain the customer's results \
in plain language, like a patient teacher: what the numbers mean and one practical next \
step. Help them understand the three spending baskets: regular essentials, unexpected \
necessities, everyday spending.

Rules:
- Answer in the language of the customer's question (Finnish, Swedish or English).
  Finnish basket names: {fi_glossary}.
- Use only numbers that appear in the results; never invent or extrapolate. Round euros \
to whole numbers. In Finnish/Swedish write amounts like "1 234 €".
- If a request was rejected or failed, say briefly what you could not check.
- Do not give investment advice. Keep "text" to 2-4 sentences.
- Reply with JSON only: {{"text": "...", "insights": [{{"title": "...", "body": "...", \
"kind": "info|good|warn|tip"}}]}} with at most 3 insights. Charts are shown separately; \
do not describe them."""


def _plan_schema(tool_names):
    return {
        "type": "object",
        "properties": {
            "requests": {"type": "array", "maxItems": 3, "items": {
                "type": "object",
                "properties": {"tool": {"type": "string", "enum": tool_names},
                               "args": {"type": "object"}},
                "required": ["tool", "args"]}},
            "reply": {"type": "string"},
        },
        "required": ["requests"],
    }


COMPOSE_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "insights": {"type": "array", "maxItems": 3, "items": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "body": {"type": "string"},
                           "kind": {"type": "string",
                                    "enum": ["info", "good", "warn", "tip"]}},
            "required": ["title", "body", "kind"]}},
    },
    "required": ["text", "insights"],
}


class LLMError(Exception):
    pass


def ssl_context():
    """Verified TLS. python.org builds on macOS ship without CA certificates; then use the
    system bundle at /etc/ssl/cert.pem instead of failing (still fully verified)."""
    ctx = ssl.create_default_context()
    if not ctx.cert_store_stats()["x509_ca"] and os.path.exists("/etc/ssl/cert.pem"):
        ctx.load_verify_locations("/etc/ssl/cert.pem")
    return ctx


class Provider:
    name = "modal-gemma"

    def __init__(self, base_url=None, api_key=None, model=None, timeout=None):
        self.base_url = (base_url or os.environ.get("AI_BASE_URL", "")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("AI_API_KEY", "")
        self.model = model or os.environ.get("AI_MODEL", "gemma")
        self.timeout = float(timeout or os.environ.get("AI_TIMEOUT", "120"))
        if not self.base_url:
            raise ValueError("AI_BASE_URL is not set (the deployed Modal URL)")
        self.stub = StubProvider()
        self.ssl = ssl_context()

    # ------------------------------------------------------------ transport
    def _chat_json(self, messages, schema, name, max_tokens):
        body = {
            "model": self.model, "messages": messages, "temperature": 0.2,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": name, "schema": schema}},
        }
        req = urllib.request.Request(
            self.base_url + "/v1/chat/completions", data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + self.api_key})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.ssl) as r:
                reply = json.load(r)
        except urllib.error.HTTPError as e:
            raise LLMError("HTTP %d from model server" % e.code)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise LLMError("model server unreachable: %s" % e)
        try:
            content = reply["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError):
            raise LLMError("model reply was not the expected JSON")

    @staticmethod
    def _history(history):
        msgs = []
        for h in (history or [])[-6:]:
            msgs.append({"role": "user" if h.get("role") == "user" else "assistant",
                         "content": h.get("text", "")[:1000]})
        return msgs

    def _fallback(self, step, err):
        sys.stderr.write("[llm] %s fell back to stub: %s\n" % (step, err))

    # ------------------------------------------------------------ step 2
    def plan(self, text, tools, history=None):
        catalog = json.dumps([{k: t[k] for k in ("name", "description", "parameters")}
                              for t in tools], ensure_ascii=False)
        messages = ([{"role": "system", "content": PLAN_SYSTEM.format(tools=catalog)}]
                    + self._history(history) + [{"role": "user", "content": text}])
        try:
            out = self._chat_json(messages, _plan_schema([t["name"] for t in tools]),
                                  "plan", 400)
        except LLMError as e:
            self._fallback("plan", e)
            return self.stub.plan(text, tools, history)
        plan = {"requests": [{"tool": r.get("tool"), "args": r.get("args") or {}}
                             for r in out.get("requests", [])[:3] if isinstance(r, dict)]}
        reply = out.get("reply")
        if not plan["requests"]:
            if not reply:
                self._fallback("plan", "no requests and no reply")
                return self.stub.plan(text, tools, history)
            plan["reply"] = str(reply)[:2000]
        return plan

    # ------------------------------------------------------------ step 6
    def compose(self, text, results, history=None):
        slim = [{k: r[k] for k in ("tool", "ok", "data", "error", "rejected", "args") if k in r}
                for r in results]
        messages = ([{"role": "system",
                      "content": COMPOSE_SYSTEM.format(fi_glossary=GLOSSARY["fi"])}]
                    + self._history(history)
                    + [{"role": "user", "content": "Customer's question: %s\n\nResults (JSON):\n%s"
                        % (text, json.dumps(slim, ensure_ascii=False))}])
        try:
            out = self._chat_json(messages, COMPOSE_SCHEMA, "answer", 700)
            answer = {"text": str(out["text"]),
                      "insights": [{"title": str(i.get("title", "")),
                                    "body": str(i.get("body", "")),
                                    "kind": i.get("kind") if i.get("kind") in
                                    ("info", "good", "warn", "tip") else "info"}
                                   for i in out.get("insights", [])[:3] if isinstance(i, dict)]}
            if not answer["text"].strip():
                raise LLMError("empty answer text")
            return answer
        except (LLMError, KeyError, TypeError) as e:
            self._fallback("compose", e)
            return self.stub.compose(text, results, history)
