"""Tests for the FastAPI server."""
import pytest
from fastapi.testclient import TestClient
from factory.server import app


client = TestClient(app)


def test_hello_endpoint_returns_json():
    """Test that /hello returns the correct JSON response."""
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "hello"}


def test_hello_endpoint_content_type():
    """Test that /hello returns application/json content type."""
    response = client.get("/hello")
    assert response.headers["content-type"] == "application/json"


def test_hello_endpoint_method_validation():
    """Test that /hello only accepts GET requests."""
    response = client.post("/hello")
    assert response.status_code == 405


def test_hello_endpoint_404():
    """Test that invalid paths return 404."""
    response = client.get("/invalid")
    assert response.status_code == 404
