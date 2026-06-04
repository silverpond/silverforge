"""Tests for the FastAPI server."""
import pytest
from fastapi.testclient import TestClient
from factory.server import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def test_hello_endpoint(client):
    """Test the /hello endpoint returns correct JSON."""
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from Silverforge Factory"}


def test_hello_content_type(client):
    """Test the /hello endpoint returns correct content type."""
    response = client.get("/hello")
    assert response.headers["content-type"] == "application/json"


def test_hello_invalid_method(client):
    """Test the /hello endpoint rejects POST requests."""
    response = client.post("/hello")
    assert response.status_code == 405


def test_404_not_found(client):
    """Test undefined routes return 404."""
    response = client.get("/undefined")
    assert response.status_code == 404
