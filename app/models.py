"""Data shapes shared across the app, validated by Pydantic."""

from typing import Literal

from pydantic import BaseModel

# The kinds of warning sign the rule checks can find
FlagCategory = Literal["urgency", "payment", "link"]


class RedFlag(BaseModel):
    """One warning sign found in a message."""

    category: FlagCategory
    explanation: str  # Plain English, shown to the user
    matched_text: str  # The exact words in the message that triggered this flag
