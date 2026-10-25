"""Shared test setup. pytest loads this file automatically before any test runs."""

from collections.abc import Callable

import pytest

import app.analyser
from app.models import AIAnalysis


@pytest.fixture(autouse=True)
def no_real_ai_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never call the real AI: it would cost money, be slow, and give different answers.

    By default the AI counts as "not set up", so the app uses the rule checks only.
    Tests that need an AI answer use the fake_ai fixture below instead.
    """
    monkeypatch.setattr(app.analyser, "ai_is_configured", lambda: False)


@pytest.fixture
def fake_ai(monkeypatch: pytest.MonkeyPatch) -> Callable[[AIAnalysis | Exception], None]:
    """Make the AI return a chosen answer, or raise a chosen error, for one test."""

    def set_ai_behaviour(outcome: AIAnalysis | Exception) -> None:
        def fake_analyse_with_ai(text: str) -> AIAnalysis:
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        monkeypatch.setattr(app.analyser, "ai_is_configured", lambda: True)
        monkeypatch.setattr(app.analyser, "analyse_with_ai", fake_analyse_with_ai)

    return set_ai_behaviour
