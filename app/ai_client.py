"""AI layer: asks Claude to analyse a message and return a validated AIAnalysis.

Every way this can fail is turned into one AIAnalysisError, so the caller has one thing
to catch and can fall back to the rule-based result.
"""

import logging
from functools import cache
from pathlib import Path

import anthropic
from pydantic import ValidationError

from app.config import AI_MODEL, AI_TIMEOUT_SECONDS
from app.models import AIAnalysis

logger = logging.getLogger(__name__)

PROMPT_FILE = Path(__file__).parent / "prompts" / "analyse_v1.txt"
MAX_OUTPUT_TOKENS = 4000  # Includes the model's thinking, so leave room beyond the JSON itself


class AIAnalysisError(Exception):
    """The AI check couldn't produce a usable answer this time."""


@cache
def _system_prompt() -> str:
    """Read the prompt file once, the first time it's needed."""
    return PROMPT_FILE.read_text(encoding="utf-8")


@cache
def _client() -> anthropic.Anthropic:
    """One shared client. It reads ANTHROPIC_API_KEY from the environment itself."""
    return anthropic.Anthropic(timeout=AI_TIMEOUT_SECONDS, max_retries=1)


def wrap_untrusted_message(text: str) -> str:
    """Put the message inside <message> tags, so the prompt can tell it apart from instructions.

    Any tags already in the text are removed first. Otherwise a scammer could write
    "</message>" to "close" the message early and add their own instructions after it.
    """
    cleaned = text.replace("<message>", "").replace("</message>", "")
    return f"<message>\n{cleaned}\n</message>"


def analyse_with_ai(text: str) -> AIAnalysis:
    """Ask the AI to analyse the message. Raises AIAnalysisError if anything goes wrong."""
    try:
        response = _client().messages.parse(
            model=AI_MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=_system_prompt(),
            messages=[{"role": "user", "content": wrap_untrusted_message(text)}],
            output_format=AIAnalysis,
        )
    except anthropic.APITimeoutError as error:
        raise AIAnalysisError("The AI took too long to reply") from error
    except anthropic.APIConnectionError as error:
        raise AIAnalysisError("Couldn't reach the AI service") from error
    except anthropic.RateLimitError as error:
        raise AIAnalysisError("Too many requests to the AI service") from error
    except anthropic.APIStatusError as error:
        raise AIAnalysisError(f"The AI service returned an error ({error.status_code})") from error
    except ValidationError as error:
        raise AIAnalysisError("The AI's reply didn't match the expected format") from error

    if response.stop_reason == "refusal":
        raise AIAnalysisError("The AI declined to analyse this message")
    if response.stop_reason == "max_tokens":
        raise AIAnalysisError("The AI's reply was cut off before it finished")
    if response.parsed_output is None:
        raise AIAnalysisError("The AI's reply couldn't be read")

    return response.parsed_output
