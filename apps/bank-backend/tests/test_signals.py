"""Life-signal rules (T011): pure-rule tests, fixture tests, MCC table coverage.
Run: bash scripts/test.sh"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "apps", "bank-backend"), os.path.join(ROOT, "packages"),
          os.path.join(ROOT, "apps")):
    sys.path.insert(0, p)

from calculation import signals  # noqa: E402
from calculation.signals import MCC_NAMES, NEVER_INFER_MCC, signals_from_counts  # noqa: E402
from cloud import seed  # noqa: E402
from cloud.store import Store  # noqa: E402


def mcc(**codes):  # mcc(m5541=4) -> {"5541": {"n": 4, "eur": 4 * 10.0}}
    return {"mcc": {k[1:]: {"n": n, "eur": n * 10.0} for k, n in codes.items()}}


def keys(counts, days=90):
    return [s["key"] for s in signals_from_counts(counts, days)]


class TestRules(unittest.TestCase):
    def test_empty_gives_no_signals(self):
        self.assertEqual(signals_from_counts({}, 90), [])
        self.assertEqual(signals_from_counts({"mcc": {}, "months": {}}, 90), [])

    def test_each_mcc_rule_fires_at_its_threshold_not_below(self):
        for key, _label, codes, per_90 in signals.MCC_RULES:
            self.assertIn(key, keys(mcc(**{"m" + codes[0]: per_90})), key)
            self.assertNotIn(key, keys(mcc(**{"m" + codes[0]: per_90 - 1})), key)

    def test_codes_in_a_rule_add_up(self):
        got = signals_from_counts(mcc(m5541=2, m5542=1, m7523=1), 90)
        self.assertEqual([s["key"] for s in got], ["drives"])
        ev = got[0]["evidence"]
        self.assertEqual((ev["count"], ev["amount_eur"], ev["at_least"]), (4, 40.0, True))
        self.assertEqual(ev["mcc"], ["5541", "5542", "7523"])

    def test_threshold_scales_with_the_period(self):
        # drives: 4 per 90 days -> 4 * 30/90 = 1.3 -> 1 per 30 days; 4 * 365/90 = 16 per year
        self.assertNotIn("drives", keys(mcc(m5541=0), days=30))
        self.assertIn("drives", keys(mcc(m5541=1), days=30))
        self.assertNotIn("drives", keys(mcc(m5541=15), days=365))
        self.assertIn("drives", keys(mcc(m5541=16), days=365))

    def test_never_inferred_codes_make_no_signal(self):
        for code in NEVER_INFER_MCC:
            self.assertEqual(signals_from_counts({"mcc": {code: {"n": 500, "eur": 9999.0}}},
                                                 365), [], code)
        # health, bars and toy shops are in the data and in the table, but are never a rule
        in_rules = {c for r in signals.MCC_RULES for c in r[2]}
        self.assertEqual(in_rules & NEVER_INFER_MCC, set())
        for code in ("5912", "8011", "8021", "8099", "5813", "5945"):
            self.assertIn(code, NEVER_INFER_MCC)
            self.assertIn(code, MCC_NAMES)

    def test_invests_needs_most_months(self):
        self.assertIn("invests", keys({"months": {"Invest Deposit": 3}}))
        self.assertNotIn("invests", keys({"months": {"Invest Deposit": 1}}))
        self.assertNotIn("invests", keys({"months": {"Invest Deposit": 2}}))

    def test_regular_salary_needs_months_and_a_monthly_gap(self):
        ok = {"months": {"Salary": 3}, "salary_gap_days": 30.0}
        self.assertIn("regular_salary", keys(ok))
        self.assertNotIn("regular_salary", keys({**ok, "salary_gap_days": 14.0}))
        self.assertNotIn("regular_salary", keys({**ok, "salary_gap_days": None}))
        self.assertNotIn("regular_salary", keys({**ok, "months": {"Salary": 1}}))


class TestFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db = os.path.join(cls.tmp.name, "t.sqlite")
        seed.build(seed.FIXTURE_DIR, db)
        cls.store = Store(db)

    @classmethod
    def tearDownClass(cls):
        cls.store.conn.close()
        cls.tmp.cleanup()

    def got(self, cid, period="last_90_days"):
        return {s["key"]: s["evidence"] for s in signals.life_signals(self.store, cid, period)}

    def test_pinned_customers(self):
        self.assertEqual(sorted(self.got("CUST00005")),
                         ["drives", "events", "invests", "regular_salary", "taxis"])
        self.assertEqual(self.got("CUST00005")["taxis"]["count"], 5)
        self.assertEqual(sorted(self.got("CUST00006")), ["events", "regular_salary"])
        self.assertEqual(sorted(self.got("CUST00004")), ["invests", "regular_salary"])

    def test_evidence_has_what_the_ui_needs(self):
        ev = self.got("CUST00005")["drives"]
        self.assertEqual(ev["count"], 15)
        self.assertTrue(ev["at_least"])
        self.assertGreater(ev["amount_eur"], 0)  # spending is reported as positive EUR
        self.assertEqual(ev["period_days"], 90)

    def test_unknown_customer_or_period_is_an_error(self):
        with self.assertRaises(ValueError):
            signals.life_signals(self.store, "NOPE")
        with self.assertRaises(ValueError):
            signals.life_signals(self.store, "CUST00001", "last_week")

    def test_every_mcc_in_the_data_is_named(self):
        used = {r["mcc"] for r in self.store.rows(
            "SELECT DISTINCT mcc FROM transactions WHERE mcc IS NOT NULL")}
        self.assertEqual(sorted(used - set(MCC_NAMES)), [])

    def test_report_runs(self):
        import io
        out = io.StringIO()
        res = signals.report(self.store, out=out)
        self.assertEqual(res["unknown_mcc"], [])
        self.assertIn("signals per customer", out.getvalue())


class TestFullData(unittest.TestCase):
    """Runs only when the full database is loaded (SPANKKI_DB or the cloud default)."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.store = Store()
        except FileNotFoundError:
            raise unittest.SkipTest("no database loaded")
        if cls.store.info()["source"] != "full":
            raise unittest.SkipTest("full data not loaded")

    def test_no_unknown_mcc_and_no_flagged_signal(self):
        import io
        res = signals.report(self.store, out=io.StringIO())
        self.assertEqual(res["unknown_mcc"], [])
        self.assertEqual(res["flagged"], 0)
        self.assertLess(res["p95_ms"], 5.0)


if __name__ == "__main__":
    unittest.main()
