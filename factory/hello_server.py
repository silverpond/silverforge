"""
Simple HTTP server with a hello endpoint.

Usage:
  from factory.hello_server import run_server
  run_server(port=8000)
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json


class HelloHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the hello endpoint."""

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/hello":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = json.dumps({"message": "hello"})
            self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = json.dumps({"error": "not found"})
            self.wfile.write(response.encode())

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the HTTP server on the specified host and port."""
    server = HTTPServer((host, port), HelloHandler)
    print(f"Hello server listening on http://{host}:{port}/hello")
    server.serve_forever()
