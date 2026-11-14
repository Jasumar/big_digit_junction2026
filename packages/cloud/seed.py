#!/usr/bin/env python3
"""Build the SQLite store from the S-pankki CSVs. Standard library only.

    python3 packages/cloud/seed.py                    # small committed fixture
    python3 packages/cloud/seed.py --full             # all data from fetch_data.py
    python3 packages/cloud/seed.py --csv-dir <dir>    # the four CSVs from anywhere

The folder must hold the four hackathon CSVs (see fetch_data.py). Output:
packages/cloud/data/s_pankki.sqlite (gitignored), or --db. The database is built in a
temporary file and swapped in at the end, so a failed run keeps the old one.
"""
import argparse
import csv
import os
import sqlite3
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from taxonomy import (  # noqa: E402
    AGE_BANDS, BUCKET_LABELS, CATEGORY_BUCKET, SPEND_CATEGORIES, age_band,
)

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "data", "s_pankki.sqlite")
FIXTURE_DIR = os.path.join(HERE, "fixture")
RAW_DIR = os.path.join(HERE, "data", "raw")
TX_CSV = "tx_junction_transactions.csv"
CU_CSV = "tx_customers_junction.csv"
MTG_EVENTS_CSV = "mtg_negotiation_history.csv"
MTG_LINK_CSV = "mtg_tx_customer_link_and_final_mtg_infio.csv"
ALL_CSVS = (TX_CSV, CU_CSV, MTG_EVENTS_CSV, MTG_LINK_CSV)
MONTHS = {m: i + 1 for i, m in enumerate(
    "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}

SCHEMA = """
CREATE TABLE customers (
  customer_id TEXT PRIMARY KEY, postal_code TEXT NOT NULL, age INTEGER NOT NULL,
  age_band TEXT NOT NULL);
CREATE TABLE transactions (
  id INTEGER PRIMARY KEY, customer_id TEXT NOT NULL, tx_date TEXT NOT NULL,
  tx_ts TEXT NOT NULL, hour INTEGER NOT NULL, weekday INTEGER NOT NULL,
  category TEXT NOT NULL, amount REAL NOT NULL, balance_after REAL NOT NULL,
  tx_type TEXT NOT NULL, merchant_id TEXT, mcc TEXT);
CREATE TABLE peer_benchmark (
  age_band TEXT NOT NULL, key TEXT NOT NULL, avg_monthly REAL NOT NULL,
  median_monthly REAL NOT NULL, n INTEGER NOT NULL, PRIMARY KEY (age_band, key));
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE mortgage_applications (
  mortgage_customer_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL,
  final_decision TEXT, rejection_reason TEXT, final_property_price_eur REAL,
  final_requested_loan_eur REAL, final_equity_amount_eur REAL,
  final_collateral_value_eur REAL, required_monthly_income_eur REAL,
  final_loan_to_value REAL);
CREATE TABLE mortgage_events (
  id INTEGER PRIMARY KEY, mortgage_customer_id TEXT NOT NULL, ts TEXT NOT NULL,
  event_type TEXT NOT NULL, property_id TEXT, property_type TEXT,
  property_price_estimate REAL, loan_amount REAL, equity_amount REAL,
  collateral_type TEXT, collateral_value REAL, collateral_status TEXT, decision TEXT,
  rejection_reason TEXT, expense_type TEXT, expense_amount REAL, note TEXT);
"""
MTG_EVENT_TEXT = ("property_id", "property_type", "collateral_type", "collateral_status",
                  "decision", "rejection_reason", "expense_type", "note")
MTG_EVENT_REAL = ("property_price_estimate", "loan_amount", "equity_amount",
                  "collateral_value", "expense_amount")
MTG_APP_REAL = ("final_property_price_eur", "final_requested_loan_eur",
                "final_equity_amount_eur", "final_collateral_value_eur",
                "required_monthly_income_eur")


def parse_ts(s):
    """'03OCT24:09:04:04' -> '2024-10-03 09:04:04'."""
    hh, mm, ss = s[8:].split(":")
    return "%04d-%02d-%02d %s:%s:%s" % (
        2000 + int(s[5:7]), MONTHS[s[2:5].upper()], int(s[:2]), hh, mm, ss)


def weekday(date_iso):
    import datetime
    y, m, d = (int(x) for x in date_iso.split("-"))
    return datetime.date(y, m, d).weekday()


def _num(v):
    return float(v) if v not in ("", ".", None) else None


def _txt(v):
    return v if v not in ("", ".", None) else None


def build(csv_dir, db_path):
    missing = [f for f in ALL_CSVS if not os.path.exists(os.path.join(csv_dir, f))]
    if missing:
        sys.exit("missing in %s: %s (run packages/cloud/fetch_data.py)"
                 % (csv_dir, ", ".join(missing)))
    tx_csv = os.path.join(csv_dir, TX_CSV)
    cu_csv = os.path.join(csv_dir, CU_CSV)
    with open(tx_csv, "rb") as f:
        if f.read(40).startswith(b"version https://git-lfs"):
            sys.exit("%s is a Git LFS pointer, not data (run fetch_data.py)" % tx_csv)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    final_path, db_path = db_path, db_path + ".building"
    if os.path.exists(db_path):
        os.remove(db_path)
    t0 = time.time()
    db = sqlite3.connect(db_path)
    db.executescript(SCHEMA)

    ages = {}
    with open(cu_csv, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            age = int(r["customer_age"])
            ages[r["customer_id"]] = age
            db.execute("INSERT INTO customers VALUES (?,?,?,?)",
                       (r["customer_id"], r["customer_postal_code"], age, age_band(age)))

    n = 0
    wd_cache = {}
    with open(tx_csv, encoding="utf-8-sig", newline="") as f:
        batch = []
        for r in csv.DictReader(f):
            ts = parse_ts(r["tx_timestamp"])
            d = r["tx_date"]
            if d not in wd_cache:
                wd_cache[d] = weekday(d)
            batch.append((
                r["customer_id"], d, ts, int(ts[11:13]), wd_cache[d], r["category"],
                float(r["tx_amount_eur"]), float(r["balance_after_eur"]),
                r["transaction_type"], r["merchant_id"] or None,
                r["mcc_code"] if r["mcc_code"] not in ("", ".") else None))
            if len(batch) >= 50000:
                db.executemany("INSERT INTO transactions (customer_id, tx_date, tx_ts, hour,"
                               " weekday, category, amount, balance_after, tx_type,"
                               " merchant_id, mcc) VALUES (?,?,?,?,?,?,?,?,?,?,?)", batch)
                n += len(batch)
                batch = []
        if batch:
            db.executemany("INSERT INTO transactions (customer_id, tx_date, tx_ts, hour,"
                           " weekday, category, amount, balance_after, tx_type,"
                           " merchant_id, mcc) VALUES (?,?,?,?,?,?,?,?,?,?,?)", batch)
            n += len(batch)
    db.execute("CREATE INDEX idx_tx_customer_date ON transactions (customer_id, tx_date)")

    mn, mx = db.execute("SELECT MIN(tx_date), MAX(tx_date) FROM transactions").fetchone()
    n_apps, n_events = load_mortgages(db, csv_dir)
    source = "fixture" if os.path.realpath(csv_dir) == os.path.realpath(FIXTURE_DIR) else "full"
    db.executemany("INSERT INTO meta VALUES (?,?)",
                   [("data_min", mn), ("data_max", mx), ("rows", str(n)), ("source", source),
                    ("mortgage_applications", str(n_apps)),
                    ("mortgage_events", str(n_events))])

    build_peer_benchmark(db, ages)
    db.commit()
    db.execute("VACUUM")
    db.close()
    os.replace(db_path, final_path)
    print("seeded %d transactions, %d customers, %d mortgage applications (%d events)"
          " -> %s (%.1fs)" % (n, len(ages), n_apps, n_events, final_path, time.time() - t0))


def load_mortgages(db, csv_dir):
    with open(os.path.join(csv_dir, MTG_LINK_CSV), encoding="utf-8-sig", newline="") as f:
        apps = [(r["mortgage_customer_id"], r["customer_id"], _txt(r["final_decision"]),
                 _txt(r["rejection_reason"]), *[_num(r[k]) for k in MTG_APP_REAL],
                 _num(r["lfinal_loan_to_value"]))  # upstream typo: "lfinal"
                for r in csv.DictReader(f)]
    db.executemany("INSERT INTO mortgage_applications VALUES (?,?,?,?,?,?,?,?,?,?)", apps)
    with open(os.path.join(csv_dir, MTG_EVENTS_CSV), encoding="utf-8-sig", newline="") as f:
        cols = ("mortgage_customer_id", "ts", "event_type") + MTG_EVENT_TEXT + MTG_EVENT_REAL
        data = []
        for r in csv.DictReader(f):
            data.append((r["mortgage_customer_id"], parse_ts(r["timestamp"]), r["event_type"],
                         *[_txt(r[k]) for k in MTG_EVENT_TEXT],
                         *[_num(r[k]) for k in MTG_EVENT_REAL]))
    db.executemany("INSERT INTO mortgage_events (%s) VALUES (%s)"
                   % (",".join(cols), ",".join("?" * len(cols))), data)
    db.execute("CREATE INDEX idx_mtg_app_customer ON mortgage_applications (customer_id)")
    db.execute("CREATE INDEX idx_mtg_events_mc ON mortgage_events (mortgage_customer_id, ts)")
    return len(apps), len(data)


def build_peer_benchmark(db, ages):
    """Per age band: typical monthly spend per category, per bucket and in total."""
    months = {c: m for c, m in db.execute(
        "SELECT customer_id, COUNT(DISTINCT substr(tx_date,1,7)) FROM transactions"
        " GROUP BY customer_id")}
    spend = {}
    marks = ",".join("?" * len(SPEND_CATEGORIES))
    for cid, cat, total in db.execute(
            "SELECT customer_id, category, -SUM(amount) FROM transactions"
            " WHERE category IN (%s) GROUP BY customer_id, category" % marks,
            SPEND_CATEGORIES):
        spend.setdefault(cid, {})[cat] = total
    samples = {}  # (band, key) -> [monthly values]
    for cid, cats in spend.items():
        band = age_band(ages[cid])
        m = max(months.get(cid, 1), 1)
        keys = {c: cats.get(c, 0.0) / m for c in SPEND_CATEGORIES}
        for b in BUCKET_LABELS:
            keys["bucket:" + b] = sum(v for c, v in keys.items()
                                      if CATEGORY_BUCKET.get(c) == b)
        keys["total"] = sum(cats.values()) / m
        for k, v in keys.items():
            samples.setdefault((band, k), []).append(v)
    rows = [(band, k, statistics.fmean(v), statistics.median(v), len(v))
            for (band, k), v in samples.items()]
    db.executemany("INSERT INTO peer_benchmark VALUES (?,?,?,?,?)", rows)
    assert all(b in AGE_BANDS for b, *_ in rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--full", action="store_true",
                   help="use %s (filled by fetch_data.py)" % RAW_DIR)
    g.add_argument("--csv-dir", default=FIXTURE_DIR)
    ap.add_argument("--db", default=DEFAULT_DB)
    a = ap.parse_args()
    build(RAW_DIR if a.full else a.csv_dir, a.db)
