#!/usr/bin/env python3
"""Download the four S-pankki CSVs from the official hackathon repo. Stdlib only.

    python3 packages/cloud/fetch_data.py            # -> packages/cloud/data/raw/ (gitignored)
    python3 packages/cloud/fetch_data.py --force    # download again even if present

Then build the database:  python3 packages/cloud/seed.py --full

The transactions file is ~363 MB and stored with Git LFS upstream; the "raw" URL
follows GitHub's redirect to the real file. If Python has no CA certificates (common
with python.org installs on macOS) it falls back to `curl`; TLS is always verified.
A file that turns out to be an LFS pointer ("version https://git-lfs...") is rejected.
"""
import argparse
import os
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(HERE, "data", "raw")
SOURCE = "https://github.com/hackjunction/Junction-2026-S-pankki/raw/main/"

# file -> expected header (after the UTF-8 BOM)
FILES = {
    "tx_customers_junction.csv": "customer_id,customer_postal_code,customer_age",
    "tx_junction_transactions.csv": "customer_id,bank_account_id,tx_date,tx_timestamp",
    "mtg_negotiation_history.csv": "mortgage_customer_id,timestamp,event_type",
    "mtg_tx_customer_link_and_final_mtg_infio.csv": "mortgage_customer_id,customer_id,",
}


def check(path, header):
    with open(path, "rb") as f:
        head = f.read(300).decode("utf-8-sig", errors="replace")
    if head.startswith("version https://git-lfs"):
        return "got a Git LFS pointer, not the data"
    if not head.startswith(header):
        return "unexpected header: %r" % head[:80]
    return None


def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "fetch-data-script"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as out:
            shutil.copyfileobj(r, out, 1 << 20)
        return
    except urllib.error.URLError as e:
        if not isinstance(e.reason, ssl.SSLCertVerificationError) or not shutil.which("curl"):
            raise
    # Python lacks CA certificates here; curl uses the system store (still verified).
    subprocess.run(["curl", "-fsSL", "--retry", "2", "-o", path, url], check=True)


def fetch(name, header, force):
    dest = os.path.join(RAW_DIR, name)
    if os.path.exists(dest) and not force and check(dest, header) is None:
        print("ok    %-46s %8.1f MB (already here)" % (name, os.path.getsize(dest) / 1e6))
        return True
    tmp = dest + ".part"
    try:
        download(SOURCE + name, tmp)
    except Exception as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        print("FAIL  %-46s %s" % (name, e))
        return False
    problem = check(tmp, header)
    if problem:
        os.remove(tmp)
        print("FAIL  %-46s %s" % (name, problem))
        return False
    os.replace(tmp, dest)
    print("ok    %-46s %8.1f MB" % (name, os.path.getsize(dest) / 1e6))
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    os.makedirs(RAW_DIR, exist_ok=True)
    ok = all([fetch(n, h, a.force) for n, h in FILES.items()])
    print("all four files in %s" % RAW_DIR if ok else "some downloads failed")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
