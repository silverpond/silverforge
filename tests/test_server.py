"""Tests for the HTTP server and endpoints."""

import pytest
from fastapi.testclient import TestClient
from factory.server import app


@pytest.fixture
def client():
    """Fixture providing a FastAPI TestClient."""
    return TestClient(app)


class TestHelloEndpoint:
    """Tests for the /hello endpoint."""

    def test_hello_returns_200(self, client):
        """Test that GET /hello returns a 200 status code."""
        response = client.get("/hello")
        assert response.status_code == 200

    def test_hello_returns_correct_message(self, client):
        """Test that GET /hello returns the correct message."""
        response = client.get("/hello")
        assert response.json() == {"message": "Hello from Silverpond Factory"}

    def test_hello_returns_json_content_type(self, client):
        """Test that GET /hello returns JSON content type."""
        response = client.get("/hello")
        assert response.headers["content-type"].startswith("application/json")

    def test_hello_with_query_params_ignored(self, client):
        """Test that GET /hello ignores query parameters."""
        response = client.get("/hello?foo=bar&baz=qux")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello from Silverpond Factory"}

    def test_hello_post_method_not_allowed(self, client):
        """Test that POST /hello is not allowed (method not allowed)."""
        response = client.post("/hello")
        assert response.status_code == 405  # Method Not Allowed

    def test_hello_put_method_not_allowed(self, client):
        """Test that PUT /hello is not allowed."""
        response = client.put("/hello")
        assert response.status_code == 405

    def test_hello_delete_method_not_allowed(self, client):
        """Test that DELETE /hello is not allowed."""
        response = client.delete("/hello")
        assert response.status_code == 405

    def test_hello_patch_method_not_allowed(self, client):
        """Test that PATCH /hello is not allowed."""
        response = client.patch("/hello")
        assert response.status_code == 405


class TestServerHealth:
    """Tests for server health and routing."""

    def test_nonexistent_endpoint_returns_404(self, client):
        """Test that requesting a nonexistent endpoint returns 404."""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_root_path_returns_404(self, client):
        """Test that GET / returns 404 (no root endpoint defined)."""
        response = client.get("/")
        assert response.status_code == 404


class TestServerStartup:
    """Tests for server initialization and app structure."""

    def test_app_is_fastapi_instance(self):
        """Test that the app is a FastAPI instance."""
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)

    def test_app_has_hello_route(self):
        """Test that the app has a /hello route defined."""
        routes = [route.path for route in app.routes]
        assert "/hello" in routes

    def test_hello_route_accepts_get(self):
        """Test that /hello route accepts GET method."""
        hello_route = next(route for route in app.routes if route.path == "/hello")
        assert "GET" in hello_route.methods


class TestConcurrentRequests:
    """Tests for handling concurrent requests."""

    def test_multiple_sequential_requests(self, client):
        """Test that the endpoint handles multiple sequential requests."""
        for _ in range(10):
            response = client.get("/hello")
            assert response.status_code == 200
            assert response.json() == {"message": "Hello from Silverpond Factory"}

    def test_requests_with_different_hosts(self, client):
        """Test that requests with different Host headers work."""
        response = client.get("/hello", headers={"Host": "example.com"})
        assert response.status_code == 200
        assert response.json() == {"message": "Hello from Silverpond Factory"}

    def test_requests_with_custom_user_agent(self, client):
        """Test that requests with custom User-Agent headers work."""
        response = client.get("/hello", headers={"User-Agent": "CustomAgent/1.0"})
        assert response.status_code == 200
        assert response.json() == {"message": "Hello from Silverpond Factory"}


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_hello_with_trailing_slash(self, client):
        """Test that GET /hello/ (with trailing slash) works."""
        response = client.get("/hello/")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello from Silverpond Factory"}

    def test_hello_case_sensitive(self, client):
        """Test that the endpoint path is case-sensitive."""
        response = client.get("/Hello")
        assert response.status_code == 404

    def test_hello_with_empty_body_post(self, client):
        """Test that POST /hello with empty body returns 405."""
        response = client.post("/hello", json={})
        assert response.status_code == 405

    def test_hello_response_is_json_serializable(self, client):
        """Test that the hello response is valid JSON."""
        response = client.get("/hello")
        # This will raise if JSON is invalid
        data = response.json()
        assert isinstance(data, dict)
        assert "message" in data
