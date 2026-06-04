import pytest
from fastapi.testclient import TestClient
from factory.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_hello_endpoint_returns_json(client):
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, world!"}


def test_hello_endpoint_has_correct_content_type(client):
    response = client.get("/hello")
    assert response.headers["content-type"] == "application/json"


def test_hello_endpoint_rejects_post_method(client):
    response = client.post("/hello")
    assert response.status_code == 405


def test_hello_endpoint_rejects_put_method(client):
    response = client.put("/hello")
    assert response.status_code == 405


def test_hello_endpoint_rejects_delete_method(client):
    response = client.delete("/hello")
    assert response.status_code == 405


def test_invalid_route_returns_404(client):
    response = client.get("/nonexistent")
    assert response.status_code == 404
