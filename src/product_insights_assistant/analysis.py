from __future__ import annotations

import json
import os
from pathlib import Path

from product_insights_assistant.data import (
    has_churn_schema,
    load_csv_rows,
    load_user_data,
    preview_csv,
    records_to_table,
    summarize_csv,
    summarize_user_data,
)
from product_insights_assistant.rag import Document, build_context_snippets, load_documents, retrieve_relevant_docs


def build_prompt(
    data_path: Path,
    docs_path: Path | None,
    question: str,
    business_context: str = "",
) -> str:
    rows = load_csv_rows(data_path)
    dataset_summary = summarize_csv(rows)
    dataset_preview = preview_csv(rows)
    specialized_metrics = _build_specialized_metrics(data_path, rows)
    relevant_docs = _load_relevant_context(docs_path, question, business_context)

    context_block = build_context_snippets(relevant_docs) if relevant_docs else "No additional context provided."

    return f"""
You are an AI product insights assistant.

Analyze the dataset preview, summary statistics, and business context.
Return concise, defensible recommendations in JSON with keys:
- dataset_summary
- patterns
- likely_drivers
- recommended_analyses
- experiments
- final_recommendation

Dataset preview:
{dataset_preview}

Dataset summary:
{json.dumps(dataset_summary, indent=2)}

Specialized metrics:
{json.dumps(specialized_metrics, indent=2)}

Business context:
{business_context or "No business context provided."}

Retrieved internal context:
{context_block}

Question:
{question}
""".strip()


def analyze_with_fallback(
    data_path: Path,
    docs_path: Path | None,
    question: str,
    business_context: str = "",
) -> dict[str, object]:
    rows = load_csv_rows(data_path)
    dataset_summary = summarize_csv(rows)
    specialized_metrics = _build_specialized_metrics(data_path, rows)
    relevant_docs = _load_relevant_context(docs_path, question, business_context)

    patterns = [
        f"The dataset contains {dataset_summary['row_count']} rows across {dataset_summary['column_count']} columns.",
        f"Numeric fields detected: {', '.join(dataset_summary['numeric_columns'][:5]) or 'none detected'}.",
    ]
    likely_drivers = [
        "Start with the business outcome column and compare it against the strongest numeric behavior fields.",
        "Check whether missing values or sparse usage patterns cluster around poor outcomes.",
    ]
    recommended_analyses = [
        "Compare outcome rates across high-usage versus low-usage segments.",
        "Review changes over time if the dataset contains weekly, monthly, or sequential behavior fields.",
        "Validate whether there are clear activation milestones that separate retained versus lost users.",
    ]

    if specialized_metrics.get("schema") == "churn":
        metrics = specialized_metrics["metrics"]
        patterns.extend(
            [
                f"Overall churn rate is {metrics['overall_churn_rate']:.0%}.",
                f"Low-usage users churn at {metrics['low_usage_churn_rate']:.0%}, compared with {metrics['overall_churn_rate']:.0%} overall.",
                f"Users with declining usage churn at {metrics['declining_usage_churn_rate']:.0%}.",
            ]
        )
        likely_drivers = [
            "Low week-2 engagement is the clearest churn signal in the dataset.",
            "A negative week-over-week usage trend appears correlated with churn risk.",
        ]

    context_text = " ".join(document.text.lower() for document in relevant_docs)
    if business_context:
        context_text = f"{business_context.lower()} {context_text}"

    experiments = []
    if "onboarding" in context_text or "activation" in context_text:
        experiments.append("Run an onboarding intervention for users who stall before activation or show sharp early drop-off.")
    if "education" in context_text or "guides" in context_text or "confusion" in context_text:
        experiments.append("Trigger contextual education for users who hit setup friction or fail key milestones.")
    if "pricing" in context_text or "renewal" in context_text:
        experiments.append("Test plan-fit messaging or retention offers only after activation issues are addressed.")
    if not experiments:
        experiments.append("Run a segmented lifecycle experiment tied to the highest-risk behavior pattern in this dataset.")

    return {
        "dataset_summary": dataset_summary,
        "patterns": patterns,
        "likely_drivers": likely_drivers,
        "recommended_analyses": recommended_analyses,
        "experiments": experiments,
        "final_recommendation": "Use the uploaded dataset and business context to focus on one measurable risk segment, then test one targeted intervention against it.",
        "sources_used": [document.name for document in relevant_docs],
        "specialized_metrics": specialized_metrics,
    }


def analyze_with_openai(prompt: str, model: str) -> dict[str, object]:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.responses.create(
        model=model,
        input=prompt,
    )
    text = response.output_text
    return {
        "raw_response": text,
    }


def generate_insights(
    data_path: Path,
    docs_path: Path | None,
    question: str,
    business_context: str = "",
    model: str | None = None,
) -> dict[str, object]:
    prompt = build_prompt(data_path, docs_path, question, business_context=business_context)
    if model and os.environ.get("OPENAI_API_KEY"):
        return {
            "mode": "openai",
            "prompt": prompt,
            "analysis": analyze_with_openai(prompt, model),
        }

    return {
        "mode": "fallback",
        "prompt": prompt,
        "analysis": analyze_with_fallback(data_path, docs_path, question, business_context=business_context),
    }


def _build_specialized_metrics(data_path: Path, rows: list[dict[str, str]]) -> dict[str, object]:
    if not has_churn_schema(rows):
        return {"schema": "generic"}

    records = load_user_data(data_path)
    return {
        "schema": "churn",
        "metrics": summarize_user_data(records),
        "preview": records_to_table(records),
    }


def _load_relevant_context(
    docs_path: Path | None,
    question: str,
    business_context: str,
) -> list[Document]:
    documents: list[Document] = []
    if docs_path and docs_path.exists():
        documents.extend(load_documents(docs_path))
    if business_context.strip():
        documents.append(Document(name="business_context.txt", text=business_context.strip()))
    if not documents:
        return []
    return retrieve_relevant_docs(f"{question}\n{business_context}", documents)
