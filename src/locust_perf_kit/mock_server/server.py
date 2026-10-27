"""Conduit mock server for deterministic, sub-second CI performance runs."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer


class MockConduitHandler(BaseHTTPRequestHandler):
    latency_ms: float = 0.0

    def log_message(self, format: str, *args) -> None:
        # Silent logger to prevent terminal noise during perf tests
        pass

    def _sleep_latency(self) -> None:
        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000.0)

    def _send_json(self, status_code: int, data: dict) -> None:
        self._sleep_latency()
        payload = json.dumps(data).encode("utf-8")
        try:
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def do_GET(self) -> None:
        if self.path == "/api/health" or self.path == "/health":
            self._send_json(200, {"status": "ok"})
        elif self.path == "/api/tags":
            self._send_json(200, {"tags": ["performance", "locust", "qa", "ci"]})
        elif self.path.startswith("/api/articles"):
            self._send_json(
                200,
                {
                    "articles": [
                        {
                            "slug": "perf-test-slug-1",
                            "title": "Performance Testing in CI",
                            "description": "Deterministic load testing with Locust",
                            "body": "Article body for test",
                            "tagList": ["performance", "locust"],
                            "createdAt": "2026-10-27T12:00:00.000Z",
                            "favorited": False,
                            "favoritesCount": 10,
                            "author": {"username": "qa_tester", "bio": None, "image": None},
                        }
                    ],
                    "articlesCount": 1,
                },
            )
        else:
            self._send_json(404, {"errors": {"body": ["Not found"]}})

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}

        if self.path == "/api/users/login":
            self._send_json(
                200,
                {
                    "user": {
                        "email": data.get("user", {}).get("email", "tester@example.com"),
                        "token": "mock-jwt-token-xyz-123",
                        "username": "qa_tester",
                        "bio": "Mock QA bio",
                        "image": None,
                    }
                },
            )
        elif self.path == "/api/articles":
            article = data.get("article", {})
            title = article.get("title", "New Article")
            slug = title.lower().replace(" ", "-")
            self._send_json(
                201,
                {
                    "article": {
                        "slug": slug,
                        "title": title,
                        "description": article.get("description", "Desc"),
                        "body": article.get("body", "Body text"),
                        "tagList": article.get("tagList", ["locust"]),
                        "createdAt": "2026-10-27T12:00:00.000Z",
                        "favorited": False,
                        "favoritesCount": 0,
                        "author": {"username": "qa_tester", "bio": None, "image": None},
                    }
                },
            )
        elif "/favorite" in self.path:
            self._send_json(
                200,
                {
                    "article": {
                        "slug": "perf-test-slug-1",
                        "title": "Performance Testing in CI",
                        "favorited": True,
                        "favoritesCount": 11,
                    }
                },
            )
        elif "/comments" in self.path:
            self._send_json(
                201,
                {
                    "comment": {
                        "id": 1,
                        "createdAt": "2026-10-27T12:00:00.000Z",
                        "body": "Great article on performance!",
                        "author": {"username": "qa_tester"},
                    }
                },
            )
        else:
            self._send_json(404, {"errors": {"body": ["Route not found"]}})


class MockConduitServer:
    def __init__(self, port: int = 8089, latency_ms: float = 0.0):
        self.port = port
        self.latency_ms = latency_ms
        self.httpd: HTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        handler_cls = MockConduitHandler
        handler_cls.latency_ms = self.latency_ms
        self.httpd = HTTPServer(("127.0.0.1", self.port), handler_cls)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def set_latency(self, latency_ms: float) -> None:
        MockConduitHandler.latency_ms = latency_ms

    def stop(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
