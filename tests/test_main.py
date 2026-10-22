"""Tests for the web layer in app/main.py."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_returns_running_message() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Is This a Scam? is running"}
