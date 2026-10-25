"""Data shapes shared across the app, validated by Pydantic."""

from typing import Literal

from pydantic import BaseModel

# The kinds of warning sign the app can find.
# The rule checks use the first three; the AI can also use the others.
FlagCategory = Literal[
    "urgency",
    "payment",
    "link",
    "impersonation",  # pretending to be a bank, company, government body or person
    "personal_details",  # asking for passwords, codes, card or bank details
    "too_good_to_be_true",  # prizes, refunds, easy money, unrealistic jobs or prices
    "other",
]

# The app never says "safe": it can't know that, only whether it found warning signs
RiskLevel = Literal["Likely scam", "Suspicious", "No obvious red flags"]


class RedFlag(BaseModel):
    """One warning sign found in a message."""

    category: FlagCategory
    explanation: str  # Plain English, shown to the user
    matched_text: str  # The exact words in the message that triggered this flag


class AIAnalysis(BaseModel):
    """The shape we ask the AI to reply in. Pydantic rejects anything that doesn't fit."""

    risk_level: RiskLevel
    red_flags: list[RedFlag]
    confidence_note: str | None  # The AI's own note when it isn't sure, otherwise null


class AnalysisResult(BaseModel):
    """Everything the app tells the user about one message."""

    risk_level: RiskLevel
    red_flags: list[RedFlag]
    next_steps: list[str]
    confidence_note: str | None = None  # Shown when the app isn't sure
    ai_used: bool = False  # False when the result comes from the rule checks only
