"""Tests for the HTTP server endpoint."""
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
    assert response.json() == {"message": "Hello, World!"}


def test_hello_content_type(client):
    """Test the /hello endpoint returns correct content type."""
    response = client.get("/hello")
    assert response.headers["content-type"] == "application/json"


def test_hello_method_validation(client):
    """Test that only GET is allowed on /hello."""
    assert client.post("/hello").status_code == 405
    assert client.put("/hello").status_code == 405
    assert client.delete("/hello").status_code == 405


def test_404_handling(client):
    """Test that non-existent routes return 404."""
    response = client.get("/notfound")
    assert response.status_code == 404
