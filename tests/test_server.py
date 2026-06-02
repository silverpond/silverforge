"""Tests for the FastAPI server."""
import pytest
from fastapi.testclient import TestClient
from factory.server import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


def test_hello_endpoint(client):
    """Test that /hello endpoint returns correct JSON."""
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "hello"}


def test_hello_content_type(client):
    """Test that /hello endpoint returns JSON content type."""
    response = client.get("/hello")
    assert response.headers["content-type"] == "application/json"


def test_hello_post_not_allowed(client):
    """Test that POST requests to /hello are not allowed."""
    response = client.post("/hello")
    assert response.status_code == 405


def test_hello_put_not_allowed(client):
    """Test that PUT requests to /hello are not allowed."""
    response = client.put("/hello")
    assert response.status_code == 405


def test_hello_delete_not_allowed(client):
    """Test that DELETE requests to /hello are not allowed."""
    response = client.delete("/hello")
    assert response.status_code == 405


def test_nonexistent_endpoint(client):
    """Test that nonexistent endpoints return 404."""
    response = client.get("/nonexistent")
    assert response.status_code == 404
