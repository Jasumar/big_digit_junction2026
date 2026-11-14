"""The Modal/Gemma provider against a fake OpenAI-compatible server (no GPU, no network)."""
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "apps", "bank-backend"), os.path.join(ROOT, "packages"),
          os.path.join(ROOT, "apps")):
    sys.path.insert(0, p)

import orchestrator  # noqa: E402
from ai.llm_provider import Provider  # noqa: E402
from ai.provider import get_provider  # noqa: E402
from calculation import tools  # noqa: E402
from cloud import seed  # noqa: E402
from cloud.store import Store  # noqa: E402
from contracts import ANSWER, validate  # noqa: E402


class FakeLLM(BaseHTTPRequestHandler):
    replies = []   # queue of python objects (sent as message content JSON) or raw strings
    seen = []      # (headers, body) of each request

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeLLM.seen.append((dict(self.headers), body))
        nxt = FakeLLM.replies.pop(0) if FakeLLM.replies else "not json"
        content = nxt if isinstance(nxt, str) else json.dumps(nxt)
        data = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class TestLLMProvider(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), FakeLLM)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        cls.tmp = tempfile.TemporaryDirectory()
        db = os.path.join(cls.tmp.name, "t.sqlite")
        seed.build(seed.FIXTURE_DIR, db)
        cls.store = Store(db)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.tmp.cleanup()

    def setUp(self):
        FakeLLM.replies, FakeLLM.seen = [], []
        self.p = Provider(base_url=self.url, api_key="test-key", model="gemma", timeout=5)

    def test_plan_request_shape_and_result(self):
        FakeLLM.replies = [{"requests": [{"tool": "spending_breakdown",
                                          "args": {"period": "this_month"}}]}]
        plan = self.p.plan("Mihin rahani menivät tässä kuussa?", tools.describe_catalog())
        self.assertEqual(plan, {"requests": [{"tool": "spending_breakdown",
                                              "args": {"period": "this_month"}}]})
        headers, body = FakeLLM.seen[0]
        self.assertEqual(headers["Authorization"], "Bearer test-key")
        self.assertEqual(body["model"], "gemma")
        enum = body["response_format"]["json_schema"]["schema"]["properties"]["requests"][
            "items"]["properties"]["tool"]["enum"]
        self.assertIn("simulate_change", enum)
        self.assertIn("spending_breakdown", body["messages"][0]["content"])

    def test_direct_reply(self):
        FakeLLM.replies = [{"requests": [], "reply": "Budjetointi tarkoittaa..."}]
        plan = self.p.plan("Mitä on budjetointi?", tools.describe_catalog())
        self.assertEqual(plan["requests"], [])
        self.assertTrue(plan["reply"].startswith("Budjetointi"))

    def test_bad_reply_falls_back_to_stub(self):
        FakeLLM.replies = ["this is not json"]
        plan = self.p.plan("What kind of spender am I?", tools.describe_catalog())
        self.assertEqual(plan["requests"][0]["tool"], "spender_profile")  # stub's answer
        FakeLLM.replies = [{"text": "", "insights": []}]
        out = self.p.compose("x", [{"tool": "safe_to_spend", "ok": False, "error": "e"}])
        self.assertIn("couldn't run", out["text"])  # stub wording

    def test_unreachable_server_falls_back(self):
        p = Provider(base_url="http://127.0.0.1:9", api_key="k", timeout=1)
        plan = p.plan("Where did my money go?", tools.describe_catalog())
        self.assertEqual(plan["requests"][0]["tool"], "spending_breakdown")

    def test_full_flow_through_orchestrator(self):
        FakeLLM.replies = [
            {"requests": [{"tool": "simulate_change",
                           "args": {"category": "Restaurants", "change_pct": -20}}]},
            {"text": "Jos vähennät ravintolakuluja 20 %, säästät noin 23 € kuussa.",
             "insights": [{"title": "Säästö vuodessa", "body": "Noin 277 €.", "kind": "good"},
                          {"title": "x", "body": "y", "kind": "bogus"}]},
        ]
        a = orchestrator.handle_command(
            {"customer_id": "CUST00001", "text": "Paljonko säästäisin, jos syön ulkona 20 % vähemmän?"},
            self.store, self.p)
        self.assertEqual(validate(ANSWER, a), [])
        self.assertTrue(a["text"].startswith("Jos vähennät"))
        self.assertEqual(a["insights"][1]["kind"], "info")  # unknown kind normalised
        self.assertEqual(a["trace"][0], {"tool": "simulate_change", "approved": True,
                                         "note": "ok"})
        self.assertTrue(a["visuals"])  # charts still come from the backend
        sent = json.loads(FakeLLM.seen[1][1]["messages"][-1]["content"].split("(JSON):\n")[1])
        self.assertNotIn("CUST00001", json.dumps(sent))  # results only, no customer id

    def test_model_cannot_pick_the_customer(self):
        FakeLLM.replies = [
            {"requests": [{"tool": "spending_breakdown", "args": {"customer_id": "CUST00002"}}]},
            {"text": "I could not check that.", "insights": []}]
        a = orchestrator.handle_command({"customer_id": "CUST00001", "text": "x"},
                                        self.store, self.p)
        self.assertFalse(a["trace"][0]["approved"])

    def test_registry(self):
        os.environ["AI_BASE_URL"] = self.url
        try:
            self.assertEqual(get_provider("modal").name, "modal-gemma")
        finally:
            del os.environ["AI_BASE_URL"]
        with self.assertRaises(ValueError):
            Provider(base_url="")


if __name__ == "__main__":
    unittest.main()
