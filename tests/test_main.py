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


def test_check_shows_result_for_scam_message() -> None:
    response = client.post(
        "/check",
        data={"message": "URGENT: your account is locked. Verify at paypa1-secure.com within 24 hours."},
    )

    assert response.status_code == 200
    assert "Likely scam" in response.text
    assert "paypa1-secure.com" in response.text


def test_check_rejects_empty_message_with_friendly_error() -> None:
    response = client.post("/check", data={"message": "   "})

    assert response.status_code == 400
    assert "Please paste a message to check." in response.text


def test_check_rejects_very_long_message() -> None:
    response = client.post("/check", data={"message": "a" * 5001})

    assert response.status_code == 400
    assert "too long" in response.text


def test_check_escapes_html_in_the_message() -> None:
    """The message is untrusted, so any HTML in it must be shown as text, never run."""
    response = client.post(
        "/check", data={"message": "<script>alert('hi')</script> act now at bit.ly/x"}
    )

    assert "<script>alert('hi')</script>" not in response.text
    assert "&lt;script&gt;" in response.text
