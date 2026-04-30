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
REQUIRED_COLUMNS = ["Date", "Description"]
OPTIONAL_TEXT_COLUMNS = ["Account", "Category", "Tags"]
SOURCE_FILE_COLUMN = "Source File"
DEFAULT_CATEGORY = "Other"
INFERRED_CATEGORY_RULES = [
    ("Credit Card Payments", ["autopay", "auto-pmt", "payment", "pmt"]),
    ("Parking", ["parking", "garage", "ccri", "honk"]),
    ("Gasoline/Fuel", ["gas", "fuel", "gasoline", "holiday", "pilot_"]),
    ("Groceries", ["grocery", "groceries", "market", "supermarket", "costco", "walmart", "wal-mart", "target", "dollar tree", "trader joe", "smith", "ocean mart", "harmons"]),
    ("Coffee & Drinks", ["coffee", "tea", "milk tea", "boba", "beans & brews", "tiger sugar", "starbucks", "liquor", "wine", "alcohol"]),
    ("Subscriptions", ["apple.com/bill", "prime", "medium.com", "ring.com", "openai", "chatgpt", "disney plus", "disney+", "disneyplus", "youtube premium", "youtubepremium", "uber one", "dashpass", "door dash pass", "doordash pass", "grubhub+", "instacart+"]),
    ("Food Delivery", ["uber eats", "ubereats", "doordash", "door dash", "grubhub", "postmates", "seamless", "delivery.com"]),
    ("Restaurants", ["restaurant", "food", "cafe", "bistro", "sushi", "bbq", "taco", "kitchen", "bakery", "tapas", "greek", "familymart", "tst*", "spitz", "sawadee", "cheesecake", "wiseguys", "concessions", "chick-fil-a", "cluckers", "mcdonald", "indochine", "halalepenos", "grill bar", "ramen"]),
    ("Online Services", ["online", "software", "cloud", "hosting", "domain", "sourcegraph", "namecheap", "patreon", "digitalocean"]),
    ("Charitable Giving", ["charity", "charitable", "rescue committee"]),
    ("Housing/Rent", ["rentapplication", "rent application"]),
    ("Career Growth", ["interview", "career", "course", "computing"]),
    ("Entertainment", ["video", "comedy", "theater", "movie", "youtube", "state parks", "national park", "disney"]),
    ("Education", ["school", "tuition"]),
    ("Insurance", ["insurance", "lemonade", "trawick"]),
    ("Home Improvement", ["home depot", "heating", "air"]),
    ("Personal Care", ["pharmacy", "spa", "personal care", "walgreens", "hammam", "camera shy"]),
    ("Clothing/Shoes", ["clothing", "shoes", "nike", "j.crew", "j. crew", "gap", "carter", "outlet", "nordstrom", "marshalls"]),
    ("Child/Dependent", ["child", "dependent", "kids", "care.com", "dancing", "thanksgiving point"]),
    ("Travel", ["travel", "booking", "hotel", "airline", "rent-a-car"]),
    ("Automotive", ["automotive", "toll", "udot", "tire", "fab freddy"]),
    ("Amazon Shopping", ["amazon", "amzn"]),
    ("Other General Merchandise", ["dollar"]),
]


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
    csv_files = find_csv_files()
    return csv_files[0] if csv_files else None


def find_csv_files() -> list[Path]:
    return sorted(path for path in DATA_DIR.glob("*") if path.is_file() and path.suffix.lower() == ".csv")


def prepare_transaction_sources(
    sources: list[tuple[str, pd.DataFrame]],
    category_rules: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cleaned_frames: list[pd.DataFrame] = []
    spending_frames: list[pd.DataFrame] = []
    excluded_frames: list[pd.DataFrame] = []

    for source_name, raw_source_df in sources:
        source_df = raw_source_df.copy()
        source_df[SOURCE_FILE_COLUMN] = source_name
        try:
            df, spending_df, excluded_df = prepare_transactions(source_df, category_rules)
        except ValueError as exc:
            raise ValueError(f"{source_name}: {exc}") from exc

        cleaned_frames.append(df)
        spending_frames.append(spending_df)
        excluded_frames.append(excluded_df)

    combined_df = concat_frames(cleaned_frames)
    combined_spending_df = concat_frames(spending_frames)
    combined_excluded_df = concat_frames(excluded_frames)
    for frame in [combined_df, combined_spending_df, combined_excluded_df]:
        frame.attrs["source_count"] = len(sources)

    return combined_df, combined_spending_df, combined_excluded_df


def concat_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def count_source_files(df: pd.DataFrame) -> int:
    if "source_count" in df.attrs:
        return int(df.attrs["source_count"])
    if SOURCE_FILE_COLUMN in df.columns:
        return int(df[SOURCE_FILE_COLUMN].nunique())
    return 1


def prepare_transactions(raw_df: pd.DataFrame, category_rules: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = normalize_transaction_schema(raw_df)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if "Amount" not in df.columns:
        missing_columns.append("Amount or Debit/Credit")
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Missing required column(s): {missing}")

    for column in OPTIONAL_TEXT_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    df["Description"] = df["Description"].fillna("").astype(str)
    df["Original Category"] = df["Category"].fillna("").astype(str).str.strip()

    inferred_categories = df["Description"].apply(infer_category)
    exact_rule_categories = df["Description"].map(category_rules)
    df["Category"] = exact_rule_categories.fillna(inferred_categories)
    df["Category"] = df["Category"].fillna(DEFAULT_CATEGORY).replace("", DEFAULT_CATEGORY)
    df["Category Normalized"] = (
        (df["Original Category"] != "")
        & (df["Category"] != df["Original Category"])
    )
    df["Category Inferred"] = exact_rule_categories.isna()
    df["Category Source"] = "inferred"
    df.loc[exact_rule_categories.notna(), "Category Source"] = "knowledge rule"

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


def normalize_transaction_schema(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.copy()
    df.columns = [str(column).strip() for column in df.columns]

    if "Date" not in df.columns and "Posted Date" in df.columns:
        df["Date"] = df["Posted Date"]

    if "Description" not in df.columns and "Payee" in df.columns:
        df["Description"] = df["Payee"]

    if "Amount" not in df.columns and {"Debit", "Credit"}.issubset(df.columns):
        debit = parse_money_series(df["Debit"]).fillna(0)
        credit = parse_money_series(df["Credit"]).fillna(0)
        df["Amount"] = credit - debit
    elif "Amount" in df.columns:
        df["Amount"] = parse_money_series(df["Amount"])

    if "Account" not in df.columns and "Member Name" in df.columns:
        df["Account"] = df["Member Name"]

    return df


def parse_money_series(series: pd.Series) -> pd.Series:
    cleaned = (
        series.fillna("")
        .astype(str)
        .str.strip()
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    )
    return pd.to_numeric(cleaned.replace("", pd.NA), errors="coerce")


def infer_category(description: object) -> str:
    text = str(description).strip().lower()
    if not text:
        return DEFAULT_CATEGORY

    for category, keywords in INFERRED_CATEGORY_RULES:
        if any(keyword in text for keyword in keywords):
            return category
    return DEFAULT_CATEGORY


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
    exact_rules = int((df["Category Source"] == "knowledge rule").sum())
    inferred = int(df["Category Inferred"].sum())
    recategorized = int(df["Category Normalized"].sum())
    invalid_dates = int(df["Date"].isna().sum())
    invalid_amounts = int(df["Amount"].isna().sum())
    source_count = count_source_files(df)
    answer = (
        f"The loaded dataset has {len(df):,} total rows across {source_count:,} source file(s). "
        f"{len(spending_df):,} rows are available for spending analysis. "
        f"{exact_rules:,} rows used exact knowledge rules. "
        f"{inferred:,} rows used inferred categories. "
        f"{recategorized:,} provider categories were replaced by app categories. "
        f"Invalid dates: {invalid_dates:,}. Invalid amounts: {invalid_amounts:,}."
    )
    checks = pd.DataFrame(
        [
            {"Check": "Source files", "Count": source_count},
            {"Check": "Rows loaded", "Count": len(df)},
            {"Check": "Rows used for spending analysis", "Count": len(spending_df)},
            {"Check": "Rows using exact knowledge rules", "Count": exact_rules},
            {"Check": "Rows using inferred categories", "Count": inferred},
            {"Check": "Provider categories replaced", "Count": recategorized},
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

    if any(term in normalized_question for term in ["subscription", "subscriptions", "apple.com/bill", "prime", "medium", "ring", "openai", "chatgpt", "disney plus", "disney+", "youtube premium"]):
        answer, table = build_specific_category_answer(spending_df, "Subscriptions")
        return answer, table, "Subscriptions"

    if any(term in normalized_question for term in ["month", "monthly", "date", "trend", "time"]):
        answer, table = build_time_answer(spending_df)
        return answer, table, "Monthly Spend"

    category_terms = {
        "Coffee & Drinks": ["tea", "coffee", "milk tea", "tiger sugar", "wine", "alcohol", "liquor"],
        "Food Delivery": ["delivery", "food delivery", "uber eats", "ubereats", "doordash", "door dash", "grubhub", "postmates", "seamless"],
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


def transaction_detail_display(details: pd.DataFrame) -> pd.DataFrame:
    detail_columns = ["Date", SOURCE_FILE_COLUMN, "Description", "Category", "Spend"]
    detail_columns = [column for column in detail_columns if column in details.columns]
    display = details[detail_columns].copy()
    if "Date" in display.columns:
        display["Date"] = display["Date"].dt.date
    return display


def render_transaction_detail_table(details: pd.DataFrame) -> None:
    st.dataframe(
        transaction_detail_display(details),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Spend": st.column_config.NumberColumn("Spend", format="$%.2f"),
        },
    )


def latest_month_tabs(details: pd.DataFrame, count: int = 3) -> list[tuple[str, pd.DataFrame]]:
    dated = details.dropna(subset=["Date"]).copy()
    if dated.empty:
        return []

    dated["Transaction Month"] = dated["Date"].dt.to_period("M")
    latest_months = sorted(dated["Transaction Month"].unique(), reverse=True)[:count]
    tabs: list[tuple[str, pd.DataFrame]] = []
    for month in latest_months:
        month_details = dated[dated["Transaction Month"] == month].drop(columns=["Transaction Month"])
        label = month.to_timestamp().strftime("%B %Y")
        tabs.append((label, month_details))
    return tabs


def latest_month_spending_tabs(spending_df: pd.DataFrame, count: int = 3) -> list[tuple[str, pd.DataFrame]]:
    dated = spending_df.dropna(subset=["Date"]).copy()
    if dated.empty:
        return []

    dated["Transaction Month"] = dated["Date"].dt.to_period("M")
    latest_months = sorted(dated["Transaction Month"].unique(), reverse=True)[:count]
    tabs: list[tuple[str, pd.DataFrame]] = []
    for month in latest_months:
        month_spending = dated[dated["Transaction Month"] == month].drop(columns=["Transaction Month"])
        label = month.to_timestamp().strftime("%B %Y")
        tabs.append((label, month_spending))
    return tabs


def render_category_summary_selection(display: pd.DataFrame, key: str) -> str | None:
    selection = st.dataframe(
        display,
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key=key,
        column_config={
            "Spend": st.column_config.NumberColumn("Spend", format="$%.2f"),
        },
    )

    selected_rows = selection.selection.rows if selection.selection else []
    if not selected_rows:
        return None
    return str(display.iloc[selected_rows[0]]["Category"])


def render_summary_table(table: pd.DataFrame | None, spending_df: pd.DataFrame) -> None:
    if table is None or table.empty:
        return
    if "Category" not in table.columns or "Spend" not in table.columns:
        render_table(table)
        return

    display = table.sort_values("Spend", ascending=False).reset_index(drop=True)
    st.caption("Select a category row to view its transactions.")
    monthly_summary_tabs = latest_month_spending_tabs(spending_df)
    tab_specs = [("All", display)] + [
        (label, category_summary(month_spending))
        for label, month_spending in monthly_summary_tabs
    ]
    tabs = st.tabs([label for label, _ in tab_specs])

    selected_category = None
    for index, (tab, (label, summary)) in enumerate(zip(tabs, tab_specs)):
        with tab:
            if summary.empty:
                st.caption("No spending rows are available for this period.")
                continue
            selected = render_category_summary_selection(
                summary.sort_values("Spend", ascending=False).reset_index(drop=True),
                f"category_summary_table_{index}",
            )
            if selected is not None:
                selected_category = selected

    if selected_category is None:
        return

    details = spending_df[spending_df["Category"] == selected_category].copy()
    if details.empty:
        return

    details = details.sort_values(["Date", "Spend"], ascending=[False, False])
    st.markdown(f"**Transactions: {selected_category}**")
    monthly_tabs = latest_month_tabs(details)
    tab_labels = ["All"] + [label for label, _ in monthly_tabs]
    tabs = st.tabs(tab_labels)
    with tabs[0]:
        render_transaction_detail_table(details)

    for tab, (label, month_details) in zip(tabs[1:], monthly_tabs):
        with tab:
            st.markdown(f"**{label}**")
            render_transaction_detail_table(month_details)


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


def format_source_names(source_names: list[str]) -> str:
    if not source_names:
        return "No dataset"
    if len(source_names) == 1:
        return source_names[0]

    preview = ", ".join(source_names[:3])
    if len(source_names) > 3:
        preview = f"{preview}, +{len(source_names) - 3} more"
    return f"{len(source_names)} files: {preview}"


def make_unique_source_names(source_names: list[str]) -> list[str]:
    totals: dict[str, int] = {}
    for source_name in source_names:
        totals[source_name] = totals.get(source_name, 0) + 1

    seen: dict[str, int] = {}
    unique_names: list[str] = []
    for source_name in source_names:
        seen[source_name] = seen.get(source_name, 0) + 1
        if totals[source_name] == 1:
            unique_names.append(source_name)
        else:
            unique_names.append(f"{source_name} ({seen[source_name]})")
    return unique_names


def main() -> None:
    render_global_styles()
    st.title("Credit Card Spending Assistant")

    category_rules = load_category_rules(str(CATEGORY_RULES_PATH))
    local_csv_files = find_csv_files()

    with st.sidebar:
        st.header("Data")
        uploaded_files = st.file_uploader("CSV files", type=["csv"], accept_multiple_files=True)
        if uploaded_files is None:
            uploaded_files = []
        has_uploaded_files = len(uploaded_files) > 0
        selected_local_csv = None
        if not has_uploaded_files and local_csv_files:
            csv_names = [path.name for path in local_csv_files]
            selected_name = st.selectbox("Sample CSV", csv_names)
            selected_local_csv = local_csv_files[csv_names.index(selected_name)]
        show_rows = st.toggle("Show cleaned rows", value=False)

        if has_uploaded_files:
            st.success(f"Loaded {len(uploaded_files)} upload(s).")
        elif selected_local_csv:
            st.success(f"Loaded sample: {selected_local_csv.name}")
        else:
            st.error("No CSV found in data/.")

    try:
        if uploaded_files:
            uploaded_source_names = make_unique_source_names(
                [uploaded_file.name for uploaded_file in uploaded_files]
            )
            transaction_sources = [
                (source_name, read_csv_from_upload(uploaded_file))
                for source_name, uploaded_file in zip(uploaded_source_names, uploaded_files)
            ]
            data_name = format_source_names(uploaded_source_names)
        elif selected_local_csv is not None:
            transaction_sources = [(selected_local_csv.name, read_csv_from_path(str(selected_local_csv)))]
            data_name = selected_local_csv.name
        else:
            st.stop()

        df, spending_df, excluded_df = prepare_transaction_sources(transaction_sources, category_rules)
    except (ValueError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        st.error(str(exc))
        st.stop()

    source_count = count_source_files(df)
    with st.sidebar:
        st.download_button(
            "Download cleaned combined CSV" if source_count > 1 else "Download cleaned CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="cleaned_combined_transactions.csv" if source_count > 1 else "cleaned_transactions.csv",
            mime="text/csv",
        )

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
                "content": "Ask about spending categories, monthly trends, subscriptions, food delivery, parking, coffee/drinks, or data cleanup.",
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
        cleaned_columns = [
            "Date",
            SOURCE_FILE_COLUMN,
            "Description",
            "Category",
            "Category Source",
            "Original Category",
            "Category Normalized",
            "Spend",
        ]
        cleaned_columns = [column for column in cleaned_columns if column in filtered_spending_df.columns]
        cleaned_display = filtered_spending_df[cleaned_columns].copy()
        cleaned_display["Date"] = cleaned_display["Date"].dt.date
        cleaned_display["Spend"] = cleaned_display["Spend"].map(money)
        st.dataframe(cleaned_display, hide_index=True, use_container_width=True)

    st.caption(f"Dataset: {data_name}")


if __name__ == "__main__":
    main()
