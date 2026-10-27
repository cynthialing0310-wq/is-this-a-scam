"""Tests for the evaluation script's maths and its labelled data file."""

from eval.run_eval import Outcome, load_messages, summarise


def outcome(id: str, label: str, category: str, flagged: bool, seconds: float = 1.0) -> Outcome:
    return Outcome(
        id=id,
        label=label,
        category=category,
        risk_level="Likely scam" if flagged else "No obvious red flags",
        flagged=flagged,
        ai_used=False,
        seconds=seconds,
    )


def test_summarise_works_out_catch_rate_and_false_alarm_rate() -> None:
    outcomes = [
        outcome("1", "scam", "bank", flagged=True),
        outcome("2", "scam", "bank", flagged=True),
        outcome("3", "scam", "prize", flagged=False),  # missed scam
        outcome("4", "scam", "prize", flagged=True),
        outcome("5", "legit", "bank", flagged=True),  # false alarm
        outcome("6", "legit", "bank", flagged=False),
    ]

    summary = summarise(outcomes)

    assert summary["scam_catch_rate"] == 75.0  # 3 of 4 scams
    assert summary["false_alarm_rate"] == 50.0  # 1 of 2 legit
    assert summary["accuracy"] == 66.7  # 4 of 6 right
    assert summary["missed_scam_ids"] == ["3"]
    assert summary["false_alarm_ids"] == ["5"]
    assert summary["by_category"]["prize"] == {"scams": 2, "caught": 1, "legit": 0, "false_alarms": 0}


def test_summarise_reports_response_times() -> None:
    summary = summarise([
        outcome("1", "scam", "bank", True, seconds=1.0),
        outcome("2", "legit", "bank", False, seconds=3.0),
    ])

    assert summary["average_seconds"] == 2.0
    assert summary["slowest_seconds"] == 3.0


def test_summarise_handles_no_legit_messages_without_crashing() -> None:
    summary = summarise([outcome("1", "scam", "bank", flagged=True)])

    assert summary["false_alarm_rate"] is None


def test_labelled_messages_file_is_well_formed() -> None:
    messages = load_messages()

    assert len(messages) >= 50
    assert len({m["id"] for m in messages}) == len(messages), "ids must be unique"
    assert {m["label"] for m in messages} == {"scam", "legit"}
    for message in messages:
        assert message["text"].strip(), f"message {message['id']} is empty"
        assert message["category"], f"message {message['id']} has no category"
