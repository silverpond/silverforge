"""Tests for the HTTP API server."""
import json

import pytest
from fastapi.testclient import TestClient

from factory.server import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_hello_endpoint_returns_correct_json(client):
    """Test that GET /hello returns the correct JSON response."""
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from Silverpond Factory"}


def test_hello_endpoint_content_type(client):
    """Test that /hello returns JSON content type."""
    response = client.get("/hello")
    assert response.headers["content-type"] == "application/json"


def test_hello_endpoint_method_not_allowed(client):
    """Test that POST to /hello is not allowed."""
    response = client.post("/hello")
    assert response.status_code == 405


def test_nonexistent_endpoint_returns_404(client):
    """Test that requesting a nonexistent endpoint returns 404."""
    response = client.get("/nonexistent")
    assert response.status_code == 404
