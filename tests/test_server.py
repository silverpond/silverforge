"""Tests for the HTTP API server."""
import pytest
from fastapi.testclient import TestClient
from factory.server import app


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)


def test_hello_endpoint(client):
    """Test the /hello endpoint returns correct JSON."""
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, Silverpond Factory!"}


def test_hello_content_type(client):
    """Test the /hello endpoint returns correct content type."""
    response = client.get("/hello")
    assert response.headers["content-type"] == "application/json"


def test_hello_invalid_method(client):
    """Test that POST to /hello returns method not allowed."""
    response = client.post("/hello")
    assert response.status_code == 405


def test_404_for_nonexistent_route(client):
    """Test that nonexistent routes return 404."""
    response = client.get("/nonexistent")
    assert response.status_code == 404
