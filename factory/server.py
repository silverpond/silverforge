"""
Simple HTTP server for the factory service.

Provides a /hello endpoint for health-check and connectivity verification.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class FactoryHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/hello":
            body = json.dumps({"message": "hello"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        # Suppress default access log to stderr
        pass


def run(host: str = "0.0.0.0", port: int = 8080) -> None:
    server = HTTPServer((host, port), FactoryHandler)
    print(f"factory server listening on {host}:{port}")
    server.serve_forever()
