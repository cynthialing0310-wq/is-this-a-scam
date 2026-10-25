"""Settings, read from environment variables (and the .env file when running locally).

On Render, these are set in the dashboard under Environment, so no secrets are in the code.
"""

import os

from dotenv import load_dotenv

load_dotenv()  # Does nothing if there's no .env file, e.g. on Render

# A small, fast model keeps each check quick and cheap
AI_MODEL: str = os.getenv("AI_MODEL", "claude-haiku-5-5")

# Give up on the AI after this many seconds and show the rule-based result instead
AI_TIMEOUT_SECONDS: float = float(os.getenv("AI_TIMEOUT_SECONDS", "20"))


def ai_is_configured() -> bool:
    """True if an API key is set. Without one, the app runs on the rule checks only."""
    return bool(os.getenv("ANTHROPIC_API_KEY"))
