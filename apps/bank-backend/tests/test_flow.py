"""End-to-end checks on the committed fixture data. Run: bash scripts/test.sh"""
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "apps", "bank-backend"), os.path.join(ROOT, "packages"),
          os.path.join(ROOT, "apps")):
    sys.path.insert(0, p)

import approval  # noqa: E402
import orchestrator  # noqa: E402
import server  # noqa: E402
from ai.provider import get_provider  # noqa: E402
from calculation import tools  # noqa: E402
from cloud import seed  # noqa: E402
from cloud.store import Store  # noqa: E402
from contracts import ANSWER, CALCULATION_REQUEST, CALCULATION_RESULT, COMMAND, EXAMPLES, validate  # noqa: E402

CID = "CUST00001"


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db = os.path.join(cls.tmp.name, "t.sqlite")
        seed.build(seed.FIXTURE_DIR, db)
        cls.store = Store(db)
        cls.provider = get_provider("stub")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def ask(self, text, cid=CID):
        return orchestrator.handle_command({"customer_id": cid, "text": text},
                                           self.store, self.provider)


class TestContracts(unittest.TestCase):
    def test_examples_match_schemas(self):
        for name, schema in (("command", COMMAND), ("calculation_request", CALCULATION_REQUEST),
                             ("calculation_result", CALCULATION_RESULT), ("answer", ANSWER)):
            self.assertEqual(validate(schema, EXAMPLES[name]), [], name)

    def test_validator_rejects(self):
        self.assertTrue(validate(COMMAND, {"customer_id": "x"}))
        self.assertTrue(validate(COMMAND, {"customer_id": "x", "text": "a", "extra": 1}))


class TestApproval(unittest.TestCase):
    def test_policy(self):
        ok = lambda t, a: approval.check({"tool": t, "args": a}, CID)[0]
        self.assertTrue(ok("spending_breakdown", {"period": "last_month"}))
        self.assertFalse(ok("drop_tables", {}))
        self.assertFalse(ok("spending_breakdown", {"period": "forever"}))
        self.assertFalse(ok("spending_breakdown", {"customer_id": "CUST00002"}))
        self.assertFalse(ok("safe_to_spend", {"horizon_days": 400}))
        self.assertFalse(ok("simulate_change", {"category": "Restaurants"}))
        self.assertFalse(ok("simulate_change", {"change_pct": -500, "bucket": "everyday"}))
        self.assertTrue(ok("simulate_change", {"change_pct": -20, "bucket": "everyday"}))
        self.assertFalse(ok("explore_transactions", {"group_by": "customer_id"}))
        self.assertFalse(approval.check({"tool": "spender_profile", "args": {}}, "")[0])


class TestTools(Base):
    def test_buckets_add_up(self):
        d = tools.run("spending_breakdown", self.store, CID, {"period": "last_90_days"})
        self.assertAlmostEqual(sum(b["amount"] for b in d["buckets"]), d["total_spend"], 1)
        self.assertAlmostEqual(sum(c["amount"] for c in d["categories"]), d["total_spend"], 1)

    def test_explore_matches_breakdown(self):
        a = tools.run("spending_breakdown", self.store, CID, {"period": "last_30_days"})
        b = tools.run("explore_transactions", self.store, CID,
                      {"period": "last_30_days", "group_by": "none"})
        self.assertAlmostEqual(a["total_spend"], b["total"], 1)

    def test_safe_to_spend_never_negative(self):
        for cid in ("CUST00001", "CUST00002", "CUST00003", "CUST00004"):
            d = tools.run("safe_to_spend", self.store, cid, {"horizon_days": 7})
            self.assertGreaterEqual(d["safe_to_spend"], 0)

    def test_all_four_files_loaded(self):
        info = self.store.info()
        self.assertEqual((info["customers"], info["mortgage_applications"]), (6, 1))
        self.assertGreater(info["mortgage_events"], 0)
        app = self.store.one("SELECT * FROM mortgage_applications WHERE customer_id = ?",
                             ("CUST00006",))
        self.assertEqual(app["final_decision"], "rejected")
        self.assertAlmostEqual(app["final_loan_to_value"], 0.93, 2)

    def test_every_tool_runs_for_every_customer(self):
        for cid in [c["customer_id"] for c in self.store.list_customers(10)]:
            for t in tools.CATALOG:
                args = {"change_pct": -20, "bucket": "everyday"} \
                    if t["name"] == "simulate_change" else {}
                tools.run(t["name"], self.store, cid, args)


    def test_simulation_math(self):
        d = tools.run("simulate_change", self.store, CID,
                      {"category": "Restaurants", "change_pct": -20, "months_ahead": 6})
        self.assertAlmostEqual(d["new_monthly"], d["baseline_monthly"] * 0.8, 1)
        self.assertAlmostEqual(d["monthly_saving"], d["baseline_monthly"] * 0.2, 1)
        self.assertAlmostEqual(d["saving_over_horizon"], d["monthly_saving"] * 6, 0)
        self.assertGreaterEqual(d["savings_rate_pct_after"], d["savings_rate_pct_now"])
        with self.assertRaises(ValueError):
            tools.run("simulate_change", self.store, CID, {"change_pct": -20})


class TestFlow(Base):
    def test_brief_questions(self):
        for q, tool in (("Where did my money go?", "spending_breakdown"),
                        ("What kind of spender am I?", "spender_profile"),
                        ("What can I safely spend this week?", "safe_to_spend"),
                        ("How could I save more?", "savings_opportunities"),
                        ("How much could I save if I reduced dining out by 20%?",
                         "simulate_change")):
            a = self.ask(q)
            self.assertEqual(validate(ANSWER, a), [], q)
            self.assertEqual([t["tool"] for t in a["trace"]], [tool], q)
            self.assertTrue(a["visuals"] and a["insights"], q)

    def test_free_exploration(self):
        a = self.ask("Show my restaurant spending by month")
        self.assertEqual(a["trace"][0]["tool"], "explore_transactions")

    def test_smalltalk_runs_no_tool(self):
        a = self.ask("hello")
        self.assertEqual(a["trace"], [])
        self.assertTrue(a["text"])

    def test_rejected_request_is_reported_not_run(self):
        class Evil:
            name = "evil"
            def plan(self, text, tools, history=None):
                return {"requests": [{"tool": "spending_breakdown",
                                      "args": {"customer_id": "CUST00002"}}]}
            def compose(self, text, results, history=None):
                return {"text": "rejected=%s" % results[0].get("rejected"), "insights": []}
        a = orchestrator.handle_command({"customer_id": CID, "text": "x"}, self.store, Evil())
        self.assertFalse(a["trace"][0]["approved"])
        self.assertEqual(a["text"], "rejected=True")

    def test_bad_input(self):
        with self.assertRaises(orchestrator.BadCommand):
            self.ask("hi", cid="NOBODY")
        with self.assertRaises(orchestrator.BadCommand):
            orchestrator.handle_command({"text": "hi"}, self.store, self.provider)

    def test_sample_data_guard(self):
        old = os.environ.get("SPANKKI_DB")
        os.environ["SPANKKI_DB"] = self.store.path  # a fixture database
        try:
            with self.assertRaises(server.SampleDataError):
                server.open_store(require_full=True)
            self.assertEqual(server.open_store(require_full=False).info()["source"], "fixture")
            os.environ["SPANKKI_DB"] = os.path.join(self.tmp.name, "missing.sqlite")
            with self.assertRaises(server.SampleDataError):
                server.open_store(require_full=True)
            self.assertFalse(os.path.exists(os.environ["SPANKKI_DB"]))
        finally:
            if old is None:
                os.environ.pop("SPANKKI_DB", None)
            else:
                os.environ["SPANKKI_DB"] = old

    def test_http(self):
        server.Handler.store, server.Handler.provider = self.store, self.provider
        srv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:%d" % srv.server_address[1]
        try:
            h = json.load(urllib.request.urlopen(base + "/api/health"))
            self.assertTrue(h["ok"])
            self.assertEqual(h["data"]["source"], "fixture")
            self.assertEqual(h["data"]["customers"], 6)
            self.assertIn(b"Money Coach", urllib.request.urlopen(base + "/").read())
            self.assertIn(b"createClient", urllib.request.urlopen(base + "/client/client.js").read())
            req = urllib.request.Request(base + "/api/command", method="POST", data=json.dumps(
                {"customer_id": CID, "text": "Where did my money go?"}).encode())
            self.assertEqual(validate(ANSWER, json.load(urllib.request.urlopen(req))), [])
            ov = json.load(urllib.request.urlopen(base + "/api/overview?customer_id=" + CID))
            self.assertIn("safe_to_spend", ov)
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(base + "/../AGENTS.md")
            self.assertEqual(cm.exception.code, 404)
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()
