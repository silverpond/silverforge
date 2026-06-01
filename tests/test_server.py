"""
Tests for the HTTP API server.
"""
import pytest
from fastapi.testclient import TestClient
from factory.server import app


client = TestClient(app)


def test_hello_endpoint():
    """Test the /hello endpoint returns correct JSON response."""
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World!"}


def test_hello_endpoint_content_type():
    """Test the /hello endpoint returns JSON content type."""
    response = client.get("/hello")
    assert response.headers["content-type"].startswith("application/json")


def test_hello_endpoint_post_not_allowed():
    """Test that POST to /hello is not allowed."""
    response = client.post("/hello")
    assert response.status_code == 405


def test_404_on_nonexistent_route():
    """Test that nonexistent routes return 404."""
    response = client.get("/nonexistent")
    assert response.status_code == 404
