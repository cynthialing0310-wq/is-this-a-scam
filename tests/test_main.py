"""Tests for the web layer in app/main.py."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home_page_loads() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Is This a Scam?" in response.text


def test_stylesheet_is_served() -> None:
    response = client.get("/static/style.css")

    assert response.status_code == 200


def test_health_check_reports_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
