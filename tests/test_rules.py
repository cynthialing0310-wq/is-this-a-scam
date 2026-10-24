"""Tests for the rule-based checks in app/rules.py."""

import pytest

from app.rules import check_links, check_payment_requests, check_urgency, run_all_checks


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


# --- check_payment_requests ------------------------------------------------------

@pytest.mark.parametrize(
    ("message", "expected_match"),
    [
        ("Please buy two Steam cards and send me the codes.", "Steam cards"),
        ("Pay the fine with iTunes gift cards today.", "iTunes gift cards"),
        ("You can settle this in Bitcoin.", "Bitcoin"),
        ("Send 50 USDT to this wallet to unlock your earnings.", "USDT"),
        ("Make a bank transfer to the account below.", "bank transfer"),
        ("Send the deposit by Western Union.", "Western Union"),
    ],
)
def test_check_payment_requests_flags_risky_payment_methods(message: str, expected_match: str) -> None:
    flags = check_payment_requests(message)

    assert len(flags) == 1
    assert flags[0].category == "payment"
    assert flags[0].matched_text == expected_match


@pytest.mark.parametrize(
    "message",
    [
        "Thanks for the birthday card!",  # "card" alone isn't a payment request
        "Your Amazon order has been dispatched.",
        "The btcx project meeting is at 3pm.",  # btc only counts as a whole word
    ],
)
def test_check_payment_requests_ignores_normal_messages(message: str) -> None:
    assert check_payment_requests(message) == []


# --- check_links -------------------------------------------------------------------

@pytest.mark.parametrize(
    ("message", "expected_match"),
    [
        ("Reschedule your delivery at bit.ly/3xYz9", "bit.ly/3xYz9"),
        ("Track it here: https://tinyurl.com/abcd.", "https://tinyurl.com/abcd"),  # full stop removed
        ("Log in at http://192.168.4.20/login now", "http://192.168.4.20/login"),
        ("Verify at paypa1-secure.com/verify", "paypa1-secure.com/verify"),
        ("Visit www.amaz0n-refunds.co.uk to claim", "www.amaz0n-refunds.co.uk"),
        ("Pay at https://royalmail-redelivery.com/fee", "https://royalmail-redelivery.com/fee"),
        ("HMRC refund: hmrc-tax-refund.net/claim", "hmrc-tax-refund.net/claim"),
    ],
)
def test_check_links_flags_risky_links(message: str, expected_match: str) -> None:
    flags = check_links(message)

    assert len(flags) == 1
    assert flags[0].category == "link"
    assert flags[0].matched_text == expected_match


@pytest.mark.parametrize(
    "message",
    [
        "Sign in at https://www.paypal.com to see the payment.",
        "Check your tax account at https://www.gov.uk/personal-tax-account",
        "Your order is on amazon.co.uk/orders",
        "Book via the NHS App or at www.nhs.uk",
        "See you at 7.30 tomorrow!",  # numbers with a dot aren't links
        "Sounds good. See you there.",
    ],
)
def test_check_links_ignores_genuine_or_harmless_links(message: str) -> None:
    assert check_links(message) == []


def test_check_links_never_opens_links(monkeypatch: pytest.MonkeyPatch) -> None:
    """Design principle: links are only read as text. Fail loudly if anything tries to connect."""
    import socket

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("check_links tried to open a network connection")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)

    check_links("Pay now at bit.ly/abc or http://10.0.0.1/pay or paypa1.com")


# --- run_all_checks ----------------------------------------------------------------

def test_run_all_checks_combines_every_kind_of_flag() -> None:
    message = "URGENT: pay with Steam cards at bit.ly/fee within 2 hours."

    categories = {flag.category for flag in run_all_checks(message)}

    assert categories == {"urgency", "payment", "link"}


def test_every_brand_has_a_display_name() -> None:
    # Without this, adding a brand to BRAND_DOMAINS but not BRAND_DISPLAY_NAMES would crash check_links
    from app.rules import BRAND_DISPLAY_NAMES, BRAND_DOMAINS

    assert set(BRAND_DOMAINS) == set(BRAND_DISPLAY_NAMES)
