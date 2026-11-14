"""OpenAI-compatible Chat Completions provider."""
import json
import logging
import math
import os
import urllib.error
import urllib.request

from ai.grounding import check
from ai.prompt import build_system_prompt
from ai.provider import split_messages
from contracts import ANSWER, PLAN, validate


STEP_PROMPT = (
    " You may call tools over several rounds; a rejected or failed tool result "
    "explains why, so adjust or answer without it. When you have what you need, reply "
    "with JSON with keys text (string) and insights (array of objects with title, body, "
    "and kind; kind must be info, good, warn, or tip)."
)
SAFE_REPLY = "Sorry, I couldn't prepare an answer. Please try again."
LOGGER = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """A configuration, transport, or response error from the model."""


def _reject_json_constant(value):
    raise ValueError("invalid JSON constant")


def _without_customer_ids(value):
    if isinstance(value, dict):
        return {key: _without_customer_ids(item) for key, item in value.items()
                if key != "customer_id"}
    if isinstance(value, list):
        return [_without_customer_ids(item) for item in value]
    return value


def _answer_text(answer):
    parts = [answer["text"]]
    for insight in answer["insights"]:
        parts += [insight.get("title", ""), insight.get("body", "")]
    return "\n".join(parts)


class Provider:
    name = "llm"

    def _chat(self, messages, **options):
        base_url = os.environ.get("LLM_BASE_URL", "").strip().rstrip("/")
        model = os.environ.get("LLM_MODEL", "").strip()
        api_key = os.environ.get("LLM_API_KEY", "").strip()
        if not base_url or not model or not api_key:
            raise LLMError("LLM_BASE_URL, LLM_MODEL and LLM_API_KEY must be configured")
        try:
            timeout = float(os.environ.get("LLM_TIMEOUT_S", "15"))
            if not math.isfinite(timeout) or timeout <= 0:
                raise ValueError("timeout must be positive and finite")
        except ValueError as exc:
            raise LLMError("LLM_TIMEOUT_S must be a positive number") from exc

        payload = {"model": model, "messages": messages, **options}
        try:
            request = urllib.request.Request(
                base_url + "/chat/completions",
                data=json.dumps(payload, allow_nan=False).encode("utf-8"),
                headers={"Content-Type": "application/json",
                         "Authorization": "Bearer " + api_key},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.load(response, parse_constant=_reject_json_constant)
        except urllib.error.HTTPError as exc:
            raise LLMError("LLM request failed with HTTP %s" % exc.code) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise LLMError("LLM request failed or timed out") from exc
        except (ValueError, UnicodeError) as exc:
            raise LLMError("LLM returned an invalid JSON response") from exc
        try:
            choice = body["choices"][0]
            message = choice["message"]
            if not isinstance(message, dict) or choice.get("finish_reason") in (
                    "length", "content_filter"):
                raise ValueError("incomplete response")
            return message
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMError("LLM returned an invalid or incomplete response") from exc

    @staticmethod
    def _messages(text, history):
        messages = [{"role": "system", "content": build_system_prompt()}]
        for turn in history or []:
            messages.append({"role": "assistant" if turn["role"] == "coach" else "user",
                             "content": turn["text"]})
        messages.append({"role": "user", "content": text})
        return messages

    @staticmethod
    def _requests(message):
        """Tool calls of a model message as CalculationRequests, or None if it has none."""
        calls = message.get("tool_calls")
        if calls is not None and not isinstance(calls, list):
            raise LLMError("LLM returned invalid tool calls")
        if not calls:
            return None
        requests = []
        try:
            for call in calls[:3]:
                if call["type"] != "function":
                    raise ValueError("unsupported tool type")
                function = call["function"]
                args = json.loads(function["arguments"], parse_constant=_reject_json_constant)
                requests.append({"tool": function["name"], "args": args})
        except (KeyError, TypeError, ValueError) as exc:
            raise LLMError("LLM returned invalid tool call arguments") from exc
        return requests

    @staticmethod
    def _step_messages(messages):
        """Provider-neutral history -> Chat Completions messages with tool_calls."""
        out = [{"role": "system", "content": build_system_prompt() + STEP_PROMPT}]
        call_ids, counter = [], 0
        for item in messages:
            role = item["role"]
            if role in ("user", "coach"):
                out.append({"role": "assistant" if role == "coach" else "user",
                            "content": item["text"]})
            elif role == "requests":
                call_ids, calls = [], []
                for request in item["requests"]:
                    counter += 1
                    call_ids.append("call_%d" % counter)
                    calls.append({"id": call_ids[-1], "type": "function", "function": {
                        "name": request["tool"],
                        "arguments": json.dumps(request["args"], ensure_ascii=False)}})
                out.append({"role": "assistant", "content": None, "tool_calls": calls})
            elif role == "results":
                for call_id, result in zip(call_ids, item["results"]):
                    out.append({"role": "tool", "tool_call_id": call_id,
                                "content": json.dumps(_without_customer_ids(result),
                                                      ensure_ascii=False)})
        return out

    def step(self, messages, tools):
        if not tools:  # no calculations left: answer from what the results say
            text, history, results = split_messages(messages)
            return {"final": self.compose(text, results, history)}
        functions = [{"type": "function", "function": tool} for tool in tools]
        message = self._chat(self._step_messages(messages), tools=functions)
        requests = self._requests(message)
        if requests:
            return {"requests": requests}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise LLMError("LLM returned an empty reply")
        try:
            answer = json.loads(content, parse_constant=_reject_json_constant)
        except ValueError:
            answer = {"text": content, "insights": []}
        try:
            answer = self._valid_answer(answer)
        except (KeyError, TypeError, ValueError):
            LOGGER.warning("LLM returned invalid answer JSON")
            return {"final": {"text": SAFE_REPLY, "insights": []}}
        question, history, results = split_messages(messages)
        return {"final": self._grounded(question, history, results, answer)}

    def plan(self, text, tools, history=None):
        functions = [{"type": "function", "function": tool} for tool in tools]
        message = self._chat(self._messages(text, history), tools=functions)
        requests = self._requests(message)
        if requests:
            plan = {"requests": requests}
        else:
            plan = {"reply": message.get("content")}
            if not isinstance(plan["reply"], str) or not plan["reply"].strip():
                raise LLMError("LLM returned an empty reply")
        if validate(PLAN, plan):
            raise LLMError("LLM returned an invalid plan")
        return plan

    @staticmethod
    def _valid_answer(answer):
        if not isinstance(answer, dict) or set(answer) != {"text", "insights"}:
            raise ValueError("invalid answer fields")
        candidate = {**answer, "visuals": [], "trace": []}
        if validate(ANSWER, candidate) or not answer["text"].strip():
            raise ValueError("invalid answer shape")
        for insight in answer["insights"]:
            if "kind" not in insight:
                raise ValueError("insight is missing kind")
        return answer

    def _compose_messages(self, text, results, history):
        messages = self._messages(text, history)
        messages.append({
            "role": "user",
            "content": ("Approved tool results (including any errors):\n"
                        + json.dumps(_without_customer_ids(results), ensure_ascii=False)
                        + "\nRespond as JSON with keys text (string) and insights "
                          "(array of objects with title, body, and kind). "
                          "kind must be info, good, warn, or tip."),
        })
        return messages

    def _chat_answer(self, messages):
        """One JSON-mode call -> a valid answer, or the safe reply if it is malformed."""
        message = self._chat(messages, response_format={"type": "json_object"})
        try:
            content = message["content"]
            if not isinstance(content, str):
                raise ValueError("content must be a string")
            return self._valid_answer(json.loads(content, parse_constant=_reject_json_constant))
        except (KeyError, TypeError, ValueError):
            LOGGER.warning("LLM returned invalid answer JSON")
            return {"text": SAFE_REPLY, "insights": []}

    def _grounded(self, text, history, results, answer):
        """Answer whose numbers all come from the results: retry once, then a template."""
        ok, unknown = check(_answer_text(answer), results)
        if ok:
            return answer
        LOGGER.warning("LLM answer had %d number(s) not in the results; retrying", len(unknown))
        messages = self._compose_messages(text, results, history)
        messages.append({"role": "assistant",
                         "content": json.dumps(answer, ensure_ascii=False)})
        messages.append({
            "role": "user",
            "content": ("These numbers are not in the tool results: " + ", ".join(unknown)
                        + ". Rewrite the answer using only numbers from the tool results, "
                          "or leave those figures out. Same JSON format."),
        })
        try:
            retry = self._chat_answer(messages)
            if check(_answer_text(retry), results)[0]:
                return retry
        except LLMError as exc:
            LOGGER.warning("LLM grounding retry failed: %s", exc)
        LOGGER.warning("LLM answer still not grounded; using templated answer")
        from ai.stub_provider import Provider as StubProvider
        return StubProvider().compose(text, results, history)

    def compose(self, text, results, history=None):
        answer = self._chat_answer(self._compose_messages(text, results, history))
        return self._grounded(text, history, results, answer)
