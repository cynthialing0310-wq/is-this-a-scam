"""Turns a message into a full result: risk level, red flags, next steps and a confidence note.

Two layers: the rule checks always run first. Then the AI reads the whole message. If the
AI fails for any reason, the person still gets the rule-based result, with a note saying so.
"""

import logging

from app.ai_client import AIAnalysisError, analyse_with_ai
from app.config import ai_is_configured
from app.models import AIAnalysis, AnalysisResult, FlagCategory, RedFlag, RiskLevel
from app.rules import run_all_checks

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 5000  # Characters. Keeps costs and abuse under control.
SHORT_MESSAGE_LENGTH = 40  # Below this, there's too little to go on

# Lets us compare risk levels, e.g. to pick the more cautious of two
RISK_ORDER: dict[RiskLevel, int] = {"No obvious red flags": 0, "Suspicious": 1, "Likely scam": 2}

# Next steps are fixed text chosen by category, never written by the AI. A scam message
# could try to trick the AI into giving bad advice, like "it's fine, click the link".
NEXT_STEPS_BY_CATEGORY: dict[FlagCategory, str] = {
    "link": "Don't open the link. If you're worried about an account, go to the organisation's "
    "website by typing the address yourself, or use its official app.",
    "personal_details": "Don't share passwords, one-time codes, or card or bank details. "
    "Genuine organisations won't ask for these by message.",
    "payment": "Don't send money, gift cards or crypto until you've checked who you're really "
    "paying. Genuine organisations won't ask for gift cards or crypto.",
    "impersonation": "If it claims to be from an organisation or someone you know, contact them "
    "separately, using details you already have, to check it's really them.",
    "too_good_to_be_true": "Be wary of prizes, refunds or offers you weren't expecting. "
    "If it sounds too good to be true, it usually is.",
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

AI_UNAVAILABLE_NOTE = (
    "Our AI check isn't available right now, so this result comes from our pattern checks "
    "only. They catch common warning signs but can miss newer tricks."
)
LAYERS_DISAGREE_NOTE = (
    "Our pattern checks and our AI check disagreed about this message, so we've shown the "
    "more cautious result."
)
SHORT_MESSAGE_NOTE = (
    "This message is very short, so there isn't much to go on. Treat this result with caution."
)
NO_FLAGS_NOTE = (
    "No obvious red flags doesn't mean the message is safe. Scammers change their wording "
    "all the time, so trust your instincts."
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


def more_cautious(first: RiskLevel, second: RiskLevel) -> RiskLevel:
    """Return whichever risk level is higher."""
    return first if RISK_ORDER[first] >= RISK_ORDER[second] else second


def _quote_is_in_message(flag: RedFlag, text: str) -> bool:
    """Every red flag must point to real words in the message. AI quotes that don't are dropped."""
    quote = flag.matched_text.strip().lower()
    return bool(quote) and quote in text.lower()


def _same_spot(first: RedFlag, second: RedFlag) -> bool:
    """True if two flags point at the same words (one quote contains the other)."""
    a, b = first.matched_text.lower(), second.matched_text.lower()
    return a in b or b in a


def combine_flags(rule_flags: list[RedFlag], ai_flags: list[RedFlag], text: str) -> list[RedFlag]:
    """Rule flags first, then AI flags that are genuine quotes and not already covered."""
    combined = list(rule_flags)
    for flag in ai_flags:
        if not _quote_is_in_message(flag, text):
            continue
        if any(_same_spot(flag, existing) for existing in combined):
            continue
        combined.append(flag)
    return combined


def next_steps_for(flags: list[RedFlag]) -> list[str]:
    """Practical advice based on which kinds of warning sign were found."""
    if not flags:
        return [NO_FLAGS_STEP]
    found = {flag.category for flag in flags}
    steps = [step for category, step in NEXT_STEPS_BY_CATEGORY.items() if category in found]
    steps.append(REPORT_STEP)
    return steps


def _try_ai(text: str) -> AIAnalysis | None:
    """Run the AI check, or return None if it isn't set up or fails."""
    if not ai_is_configured():
        return None
    try:
        return analyse_with_ai(text)
    except AIAnalysisError as error:
        # Log what went wrong, never the message itself (it may contain personal details)
        logger.warning("AI check failed, showing rule-based result instead: %s", error)
        return None


def analyse_message(text: str) -> AnalysisResult:
    """Check a message and build the full result. Assumes validate_message has passed."""
    rule_flags = run_all_checks(text)
    rule_risk = risk_level_from_flags(rule_flags)
    ai_result = _try_ai(text)
    notes: list[str] = []

    if ai_result is None:
        flags, risk_level = rule_flags, rule_risk
        notes.append(AI_UNAVAILABLE_NOTE)
    else:
        flags = combine_flags(rule_flags, ai_result.red_flags, text)
        # The more cautious level wins, so a scam message can't talk the AI into a lower one
        risk_level = more_cautious(rule_risk, ai_result.risk_level)
        if ai_result.confidence_note:
            notes.append(ai_result.confidence_note)
        if ai_result.risk_level != rule_risk:
            notes.append(LAYERS_DISAGREE_NOTE)

    if len(text.strip()) < SHORT_MESSAGE_LENGTH and not (ai_result and ai_result.confidence_note):
        notes.append(SHORT_MESSAGE_NOTE)
    if risk_level == "No obvious red flags":
        notes.append(NO_FLAGS_NOTE)

    return AnalysisResult(
        risk_level=risk_level,
        red_flags=flags,
        next_steps=next_steps_for(flags),
        confidence_note=" ".join(notes) or None,
        ai_used=ai_result is not None,
    )
