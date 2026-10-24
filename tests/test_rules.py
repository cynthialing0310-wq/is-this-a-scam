"""Tests for the rule-based checks in app/rules.py."""

import pytest

from app.rules import check_urgency


# --- check_urgency -------------------------------------------------------------

@pytest.mark.parametrize(
    ("message", "expected_match"),
    [
        ("Please act now to keep your account open.", "act now"),
        ("URGENT: your parcel could not be delivered.", "URGENT"),
        ("Pay the fee within 24 hours or it will be returned.", "within 24 hours"),
        ("This offer expires today!", "expires today"),
        ("Your account has been suspended.", "account has been suspended"),
        ("Your card is blocked until you confirm your details.", "card is blocked"),
        ("FINAL NOTICE from HMRC regarding your tax refund.", "FINAL NOTICE"),
        ("This is your last chance to claim your prize.", "last chance"),
        ("Failure to respond will result in legal action.", "Failure to respond"),
        ("If you don't verify your identity, we will close it.", "If you don't verify"),
    ],
)
def test_check_urgency_flags_pressure_phrases(message: str, expected_match: str) -> None:
    flags = check_urgency(message)

    assert len(flags) == 1
    assert flags[0].category == "urgency"
    # matched_text keeps the original capitalisation, so the page can point to the exact words
    assert flags[0].matched_text == expected_match


@pytest.mark.parametrize(
    "message",
    [
        "Hi, are we still on for dinner on Saturday?",
        "Your parcel was delivered to your safe place.",
        "Thanks for your order. It will arrive in 3 to 5 working days.",
        "",
    ],
)
def test_check_urgency_ignores_normal_messages(message: str) -> None:
    assert check_urgency(message) == []


def test_check_urgency_respects_word_boundaries() -> None:
    # "react now" contains "act now", but it's a different word, so it shouldn't count
    assert check_urgency("Did you see how they'd react now?") == []


def test_check_urgency_returns_one_flag_per_kind_of_pressure() -> None:
    message = "URGENT: act now! Your account has been suspended. Reply within 2 hours."

    flags = check_urgency(message)

    assert [flag.matched_text for flag in flags] == [
        "act now",
        "URGENT",
        "within 2 hours",
        "account has been suspended",
    ]
