from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
CATEGORY_RULES_PATH = KNOWLEDGE_DIR / "category_normalization_rules.md"
EXCLUDED_SPENDING_CATEGORIES = {"Credit Card Payments"}
REQUIRED_COLUMNS = ["Date", "Account", "Description", "Category", "Tags", "Amount"]


st.set_page_config(
    page_title="Credit Card Spending Assistant",
    layout="wide",
)


@st.cache_data
def load_category_rules(path: str) -> dict[str, str]:
    rules: dict[str, str] = {}
    rules_path = Path(path)
    if not rules_path.exists():
        return rules

    row_pattern = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|")
    for line in rules_path.read_text(encoding="utf-8").splitlines():
        match = row_pattern.match(line)
        if match:
            description, category = match.groups()
            rules[description] = category
    return rules


@st.cache_data
def read_csv_from_path(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def read_csv_from_upload(uploaded_file) -> pd.DataFrame:
    return pd.read_csv(uploaded_file)


def find_default_csv() -> Path | None:
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    return csv_files[0] if csv_files else None


def prepare_transactions(raw_df: pd.DataFrame, category_rules: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in raw_df.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Missing required column(s): {missing}")

    df = raw_df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    df["Original Category"] = df["Category"].astype(str)
    df["Category"] = df["Description"].map(category_rules).fillna(df["Original Category"])
    df["Category Normalized"] = df["Category"] != df["Original Category"]

    valid_amount = df["Amount"].notna()
    spending_mask = (
        valid_amount
        & (df["Amount"] < 0)
        & ~df["Category"].isin(EXCLUDED_SPENDING_CATEGORIES)
    )
    spending_df = df.loc[spending_mask].copy()
    spending_df["Spend"] = spending_df["Amount"].abs()
    excluded_df = df.loc[~spending_mask].copy()
    return df, spending_df, excluded_df


def filter_spending_by_date(spending_df: pd.DataFrame, start_date: date | None, end_date: date | None) -> pd.DataFrame:
    if spending_df.empty or start_date is None or end_date is None:
        return spending_df

    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    return spending_df[
        spending_df["Date"].notna()
        & (spending_df["Date"] >= start)
        & (spending_df["Date"] <= end)
    ].copy()


def money(value: float) -> str:
    return f"${value:,.2f}"


def date_range_text(spending_df: pd.DataFrame) -> str:
    valid_dates = spending_df["Date"].dropna()
    if valid_dates.empty:
        return "No valid dates"
    return f"{valid_dates.min().date()} to {valid_dates.max().date()}"


def category_summary(spending_df: pd.DataFrame) -> pd.DataFrame:
    if spending_df.empty:
        return pd.DataFrame(columns=["Category", "Transactions", "Spend"])

    summary = (
        spending_df.groupby("Category", dropna=False)
        .agg(Transactions=("Spend", "size"), Spend=("Spend", "sum"))
        .reset_index()
        .sort_values("Spend", ascending=False)
    )
    return summary


def monthly_summary(spending_df: pd.DataFrame) -> pd.DataFrame:
    dated = spending_df.dropna(subset=["Date"]).copy()
    if dated.empty:
        return pd.DataFrame(columns=["Month", "Transactions", "Spend"])

    dated["Month"] = dated["Date"].dt.to_period("M").astype(str)
    return (
        dated.groupby("Month")
        .agg(Transactions=("Spend", "size"), Spend=("Spend", "sum"))
        .reset_index()
        .sort_values("Month")
    )


def monthly_category_summary(spending_df: pd.DataFrame) -> pd.DataFrame:
    dated = spending_df.dropna(subset=["Date"]).copy()
    if dated.empty:
        return pd.DataFrame(columns=["Month", "Category", "Transactions", "Spend"])

    dated["Month"] = dated["Date"].dt.to_period("M").astype(str)
    return (
        dated.groupby(["Month", "Category"], dropna=False)
        .agg(Transactions=("Spend", "size"), Spend=("Spend", "sum"))
        .reset_index()
        .sort_values(["Month", "Spend"], ascending=[True, False])
    )


def build_overview(spending_df: pd.DataFrame) -> str:
    if spending_df.empty:
        return "No spending rows are available."

    categories = category_summary(spending_df)
    top = categories.iloc[0]
    category_count = spending_df["Category"].nunique()
    return (
        f"Spending analysis covers {len(spending_df):,} transactions from {date_range_text(spending_df)}. "
        f"Total spending is {money(spending_df['Spend'].sum())}. "
        f"The dataset includes {category_count:,} spending categories. "
        f"The largest category is {top['Category']} at {money(float(top['Spend']))}."
    )


def build_category_answer(spending_df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    categories = category_summary(spending_df)
    if categories.empty:
        return "No spending categories are available.", categories

    top_rows = categories.head(5)
    top_text = "; ".join(
        f"{row.Category}: {money(float(row.Spend))}"
        for row in top_rows.itertuples(index=False)
    )
    answer = f"Top spending categories are {top_text}."
    return answer, categories


def build_time_answer(spending_df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    months = monthly_summary(spending_df)
    if months.empty:
        return "No valid dates are available for trend analysis.", months

    peak = months.sort_values("Spend", ascending=False).iloc[0]
    answer = (
        f"Monthly spending is available for {len(months)} month(s). "
        f"The highest month in this sample is {peak['Month']} at {money(float(peak['Spend']))}."
    )
    return answer, months


def build_specific_category_answer(spending_df: pd.DataFrame, category: str) -> tuple[str, pd.DataFrame]:
    filtered = spending_df[spending_df["Category"].str.lower() == category.lower()]
    if filtered.empty:
        return f"No spending rows are currently categorized as {category}.", pd.DataFrame()

    answer = (
        f"{category} has {len(filtered):,} transaction(s), totaling {money(filtered['Spend'].sum())}. "
        f"Average transaction size is {money(filtered['Spend'].mean())}."
    )
    summary = (
        filtered.groupby("Description")
        .agg(Transactions=("Spend", "size"), Spend=("Spend", "sum"))
        .reset_index()
        .sort_values("Spend", ascending=False)
    )
    return answer, summary


def build_data_quality_answer(df: pd.DataFrame, spending_df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    normalized = int(df["Category Normalized"].sum())
    invalid_dates = int(df["Date"].isna().sum())
    invalid_amounts = int(df["Amount"].isna().sum())
    answer = (
        f"The loaded file has {len(df):,} total rows. "
        f"{len(spending_df):,} rows are available for spending analysis. "
        f"{normalized:,} rows had categories normalized by the knowledge rules. "
        f"Invalid dates: {invalid_dates:,}. Invalid amounts: {invalid_amounts:,}."
    )
    checks = pd.DataFrame(
        [
            {"Check": "Rows loaded", "Count": len(df)},
            {"Check": "Rows used for spending analysis", "Count": len(spending_df)},
            {"Check": "Rows with normalized categories", "Count": normalized},
            {"Check": "Rows with invalid dates", "Count": invalid_dates},
            {"Check": "Rows with invalid amounts", "Count": invalid_amounts},
        ]
    )
    return answer, checks


def answer_question(question: str, df: pd.DataFrame, spending_df: pd.DataFrame) -> tuple[str, pd.DataFrame | None, str]:
    normalized_question = question.strip().lower()
    if not normalized_question:
        return build_overview(spending_df), category_summary(spending_df), "Category Spend"

    if any(term in normalized_question for term in ["quality", "clean", "normalize", "excluded", "payment", "payback"]):
        answer, table = build_data_quality_answer(df, spending_df)
        return answer, table, "Data Checks"

    if any(term in normalized_question for term in ["month", "monthly", "date", "trend", "time"]):
        answer, table = build_time_answer(spending_df)
        return answer, table, "Monthly Spend"

    category_terms = {
        "Milk Tea/Coffee": ["tea", "coffee", "milk tea", "tiger sugar"],
        "Wine/Alcohol": ["wine", "alcohol", "liquor"],
        "Parking": ["parking", "airgarage", "ccri"],
        "Career Growth": ["career", "interview", "growth"],
    }
    for category, terms in category_terms.items():
        if any(term in normalized_question for term in terms):
            answer, table = build_specific_category_answer(spending_df, category)
            return answer, table, category

    if any(term in normalized_question for term in ["category", "categories", "top", "largest", "biggest"]):
        answer, table = build_category_answer(spending_df)
        return answer, table, "Category Spend"

    return build_overview(spending_df), category_summary(spending_df), "Category Spend"


def render_metric_row(spending_df: pd.DataFrame) -> None:
    total_spend = spending_df["Spend"].sum() if not spending_df.empty else 0.0
    avg_transaction = spending_df["Spend"].mean() if not spending_df.empty else 0.0

    st.markdown(
        f"""
        <section class="date-range-section">
          <div class="date-range-label">Date Range</div>
          <div class="date-range-value">{date_range_text(spending_df)}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Spend", money(total_spend))
    col2.metric("Transactions", f"{len(spending_df):,}")
    col3.metric("Avg Transaction", money(avg_transaction))


def render_spending_date_filter(spending_df: pd.DataFrame) -> pd.DataFrame:
    valid_dates = spending_df["Date"].dropna()
    if valid_dates.empty:
        return spending_df

    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()
    selected_range = st.date_input(
        "Filter spending date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="spending_summary_date_range",
    )
    if not isinstance(selected_range, tuple) or len(selected_range) != 2:
        st.stop()

    selected_start, selected_end = selected_range
    if not isinstance(selected_start, date) or not isinstance(selected_end, date):
        st.stop()
    if selected_start > selected_end:
        st.error("Start date must be before or equal to end date.")
        st.stop()

    return filter_spending_by_date(spending_df, selected_start, selected_end)


def render_global_styles() -> None:
    st.markdown(
        """
        <style>
          .date-range-section {
            padding: 0 0 1rem 0;
            margin: 0.25rem 0 1.25rem 0;
            border-bottom: 1px solid rgba(49, 51, 63, 0.18);
          }
          .date-range-label {
            font-size: 1.15rem;
            font-weight: 700;
            line-height: 1.2;
            margin: 0 0 0.2rem 0;
          }
          .date-range-value {
            font-size: 1.75rem;
            font-weight: 650;
            line-height: 1.15;
            margin: 0;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_table(table: pd.DataFrame | None) -> None:
    if table is None or table.empty:
        return

    display = table.copy()
    if "Spend" in display.columns:
        display["Spend"] = display["Spend"].map(money)
    st.dataframe(display, hide_index=True, use_container_width=True)


def render_summary_table(table: pd.DataFrame | None, spending_df: pd.DataFrame) -> None:
    if table is None or table.empty:
        return
    if "Category" not in table.columns or "Spend" not in table.columns:
        render_table(table)
        return

    display = table.sort_values("Spend", ascending=False).reset_index(drop=True)
    st.caption("Select a category row to view its transactions.")
    selection = st.dataframe(
        display,
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key="category_summary_table",
        column_config={
            "Spend": st.column_config.NumberColumn("Spend", format="$%.2f"),
        },
    )

    selected_rows = selection.selection.rows if selection.selection else []
    if not selected_rows:
        return

    selected_category = str(display.iloc[selected_rows[0]]["Category"])
    details = spending_df[spending_df["Category"] == selected_category].copy()
    if details.empty:
        return

    details = details.sort_values(["Date", "Spend"], ascending=[False, False])
    details_display = details[["Date", "Description", "Category", "Spend"]].copy()
    details_display["Date"] = details_display["Date"].dt.date

    st.markdown(f"**Transactions: {selected_category}**")
    st.dataframe(
        details_display,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Spend": st.column_config.NumberColumn("Spend", format="$%.2f"),
        },
    )


def render_chart(table: pd.DataFrame | None, title: str) -> None:
    if table is None or table.empty or "Spend" not in table.columns:
        return

    chart_table = table.copy()
    label_column = "Category" if "Category" in chart_table.columns else "Month"
    if label_column not in chart_table.columns:
        return

    if label_column == "Category":
        chart_table = chart_table.sort_values("Spend", ascending=False)
        chart = (
            alt.Chart(chart_table)
            .mark_bar()
            .encode(
                x=alt.X(
                    "Category:N",
                    title="Category",
                    sort=alt.SortField(field="Spend", order="descending"),
                ),
                y=alt.Y("Spend:Q", title="Spend"),
                tooltip=[
                    alt.Tooltip("Category:N", title="Category"),
                    alt.Tooltip("Spend:Q", title="Spend", format="$,.2f"),
                    alt.Tooltip("Transactions:Q", title="Transactions"),
                ],
            )
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)
        return

    st.bar_chart(
        chart_table.set_index(label_column)["Spend"],
        use_container_width=True,
    )


def render_monthly_category_chart(spending_df: pd.DataFrame) -> None:
    monthly_category = monthly_category_summary(spending_df)
    if monthly_category.empty:
        return

    month_order = sorted(monthly_category["Month"].unique())
    chart = (
        alt.Chart(monthly_category)
        .mark_bar()
        .encode(
            x=alt.X("Month:N", title="Month", sort=month_order),
            y=alt.Y("Spend:Q", title="Spend"),
            color=alt.Color("Category:N", title="Category"),
            tooltip=[
                alt.Tooltip("Month:N", title="Month"),
                alt.Tooltip("Category:N", title="Category"),
                alt.Tooltip("Spend:Q", title="Spend", format="$,.2f"),
                alt.Tooltip("Transactions:Q", title="Transactions"),
            ],
        )
        .properties(height=480)
        .configure_legend(orient="bottom", columns=4)
    )

    st.subheader("Month Over Month Spending")
    st.caption("Category colors use the cleaned spending categories.")
    st.altair_chart(chart, use_container_width=True)


def render_monthly_category_comparison_chart(spending_df: pd.DataFrame) -> None:
    monthly_category = monthly_category_summary(spending_df)
    if monthly_category.empty:
        return

    category_order = (
        monthly_category.groupby("Category")["Spend"]
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )
    month_order = sorted(monthly_category["Month"].unique())

    chart = (
        alt.Chart(monthly_category)
        .mark_bar()
        .encode(
            x=alt.X(
                "Category:N",
                title="Category",
                sort=category_order,
                axis=alt.Axis(labelAngle=-45),
            ),
            xOffset=alt.XOffset("Month:N", sort=month_order),
            y=alt.Y("Spend:Q", title="Spend"),
            color=alt.Color("Month:N", title="Month", sort=month_order),
            tooltip=[
                alt.Tooltip("Category:N", title="Category"),
                alt.Tooltip("Month:N", title="Month"),
                alt.Tooltip("Spend:Q", title="Spend", format="$,.2f"),
                alt.Tooltip("Transactions:Q", title="Transactions"),
            ],
        )
        .properties(height=430)
        .configure_legend(orient="bottom")
    )

    st.subheader("Category Spend by Month")
    st.caption("Categories are sorted by total spend, with monthly bars shown side by side.")
    st.altair_chart(chart, use_container_width=True)


def main() -> None:
    render_global_styles()
    st.title("Credit Card Spending Assistant")

    category_rules = load_category_rules(str(CATEGORY_RULES_PATH))
    default_csv = find_default_csv()

    with st.sidebar:
        st.header("Data")
        uploaded_file = st.file_uploader("CSV file", type=["csv"])
        show_rows = st.toggle("Show cleaned rows", value=False)

        if uploaded_file is None and default_csv:
            st.success(f"Loaded sample: {default_csv.name}")
        elif uploaded_file is not None:
            st.success(f"Loaded upload: {uploaded_file.name}")
        else:
            st.error("No CSV found in data/.")

        st.divider()
        st.header("Rules")
        st.write(f"Category rules: {len(category_rules)}")
        st.write("Analysis view: spending transactions only")

    if uploaded_file is not None:
        raw_df = read_csv_from_upload(uploaded_file)
        data_name = uploaded_file.name
    elif default_csv is not None:
        raw_df = read_csv_from_path(str(default_csv))
        data_name = default_csv.name
    else:
        st.stop()

    try:
        df, spending_df, excluded_df = prepare_transactions(raw_df, category_rules)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    render_metric_row(spending_df)
    render_monthly_category_chart(spending_df)
    render_monthly_category_comparison_chart(spending_df)

    left, right = st.columns([0.9, 1.1], gap="large")

    with left:
        st.subheader("Spending Summary")
        filtered_spending_df = render_spending_date_filter(spending_df)

    data_signature = f"{data_name}:{len(df)}:{filtered_spending_df['Spend'].sum() if not filtered_spending_df.empty else 0}:{date_range_text(filtered_spending_df)}"

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Ask about spending categories, monthly trends, parking, milk tea/coffee, wine/alcohol, or data cleanup.",
            }
        ]
    if st.session_state.get("data_signature") != data_signature:
        st.session_state.data_signature = data_signature
        answer, table, title = answer_question("", df, filtered_spending_df)
        st.session_state.latest_answer = {"answer": answer, "table": table, "title": title}

    with left:
        latest = st.session_state.latest_answer
        st.write(latest["answer"])
        render_chart(latest["table"], latest["title"])
        render_summary_table(latest["table"], filtered_spending_df)

    with right:
        st.subheader("Chat")
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        question = st.chat_input("Ask a spending question")
        if question:
            st.session_state.messages.append({"role": "user", "content": question})
            answer, table, title = answer_question(question, df, filtered_spending_df)
            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.session_state.latest_answer = {"answer": answer, "table": table, "title": title}
            st.rerun()

    if show_rows:
        st.subheader("Cleaned Spending Rows")
        cleaned_display = filtered_spending_df[
            ["Date", "Description", "Category", "Original Category", "Category Normalized", "Spend"]
        ].copy()
        cleaned_display["Date"] = cleaned_display["Date"].dt.date
        cleaned_display["Spend"] = cleaned_display["Spend"].map(money)
        st.dataframe(cleaned_display, hide_index=True, use_container_width=True)

    st.caption(f"Dataset: {data_name}")


if __name__ == "__main__":
    main()
