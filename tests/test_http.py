import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from app import Handler
from reconcile.demo import demo


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        c.request(method, path, body, headers or {})
        r = c.getresponse()
        status, data = r.status, r.read()
        c.close()
        return status, data

    def test_page(self):
        self.assertEqual(self.request("GET", "/")[0], 200)

    def test_origin_blocked(self):
        self.assertEqual(
            self.request(
                "POST", "/api/reconcile", "{}", {"Origin": "https://example.com"}
            )[0],
            403,
        )

    def test_host_blocked(self):
        self.assertEqual(
            self.request("GET", "/", headers={"Host": "example.com"})[0], 403
        )

    def test_path_traversal(self):
        self.assertEqual(self.request("GET", "/../app.py")[0], 404)

    def test_upload(self):
        status, body = self.request(
            "POST",
            "/api/reconcile",
            json.dumps(demo()[0]),
            {"Content-Type": "application/json"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["summary"]["matched"], 43)

    def test_malformed_json(self):
        self.assertEqual(
            self.request(
                "POST", "/api/reconcile", "{", {"Content-Type": "application/json"}
            )[0],
            400,
        )

    def test_missing_inputs(self):
        self.assertEqual(
            self.request(
                "POST", "/api/reconcile", "{}", {"Content-Type": "application/json"}
            )[0],
            400,
        )

    def test_non_json(self):
        self.assertEqual(
            self.request(
                "POST", "/api/reconcile", "hi", {"Content-Type": "text/plain"}
            )[0],
            415,
        )
