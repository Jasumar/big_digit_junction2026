"""Read-only access to the client data. The calculation tools are the only caller."""
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "data", "s_pankki.sqlite")


class Store:
    def __init__(self, path=None):
        self.path = path or os.environ.get("SPANKKI_DB") or DEFAULT_DB
        if not os.path.exists(self.path):
            raise FileNotFoundError(self.path)
        self.conn = sqlite3.connect("file:%s?mode=ro" % self.path, uri=True,
                                    check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def rows(self, sql, params=()):
        return [dict(r) for r in self.conn.execute(sql, params)]

    def one(self, sql, params=()):
        r = self.conn.execute(sql, params).fetchone()
        return dict(r) if r else None

    def customer(self, customer_id):
        return self.one("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))

    def list_customers(self, limit=20):
        return self.rows(
            "SELECT c.customer_id, c.age, c.postal_code FROM customers c"
            " WHERE EXISTS (SELECT 1 FROM transactions t WHERE t.customer_id = c.customer_id)"
            " ORDER BY c.customer_id LIMIT ?", (limit,))

    def as_of(self, customer_id):
        """'Today' for a customer: the date of their latest transaction."""
        r = self.one("SELECT MAX(tx_date) AS d FROM transactions WHERE customer_id = ?",
                     (customer_id,))
        return r["d"] if r else None

    def info(self):
        """Which data is loaded. `source` is 'fixture' (6-customer sample) or 'full'."""
        meta = {r["key"]: r["value"] for r in self.rows("SELECT key, value FROM meta")}
        customers = self.one("SELECT COUNT(*) AS n FROM customers")["n"]
        source = meta.get("source") or ("fixture" if customers <= 10 else "full")
        return {"path": self.path, "source": source, "customers": customers,
                "transactions": int(meta.get("rows", 0)),
                "data_from": meta.get("data_min"), "data_to": meta.get("data_max")}

    def peer(self, age_band, key):
        return self.one("SELECT avg_monthly, median_monthly, n FROM peer_benchmark"
                        " WHERE age_band = ? AND key = ?", (age_band, key))
