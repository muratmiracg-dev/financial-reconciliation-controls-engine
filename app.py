"""Loopback-only workbench. No upload persistence or third-party services."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from reconcile.demo import demo
from reconcile.engine import reconcile

ROOT = Path(__file__).parent
LIMIT = 8 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, kind="application/json"):
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'",
        )
        self.end_headers()
        self.wfile.write(payload)

    def allowed(self):
        expected = f"127.0.0.1:{self.server.server_port}"
        return self.headers.get("Host") == expected and self.headers.get("Origin") in (
            None,
            "http://" + expected,
        )

    def do_GET(self):
        if not self.allowed():
            return self.reply(403, '{"error":"Use the printed loopback URL"}')
        routes = {
            "/": ("web/index.html", "text/html"),
            "/app.js": ("web/app.js", "text/javascript"),
            "/style.css": ("web/style.css", "text/css"),
        }
        if self.path in routes:
            path, kind = routes[self.path]
            return self.reply(200, (ROOT / path).read_text(), kind)
        if self.path == "/api/demo":
            return self.reply(200, json.dumps(demo()[0]))
        return self.reply(404, '{"error":"Not found"}')

    def do_POST(self):
        if not self.allowed():
            return self.reply(403, '{"error":"Origin rejected"}')
        if self.path != "/api/reconcile":
            return self.reply(404, '{"error":"Not found"}')
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= LIMIT:
                return self.reply(413, '{"error":"Maximum request size: 8 MB"}')
            if self.headers.get("Content-Type") != "application/json":
                return self.reply(415, '{"error":"JSON required"}')
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict) or any(
                not isinstance(payload.get(k), str)
                for k in ("bank", "invoices", "journal")
            ):
                raise ValueError("Three CSV text inputs required")
            result = reconcile(
                payload["bank"],
                payload["invoices"],
                payload["journal"],
                payload.get("days", 45),
                payload.get("tolerance", 1),
            )
            self.reply(200, json.dumps(result))
        except (ValueError, UnicodeError, OverflowError) as exc:
            self.reply(400, json.dumps({"error": str(exc)}))

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("Reconcile / Local workbench → http://127.0.0.1:8765", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
