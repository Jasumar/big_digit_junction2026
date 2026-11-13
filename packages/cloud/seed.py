#!/usr/bin/env python3
"""Build the SQLite store from the S-pankki CSVs. Standard library only.

    python3 packages/cloud/seed.py                    # tiny committed fixture
    python3 packages/cloud/seed.py --csv-dir <dir>    # full dataset

<dir> must hold tx_junction_transactions.csv and tx_customers_junction.csv.
Output: packages/cloud/data/s_pankki.sqlite (gitignored), or --db.
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
"""


def parse_ts(s):
    """'03OCT24:09:04:04' -> '2024-10-03 09:04:04'."""
    hh, mm, ss = s[8:].split(":")
    return "%04d-%02d-%02d %s:%s:%s" % (
        2000 + int(s[5:7]), MONTHS[s[2:5].upper()], int(s[:2]), hh, mm, ss)


def weekday(date_iso):
    import datetime
    y, m, d = (int(x) for x in date_iso.split("-"))
    return datetime.date(y, m, d).weekday()


def build(csv_dir, db_path):
    tx_csv = os.path.join(csv_dir, "tx_junction_transactions.csv")
    cu_csv = os.path.join(csv_dir, "tx_customers_junction.csv")
    for p in (tx_csv, cu_csv):
        if not os.path.exists(p):
            sys.exit("missing %s" % p)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
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
    db.executemany("INSERT INTO meta VALUES (?,?)",
                   [("data_min", mn), ("data_max", mx), ("rows", str(n))])

    build_peer_benchmark(db, ages)
    db.commit()
    db.execute("VACUUM")
    db.close()
    print("seeded %d transactions, %d customers -> %s (%.1fs)"
          % (n, len(ages), db_path, time.time() - t0))


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
    ap.add_argument("--csv-dir", default=FIXTURE_DIR)
    ap.add_argument("--db", default=DEFAULT_DB)
    a = ap.parse_args()
    build(a.csv_dir, a.db)
