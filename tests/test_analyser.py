"""Tests for app/analyser.py: input limits, risk levels, next steps and confidence notes."""

import pytest

from app.analyser import MAX_MESSAGE_LENGTH, analyse_message, validate_message


# --- validate_message --------------------------------------------------------------

@pytest.mark.parametrize("message", ["", "   ", "\n\t"])
def test_validate_message_rejects_empty_input(message: str) -> None:
    assert validate_message(message) == "Please paste a message to check."


def test_validate_message_rejects_very_long_input() -> None:
    error = validate_message("a" * (MAX_MESSAGE_LENGTH + 1))

    assert error is not None
    assert "too long" in error


def test_validate_message_accepts_input_at_the_limit() -> None:
    assert validate_message("a" * MAX_MESSAGE_LENGTH) is None


# --- analyse_message ---------------------------------------------------------------

def test_several_kinds_of_warning_sign_means_likely_scam() -> None:
    result = analyse_message(
        "Royal Mail: your parcel is on hold. Pay the £1.99 fee within 24 hours at bit.ly/rm-fee"
    )

    assert result.risk_level == "Likely scam"
    assert any("7726" in step for step in result.next_steps)


def test_one_kind_of_warning_sign_means_suspicious() -> None:
    result = analyse_message("Hi, can you send the rent by bank transfer this month as usual? Thanks")

    assert result.risk_level == "Suspicious"


def test_no_warning_signs_never_claims_the_message_is_safe() -> None:
    result = analyse_message("Hi! Are we still on for dinner on Saturday at the Italian place?")

    assert result.risk_level == "No obvious red flags"
    assert result.red_flags == []
    assert result.confidence_note is not None
    assert "doesn't mean the message is safe" in result.confidence_note


def test_very_short_message_gets_a_caution_note() -> None:
    result = analyse_message("ok see u")

    assert result.confidence_note is not None
    assert "very short" in result.confidence_note
