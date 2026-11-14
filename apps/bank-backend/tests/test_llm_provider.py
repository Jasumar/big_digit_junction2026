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
        self.assertEqual(a["lang"], "en")  # the fake reply had no lang -> English charts
        sent = json.loads(FakeLLM.seen[1][1]["messages"][-1]["content"].split("(JSON):\n")[1])
        self.assertNotIn("CUST00001", json.dumps(sent))  # results only, no customer id

    def test_partial_answer_gets_notice_and_invented_numbers_are_removed(self):
        FakeLLM.replies = [
            {"requests": [{"tool": "spending_breakdown", "args": {"period": "this_month"}}],
             "coverage": "partial", "lang": "fi",
             "limitation": "En voi valita maaliskuuta; näytän syyskuun."},
            # compose invents 357 €, retry still invents it -> backend must strip it
            {"lang": "fi", "text": "Kulutit 1 879 € syyskuussa. Ravintoloihin meni 357 €.",
             "insights": [{"title": "Keksitty", "body": "Säästit 4 444 €.", "kind": "info"},
                          {"title": "Oikea", "body": "Tulot 2 448 €.", "kind": "good"}]},
            {"lang": "fi", "text": "Kulutit 1 879 € syyskuussa. Ravintoloihin meni 357 €.",
             "insights": [{"title": "Keksitty", "body": "Säästit 4 444 €.", "kind": "info"}]},
        ]
        a = orchestrator.handle_command(
            {"customer_id": "CUST00001", "text": "Paljonko kulutin maaliskuussa?"},
            self.store, self.p)
        self.assertEqual(validate(ANSWER, a), [])
        self.assertIn("kalenterikuukautta", a["notice"])  # decided by the scope check
        self.assertNotIn("357", a["text"])
        self.assertNotIn("4 444", json.dumps(a["insights"], ensure_ascii=False))
        self.assertEqual(a["data_as_of"], self.store.as_of("CUST00001"))
        retry = FakeLLM.seen[2][1]["messages"][-1]["content"]
        self.assertIn("357", retry)  # the model was told which numbers were not backed
        self.assertIn("kalenterikuukautta", FakeLLM.seen[1][1]["messages"][-1]["content"])

    def test_rejected_plan_gets_one_retry(self):
        FakeLLM.replies = [
            {"requests": [{"tool": "explore_transactions",
                           "args": {"category": "Investments"}}], "coverage": "full", "lang": "fi"},
            {"requests": [{"tool": "explore_transactions",
                           "args": {"category": "Invest Deposit", "group_by": "none"}}],
             "coverage": "full", "lang": "fi"},
            {"lang": "fi", "text": "Sijoitit rahaa.", "insights": []},
        ]
        a = orchestrator.handle_command({"customer_id": "CUST00001",
                                         "text": "Paljonko olen sijoittanut?"}, self.store, self.p)
        self.assertEqual([x["approved"] for x in a["trace"]], [True])
        self.assertIn("rejected", FakeLLM.seen[1][1]["messages"][-1]["content"])

    def test_model_cannot_pick_the_customer(self):
        FakeLLM.replies = [
            {"requests": [{"tool": "spending_breakdown", "args": {"customer_id": "CUST00002"}}]},
            {"text": "I could not check that.", "insights": []}]
        a = orchestrator.handle_command({"customer_id": "CUST00001", "text": "x"},
                                        self.store, self.p)
        self.assertFalse(a["trace"][0]["approved"])

    def test_money_format(self):
        from ai.llm_provider import format_money
        self.assertEqual(format_money("You spent 1 879 € and 4,50 €.", "en"),
                         "You spent €1,879 and €4.50.")
        self.assertEqual(format_money("Käytit €1,879 ja €4.50.", "fi"),
                         "Käytit 1\u00a0879\u00a0€ ja 4,50\u00a0€.")
        self.assertEqual(format_money("Sinulla on 3 796,50 €", "fi"), "Sinulla on 3\u00a0797\u00a0€")
        self.assertEqual(format_money("you spent €1,903.71 a month", "en"), "you spent €1,904 a month")
        self.assertEqual(format_money("only €1,903.49", "en"), "only €1,903")
        self.assertEqual(format_money("You have 3,797 € to spend", "en"), "You have €3,797 to spend")
        self.assertEqual(format_money("Du har 3,796.50 € kvar", "sv"), "Du har 3\u00a0797\u00a0€ kvar")
        self.assertEqual(format_money("Säästö 46 € kuussa", "fi"), "Säästö 46\u00a0€ kuussa")
        self.assertEqual(format_money("23 % and 2026", "en"), "23 % and 2026")

    def test_date_format(self):
        from ai.llm_provider import format_dates
        self.assertEqual(format_dates("ajalta 2025-10-01–2026-09-30", "fi"),
                         "ajalta 1.10.2025–30.9.2026")
        self.assertEqual(format_dates("until 2026-09-30", "en"), "until 30 Sep 2026")
        self.assertEqual(format_dates("id 2026-13-40", "fi"), "id 2026-13-40")

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


class TestEvalRunner(unittest.TestCase):
    """The evaluation harness itself (apps/ai/eval) runs offline with the stub."""

    def test_checks(self):
        sys.path.insert(0, os.path.join(ROOT, "apps", "ai", "eval"))
        import run_eval
        self.assertEqual(run_eval.detect_lang("Käytit tässä kuussa noin 1 879 € ja se on hyvä"), "fi")
        self.assertEqual(run_eval.detect_lang("Du har spenderat det här och det är bra"), "sv")
        self.assertEqual(run_eval.numbers_in("1 879 € ja 23,3 %", "fi"), [1879.0, 23.3])
        self.assertEqual(run_eval.numbers_in("€1,879 and 4.5", "en"), [1879.0, 4.5])
        self.assertTrue(run_eval.grounded(1879, [1879.4]))
        self.assertFalse(run_eval.grounded(5000, [1879.4]))
        tmp = tempfile.TemporaryDirectory()
        db = os.path.join(tmp.name, "t.sqlite")
        seed.build(seed.FIXTURE_DIR, db)
        store = Store(db)
        case = {"id": "x", "lang": "en", "q": "Where did my money go?",
                "tools": ["spending_breakdown"], "must_not": ["CUST"]}
        r = run_eval.run_case(case, store, get_provider("stub"), "CUST00001")
        self.assertTrue(r["passed"], r)
        tmp.cleanup()
