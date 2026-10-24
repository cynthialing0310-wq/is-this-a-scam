"""Data shapes shared across the app, validated by Pydantic."""

from typing import Literal

from pydantic import BaseModel

# The kinds of warning sign the rule checks can find
FlagCategory = Literal["urgency", "payment", "link"]

# The app never says "safe": it can't know that, only whether it found warning signs
RiskLevel = Literal["Likely scam", "Suspicious", "No obvious red flags"]


class RedFlag(BaseModel):
    """One warning sign found in a message."""

    category: FlagCategory
    explanation: str  # Plain English, shown to the user
    matched_text: str  # The exact words in the message that triggered this flag


class AnalysisResult(BaseModel):
    """Everything the app tells the user about one message."""

    risk_level: RiskLevel
    red_flags: list[RedFlag]
    next_steps: list[str]
    confidence_note: str | None = None  # Shown when the app isn't sure
