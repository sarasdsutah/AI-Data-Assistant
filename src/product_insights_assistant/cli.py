from __future__ import annotations

import argparse
import json
from pathlib import Path

from product_insights_assistant.analysis import generate_insights
from product_insights_assistant.evaluate import run_evaluation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI Product Insights Assistant")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/users.csv"),
        help="Path to a CSV file containing user behavior data.",
    )
    parser.add_argument(
        "--docs",
        type=Path,
        default=Path("knowledge"),
        help="Path to a directory of markdown documents used for retrieval.",
    )
    parser.add_argument(
        "--question",
        default="Based on current behavior and prior experiments, what should we do next?",
        help="Natural-language question to analyze.",
    )
    parser.add_argument(
        "--business-context",
        default="",
        help="Optional description of the dataset, company, or business problem.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional OpenAI model name. Requires OPENAI_API_KEY.",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Run the lightweight evaluation suite instead of a single analysis.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.eval:
        print(json.dumps(run_evaluation(args.data, args.docs), indent=2))
        return

    result = generate_insights(
        args.data,
        args.docs,
        args.question,
        business_context=args.business_context,
        model=args.model,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
