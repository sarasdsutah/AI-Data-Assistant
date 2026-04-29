# AI Data Assistant

A local Streamlit app for exploring personal credit card spending from transaction CSV data.

The current project focuses on Costco Anywhere Visa Card by Citi transactions exported from Empower. The dataset in `data/` is treated as a local sample dataset and is not committed to the repository.

## What It Does

- Loads a transaction CSV from the local `data/` folder or from a user upload.
- Applies user-approved category normalization rules from `knowledge/category_normalization_rules.md`.
- Filters analysis to spending transactions only, excluding credit card payback/payment rows.
- Shows a dashboard with date range, total spend, transaction count, and average transaction size.
- Visualizes month-over-month spending by category.
- Ranks spending categories from highest to lowest spend.
- Lets users select a category to inspect detailed transactions for that category.
- Provides a simple chat-style question area for spending summaries, category questions, monthly trends, and data quality checks.

## Project Structure

```text
.
├── AGENTS.md
├── README.md
├── knowledge/
│   ├── category_normalization_rules.md
│   ├── dataset_structure.md
│   └── spending_analysis_rules.md
├── pyproject.toml
└── streamlit_app.py
```

The local `data/` folder is expected during development, but transaction CSV files are ignored by git to avoid pushing personal spending data.

## Expected Dataset

The app expects a CSV with these columns:

- `Date`
- `Account`
- `Description`
- `Category`
- `Tags`
- `Amount`

Current schema notes live in `knowledge/dataset_structure.md`.

## Knowledge Files

- `knowledge/dataset_structure.md`: documents the CSV structure only.
- `knowledge/category_normalization_rules.md`: stores exact-match category cleanup rules.
- `knowledge/spending_analysis_rules.md`: records analysis rules, including spending-only filtering.

Knowledge files should avoid row-level personal spending details, account identifiers, transaction examples, and amount summaries unless explicitly needed and approved.

## Local Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -e .
```

Run the app:

```bash
streamlit run streamlit_app.py
```

Then open:

```text
http://localhost:8501
```

## Development Notes

- The app currently runs locally and does not require an OpenAI API key.
- The chat section is rule-based and uses the cleaned transaction dataframe.
- The Streamlit app is the main entry point.
- Keep private CSVs and `.env` files out of git.

## Future Ideas

- Add richer natural-language analysis powered by an LLM.
- Add persistent category rule editing from the UI.
- Support multiple cards/accounts with account-level filters.
- Add budget comparison and recurring-spend detection.
- Add exportable spending summaries.
