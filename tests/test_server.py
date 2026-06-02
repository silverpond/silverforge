"""Tests for the FastAPI server."""
import pytest
from fastapi.testclient import TestClient
from factory.server import app


@pytest.fixture
def client():
    """Fixture for FastAPI test client."""
    return TestClient(app)


def test_hello_endpoint_returns_json(client):
    """Test that the /hello endpoint returns a JSON response."""
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World!"}


def test_hello_endpoint_content_type(client):
    """Test that the /hello endpoint returns the correct content type."""
    response = client.get("/hello")
    assert response.headers["content-type"] == "application/json"


def test_hello_endpoint_method_validation(client):
    """Test that the /hello endpoint only accepts GET requests."""
    assert client.post("/hello").status_code == 405
    assert client.put("/hello").status_code == 405
    assert client.delete("/hello").status_code == 405


def test_hello_endpoint_404(client):
    """Test that non-existent endpoints return 404."""
    response = client.get("/nonexistent")
    assert response.status_code == 404
