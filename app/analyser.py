"""Turns a message into a full result: risk level, red flags, next steps and a confidence note.

For now this uses the rule checks only. The AI layer will be added here later, with the
rule result as the fallback if the AI fails.
"""

from app.models import AnalysisResult, FlagCategory, RedFlag, RiskLevel
from app.rules import run_all_checks

MAX_MESSAGE_LENGTH = 5000  # Characters. Keeps costs and abuse under control.
SHORT_MESSAGE_LENGTH = 40  # Below this, there's too little to go on

NEXT_STEPS_BY_CATEGORY: dict[FlagCategory, str] = {
    "link": "Don't open the link. If you're worried about an account, go to the organisation's "
    "website by typing the address yourself, or use its official app.",
    "payment": "Don't send money, gift cards or crypto until you've checked who you're really "
    "paying. Genuine organisations won't ask for gift cards or crypto.",
    "urgency": "Take your time. Contact the organisation using a phone number or website you "
    "already trust, not one given in the message.",
}
REPORT_STEP = (
    "In the UK, you can forward scam texts to 7726 for free, and report scam emails to "
    "report@phishing.gov.uk."
)
NO_FLAGS_STEP = (
    "If anything still feels wrong, check with the organisation directly using contact "
    "details you already trust."
)


def validate_message(text: str) -> str | None:
    """Return a friendly error message if the input can't be checked, or None if it's fine."""
    if not text.strip():
        return "Please paste a message to check."
    if len(text) > MAX_MESSAGE_LENGTH:
        return (
            f"That message is too long to check. Please paste up to {MAX_MESSAGE_LENGTH:,} "
            "characters, for example just the main part of the email."
        )
    return None


def risk_level_from_flags(flags: list[RedFlag]) -> RiskLevel:
    """Simple rule-only scoring: more kinds of warning sign means higher risk."""
    categories = {flag.category for flag in flags}
    if not categories:
        return "No obvious red flags"
    if len(categories) >= 2:
        return "Likely scam"
    return "Suspicious"


def next_steps_for(flags: list[RedFlag]) -> list[str]:
    """Practical advice based on which kinds of warning sign were found."""
    if not flags:
        return [NO_FLAGS_STEP]
    found = {flag.category for flag in flags}
    steps = [step for category, step in NEXT_STEPS_BY_CATEGORY.items() if category in found]
    steps.append(REPORT_STEP)
    return steps


def confidence_note_for(text: str, risk_level: RiskLevel) -> str | None:
    """Be honest when the result could easily be wrong."""
    if len(text.strip()) < SHORT_MESSAGE_LENGTH:
        return "This message is very short, so there isn't much to go on. Treat this result with caution."
    if risk_level == "No obvious red flags":
        return (
            "No obvious red flags doesn't mean the message is safe. Scammers change their "
            "wording all the time, so trust your instincts."
        )
    return None


def analyse_message(text: str) -> AnalysisResult:
    """Check a message and build the full result. Assumes validate_message has passed."""
    flags = run_all_checks(text)
    risk_level = risk_level_from_flags(flags)
    return AnalysisResult(
        risk_level=risk_level,
        red_flags=flags,
        next_steps=next_steps_for(flags),
        confidence_note=confidence_note_for(text, risk_level),
    )
