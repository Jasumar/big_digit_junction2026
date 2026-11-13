#!/usr/bin/env python3
"""S-pankki backend: HTTP API plus static hosting for the demo UI. Standard library only.

    python3 apps/bank-backend/server.py            # http://localhost:8000

Env: PORT (8000), AI_PROVIDER (stub), SPANKKI_DB (packages/cloud/data/s_pankki.sqlite),
REQUIRE_FULL_DATA (set to 1 to refuse to start on the sample).
If the database is missing it is built from the small committed fixture, with a loud
warning; /api/health and the UI also say which data is loaded.
"""
import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (HERE, os.path.join(ROOT, "packages"), os.path.join(ROOT, "apps")):
    if p not in sys.path:
        sys.path.insert(0, p)

from ai.provider import get_provider  # noqa: E402
from cloud import seed  # noqa: E402
from cloud.store import DEFAULT_DB, Store  # noqa: E402
import orchestrator  # noqa: E402

STATIC = {"": os.path.join(ROOT, "apps", "frontend"),
          "client": os.path.join(ROOT, "apps", "client")}
MAX_BODY = 20000


class SampleDataError(RuntimeError):
    pass


def open_store(require_full=None):
    if require_full is None:
        require_full = os.environ.get("REQUIRE_FULL_DATA", "") not in ("", "0")
    path = os.environ.get("SPANKKI_DB") or DEFAULT_DB
    if not os.path.exists(path):
        if require_full:
            raise SampleDataError("no database at %s and REQUIRE_FULL_DATA is set; run "
                                  "packages/cloud/fetch_data.py, then seed.py --full" % path)
        print("no database at %s; building the small fixture" % path, flush=True)
        seed.build(seed.FIXTURE_DIR, path)
    store = Store(path)
    info = store.info()
    if info["source"] == "fixture":
        if require_full:
            raise SampleDataError("%s holds the %d-customer sample, not the full data; "
                                  "REQUIRE_FULL_DATA is set" % (path, info["customers"]))
        bar = "!" * 72
        print("%s\n  WARNING: running on the SAMPLE data (%d customers), not the full "
              "dataset.\n  For the demo: python3 packages/cloud/fetch_data.py && python3 packages/cloud/seed.py --full\n%s"
              % (bar, info["customers"], bar), file=sys.stderr, flush=True)
    return store


class Handler(BaseHTTPRequestHandler):
    store = None
    provider = None

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.command, self.path))

    def _json(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        try:
            if url.path == "/api/health":
                return self._json(200, {"ok": True, "provider": self.provider.name,
                                        "data": self.store.info()})
            if url.path == "/api/customers":
                limit = min(int(q.get("limit", ["12"])[0]), 100)
                return self._json(200, {"customers": self.store.list_customers(limit)})
            if url.path == "/api/overview":
                return self._json(200, orchestrator.overview(
                    q.get("customer_id", [""])[0], self.store))
        except orchestrator.BadCommand as e:
            return self._json(400, {"error": str(e)})
        except Exception as e:
            return self._json(500, {"error": "server error: %s" % e})
        if url.path.startswith("/api/"):
            return self._json(404, {"error": "not found"})
        self._static(url.path)

    def do_POST(self):
        if urlparse(self.path).path != "/api/command":
            return self._json(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n > MAX_BODY:
                return self._json(413, {"error": "request too large"})
            command = json.loads(self.rfile.read(n) or b"{}")
            return self._json(200, orchestrator.handle_command(
                command, self.store, self.provider))
        except (orchestrator.BadCommand, ValueError) as e:
            return self._json(400, {"error": str(e)})
        except Exception as e:
            return self._json(500, {"error": "server error: %s" % e})

    def _static(self, path):
        parts = [p for p in path.split("/") if p]
        base_key = ""
        if parts and parts[0] == "client":
            base_key, parts = "client", parts[1:]
        rel = "/".join(parts) or "index.html"
        base = os.path.realpath(STATIC[base_key])
        full = os.path.realpath(os.path.join(base, rel))
        if not full.startswith(base + os.sep) or not os.path.isfile(full) \
                or full.endswith(".md"):
            return self._json(404, {"error": "not found"})
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(full)[0] or "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)


def main():
    try:
        Handler.store = open_store()
    except SampleDataError as e:
        sys.exit("refusing to start: %s" % e)
    Handler.provider = get_provider()
    port = int(os.environ.get("PORT", "8000"))
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    info = Handler.store.info()
    print("S-pankki coach on http://localhost:%d  (AI provider: %s, data: %s, %d customers,"
          " %s)" % (port, Handler.provider.name, info["source"], info["customers"], info["path"]), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
