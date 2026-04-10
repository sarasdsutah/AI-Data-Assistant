from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class UserRecord:
    user_id: int
    week1_usage: int
    week2_usage: int
    churned: int

    @property
    def usage_delta(self) -> int:
        return self.week2_usage - self.week1_usage

    @property
    def low_usage(self) -> bool:
        return self.week2_usage <= 1

    @property
    def declining_usage(self) -> bool:
        return self.usage_delta < 0


def load_user_data(path: Path) -> list[UserRecord]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            UserRecord(
                user_id=int(row["user_id"]),
                week1_usage=int(row["week1_usage"]),
                week2_usage=int(row["week2_usage"]),
                churned=int(row["churned"]),
            )
            for row in reader
        ]


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def infer_numeric_columns(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return []

    numeric_columns = []
    for column in rows[0]:
        values = [row.get(column, "").strip() for row in rows if row.get(column, "").strip()]
        if values and all(_is_number(value) for value in values):
            numeric_columns.append(column)
    return numeric_columns


def summarize_csv(rows: list[dict[str, str]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("Expected at least one CSV row.")

    columns = list(rows[0].keys())
    numeric_columns = infer_numeric_columns(rows)
    missing_by_column = {
        column: sum(1 for row in rows if not row.get(column, "").strip()) for column in columns
    }
    numeric_summary = {}
    for column in numeric_columns[:8]:
        numeric_values = [float(row[column]) for row in rows if row.get(column, "").strip()]
        numeric_summary[column] = {
            "min": min(numeric_values),
            "max": max(numeric_values),
            "avg": round(sum(numeric_values) / len(numeric_values), 2),
        }

    return {
        "row_count": len(rows),
        "column_count": len(columns),
        "columns": columns,
        "numeric_columns": numeric_columns,
        "missing_values": missing_by_column,
        "numeric_summary": numeric_summary,
    }


def preview_csv(rows: list[dict[str, str]], limit: int = 8) -> str:
    if not rows:
        return ""

    headers = list(rows[0].keys())
    lines = [" | ".join(headers)]
    for row in rows[:limit]:
        lines.append(" | ".join(row.get(header, "") for header in headers))
    return "\n".join(lines)


def has_churn_schema(rows: list[dict[str, str]]) -> bool:
    if not rows:
        return False
    expected = {"user_id", "week1_usage", "week2_usage", "churned"}
    return expected.issubset(set(rows[0].keys()))


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def summarize_user_data(records: list[UserRecord]) -> dict[str, float]:
    if not records:
        raise ValueError("Expected at least one user record.")

    total = len(records)
    churned = [record for record in records if record.churned == 1]
    low_usage = [record for record in records if record.low_usage]
    declining = [record for record in records if record.declining_usage]
    low_usage_churn = [record for record in low_usage if record.churned == 1]
    declining_churn = [record for record in declining if record.churned == 1]

    return {
        "total_users": float(total),
        "overall_churn_rate": len(churned) / total,
        "low_usage_rate": len(low_usage) / total,
        "declining_usage_rate": len(declining) / total,
        "low_usage_churn_rate": len(low_usage_churn) / max(len(low_usage), 1),
        "declining_usage_churn_rate": len(declining_churn) / max(len(declining), 1),
    }


def records_to_table(records: list[UserRecord]) -> str:
    headers = ["user_id", "week1_usage", "week2_usage", "usage_delta", "churned"]
    lines = [" | ".join(headers)]
    for record in records:
        lines.append(
            " | ".join(
                [
                    str(record.user_id),
                    str(record.week1_usage),
                    str(record.week2_usage),
                    str(record.usage_delta),
                    str(record.churned),
                ]
            )
        )
    return "\n".join(lines)
