# AI Data Assistant

A local Streamlit app for exploring personal credit card spending from transaction CSV data and supported PDF statements.

The current project focuses on credit card transactions exported from Empower, Citi, Bank of America, and Amazon Store Card statements from Synchrony. The dataset in `data/` is treated as a local sample dataset and is not committed to the repository.

## What It Does

- Loads user-uploaded transaction CSVs or supported PDF statements.
- Converts Amazon Store Card PDF statement transaction detail into CSV-shaped rows before cleaning.
- Cleans each uploaded source, assigns app-defined categories, adds its source file name, and combines the cleaned rows before analysis.
- Applies user-approved category normalization rules from `knowledge/category_normalization_rules.md`.
- Filters analysis to spending transactions only, excluding credit card payback/payment rows.
- Shows a dashboard with date range, total spend, transaction count, and average transaction size.
- Visualizes month-over-month spending by category.
- Ranks spending categories from highest to lowest spend.
- Lets users select a category to inspect detailed transactions for that category.
- Provides an OpenAI API-backed chat area that answers questions from the cleaned spending transaction context.

## Project Structure

```text
.
├── AGENTS.md
├── README.md
├── knowledge/
│   ├── category_normalization_rules.md
│   ├── category_inference_rules.md
│   ├── dataset_structure.md
│   └── spending_analysis_rules.md
├── pyproject.toml
└── streamlit_app.py
```

The local `data/` folder is expected during development, but transaction CSV files are ignored by git to avoid pushing personal spending data.

## Expected Dataset

The app requires a CSV with these columns:

- `Date`
- `Description`

For transaction value, provide either:

- `Amount`, using signed values, or
- `Debit` and `Credit`, where debit charges are converted to negative spending amounts and credit rows are converted to positive amounts.

These columns are optional. If they are missing, the app creates blank defaults:

- `Account`
- `Category`
- `Tags`

If `Category` is present, the app keeps it as `Original Category` for audit but does not use it
for analysis. The cleaned `Category` is assigned from exact knowledge rules first, then inferred
from `Description`.

The sidebar accepts one or more CSV/PDF uploads.
When multiple files are uploaded, the app combines the cleaned transactions and offers a cleaned combined CSV download.

Current schema notes live in `knowledge/dataset_structure.md`.

## Knowledge Files

- `knowledge/dataset_structure.md`: documents supported CSV and PDF source structures.
- `knowledge/category_normalization_rules.md`: stores exact-match category cleanup rules.
- `knowledge/category_inference_rules.md`: documents how missing categories are inferred.
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

Create a local `.env` file with your OpenAI API key:

```text
OPENAI_API_KEY=your_api_key_here
```

Optional model override:

```text
OPENAI_MODEL=gpt-5.4-mini
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

- The app runs locally, but the chat section sends the current cleaned spending transaction context to the OpenAI API.
- Credit card payment rows are excluded before chat analysis.
- The Streamlit app is the main entry point.
- Keep private CSVs and `.env` files out of git.

## Future Ideas

- Add richer natural-language analysis powered by an LLM.
- Add persistent category rule editing from the UI.
- Add account-level filters for multiple cards/accounts.
- Add budget comparison and recurring-spend detection.
- Add exportable spending summaries.
