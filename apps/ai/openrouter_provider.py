"""Real provider: an OpenRouter-hosted model behind the same two-call interface.

    plan(text, tools, history)        -> native tool calling over the catalog
    compose(text, results, history)   -> JSON {text, insights}

OpenRouter speaks the OpenAI-compatible chat-completions API, so the tool catalog
(name/description/parameters from calculation.tools.describe_catalog()) maps straight
onto `tools` without translation, and the selected tool calls map straight back onto
{"requests": [{"tool", "args"}]}. Standard library only (urllib), like the rest of the
repo: no SDK, no install.

Config (env, see .env.example):
    OPENROUTER_API_KEY   required; empty = startup error with instructions
    OPENROUTER_MODEL     default google/gemma-4-26b-a4b-it
    OPENROUTER_BASE_URL  default https://openrouter.ai/api/v1
"""
import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_MODEL = "google/gemma-4-26b-a4b-it"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
MAX_TOKENS = 1200
TIMEOUT_S = 90

PLAN_SYSTEM = (
    "You are the money coach in the S-pankki mobile app. The customer is asking about "
    "their own spending. Decide which of the available calculation tools you need: call "
    "at most 3, and only when the answer requires their data. Fill each tool's arguments "
    "exactly per its parameter schema - never invent a field name, never pass a customer "
    "id, never pass null. If the message is small talk, a greeting, or something no tool "
    "can answer, call no tool and reply briefly in the customer's language instead."
)

COMPOSE_SYSTEM = (
    "You are the money coach in the S-pankki mobile app. First note the language of the "
    "customer's question; your whole answer must be in that language - an English question "
    "gets an English answer even though the data labels are Finnish. "
    "Explain the calculation results "
    "below to the customer, in the language they wrote in (Finnish, Swedish or English). "
    "Use only figures that appear in the results - never estimate, never invent a number, "
    "date or merchant. If a result has ok=false it was refused or failed: say plainly that "
    "this part cannot be shown. Be warm, concrete and short: 2-4 sentences. Write every "
    "amount in the bank's European style, in any language: space as thousands separator, "
    "comma decimals (2 541,89 €).\n\n"
    "Answer with JSON only, no prose outside it:\n"
    '{"text": "...", "insights": [{"title": "...", "body": "...", "kind": "info"}]}\n'
    "1-3 insights; kind is one of info, good, warn, tip."
)

KINDS = ("info", "good", "warn", "tip")


class OpenRouterError(RuntimeError):
    """The provider could not reach or understand the API."""


class Provider:
    name = "openrouter"

    def __init__(self, api_key=None, model=None, base_url=None, timeout=TIMEOUT_S,
                 transport=None):
        self.api_key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY", "")
        self.model = model or os.environ.get("OPENROUTER_MODEL") or DEFAULT_MODEL
        self.base_url = (base_url or os.environ.get("OPENROUTER_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._transport = transport  # tests inject a callable(payload) -> dict
        if not self.api_key and transport is None:
            raise OpenRouterError(
                "OPENROUTER_API_KEY is not set. Copy .env.example to .env, put your key in "
                "OPENROUTER_API_KEY, then `set -a; source .env; set +a` before starting the "
                "server (or keep AI_PROVIDER=stub).")

    # ------------------------------------------------------------ transport

    def _post(self, payload):
        if self._transport is not None:
            return self._transport(payload)
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            self.base_url + "/chat/completions", data=body, method="POST",
            headers={"Authorization": "Bearer " + self.api_key,
                     "Content-Type": "application/json",
                     "X-Title": "S-pankki Money Coach"})
        last = None
        for attempt in (0, 1):  # one retry on transient failures; the demo must not die on a 429
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read() or b"{}")
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:300]
                last = OpenRouterError("OpenRouter HTTP %d: %s" % (e.code, detail))
                if e.code not in (408, 429) and e.code < 500:
                    raise last
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last = OpenRouterError("OpenRouter unreachable: %s" % e)
            if attempt == 0:
                time.sleep(1)
        raise last

    def _chat(self, messages, **extra):
        payload = {"model": self.model, "messages": messages,
                   "temperature": 0.2, "max_tokens": MAX_TOKENS, **extra}
        data = self._post(payload)
        if "error" in data and data["error"]:
            err = data["error"]
            raise OpenRouterError("OpenRouter error: %s" % (
                err.get("message") if isinstance(err, dict) else err))
        try:
            return data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            raise OpenRouterError("OpenRouter returned no choice: %s" % str(data)[:300])

    # ------------------------------------------------------------ the two calls

    def plan(self, text, tools, history=None):
        messages = [{"role": "system", "content": PLAN_SYSTEM}]
        messages += _history(history)
        messages.append({"role": "user", "content": text})
        tool_specs = [{"type": "function",
                       "function": {"name": t["name"], "description": t["description"],
                                    "parameters": t["parameters"]}}
                      for t in tools]
        if not tool_specs:
            return {"requests": [], "reply": ""}
        message = self._chat(messages, tools=tool_specs, tool_choice="auto")
        requests = []
        for call in message.get("tool_calls") or []:
            fn = (call or {}).get("function") or {}
            args = _args(fn.get("arguments"))
            if fn.get("name") and args is not None:
                requests.append({"tool": fn["name"], "args": args})
        reply = (message.get("content") or "").strip()
        if not requests and not reply:
            raise OpenRouterError("the model returned neither tool calls nor text")
        return {"requests": requests[:3], **({"reply": reply[:2000]} if reply else {})}

    def compose(self, text, results, history=None):
        messages = [{"role": "system", "content": COMPOSE_SYSTEM}]
        messages += _history(history)
        messages.append({"role": "user", "content":
                         "Customer question: %s\n\nCalculation results (JSON):\n%s\n\n"
                         "Answer in the same language as the customer question above." % (
                             text, json.dumps(results, ensure_ascii=False, indent=1))})
        message = self._chat(messages, response_format={"type": "json_object"})
        content = (message.get("content") or "").strip()
        parsed = _json_object(content)
        if not parsed or not isinstance(parsed.get("text"), str):
            # Not JSON despite the request: the prose is still a usable answer.
            if not content:
                raise OpenRouterError("the model returned an empty answer")
            return {"text": content, "insights": []}
        return {"text": parsed["text"], "insights": _insights(parsed.get("insights"))}


def _history(history):
    """Earlier turns in the backend's shape -> chat messages."""
    out = []
    for turn in history or []:
        if isinstance(turn, dict) and turn.get("text"):
            out.append({"role": "assistant" if turn.get("role") == "coach" else "user",
                        "content": turn["text"]})
    return out


def _args(raw):
    """Tool-call arguments: a JSON object string, or already a dict. None if unusable."""
    if isinstance(raw, dict):
        args = raw
    else:
        try:
            args = json.loads(raw or "{}")
        except (TypeError, ValueError):
            return None
    if not isinstance(args, dict):
        return None
    return {k: v for k, v in args.items() if v is not None}


def _json_object(text):
    """Parse a JSON object out of model output, tolerating code fences and stray prose."""
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(text[start:end + 1])
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _insights(items):
    out = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or not item.get("title") or not item.get("body"):
            continue
        out.append({"title": str(item["title"])[:120], "body": str(item["body"])[:600],
                    "kind": item.get("kind") if item.get("kind") in KINDS else "info"})
    return out[:3]
