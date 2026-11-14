"""Tests for the numeric grounding check and its use by the hosted provider."""
import io
import json
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for path in (os.path.join(ROOT, "apps", "bank-backend"), os.path.join(ROOT, "packages"),
             os.path.join(ROOT, "apps")):
    if path not in sys.path:
        sys.path.insert(0, path)

from ai.grounding import check  # noqa: E402
from ai.llm_provider import Provider  # noqa: E402
from ai.prompt import build_system_prompt  # noqa: E402

RESULTS = [{"tool": "spending_breakdown", "ok": True, "args": {"period": "last_month"},
            "data": {"total_spend": 1234.5, "share_pct": 12.5, "change_pct": -8.2,
                     "days": 30, "from": "2026-10-01",
                     "buckets": [{"bucket": "everyday", "amount": 310.04}]}}]


class TestGrounding(unittest.TestCase):
    def test_correct_amounts_pass(self):
        for text in ("You spent €1,234.50 last month.", "You spent €1,234 or 1,235 EUR.",
                     "Everyday spending was €310.04.", "Total 1234.5 euros."):
            with self.subTest(text=text):
                self.assertEqual(check(text, RESULTS), (True, []))

    def test_invented_amount_is_caught(self):
        ok, unknown = check("You spent €2,500 last month, of which €310.04 was everyday.",
                            RESULTS)
        self.assertFalse(ok)
        self.assertEqual(unknown, ["2,500"])

    def test_finnish_formatting(self):
        self.assertEqual(check("Käytit yhteensä 1 234,50 € ja arjen pikkukuluihin 310,04\u00a0€.",
                               RESULTS), (True, []))
        self.assertEqual(check("Käytit 1\u202f234,50 € ja osuus oli 12,5 %.", RESULTS)[0], True)
        ok, unknown = check("Käytit 1 999,90 €.", RESULTS)
        self.assertFalse(ok)
        self.assertEqual(unknown, ["1 999,90"])

    def test_percentages(self):
        self.assertTrue(check("That is 12.5% of spending, down 8% on last time.", RESULTS)[0])
        self.assertTrue(check("Osuus oli 13 %.", RESULTS)[0])
        ok, unknown = check("That is 40% of spending.", RESULTS)
        self.assertFalse(ok)
        self.assertEqual(unknown, ["40"])

    def test_rounding(self):
        self.assertTrue(check("About €1,235.", [{"tool": "t", "ok": True,
                                                  "data": {"v": 1234.6}}])[0])
        self.assertTrue(check("€310.04", RESULTS)[0])
        self.assertFalse(check("€310.09", RESULTS)[0])
        self.assertFalse(check("€1,236", RESULTS)[0])

    def test_small_integers_years_and_dates_are_ignored(self):
        text = ("In 2 of the last 3 months, since 2026-10-01 and 14.11.2026, "
                "at 14:30, in 2025 you spent 12 times.")
        self.assertEqual(check(text, []), (True, []))
        self.assertFalse(check("You spent €5.", [])[0])

    def test_args_and_days_count_as_results(self):
        self.assertTrue(check("Over the last 30 days.", RESULTS)[0])

    def test_no_numbers_or_no_results(self):
        self.assertEqual(check("I couldn't run that tool.", []), (True, []))
        self.assertFalse(check("You spent 500 euros.", [])[0])

    def test_ambiguous_separator_reads_either_way(self):
        data = [{"tool": "t", "ok": True, "data": {"a": 1.234}}]
        self.assertTrue(check("1,234", data)[0])
        self.assertTrue(check("1,234", [{"tool": "t", "ok": True, "data": {"a": 1234}}])[0])


class TestPrompt(unittest.TestCase):
    def test_prompt_content(self):
        prompt = build_system_prompt()
        for part in ("pakolliset säännölliset menot", "pakolliset yllättävät menot",
                     "arjen pikkukulut", "investment advice", "tool result"):
            self.assertIn(part, prompt)
        self.assertIn("Swedish", build_system_prompt("sv"))
        self.assertNotIn("{", prompt)


ENV = {"LLM_BASE_URL": "https://example.test/v1", "LLM_MODEL": "m", "LLM_API_KEY": "k"}


def reply(answer):
    body = {"choices": [{"message": {"content": json.dumps(answer)}, "finish_reason": "stop"}]}
    return io.BytesIO(json.dumps(body).encode())


def answer(text):
    return {"text": text, "insights": []}


class TestProviderGrounding(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ, ENV)
        env.start()
        self.addCleanup(env.stop)
        self.provider = Provider()
        self.results = [{"tool": "spending_breakdown", "ok": True, "data": {
            "from": "2026-09-01", "to": "2026-09-30", "total_spend": 1234.0, "change_pct": None,
            "buckets": [{"bucket": b, "amount": 100.0} for b in
                        ("essentials", "necessities", "everyday")],
            "categories": [], "top_merchants": []}}]

    @mock.patch("urllib.request.urlopen")
    def test_grounded_answer_makes_one_call(self, urlopen):
        urlopen.return_value = reply(answer("You spent €1,234."))
        self.assertEqual(self.provider.compose("How much?", self.results, [])["text"],
                         "You spent €1,234.")
        self.assertEqual(urlopen.call_count, 1)

    @mock.patch("urllib.request.urlopen")
    def test_retry_names_unknown_numbers(self, urlopen):
        urlopen.side_effect = [reply(answer("You spent €9,999.")),
                               reply(answer("You spent €1,234."))]
        out = self.provider.compose("How much?", self.results, [])
        self.assertEqual(out["text"], "You spent €1,234.")
        self.assertEqual(urlopen.call_count, 2)
        sent = json.loads(urlopen.call_args.args[0].data)["messages"]
        self.assertIn("9,999", sent[-1]["content"])

    @mock.patch("urllib.request.urlopen")
    def test_second_failure_returns_templated_answer(self, urlopen):
        urlopen.side_effect = [reply(answer("You spent €9,999.")),
                               reply(answer("You spent €8,888."))]
        with self.assertLogs("ai.llm_provider", "WARNING"):
            out = self.provider.compose("How much?", self.results, [])
        self.assertEqual(urlopen.call_count, 2)
        self.assertIn("€1,234", out["text"])
        self.assertNotIn("9,999", out["text"])
        self.assertNotIn("8,888", out["text"])

    @mock.patch("urllib.request.urlopen")
    def test_step_final_is_grounded_too(self, urlopen):
        urlopen.side_effect = [reply(answer("You spent €9,999.")),
                               reply(answer("You spent €1,234."))]
        messages = [{"role": "user", "text": "How much?"},
                    {"role": "requests", "requests": [{"tool": "spending_breakdown",
                                                       "args": {}}]},
                    {"role": "results", "results": self.results}]
        out = self.provider.step(messages, [{"name": "spending_breakdown",
                                             "description": "d", "parameters": {}}])
        self.assertEqual(out["final"]["text"], "You spent €1,234.")


if __name__ == "__main__":
    unittest.main()
