"""End-to-end checks on the committed fixture data. Run: bash scripts/test.sh"""
import io
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

    def test_clean_drops_unknown_args_but_never_customer_id(self):
        req, dropped = approval.clean({"tool": "spending_breakdown", "args": {
            "period": "last_month", "type": "category", "category": "Transportation"}})
        self.assertEqual(req["args"], {"period": "last_month"})
        self.assertEqual(sorted(dropped), ["category", "type"])
        self.assertTrue(approval.check(req, CID)[0])
        req, _ = approval.clean({"tool": "spending_breakdown",
                                 "args": {"customer_id": "CUST00002", "x": 1}})
        self.assertFalse(approval.check(req, CID)[0])  # still rejected
        req, _ = approval.clean({"tool": "explore_transactions",
                                 "args": {"category": ["Invest Deposit"]}})
        self.assertEqual(req["args"], {"category": "Invest Deposit"})
        self.assertTrue(approval.check(req, CID)[0])
        req, _ = approval.clean({"tool": "explore_transactions",
                                 "args": {"category": ["Housing", "Travel"]}})
        self.assertFalse(approval.check(req, CID)[0])  # real lists are still rejected
        req, _ = approval.clean({"tool": "spending_breakdown", "args": {"period": "forever"}})
        self.assertFalse(approval.check(req, CID)[0])  # bad values still rejected


class TestTools(Base):
    def test_profile_signals(self):
        d = tools.run("spender_profile", self.store, "CUST00005", {})
        keys = sorted(s["key"] for s in d["signals"])
        self.assertEqual(keys, ["drives", "events", "invests", "regular_salary", "taxis"])
        for s in d["signals"]:
            self.assertTrue(s["label"] and s["evidence"]["period_days"] == 90)
        self.assertIn("never state them as fact", d["notes"])
        # too short a window says nothing rather than guessing from one purchase
        self.assertEqual(tools.run("spender_profile", self.store, "CUST00005",
                                   {"period": "last_7_days"})["signals"], [])

    def test_profile_signals_reach_the_answer(self):
        import present
        d = tools.run("spender_profile", self.store, "CUST00005", {})
        res = [{"tool": "spender_profile", "ok": True, "data": d}]
        en = json.dumps(present.build(res, "en"))
        fi = json.dumps(present.build(res, "fi"), ensure_ascii=False)
        self.assertIn("What your spending suggests", en)
        self.assertIn("at least", en)
        self.assertIn("Mitä kulutuksesi kertoo", fi)
        self.assertIn("Käyttää takseja", fi)
        for english in ("Takes taxis", "What your spending suggests", "at least"):
            self.assertNotIn(english, fi)
        ans = self.ask("What kind of spender am I?", "CUST00005")
        self.assertTrue(any(i["title"].startswith("Looks like:") for i in ans["insights"]))

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


class TestChartsLanguage(Base):
    def test_charts_follow_language(self):
        import present
        res = [{"tool": "spender_profile", "ok": True,
                "data": tools.run("spender_profile", self.store, CID, {})},
               {"tool": "spending_breakdown", "ok": True,
                "data": tools.run("spending_breakdown", self.store, CID, {})},
               {"tool": "safe_to_spend", "ok": True,
                "data": tools.run("safe_to_spend", self.store, CID, {})}]
        fi = json.dumps(present.build(res, "fi"), ensure_ascii=False)
        en = json.dumps(present.build(res, "en"), ensure_ascii=False)
        sv = json.dumps(present.build(res, "sv"), ensure_ascii=False)
        for word in ("Tyyppi", "Kulutus kuukaudessa", "Kolme menokoria", "Arjen pikkukulut",
                     "Turvallisesti käytettävissä", "Kuukausikulutus menokoreittain"):
            self.assertIn(word, fi)
        for english in ("Monthly spend", "Regular essentials", "Safe to spend", "by basket"):
            self.assertNotIn(english, fi)
        self.assertIn("\u00a0€", fi)
        self.assertNotIn("\u00a0€", en)
        self.assertIn("Monthly spend", en)
        self.assertIn("Vardagsutgifter", sv)
        for t in tools.CATALOG:  # every tool's chart builds in every language
            args = {"change_pct": -20, "bucket": "everyday"} \
                if t["name"] == "simulate_change" else {}
            data = tools.run(t["name"], self.store, CID, args)
            for lang in ("en", "fi", "sv"):
                present.build([{"tool": t["name"], "ok": True, "data": data}], lang)


class TestSafety(Base):
    def test_strip_unbacked(self):
        from ai.grounding import strip_unbacked
        ans = {"lang": "en", "text": "You spent €1,879. You also spent €357 on coffee.",
               "insights": [{"title": "x", "body": "€4,444 saved", "kind": "info"}]}
        out, removed = strip_unbacked(ans, [1879.0], "SAFE")
        self.assertEqual(out["text"], "You spent €1,879.")
        self.assertEqual(out["insights"], [])
        self.assertEqual(sorted(removed), [357.0, 4444.0])
        out, _ = strip_unbacked({"lang": "en", "text": "€357 only.", "insights": []}, [], "SAFE")
        self.assertEqual(out["text"], "SAFE")
        ex = {"lang": "fi", "text": "Esimerkiksi 1 000 € kasvaa 5 %:n korolla.", "insights": []}
        out, _ = strip_unbacked(ex, [], "SAFE", allow_examples=True)
        self.assertIn("1 000", out["text"])

    def test_transfer_categories_are_not_filtered_out(self):
        d = tools.run("explore_transactions", self.store, CID,
                      {"period": "all", "category": "Invest Deposit", "group_by": "none"})
        self.assertEqual(d["direction"], "all")
        self.assertGreaterEqual(d["count"], 0)

    def test_scope_detector(self):
        import scope
        lim = lambda q, lang="fi": scope.limitation(q, lang, "2026-09-30")  # noqa: E731
        self.assertIn("kalenterikuukautta", lim("Paljonko kulutin maaliskuussa?"))
        self.assertEqual(lim("Paljonko kulutin syyskuussa?"), "")      # = this month
        self.assertEqual(lim("Paljonko kulutin elokuussa?"), "")       # = last month
        self.assertEqual(lim("Paljonko käytin liikkumiseen viime kuussa?"), "")
        self.assertIn("single day", lim("What did I spend yesterday?", "en"))
        self.assertEqual(lim("Paljonko kulutan perjantaisin?"), "")  # one weekday: supported
        self.assertIn("kalenterivuosia", lim("Kulutinko enemmän tänä vuonna kuin viime vuonna?"))
        self.assertIn("tallentaa", lim("Aseta minulle 300 euron budjetti ravintoloille."))
        self.assertIn("shop names", lim("How much did I spend at Prisma?", "en"))
        self.assertIn("kahvi", lim("Paljonko käytän kahviin kuukaudessa?"))
        self.assertIn("listata", lim("Näytä viimeiset 5 ostostani."))
        self.assertEqual(lim("Mihin rahani menivät tässä kuussa?"), "")
        self.assertEqual(lim("How much may I spend this week?", "en"), "")
        self.assertEqual(lim("Minä viikonpäivänä kulutan eniten?"), "")

    def test_merchant_ids_never_shown_and_not_accepted(self):
        import scope
        out = scope.redact_merchants({"lang": "fi", "text": "Eniten MRC-GRO-0032:ssa.",
                                      "insights": [{"title": "MRC-ENT-0001", "body": "x"}]})
        self.assertNotIn("MRC-", json.dumps(out))
        ok, _ = approval.check({"tool": "explore_transactions",
                                "args": {"merchant_id": "MRC-GRO-0032"}}, CID)
        self.assertFalse(ok)

    def test_foreign_terms_in_brackets_removed(self):
        import scope
        out = scope.drop_foreign_terms({"lang": "en", "text": "You spend €17 a day on everyday "
                                        "spending (arjen pikkukulut / vardagsutgifter).",
                                        "insights": []})
        self.assertEqual(out["text"], "You spend €17 a day on everyday spending.")
        keep = scope.drop_foreign_terms({"lang": "en", "text": "Rent (due 6 Oct) is set aside.",
                                         "insights": []})
        self.assertIn("(due 6 Oct)", keep["text"])

    def test_day_and_time_analysis(self):
        friday = tools.run("explore_transactions", self.store, CID,
                           {"period": "all", "weekday": "friday", "group_by": "weekday"})
        self.assertTrue(friday["purchases_only"])
        self.assertTrue(all(g["key"] == "Fri" for g in friday["groups"]))
        weekend = tools.run("explore_transactions", self.store, CID,
                            {"period": "all", "day_type": "weekend", "group_by": "category"})
        self.assertNotIn("Housing", [g["key"] for g in weekend["groups"]])
        self.assertNotIn("Utilities", [g["key"] for g in weekend["groups"]])
        with_bills = tools.run("explore_transactions", self.store, CID,
                               {"period": "all", "day_type": "weekend", "include_bills": True,
                                "group_by": "none"})
        self.assertGreaterEqual(with_bills["total"], weekend["total"])
        whole = tools.run("explore_transactions", self.store, CID,
                          {"period": "all", "group_by": "none"})
        self.assertFalse(whole["purchases_only"])  # plain totals still include rent
        night = tools.run("explore_transactions", self.store, CID,
                          {"period": "all", "time_of_day": "night", "group_by": "hour_band"})
        self.assertTrue(all(g["key"] == "night (22-6)" for g in night["groups"]))

    def test_answer_has_data_date(self):
        a = self.ask("Where did my money go?")
        self.assertEqual(a["data_as_of"], self.store.as_of(CID))

class TestOpenRouterProvider(Base):
    """No network: a fake transport stands in for the HTTP call."""

    def provider_with(self, *responses):
        from ai import openrouter_provider as op

        class Fake:
            def __init__(self):
                self.responses = list(responses)
                self.payloads = []

            def __call__(self, payload):
                self.payloads.append(payload)
                return self.responses.pop(0)

        fake = Fake()
        return op.Provider(api_key="test", transport=fake), fake

    @staticmethod
    def message(content=None, tool_calls=None):
        return {"choices": [{"message": {"role": "assistant", "content": content,
                                         "tool_calls": tool_calls or []}}]}

    @staticmethod
    def call(name, arguments):
        return {"id": "c1", "type": "function",
                "function": {"name": name, "arguments": arguments}}

    def test_plan_maps_tool_calls_to_requests(self):
        provider, fake = self.provider_with(self.message(None, [
            self.call("spending_breakdown", '{"period": "last_month", "bogus": null}')]))
        plan = provider.plan("Mihin rahani meni viime kuussa?", tools.describe_catalog())
        self.assertEqual(plan, {"requests": [{"tool": "spending_breakdown",
                                              "args": {"period": "last_month"}}]})
        payload = fake.payloads[0]
        self.assertEqual(payload["model"], "google/gemma-4-26b-a4b-it")
        self.assertEqual(payload["tool_choice"], "auto")
        self.assertEqual(payload["messages"][-1]["content"], "Mihin rahani meni viime kuussa?")
        names = [t["function"]["name"] for t in payload["tools"]]
        self.assertEqual(names, [t["name"] for t in tools.describe_catalog()])
        self.assertIn("parameters", payload["tools"][0]["function"])

    def test_plan_smalltalk_is_a_reply(self):
        provider, fake = self.provider_with(self.message("Hei! Kysy rahankäytöstäsi."))
        self.assertEqual(provider.plan("moi", tools.describe_catalog()),
                         {"requests": [], "reply": "Hei! Kysy rahankäytöstäsi."})

    def test_plan_skips_unparseable_arguments_and_caps_at_three(self):
        provider, _ = self.provider_with(self.message(None, [
            self.call("spending_breakdown", "not json"),
            self.call("spender_profile", "{}"),
            self.call("safe_to_spend", '{"horizon_days": 7}'),
            self.call("savings_opportunities", "{}"),
            self.call("explore_transactions", "{}"),
        ]))
        plan = provider.plan("x", tools.describe_catalog())
        self.assertEqual(len(plan["requests"]), 3)
        self.assertEqual(plan["requests"][0]["tool"], "spender_profile")

    def test_compose_parses_json_and_fixes_kinds(self):
        provider, fake = self.provider_with(self.message(
            '```json\n{"text": "Käytit 1 234,50 € viime kuussa.", "insights": ['
            '{"title": "Asuminen", "body": "Suurin menoerä.", "kind": "bogus"},'
            '{"title": "no body"}]}\n```'))
        out = provider.compose("mihin rahat meni", [{"tool": "spending_breakdown", "ok": True,
                                                     "data": {"total_spend": 1234.5}}])
        self.assertEqual(out["text"], "Käytit 1 234,50 € viime kuussa.")
        self.assertEqual(out["insights"], [{"title": "Asuminen", "body": "Suurin menoerä.",
                                            "kind": "info"}])
        self.assertEqual(fake.payloads[0]["response_format"], {"type": "json_object"})
        self.assertIn("spending_breakdown", fake.payloads[0]["messages"][-1]["content"])

    def test_compose_falls_back_to_prose(self):
        provider, _ = self.provider_with(self.message("Et voi näyttää tuota juuri nyt."))
        self.assertEqual(provider.compose("x", [{"tool": "safe_to_spend", "ok": False,
                                                 "error": "rejected"}]),
                         {"text": "Et voi näyttää tuota juuri nyt.", "insights": []})

    def test_api_error_is_loud_not_invented(self):
        from ai import openrouter_provider as op
        provider, _ = self.provider_with({"error": {"message": "model not found"}})
        with self.assertRaises(op.OpenRouterError):
            provider.plan("x", tools.describe_catalog())

    def test_missing_key_is_a_clear_error(self):
        from ai import openrouter_provider as op
        with self.assertRaises(op.OpenRouterError) as cm:
            op.Provider(api_key="")
        self.assertIn("OPENROUTER_API_KEY", str(cm.exception))

    def test_end_to_end_with_fake_transport(self):
        provider, fake = self.provider_with(
            self.message(None, [self.call("safe_to_spend", '{"horizon_days": 7}')]),
            self.message('{"text": "Voit käyttää turvallisesti 120 €.", "insights": '
                         '[{"title": "Turvamarginaali", "body": "7 päivän horisontti.", '
                         '"kind": "good"}]}'))
        answer = orchestrator.handle_command(
            {"customer_id": CID, "text": "Kuinka paljon voin käyttää?"}, self.store, provider)
        self.assertEqual(validate(ANSWER, answer), [])
        self.assertEqual(answer["provider"], "openrouter")
        self.assertEqual([t["tool"] for t in answer["trace"]], ["safe_to_spend"])
        self.assertEqual(len(fake.payloads), 2)


class TestProviderSelection(unittest.TestCase):
    """The three providers coexist: picking one never disturbs the others."""

    KEYS = ("AI_BASE_URL", "OPENROUTER_API_KEY", "AI_PROVIDER")

    def setUp(self):
        self.saved = {k: os.environ.get(k) for k in self.KEYS}

    def tearDown(self):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_stub_needs_nothing(self):
        for k in self.KEYS:  # incl. AI_PROVIDER, so the default is what is tested
            os.environ.pop(k, None)
        self.assertEqual(get_provider("stub").name, "stub")
        self.assertEqual(get_provider().name, "stub")  # the default

    def test_openrouter_needs_only_its_key(self):
        os.environ.pop("AI_BASE_URL", None)
        os.environ["OPENROUTER_API_KEY"] = "test-key"
        self.assertEqual(get_provider("openrouter").name, "openrouter")

    def test_modal_needs_only_its_url(self):
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ["AI_BASE_URL"] = "http://127.0.0.1:9"
        self.assertEqual(get_provider("modal").name, "modal-gemma")

    def test_one_providers_config_does_not_block_another(self):
        # A Modal deployment URL set but no OpenRouter key: modal works, openrouter
        # says what is missing, stub still answers.
        os.environ["AI_BASE_URL"] = "http://127.0.0.1:9"
        os.environ["OPENROUTER_API_KEY"] = ""
        self.assertEqual(get_provider("modal").name, "modal-gemma")
        self.assertEqual(get_provider("stub").name, "stub")
        with self.assertRaises(RuntimeError) as cm:
            get_provider("openrouter")
        self.assertIn("OPENROUTER_API_KEY", str(cm.exception))

    def test_unknown_provider_is_a_clear_error(self):
        with self.assertRaises(ValueError) as cm:
            get_provider("gpt-5")
        self.assertIn("stub, modal, openrouter", str(cm.exception))


class TestUiLanguage(Base):
    def test_overview_bucket_labels_follow_language(self):
        fi = orchestrator.overview(CID, self.store, "fi")["bucket_labels"]
        self.assertEqual(fi["everyday"], "Arjen pikkukulut")
        sv = orchestrator.overview(CID, self.store, "sv")["bucket_labels"]
        self.assertEqual(sv["everyday"], "Vardagsutgifter")
        self.assertEqual(orchestrator.overview(CID, self.store)["bucket_labels"]["everyday"],
                         "Everyday spending")

    def test_ui_language_is_the_fallback(self):
        class NoLang:  # a provider that does not report the answer language
            name = "nolang"
            def plan(self, text, tools, history=None, context=None):
                return {"requests": [{"tool": "spending_breakdown", "args": {}}]}
            def compose(self, text, results, history=None, context=None):
                return {"text": "Ok.", "insights": []}
        a = orchestrator.handle_command({"customer_id": CID, "text": "x", "lang": "fi"},
                                        self.store, NoLang())
        self.assertEqual(a["lang"], "fi")
        self.assertIn("Kolme menokoria", json.dumps(a["visuals"], ensure_ascii=False))
        b = orchestrator.handle_command({"customer_id": CID, "text": "x"}, self.store, NoLang())
        self.assertEqual(b["lang"], "en")
        with self.assertRaises(orchestrator.BadCommand):
            orchestrator.handle_command({"customer_id": CID, "text": "x", "lang": "de"},
                                        self.store, NoLang())


class TestFollowUps(Base):
    """First four by CuriousGeorg1 (feat/t009), adapted; the rest cover the integration."""

    def test_savings_opportunities_offers_choices(self):
        a = self.ask("How could I save more?")
        self.assertEqual(validate(ANSWER, a), [])
        for f in a["follow_ups"]:
            self.assertIn(f["kind"], ("clarify", "explore"))
            self.assertTrue(f["label"] and f["prompt"])

    def test_tapping_a_follow_up_is_itself_a_valid_answer(self):
        a = self.ask("How could I save more?")
        if not a["follow_ups"]:
            self.skipTest("no savings ideas for this fixture customer")
        b = self.ask(a["follow_ups"][0]["prompt"])
        self.assertEqual(validate(ANSWER, b), [])
        self.assertEqual(b["trace"][0]["tool"], "simulate_change")

    def test_follow_ups_capped_and_deduped(self):
        a = self.ask("What kind of spender am I?")
        self.assertLessEqual(len(a["follow_ups"]), 3)
        self.assertEqual(len(a["follow_ups"]), len({f["prompt"] for f in a["follow_ups"]}))

    def test_smalltalk_has_no_follow_ups(self):
        a = self.ask("hello")
        self.assertEqual(a["follow_ups"], [])

    def test_clean_drops_unanswerable_dishonest_and_repeated(self):
        import followups
        items = [
            {"kind": "explore", "label": "Yesterday?", "prompt": "What did I spend yesterday?"},
            {"kind": "explore", "label": "Prisma?", "prompt": "How much at Prisma?"},
            {"kind": "explore", "label": "MRC-GRO-0032", "prompt": "Tell me about MRC-GRO-0032"},
            {"kind": "explore", "label": "Save 4 444 €?", "prompt": "How to save 4 444 €?"},
            {"kind": "explore", "label": "Same", "prompt": "Where did my money go?"},
            {"kind": "bogus", "label": "Save more?", "prompt": "How could I save more?"},
            {"kind": "explore", "label": "Save more?", "prompt": "How could I save more?"},
            {"label": "", "prompt": "x"},
        ]
        out = followups.clean(items, "Where did my money go?", "en", "2026-09-30", [1879.0])
        self.assertEqual(out, [{"kind": "explore", "label": "Save more?",
                                "prompt": "How could I save more?"}])

    def test_fallback_in_the_answer_language_when_provider_suggests_none(self):
        class NoFollowUps:  # like OpenRouter today: answers, but suggests nothing
            name = "nofu"
            def plan(self, text, tools, history=None, context=None):
                return {"requests": [{"tool": "spending_breakdown", "args": {}}], "lang": "fi"}
            def compose(self, text, results, history=None, context=None):
                return {"text": "Selvä.", "insights": [], "lang": "fi"}
        a = orchestrator.handle_command({"customer_id": CID, "text": "Mihin rahat menivät?",
                                         "lang": "fi"}, self.store, NoFollowUps())
        self.assertEqual(validate(ANSWER, a), [])
        self.assertTrue(a["follow_ups"])
        prompts = " ".join(f["prompt"] for f in a["follow_ups"])
        self.assertIn("Miten voisin säästää enemmän?", prompts)
        self.assertNotIn("What if", prompts)
        for f in a["follow_ups"]:  # every fallback suggestion is answerable
            import scope
            self.assertEqual(scope.limitation(f["prompt"], "fi", self.store.as_of(CID)), "")

    def test_provider_suggestions_first_then_filled_up(self):
        class OneVague:
            name = "onevague"
            def plan(self, text, tools, history=None, context=None):
                return {"requests": [{"tool": "savings_opportunities", "args": {}}], "lang": "fi"}
            def compose(self, text, results, history=None, context=None):
                return {"text": "Selvä.", "insights": [], "lang": "fi",
                        "follow_ups": [{"kind": "explore", "label": "Lisää?",
                                        "prompt": "Kerro lisää säästämisestä."}]}
        a = orchestrator.handle_command({"customer_id": CID, "text": "Miten säästän?",
                                         "lang": "fi"}, self.store, OneVague())
        self.assertEqual(a["follow_ups"][0]["prompt"], "Kerro lisää säästämisestä.")
        self.assertLessEqual(len(a["follow_ups"]), 3)

    def test_fallback_never_suggests_cutting_rent(self):
        import followups
        res = [{"tool": "spending_breakdown", "ok": True,
                "data": tools.run("spending_breakdown", self.store, CID, {"period": "all"})}]
        for lang in ("en", "fi", "sv"):
            for f in followups.fallback(res, lang):
                self.assertNotIn("Housing", f["prompt"])
                self.assertNotIn("Asuminen", f["prompt"])


class TestMccCodes(Base):
    """T014: MCC reference table, subcategories, and consistency with T011 life signals."""

    def test_reference_table_loaded(self):
        self.assertGreater(self.store.info()["mcc_codes"], 900)
        self.assertEqual(self.store.mcc_names(["4121"]), {"4121": "Taxicabs and Limousines"})

    def test_every_data_mcc_has_subcategory_names_and_reference(self):
        from cloud import glossary
        from cloud.taxonomy import MCC_SUBCATEGORY, SUBCATEGORIES
        data = {r["mcc"] for r in self.store.rows(
            "SELECT DISTINCT mcc FROM transactions WHERE mcc IS NOT NULL")}
        self.assertTrue(data)
        self.assertEqual(data - set(MCC_SUBCATEGORY), set())   # fixture codes mapped
        all_codes = set(MCC_SUBCATEGORY)
        self.assertEqual(all_codes - set(self.store.mcc_names(all_codes)), set())
        for key in SUBCATEGORIES:
            self.assertIn(key, glossary.SUBCATEGORY_NAMES)
        for key, (cat, _) in SUBCATEGORIES.items():
            self.assertIn(cat, glossary.CATEGORIES)

    def test_consistent_with_t011_life_signals(self):
        from calculation import signals
        from cloud.taxonomy import MCC_SUBCATEGORY, SUBCATEGORIES
        self.assertEqual(set(signals.MCC_NAMES), set(MCC_SUBCATEGORY))
        rule_codes = {c for _, _, codes, _ in signals.MCC_RULES for c in codes}
        self.assertEqual(rule_codes - set(self.store.mcc_names(rule_codes)), set())
        taxis = next(codes for k, _, codes, _ in signals.MCC_RULES if k == "taxis")
        self.assertEqual(set(taxis), set(SUBCATEGORIES["taxi"][1]))
        public = next(codes for k, _, codes, _ in signals.MCC_RULES if k == "public_transport")
        self.assertEqual(set(public), set(SUBCATEGORIES["public_transport"][1]))

    def test_subcategory_filter_and_grouping(self):
        taxi = tools.run("explore_transactions", self.store, CID,
                         {"period": "all", "subcategory": "taxi", "group_by": "none"})
        sql = self.store.one("SELECT COALESCE(-SUM(amount),0) AS v, COUNT(*) AS n FROM "
                             "transactions WHERE customer_id = ? AND mcc = '4121'", (CID,))
        self.assertAlmostEqual(taxi["total"], round(sql["v"], 2), 1)
        self.assertEqual(taxi["count"], sql["n"])
        self.assertIn("do not claim they include all", taxi["notes"])
        self.assertEqual(taxi["mcc_names"], {"4121": "Taxicabs and Limousines"})
        split = tools.run("explore_transactions", self.store, CID,
                          {"period": "all", "category": "Transportation",
                           "group_by": "subcategory", "limit": 36})
        whole = tools.run("explore_transactions", self.store, CID,
                          {"period": "all", "category": "Transportation", "group_by": "none"})
        self.assertAlmostEqual(sum(g["value"] for g in split["groups"]), whole["total"], 1)
        keys = {g["key"] for g in split["groups"]}
        self.assertTrue(keys <= {"taxi", "public_transport", "fuel", "parking", "unknown"})

    def test_subcategory_charts_localized(self):
        import present
        d = tools.run("explore_transactions", self.store, CID,
                      {"period": "all", "category": "Transportation", "group_by": "subcategory"})
        fi = json.dumps(present.build([{"tool": "explore_transactions", "ok": True,
                                        "data": d}], "fi"), ensure_ascii=False)
        self.assertIn("Joukkoliikenne", fi)
        self.assertIn("alaluokka", fi)

    def test_scope_taxi_answerable_coffee_not(self):
        import scope
        self.assertEqual(scope.limitation("Paljonko käytin takseihin viime kuussa?", "fi",
                                          "2026-09-30"), "")
        self.assertEqual(scope.limitation("How much do I spend on fuel?", "en",
                                          "2026-09-30"), "")
        self.assertTrue(scope.limitation("Paljonko käytän kahviin?", "fi", "2026-09-30"))

    def test_subcategory_answers_have_no_merchant_code_notice(self):
        class Taxi:
            name = "taxi"
            def plan(self, text, tools, history=None, context=None):
                return {"requests": [{"tool": "explore_transactions",
                                      "args": {"subcategory": "taxi", "group_by": "none"}}],
                        "lang": "fi"}
            def compose(self, text, results, history=None, context=None):
                return {"text": "Selvä.", "insights": [], "lang": "fi"}
        a = orchestrator.handle_command({"customer_id": CID, "text": "Taksit?", "lang": "fi"},
                                        self.store, Taxi())
        self.assertNotIn("notice", a)  # team decision: no merchant-code warning to users
        self.assertNotIn("kauppakoodi", a["text"])

    def test_seed_falls_back_to_fixture_mcc_file(self):
        import shutil
        tmp = tempfile.mkdtemp()
        try:
            for f in seed.ALL_CSVS:  # customer data without an mcc_codes.csv beside it
                shutil.copy(os.path.join(seed.FIXTURE_DIR, f), tmp)
            db = os.path.join(tmp, "x.sqlite")
            seed.build(tmp, db)
            self.assertGreater(Store(db).info()["mcc_codes"], 900)
        finally:
            shutil.rmtree(tmp)


class TestNoOtherCustomersData(Base):
    """T017: nothing about other customers — not even medians or averages — is computed,
    stored for the coach, or shown (banking secrecy)."""

    WORDS = ("peer", "median", "age_band", "average_of", "cohort")

    def test_no_peer_tool_or_table(self):
        names = [t["name"] for t in tools.describe_catalog()]
        self.assertNotIn("peer_comparison", names)
        self.assertFalse(hasattr(self.store, "peer"))
        tables = {r["name"] for r in self.store.rows(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertNotIn("peer_benchmark", tables)
        catalog = json.dumps(tools.describe_catalog()).lower()
        for w in ("peer", "median", "same age"):
            self.assertNotIn(w, catalog)

    def test_no_tool_result_mentions_other_customers(self):
        import present
        for name, args in (("spender_profile", {}), ("savings_opportunities", {}),
                           ("spending_breakdown", {}), ("safe_to_spend", {}),
                           ("simulate_change", {"category": "Restaurants", "change_pct": -20}),
                           ("explore_transactions", {"group_by": "category"})):
            d = json.dumps(tools.run(name, self.store, CID, args)).lower()
            for w in self.WORDS:
                self.assertNotIn(w, d, "%s result mentions %r" % (name, w))
            for lang in ("fi", "sv", "en"):
                shown = json.dumps(present.build([{"tool": name, "ok": True, "data":
                                                   tools.run(name, self.store, CID, args)}],
                                                  lang), ensure_ascii=False).lower()
                for w in ("ikätover", "jämnårig", "peer", "median", "mediaani"):
                    self.assertNotIn(w, shown)

    def test_savings_use_own_history(self):
        d = tools.run("savings_opportunities", self.store, CID, {})
        self.assertIn(d["basis"], ("above_usual", "gentle_trim"))
        for i in d["ideas"]:
            self.assertIn("usual_monthly", i)
            self.assertGreaterEqual(i["potential_monthly"], 0)

    def test_peer_questions_are_declined(self):
        import scope
        for q, lang in (("Miten tuloni vertautuvat muihin ikäisiini?", "fi"),
                        ("Miten kulutukseni vertautuu samanikäisiin?", "fi"),
                        ("Kulutanko enemmän kuin keskivertosuomalainen?", "fi"),
                        ("How do I compare to others my age?", "en"),
                        ("Do I spend more than the average customer?", "en"),
                        ("Hur står jag mig jämfört med andra i min ålder?", "sv")):
            self.assertEqual(scope.limitation(q, lang, "2026-09-30"),
                             scope.TEXT["others"][lang], q)
        self.assertEqual(scope.limitation("Mihin rahani menivät tässä kuussa?", "fi",
                                          "2026-09-30"), "")

    def test_no_peer_follow_ups(self):
        import followups
        res = [{"tool": "spender_profile", "ok": True,
                "data": tools.run("spender_profile", self.store, CID, {})}]
        for lang in ("fi", "sv", "en"):
            text = json.dumps(followups.fallback(res, lang), ensure_ascii=False).lower()
            for w in ("ikätover", "ikäisi", "jämnårig", "others my age"):
                self.assertNotIn(w, text)
        kept = followups.clean([{"kind": "explore", "label": "Vertaa muihin",
                                 "prompt": "Miten vertaudun muihin ikäisiini?"}],
                               "x", "fi", "2026-09-30", set())
        self.assertEqual(kept, [])


class TestGemma4Fixes(Base):
    """Model-agnostic fixes found when evaluating Gemma 4 (T016)."""

    def test_category_wins_over_contradicting_direction(self):
        d = tools.run("explore_transactions", self.store, CID,
                      {"period": "all", "category": "Invest Deposit", "direction": "spend",
                       "group_by": "none"})
        plain = tools.run("explore_transactions", self.store, CID,
                          {"period": "all", "category": "Invest Deposit", "group_by": "none"})
        self.assertEqual(d["direction"], "all")
        self.assertEqual(d["total"], plain["total"])

    def test_guess_lang(self):
        import scope
        self.assertEqual(scope.guess_lang("What did I spend yesterday?"), "en")
        self.assertEqual(scope.guess_lang("Paljonko olen sijoittanut viimeisen vuoden aikana?"), "fi")
        self.assertEqual(scope.guess_lang("Hur mycket kan jag spendera den här veckan?"), "sv")
        self.assertIsNone(scope.guess_lang("OK"))

    def test_localize_terms(self):
        import scope
        en = scope.localize_terms({"lang": "en", "insights": [], "text":
            "51 % went to pakolliset säännölliset menot and 22 % to arjen pikkukulut; "
            "your largest category was asuminen."})
        self.assertIn("regular essentials", en["text"])
        self.assertIn("everyday spending", en["text"])
        self.assertIn("housing", en["text"])
        self.assertNotIn("pakolliset", en["text"])
        sv = scope.localize_terms({"lang": "sv", "insights": [], "text":
            "Främst Pakolliset säännölliset menot och vardagsutgifter."})
        self.assertIn("Nödvändiga fasta utgifter", sv["text"])
        fi = scope.localize_terms({"lang": "fi", "insights": [], "text":
            "Arjen pikkukulut ja asuminen."})
        self.assertEqual(fi["text"], "Arjen pikkukulut ja asuminen.")  # already Finnish


class TestBigPurchases(Base):
    """T020: could the customer's own finances carry a home, a car or another big purchase?
    An illustration from their own data, never advice to buy and never a loan decision."""

    def run_tool(self, args, cid=CID):
        ok, why = approval.check({"tool": "purchase_affordability", "args": args}, cid)
        self.assertTrue(ok, why)
        return tools.run("purchase_affordability", self.store, cid, args)

    def test_annuity(self):
        self.assertAlmostEqual(tools._annuity(100000, 3.5, 25), 500.62, places=1)
        self.assertAlmostEqual(tools._annuity(12000, 0, 1), 1000.0)
        self.assertEqual(tools._annuity(0, 5, 10), 0.0)

    def test_approval(self):
        ok = lambda a: approval.check({"tool": "purchase_affordability", "args": a}, CID)[0]  # noqa: E731
        self.assertTrue(ok({"kind": "home", "price": 250000, "down_payment": 30000}))
        self.assertTrue(ok({}))
        self.assertFalse(ok({"kind": "boat", "price": 1000}))
        self.assertFalse(ok({"kind": "car", "price": -5}))
        self.assertFalse(ok({"kind": "car", "price": 20000, "loan_years": 99}))
        self.assertFalse(ok({"kind": "car", "price": 20000, "customer_id": "CUST00002"}))

    def test_max_price_is_consistent_with_the_verdict(self):
        for cid in [c["customer_id"] for c in self.store.list_customers(10)]:
            for kind in ("home", "car", "other"):
                d = self.run_tool({"kind": kind}, cid)
                self.assertEqual(d["status"], "range_only")
                self.assertGreaterEqual(d["max_price_estimate"], 0)
                if d["max_price_estimate"] >= 1:
                    at = self.run_tool({"kind": kind, "price": d["max_price_estimate"]}, cid)
                    self.assertNotIn("savings_short", at["reasons"], (cid, kind))
                    self.assertNotIn("monthly_negative", at["reasons"], (cid, kind))
                    self.assertNotIn("payment_share_high", at["reasons"], (cid, kind))
                    self.assertNotIn("stress_test_negative", at["reasons"], (cid, kind))
                far = self.run_tool({"kind": kind, "price": 2000000}, cid)
                self.assertIn(far["status"], ("save_first", "over_budget"), (cid, kind))

    def test_more_own_money_closes_the_gap(self):
        base = self.run_tool({"kind": "car", "price": 20000})
        more = self.run_tool({"kind": "car", "price": 20000, "other_savings": 10000})
        self.assertLessEqual(more["savings_gap"], base["savings_gap"])
        self.assertEqual(more["other_savings_stated"], 10000)
        down = self.run_tool({"kind": "car", "price": 20000, "down_payment": 15000})
        self.assertEqual(down["loan_amount"], 5000)
        self.assertLess(down["monthly_payment"], base["monthly_payment"])

    def test_home_replaces_rent_and_is_stress_tested(self):
        d = self.run_tool({"kind": "home", "price": 150000})
        self.assertEqual(d["housing_cost_freed"], d["monthly_housing_now"])
        self.assertIsNotNone(d["monthly_payment_stress"])
        self.assertGreater(d["monthly_payment_stress"], d["monthly_payment"])
        keep = self.run_tool({"kind": "home", "price": 150000, "replaces_housing": False})
        self.assertEqual(keep["housing_cost_freed"], 0)
        cash = self.run_tool({"kind": "other", "price": 3000})
        self.assertEqual((cash["loan_amount"], cash["monthly_payment"]), (0, 0))

    def test_result_is_an_illustration_not_advice(self):
        d = self.run_tool({"kind": "home", "price": 250000})
        self.assertIn("not advice to buy", d["notes"])
        text = json.dumps(d).lower()
        for w in ("peer", "median", "cohort", "you should buy"):
            self.assertNotIn(w, text)

    def test_questions_reach_the_tool_in_three_languages(self):
        for q, kind in (("Could I afford a €20,000 car?", "car"),
                        ("Voinko ostaa 200 000 €:n asunnon?", "home"),
                        ("Har jag råd med en bil för 15 000 €?", "car"),
                        ("How expensive a home could I afford?", "home")):
            a = self.ask(q)
            self.assertEqual(validate(ANSWER, a), [], q)
            self.assertEqual([t["tool"] for t in a["trace"]], ["purchase_affordability"], q)
            self.assertTrue(a["trace"][0]["approved"], q)
            self.assertTrue(a["visuals"], q)
            self.assertNotIn("notice", a, q)

    def test_answer_leaves_the_decision_to_the_customer(self):
        a = self.ask("Could I afford a €20,000 car?")
        self.assertIn("not a loan decision", a["text"])
        for w in ("you should buy", "don't buy", "you will get the loan"):
            self.assertNotIn(w, a["text"].lower())

    def test_follow_up_turn_keeps_the_purchase(self):
        history = [{"role": "user", "text": "Can I afford a 250 000 € apartment?"},
                   {"role": "coach", "text": "..."}]
        a = orchestrator.handle_command({"customer_id": CID, "history": history,
                                         "text": "What if I put 40 000 down?"},
                                        self.store, self.provider)
        self.assertEqual(a["trace"][0]["tool"], "purchase_affordability")
        plan = self.provider.plan("What if I put 40 000 down?", [], history)
        self.assertEqual(plan["requests"][0]["args"],
                         {"kind": "home", "price": 250000.0, "down_payment": 40000.0})

    def test_purchase_questions_are_in_scope(self):
        import scope
        lim = lambda q, lang: scope.limitation(q, lang, "2026-09-30")  # noqa: E731
        self.assertEqual(lim("Is a 2024 car for 18 000 € within my budget? Can I afford it?",
                             "en"), "")
        self.assertEqual(lim("Mahtuuko 200 000 €:n asunto budjettiini?", "fi"), "")
        self.assertIn("tallentaa", lim("Aseta minulle 300 euron budjetti ravintoloille.", "fi"))

    def test_charts_and_follow_ups_localized_and_answerable(self):
        import followups
        import present
        d = self.run_tool({"kind": "home", "price": 250000})
        res = [{"tool": "purchase_affordability", "ok": True, "data": d}]
        fi = json.dumps(present.build(res, "fi"), ensure_ascii=False)
        for w in ("Loan payment", "Down payment", "Still to save", "years at"):
            self.assertNotIn(w, fi)
        self.assertIn("Omarahoitus", fi)
        self.assertIn("3,5", fi)  # interest keeps its decimal
        from ai.grounding import known_numbers
        for lang in ("fi", "sv", "en"):
            fus = followups.clean(followups.fallback(res, lang), "x", lang, "2026-09-30",
                                  known_numbers(res, "", lang))
            self.assertGreaterEqual(len(fus), 2, lang)
            for f in fus:  # every suggestion leads to a purchase or savings answer
                if lang != "en" and f["prompt"] == followups.T["save"][lang][1]:
                    continue  # the offline stub reads English only (known limit)
                tool = self.provider.plan(f["prompt"], [])["requests"][0]["tool"]
                self.assertIn(tool, ("purchase_affordability", "savings_opportunities"),
                              f["prompt"])


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
            def plan(self, text, tools, history=None, context=None):
                return {"requests": [{"tool": "spending_breakdown",
                                      "args": {"customer_id": "CUST00002"}}]}
            def compose(self, text, results, history=None, context=None):
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

    def test_client_hangs_up_before_answer(self):
        """The proxy closed the socket during a slow answer: no 500 retry, no traceback."""
        class DeadSocket:
            writes = 0
            def write(self, b):
                DeadSocket.writes += 1
                raise BrokenPipeError(32, "Broken pipe")
            def flush(self):
                pass
        body = json.dumps({"customer_id": CID, "text": "Where did my money go?"}).encode()
        h = server.Handler.__new__(server.Handler)
        h.store, h.provider = self.store, self.provider
        h.command, h.path, h.request_version = "POST", "/api/command", "HTTP/1.1"
        h.requestline = "POST /api/command HTTP/1.1"
        h.headers = {"Content-Length": str(len(body))}
        h.rfile, h.wfile = io.BytesIO(body), DeadSocket()
        h.close_connection = False
        h.do_POST()  # must not raise
        self.assertTrue(h.close_connection)
        self.assertEqual(DeadSocket.writes, 1)  # gave up; did not try to send a 500 too


if __name__ == "__main__":
    unittest.main()
