# Dataset Structure

This note documents only the structure of the sample transaction dataset in `data/`.
It intentionally excludes personal spending details, merchant names, account identifiers,
category values, transaction examples, amount totals, and amount statistics.

## Source Format

- Source location: `data/`
- Files analyzed: 1 sample CSV file
- Format: CSV
- Delimiter: comma
- Quote character: double quote
- Header row: yes
- Data rows: 108
- Columns: 6

## Column Schema

| Position | Column | Inferred Type | Completeness | Structural Notes |
|---:|---|---|---:|---|
| 1 | `Date` | Date, `yyyy-mm-dd` | 108 / 108 populated | Transaction date field. |
| 2 | `Account` | Categorical text | 108 / 108 populated | Account-level field. The sample contains one distinct non-empty account value, which is intentionally omitted here. |
| 3 | `Description` | Free text | 108 / 108 populated | Transaction descriptor field. Actual values are intentionally omitted. |
| 4 | `Category` | Categorical text | 108 / 108 populated | Provider-supplied transaction category field. Actual category labels are intentionally omitted. |
| 5 | `Tags` | Empty text field | 0 / 108 populated | Present in the schema but empty in the sample. |
| 6 | `Amount` | Signed decimal number | 108 / 108 populated | Numeric transaction amount field. Both positive and negative signs are present; magnitudes and summaries are intentionally omitted. |

## Structural Observations

- The dataset is transaction-level: each row appears to represent one transaction record.
- The schema is flat and narrow, with no nested fields.
- `Date` should be parsed as a date type before time-based analysis.
- `Amount` should be parsed as a decimal numeric type.
- `Account`, `Description`, `Category`, and `Tags` should be treated as text fields before any downstream cleaning.
- `Tags` currently has no populated values, so it should not be used for modeling or filtering until populated.

## Recommended Data Contract

Required columns for the current sample structure:

- `Date`
- `Account`
- `Description`
- `Category`
- `Tags`
- `Amount`

Recommended validation checks:

- Confirm all required columns exist.
- Confirm `Date` values parse as `yyyy-mm-dd`.
- Confirm `Amount` values parse as signed decimals.
- Track missingness by column.
- Avoid storing raw account identifiers, merchant descriptors, or transaction examples in knowledge files unless explicitly needed and approved.
