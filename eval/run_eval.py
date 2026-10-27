"""Run every message in eval/messages.csv through the app and report how well it did.

Usage (from the project root):
    python -m eval.run_eval --mode rules   # pattern rules only, free
    python -m eval.run_eval --mode ai      # rules + AI, uses the API key in .env

A message counts as "flagged" if the app says anything other than "No obvious red flags".
Each run is saved to eval/results/ with the date and time, so runs can be compared.
"""

import argparse
import csv
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from app.analyser import analyse_message
from app.config import ai_is_configured
from app.models import RiskLevel

EVAL_DIR = Path(__file__).parent
MESSAGES_FILE = EVAL_DIR / "messages.csv"
RESULTS_DIR = EVAL_DIR / "results"


@dataclass
class Outcome:
    """What the app said about one labelled message."""

    id: str
    label: str  # "scam" or "legit": the right answer
    category: str
    risk_level: RiskLevel  # what the app said
    flagged: bool
    ai_used: bool
    seconds: float

    @property
    def correct(self) -> bool:
        return self.flagged == (self.label == "scam")


def load_messages(path: Path = MESSAGES_FILE) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def is_flagged(risk_level: RiskLevel) -> bool:
    return risk_level != "No obvious red flags"


def run(messages: list[dict[str, str]], use_ai: bool) -> list[Outcome]:
    outcomes: list[Outcome] = []
    for number, message in enumerate(messages, start=1):
        start = time.perf_counter()
        result = analyse_message(message["text"], use_ai=use_ai)
        seconds = time.perf_counter() - start
        outcomes.append(
            Outcome(
                id=message["id"],
                label=message["label"],
                category=message["category"],
                risk_level=result.risk_level,
                flagged=is_flagged(result.risk_level),
                ai_used=result.ai_used,
                seconds=round(seconds, 3),
            )
        )
        print(f"  {number}/{len(messages)} done", end="\r", flush=True)
    print()
    return outcomes


def _rate(part: int, whole: int) -> float | None:
    """A percentage, or None when there's nothing to divide by."""
    return round(100 * part / whole, 1) if whole else None


def summarise(outcomes: list[Outcome]) -> dict:
    """Work out the headline numbers from a list of outcomes."""
    scams = [o for o in outcomes if o.label == "scam"]
    legit = [o for o in outcomes if o.label == "legit"]
    caught = [o for o in scams if o.flagged]
    false_alarms = [o for o in legit if o.flagged]
    times = [o.seconds for o in outcomes]

    by_category: dict[str, dict[str, int]] = {}
    for o in outcomes:
        row = by_category.setdefault(
            o.category, {"scams": 0, "caught": 0, "legit": 0, "false_alarms": 0}
        )
        if o.label == "scam":
            row["scams"] += 1
            row["caught"] += o.flagged
        else:
            row["legit"] += 1
            row["false_alarms"] += o.flagged

    return {
        "messages": len(outcomes),
        "accuracy": _rate(sum(o.correct for o in outcomes), len(outcomes)),
        "scam_catch_rate": _rate(len(caught), len(scams)),
        "false_alarm_rate": _rate(len(false_alarms), len(legit)),
        "scams_marked_likely_scam": _rate(
            sum(o.risk_level == "Likely scam" for o in scams), len(scams)
        ),
        "average_seconds": round(sum(times) / len(times), 2) if times else None,
        "slowest_seconds": max(times, default=None),
        "ai_used_on": sum(o.ai_used for o in outcomes),
        "missed_scam_ids": [o.id for o in scams if not o.flagged],
        "false_alarm_ids": [o.id for o in false_alarms],
        "by_category": dict(sorted(by_category.items())),
    }


def _show(value: object, suffix: str = "") -> str:
    return "n/a" if value is None else f"{value}{suffix}"


def format_report(summary: dict, mode: str, when: datetime) -> str:
    """A Markdown report, readable in the terminal and on GitHub."""
    lines = [
        f"# Evaluation run: {when:%Y-%m-%d %H:%M} ({mode})",
        "",
        "| Measure | Result |",
        "|---|---|",
        f"| Messages | {summary['messages']} |",
        f"| Accuracy | {_show(summary['accuracy'], '%')} |",
        f"| **Scam catch rate** | **{_show(summary['scam_catch_rate'], '%')}** |",
        f"| **False alarm rate** | **{_show(summary['false_alarm_rate'], '%')}** |",
        f"| Scams marked \"Likely scam\" | {_show(summary['scams_marked_likely_scam'], '%')} |",
        f"| Average response time | {_show(summary['average_seconds'], ' s')} |",
        f"| Slowest response time | {_show(summary['slowest_seconds'], ' s')} |",
        f"| AI check used on | {summary['ai_used_on']} of {summary['messages']} |",
        "",
        "## By category",
        "",
        "| Category | Scams caught | False alarms |",
        "|---|---|---|",
    ]
    for category, row in summary["by_category"].items():
        caught = f"{row['caught']} / {row['scams']}" if row["scams"] else "-"
        alarms = f"{row['false_alarms']} / {row['legit']}" if row["legit"] else "-"
        lines.append(f"| {category} | {caught} | {alarms} |")
    lines += [
        "",
        f"Missed scams (ids): {', '.join(summary['missed_scam_ids']) or 'none'}",
        "",
        f"False alarms (ids): {', '.join(summary['false_alarm_ids']) or 'none'}",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the scam checker on labelled messages.")
    parser.add_argument("--mode", choices=["rules", "ai"], default="ai",
                        help="'rules' for pattern rules only, 'ai' for rules + AI (default)")
    args = parser.parse_args()
    use_ai = args.mode == "ai"

    if use_ai and not ai_is_configured():
        raise SystemExit("No ANTHROPIC_API_KEY found. Add it to .env, or run with --mode rules.")

    messages = load_messages()
    print(f"Checking {len(messages)} messages ({args.mode})...")
    outcomes = run(messages, use_ai)
    summary = summarise(outcomes)
    when = datetime.now()

    RESULTS_DIR.mkdir(exist_ok=True)
    stem = f"{when:%Y-%m-%d_%H%M}_{args.mode}"
    report = format_report(summary, args.mode, when)
    (RESULTS_DIR / f"{stem}.md").write_text(report, encoding="utf-8")
    (RESULTS_DIR / f"{stem}.json").write_text(
        json.dumps({"mode": args.mode, "summary": summary,
                    "outcomes": [asdict(o) for o in outcomes]}, indent=2),
        encoding="utf-8",
    )

    print(report)
    print(f"Saved to eval/results/{stem}.md and .json")


if __name__ == "__main__":
    main()
