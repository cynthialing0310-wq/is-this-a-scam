"""Rule-based checks: plain Python that looks for known warning signs in a message.

These run before the AI, so the app can still give a useful answer if the AI fails.
"""

import re

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

