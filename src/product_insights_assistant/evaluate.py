from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from product_insights_assistant.analysis import generate_insights


@dataclass(frozen=True)
class EvalCase:
    name: str
    question: str
    expected_substring: str


DEFAULT_EVAL_CASES = [
    EvalCase(
        name="Low usage risk",
        question="Which users are most likely to churn and why?",
        expected_substring="low",
    ),
    EvalCase(
        name="Declining usage risk",
        question="Find patterns in week-over-week engagement decline.",
        expected_substring="declining",
    ),
    EvalCase(
        name="Retention action",
        question="What experiment should we run next to reduce churn?",
        expected_substring="experiment",
    ),
]


def run_evaluation(data_path: Path, docs_path: Path) -> list[dict[str, object]]:
    results = []
    for case in DEFAULT_EVAL_CASES:
        output = generate_insights(data_path, docs_path, case.question)
        analysis = str(output["analysis"]).lower()
        passed = case.expected_substring in analysis
        results.append(
            {
                "name": case.name,
                "passed": passed,
                "expected_substring": case.expected_substring,
            }
        )
    return results

