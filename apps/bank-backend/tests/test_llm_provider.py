"""Offline tests for the hosted model provider and its fallback."""
import io
import json
import os
import sys
import threading
import unittest
import urllib.error
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for path in (os.path.join(ROOT, "apps", "bank-backend"), os.path.join(ROOT, "packages"),
             os.path.join(ROOT, "apps")):
    if path not in sys.path:
        sys.path.insert(0, path)

import orchestrator  # noqa: E402
from ai.llm_provider import LLMError, Provider, SAFE_REPLY  # noqa: E402
from ai.provider import get_provider  # noqa: E402
from calculation import tools  # noqa: E402
from contracts import ANSWER, PLAN, validate  # noqa: E402


ENV = {"LLM_BASE_URL": "https://example.test/v1/", "LLM_MODEL": "test-model",
       "LLM_API_KEY": "test-key", "LLM_TIMEOUT_S": "15"}


def response(message, finish_reason="stop"):
    return io.BytesIO(json.dumps({"choices": [{"message": message,
                                               "finish_reason": finish_reason}]}).encode())


def tool_call(name, args):
    return {"type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


class Store:
    def customer(self, customer_id):
        return {"customer_id": customer_id}


class TestLLMProvider(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, ENV)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.provider = Provider()

    @mock.patch("urllib.request.urlopen")
    def test_tool_calls_map_to_valid_plan_and_send_catalog(self, urlopen):
        calls = [tool_call("spending_breakdown", {"period": "last_month"})] * 4
        urlopen.return_value = response({"tool_calls": calls})
        catalog = tools.describe_catalog()
        history = [{"role": "user", "text": "Hi"}, {"role": "coach", "text": "Hello"}]
        plan = self.provider.plan("Where did I spend?", catalog, history)
        self.assertEqual(validate(PLAN, plan), [])
        self.assertEqual(plan["requests"], [{"tool": "spending_breakdown",
                                            "args": {"period": "last_month"}}] * 3)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.test/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 15)
        payload = json.loads(request.data)
        self.assertEqual(payload["tools"], [{"type": "function", "function": tool}
                                             for tool in catalog])
        self.assertEqual([m["role"] for m in payload["messages"]],
                         ["system", "user", "assistant", "user"])

    @mock.patch("urllib.request.urlopen")
    def test_plain_reply(self, urlopen):
        urlopen.return_value = response({"content": "Hello!"})
        plan = self.provider.plan("Hello", tools.describe_catalog(), [])
        self.assertEqual(plan, {"reply": "Hello!"})
        self.assertEqual(validate(PLAN, plan), [])

    @mock.patch("urllib.request.urlopen")
    def test_bad_tool_arguments_and_bad_responses_raise(self, urlopen):
        for message in (
                {"tool_calls": [{"type": "function",
                                 "function": {"name": "x", "arguments": "not json"}}]},
                {"tool_calls": [{"type": "function",
                                 "function": {"name": "x", "arguments": '{"x": NaN}'}}]},
                {"tool_calls": [tool_call("x", ["not", "an", "object"])]},
                {"content": "x" * 2001},
                {"content": None}):
            with self.subTest(message=message):
                urlopen.return_value = response(message)
                with self.assertRaises(LLMError):
                    self.provider.plan("Hello", [], [])
        urlopen.return_value = io.BytesIO(b"not json")
        with self.assertRaisesRegex(LLMError, "invalid JSON response"):
            self.provider.plan("Hello", [], [])
        urlopen.return_value = response({"content": "partial"}, finish_reason="length")
        with self.assertRaisesRegex(LLMError, "incomplete"):
            self.provider.plan("Hello", [], [])

    @mock.patch("urllib.request.urlopen")
    def test_compose_uses_json_mode_and_removes_customer_ids(self, urlopen):
        answer = {"text": "You spent 42.", "insights": [
            {"title": "Spending", "body": "42", "kind": "info"}]}
        urlopen.return_value = response({"content": json.dumps(answer)})
        results = [{"tool": "example", "ok": True, "data": {
            "customer_id": "secret-id", "nested": [{"customer_id": "secret-id", "total": 42}]}}]
        self.assertEqual(self.provider.compose("My spending?", results, []), answer)
        payload = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertNotIn("secret-id", json.dumps(payload))
        self.assertIn('"total": 42', payload["messages"][-1]["content"])
        self.assertEqual(results[0]["data"]["customer_id"], "secret-id")

    @mock.patch("urllib.request.urlopen")
    def test_bad_composition_json_returns_safe_text(self, urlopen):
        for content in ("not json", "[]", '{"text": 4, "insights": []}',
                        '{"text": "ok", "insights": [{"title": "x", "body": "y"}]}',
                        '{"text": "ok", "insights": [{"title": "x", "body": "y", "kind": "bad"}]}'):
            with self.subTest(content=content), self.assertLogs("ai.llm_provider", "WARNING"):
                urlopen.return_value = response({"content": content})
                self.assertEqual(self.provider.compose("Hello", [], []),
                                 {"text": SAFE_REPLY, "insights": []})

    @mock.patch("urllib.request.urlopen")
    def test_step_sends_tool_history_and_parses_outcomes(self, urlopen):
        catalog = tools.describe_catalog()
        asked = [{"tool": "spending_breakdown", "args": {"period": "last_month"}},
                 {"tool": "bad_tool", "args": {}}]
        messages = [{"role": "coach", "text": "Hello"}, {"role": "user", "text": "Q"},
                    {"role": "requests", "requests": asked},
                    {"role": "results", "results": [
                        {"tool": "spending_breakdown", "ok": True,
                         "data": {"customer_id": "C", "total_spend": 5}, "args": {}},
                        {"tool": "bad_tool", "ok": False, "rejected": True,
                         "error": "unknown tool 'bad_tool'"}]}]
        urlopen.return_value = response({"content": json.dumps(
            {"text": "Done", "insights": []})})
        self.assertEqual(self.provider.step(messages, catalog),
                         {"final": {"text": "Done", "insights": []}})
        payload = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual([m["role"] for m in payload["messages"]],
                         ["system", "assistant", "user", "assistant", "tool", "tool"])
        calls = payload["messages"][3]["tool_calls"]
        self.assertEqual([c["id"] for c in calls], ["call_1", "call_2"])
        self.assertEqual([m["tool_call_id"] for m in payload["messages"][4:]],
                         ["call_1", "call_2"])
        self.assertNotIn("customer_id", payload["messages"][4]["content"])
        self.assertIn('"rejected": true', payload["messages"][5]["content"])
        self.assertIn("tools", payload)

        urlopen.return_value = response({"tool_calls": [tool_call("safe_to_spend", {})]})
        self.assertEqual(self.provider.step(messages[:2], catalog),
                         {"requests": [{"tool": "safe_to_spend", "args": {}}]})
        urlopen.return_value = response({"content": "Plain text"})
        self.assertEqual(self.provider.step(messages[:2], catalog),
                         {"final": {"text": "Plain text", "insights": []}})

    @mock.patch("urllib.request.urlopen")
    def test_step_without_tools_composes_final_answer(self, urlopen):
        urlopen.return_value = response({"content": json.dumps(
            {"text": "Final", "insights": []})})
        messages = [{"role": "user", "text": "Q"},
                    {"role": "requests", "requests": [{"tool": "t", "args": {}}]},
                    {"role": "results", "results": [{"tool": "t", "ok": True, "data": {}}]}]
        self.assertEqual(self.provider.step(messages, []),
                         {"final": {"text": "Final", "insights": []}})
        payload = json.loads(urlopen.call_args.args[0].data)
        self.assertNotIn("tools", payload)
        self.assertEqual(payload["response_format"], {"type": "json_object"})

    @mock.patch("urllib.request.urlopen")
    def test_fallback_step_uses_stub_after_failure(self, urlopen):
        provider = get_provider("llm")
        urlopen.side_effect = TimeoutError("timeout")
        with self.assertLogs("ai.provider", "WARNING"):
            answer = orchestrator.handle_command(
                {"customer_id": "CUST1", "text": "hello"}, Store(), provider)
        self.assertEqual(answer["provider"], "stub (fallback)")
        self.assertTrue(answer["text"])

    @mock.patch("urllib.request.urlopen")
    def test_timeout_falls_back_and_next_request_retries(self, urlopen):
        provider = get_provider("llm")
        urlopen.side_effect = [TimeoutError("timeout"), response({"content": "Hello again"})]
        with self.assertLogs("ai.provider", "WARNING"):
            answer = orchestrator.handle_command({"customer_id": "CUST1", "text": "hello"},
                                                 Store(), provider)
        self.assertEqual(answer["provider"], "stub (fallback)")
        self.assertEqual(validate(ANSWER, answer), [])
        self.assertTrue(answer["text"])
        answer = orchestrator.handle_command({"customer_id": "CUST1", "text": "hello"},
                                             Store(), provider)
        self.assertEqual(answer["provider"], "llm")
        self.assertEqual(answer["text"], "Hello again")

    @mock.patch("urllib.request.urlopen")
    def test_compose_timeout_uses_stub_for_rejected_result(self, urlopen):
        provider = get_provider("llm")
        urlopen.side_effect = [response({"tool_calls": [tool_call("unknown_tool", {})]}),
                               TimeoutError("timeout")]
        with self.assertLogs("ai.provider", "WARNING"):
            answer = orchestrator.handle_command({"customer_id": "CUST1", "text": "hello"},
                                                 Store(), provider)
        self.assertEqual(answer["provider"], "stub (fallback)")
        self.assertIn("unknown_tool", answer["text"])
        self.assertFalse(answer["trace"][0]["approved"])

    @mock.patch("orchestrator.tools.run")
    @mock.patch("urllib.request.urlopen")
    def test_compose_timeout_uses_stub_for_approved_result(self, urlopen, run):
        provider = get_provider("llm")
        urlopen.side_effect = [response({"tool_calls": [tool_call("safe_to_spend",
                                                                {"horizon_days": 7})]}),
                               TimeoutError("timeout")]
        run.return_value = {"safe_to_spend": 100, "horizon_days": 7, "safe_per_day": 14,
                            "housing_due": {"amount": 0}, "expected_income": {
                                "amount": 0, "next_date": None}, "status": "comfortable",
                            "typical_everyday_spend": 50, "balance": 200,
                            "expected_essentials": 50, "reserve_for_surprises": 25,
                            "buffer": 25, "until": "2026-09-30"}
        with self.assertLogs("ai.provider", "WARNING"):
            answer = orchestrator.handle_command(
                {"customer_id": "CUST1", "text": "safe to spend"}, Store(), provider)
        self.assertEqual(answer["provider"], "stub (fallback)")
        self.assertIn("100", answer["text"])
        self.assertTrue(answer["trace"][0]["approved"])
        self.assertEqual(validate(ANSWER, answer), [])

    @mock.patch("urllib.request.urlopen")
    def test_bad_config_and_http_error_are_clear(self, urlopen):
        with mock.patch.dict(os.environ, {"LLM_TIMEOUT_S": "nan"}):
            with self.assertRaisesRegex(LLMError, "LLM_TIMEOUT_S"):
                self.provider.plan("Hello", [], [])
        urlopen.side_effect = urllib.error.HTTPError("https://example.test", 401, "", {}, None)
        with self.assertRaisesRegex(LLMError, "HTTP 401"):
            self.provider.plan("Hello", [], [])

    @mock.patch("urllib.request.urlopen")
    def test_fallback_status_is_thread_local(self, urlopen):
        provider = get_provider("llm")
        barrier = threading.Barrier(2)
        observed = {}

        def fake_open(request, timeout):
            text = json.loads(request.data)["messages"][-1]["content"]
            if text == "fail":
                raise TimeoutError("timeout")
            return response({"content": "ok"})

        def worker(text):
            provider.plan(text, [], [])
            barrier.wait(timeout=3)
            observed[text] = provider.name

        urlopen.side_effect = fake_open
        with self.assertLogs("ai.provider", "WARNING"):
            threads = [threading.Thread(target=worker, args=(text,)) for text in ("fail", "ok")]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)
        self.assertEqual(observed, {"fail": "stub (fallback)", "ok": "llm"})
        self.assertEqual(provider.name, "llm")


if __name__ == "__main__":
    unittest.main()
