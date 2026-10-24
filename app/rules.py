"""Rule-based checks: plain Python that looks for known warning signs in a message.

These run before the AI, so the app can still give a useful answer if the AI fails.
"""

import ipaddress
import re
from urllib.parse import urlsplit

from app.models import RedFlag

# Each entry pairs a pattern to look for with the explanation shown to the user.
# re.IGNORECASE means "ACT NOW" and "act now" both match.
# \b is a word boundary, so "act now" doesn't match inside "react now".
URGENCY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\bact (now|immediately|fast|quickly)\b", re.IGNORECASE),
        "Pushes you to act straight away. Scammers rush people so they don't stop to think or check.",
    ),
    (
        re.compile(r"\burgent(ly)?\b", re.IGNORECASE),
        "Calls itself urgent. Genuine organisations rarely pressure you like this by message.",
    ),
    (
        re.compile(r"\bwithin \d+ (minutes?|hours?|hrs?|days?)\b", re.IGNORECASE),
        "Sets a short deadline. Tight time limits are a common way to stop you checking if a message is real.",
    ),
    (
        re.compile(r"\b(expires?|ends?) (today|tonight|soon)\b", re.IGNORECASE),
        "Says an offer or deadline ends very soon, to rush your decision.",
    ),
    (
        re.compile(
            r"\b(account|card|access) (has been |will be |is )?"
            r"(suspended|locked|blocked|frozen|closed|deactivated)\b",
            re.IGNORECASE,
        ),
        "Says your account or card is blocked. This is a common scare tactic to make you click or call quickly.",
    ),
    (
        re.compile(r"\bfinal (notice|warning|reminder)\b", re.IGNORECASE),
        "Calls itself a final notice, to make you feel you've run out of time.",
    ),
    (
        re.compile(r"\blast chance\b", re.IGNORECASE),
        "Says this is your last chance, a common pressure phrase.",
    ),
    (
        re.compile(
            r"\b(failure to|if you do not|if you don'?t) (respond|reply|pay|verify|confirm)\b",
            re.IGNORECASE,
        ),
        "Threatens a consequence if you don't respond. Scammers use threats to rush you.",
    ),
]


def check_urgency(text: str) -> list[RedFlag]:
    """Find urgency and pressure phrases in the message."""
    flags: list[RedFlag] = []
    for pattern, explanation in URGENCY_PATTERNS:
        match = pattern.search(text)
        if match:
            flags.append(
                RedFlag(
                    category="urgency",
                    explanation=explanation,
                    matched_text=match.group(),
                )
            )
    return flags


PAYMENT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\b(gift|itunes|apple|google play|steam|amazon|ebay) (gift )?(cards?|vouchers?)\b",
            re.IGNORECASE,
        ),
        "Asks for payment by gift card. Real companies and government bodies never ask for this, "
        "because gift card payments can't be traced or refunded.",
    ),
    (
        re.compile(
            r"\b(bitcoin|btc|crypto|cryptocurrency|cryptocurrencies|usdt|tether|ethereum)\b",
            re.IGNORECASE,
        ),
        "Mentions paying in cryptocurrency. Crypto payments are almost impossible to get back, "
        "which is why scammers ask for them.",
    ),
    (
        re.compile(r"\b(bank|wire|money) transfer\b", re.IGNORECASE),
        "Asks for a bank transfer. This can be normal, but once sent the money is hard to recover. "
        "Check who you're paying through contact details you already trust.",
    ),
    (
        re.compile(r"\b(western union|moneygram)\b", re.IGNORECASE),
        "Asks you to send money through a cash transfer service. These are hard to trace and a "
        "common way scammers get paid.",
    ),
]


def check_payment_requests(text: str) -> list[RedFlag]:
    """Find payment requests in the message."""
    flags: list[RedFlag] = []
    for pattern, explanation in PAYMENT_PATTERNS:
        match = pattern.search(text)
        if match:
            flags.append(
                RedFlag(
                    category="payment",
                    explanation=explanation,
                    matched_text=match.group(),
                )
            )
    return flags



# --- Links -----------------------------------------------------------------------
# IMPORTANT: these checks only read the text of a link. They never visit it, because
# opening a scam link could be dangerous.

# Finds things that look like web addresses, with or without "http://" or "www."
URL_PATTERN = re.compile(
    r"\b(?:https?://)?(?:www\.)?"  # optional http:// or https:// and www.
    r"(?:[a-z0-9-]+\.)+[a-z]{2,}"  # a domain name, e.g. bit.ly or paypal-login.com
    r"(?::\d+)?"  # an optional port, e.g. :8080
    r"(?:/[^\s]*)?",  # an optional path, e.g. /abc123
    re.IGNORECASE,
)
IP_URL_PATTERN = re.compile(
    r"\b(?:https?://)?\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?(?:/[^\s]*)?",
    re.IGNORECASE,
)

URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly", "rebrand.ly",
    "cutt.ly", "shorturl.at", "rb.gy", "t.ly", "tiny.cc", "s.id", "tr.im", "bl.ink",
}

# Brands scammers often pretend to be, and the real websites they use.
# A link that uses the brand's name on any other website is a lookalike.
BRAND_DOMAINS: dict[str, set[str]] = {
    "paypal": {"paypal.com", "paypal.co.uk", "paypal.me"},
    "amazon": {"amazon.com", "amazon.co.uk"},
    "apple": {"apple.com", "icloud.com"},
    "microsoft": {"microsoft.com", "live.com", "outlook.com"},
    "netflix": {"netflix.com"},
    "hmrc": {"gov.uk"},
    "govuk": {"gov.uk"},
    "dvla": {"gov.uk"},
    "royalmail": {"royalmail.com"},
    "evri": {"evri.com"},
    "dpd": {"dpd.co.uk", "dpd.com"},
    "hsbc": {"hsbc.co.uk", "hsbc.com"},
    "barclays": {"barclays.co.uk", "barclays.com"},
    "lloyds": {"lloydsbank.com", "lloydsbank.co.uk", "lloydsbankinggroup.com"},
    "natwest": {"natwest.com"},
    "santander": {"santander.co.uk", "santander.com"},
    "monzo": {"monzo.com"},
    "nhs": {"nhs.uk", "gov.uk"},
}

# How each brand's name is written in explanations shown to the user
BRAND_DISPLAY_NAMES: dict[str, str] = {
    "paypal": "PayPal", "amazon": "Amazon", "apple": "Apple", "microsoft": "Microsoft",
    "netflix": "Netflix", "hmrc": "HMRC", "govuk": "GOV.UK", "dvla": "DVLA",
    "royalmail": "Royal Mail", "evri": "Evri", "dpd": "DPD", "hsbc": "HSBC",
    "barclays": "Barclays", "lloyds": "Lloyds", "natwest": "NatWest",
    "santander": "Santander", "monzo": "Monzo", "nhs": "the NHS",
}

# Numbers scammers swap in for letters that look similar, e.g. paypa1 or amaz0n
LOOKALIKE_DIGITS = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t"})


def _strip_trailing_punctuation(url: str) -> str:
    """A link at the end of a sentence picks up the full stop, e.g. 'bit.ly/abc.'"""
    return url.rstrip(".,;:!?)'\"")


def _host_of(url: str) -> str:
    """Pull out just the website name, e.g. 'www.Bit.ly/abc' -> 'bit.ly'."""
    if "://" not in url:
        url = "http://" + url
    host = (urlsplit(url).hostname or "").lower()
    return host.removeprefix("www.")


def _is_on_domain(host: str, domain: str) -> bool:
    """True if host is the domain itself or one of its subdomains (e.g. www.gov.uk)."""
    return host == domain or host.endswith("." + domain)


def _impersonated_brand(host: str) -> str | None:
    """Return the brand a website name pretends to be, or None if it's genuine or unrelated."""
    squashed = host.translate(LOOKALIKE_DIGITS).replace("-", "").replace(".", "")
    for brand, real_domains in BRAND_DOMAINS.items():
        if brand in squashed and not any(_is_on_domain(host, d) for d in real_domains):
            return brand
    return None


def check_links(text: str) -> list[RedFlag]:
    """Find risky-looking links in the message, by reading their text only."""
    flags: list[RedFlag] = []

    for match in IP_URL_PATTERN.finditer(text):
        flags.append(
            RedFlag(
                category="link",
                explanation="This link uses a string of numbers instead of a website name. "
                "Real companies almost never do this. It's often used to hide where a link goes.",
                matched_text=_strip_trailing_punctuation(match.group()),
            )
        )

    for match in URL_PATTERN.finditer(text):
        url = _strip_trailing_punctuation(match.group())
        host = _host_of(url)
        if not host:
            continue

        if host in URL_SHORTENERS:
            flags.append(
                RedFlag(
                    category="link",
                    explanation="This is a shortened link, which hides the real website it leads to. "
                    "Don't open it unless you trust the sender.",
                    matched_text=url,
                )
            )
            continue

        brand = _impersonated_brand(host)
        if brand:
            flags.append(
                RedFlag(
                    category="link",
                    explanation=f"This link uses the name {BRAND_DISPLAY_NAMES[brand]} but isn't "
                    "their real website. Scammers make lookalike addresses to trick you into entering your details.",
                    matched_text=url,
                )
            )

    return flags


def run_all_checks(text: str) -> list[RedFlag]:
    """Run every rule check and return all the red flags found."""
    return check_links(text) + check_payment_requests(text) + check_urgency(text)
