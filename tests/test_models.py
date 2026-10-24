"""Tests for the data models in app/models.py."""

import pytest
from pydantic import ValidationError

from app.models import RedFlag


def test_red_flag_accepts_valid_data() -> None:
    flag = RedFlag(category="urgency", explanation="Rushes you.", matched_text="act now")

    assert flag.category == "urgency"


def test_red_flag_rejects_unknown_category() -> None:
    with pytest.raises(ValidationError):
        RedFlag(category="weather", explanation="Not a real category.", matched_text="sunny")
