# Dataset Structure

This note documents only the structure of transaction datasets in `data/`.
It intentionally excludes personal spending details, merchant names, account identifiers,
category values, transaction examples, amount totals, and amount statistics.

## Source Format

- Source location: `data/`
- Format: CSV
- Delimiter: comma
- Quote character: double quote
- Header row: yes
- Grain: transaction-level, with one row per transaction record

## Known Source Schemas

The app currently supports three sample export shapes. Each source is normalized into the app's canonical transaction schema before analysis. If multiple CSV files are uploaded, the app normalizes each file separately and then combines the cleaned rows.

### Empower Export

Observed file pattern: `empower credit transaction.csv`

| Position | Source Column | Inferred Type | Canonical Field | Structural Notes |
|---:|---|---|---|---|
| 1 | `Date` | Date, `yyyy-mm-dd` | `Date` | Transaction date field. |
| 2 | `Account` | Text | `Account` | Account-level field. |
| 3 | `Description` | Text | `Description` | Transaction descriptor field. |
| 4 | `Category` | Text | `Category` | Provider-supplied category field. |
| 5 | `Tags` | Text | `Tags` | Optional tag field; may be blank. |
| 6 | `Amount` | Signed decimal number | `Amount` | Signed transaction amount field. |

### Citi Credit Card Export

Observed file pattern: `citi credit card transaction.CSV`

| Position | Source Column | Inferred Type | Canonical Field | Structural Notes |
|---:|---|---|---|---|
| 1 | `Status` | Text | Not used for current analysis | Transaction posting status. |
| 2 | `Date` | Date, `mm/dd/yyyy` | `Date` | Transaction date field. |
| 3 | `Description` | Text | `Description` | Transaction descriptor field. |
| 4 | `Debit` | Decimal number | `Amount` | Debit values are converted to negative spending amounts. |
| 5 | `Credit` | Decimal number | `Amount` | Credit values are converted to positive non-spending amounts. |
| 6 | `Member Name` | Text | `Account` | Used as an account-like field when `Account` is absent. |

### Bank Of America Credit Card Export

Observed file pattern: `bank of america credit transaction.csv`

| Position | Source Column | Inferred Type | Canonical Field | Structural Notes |
|---:|---|---|---|---|
| 1 | `Posted Date` | Date, `mm/dd/yyyy` | `Date` | Posted transaction date. |
| 2 | `Reference Number` | Text or identifier | Not used for current analysis | Transaction reference identifier. |
| 3 | `Payee` | Text | `Description` | Transaction descriptor field. |
| 4 | `Address` | Text | Not used for current analysis | Optional merchant/location field. |
| 5 | `Amount` | Signed decimal number | `Amount` | Signed transaction amount field. |

## Canonical App Schema

The app normalizes supported files into these canonical fields:

| Canonical Field | Required | Description |
|---|---:|---|
| `Date` | Yes | Transaction date after parsing source date formats. |
| `Description` | Yes | Transaction descriptor used for category inference. |
| `Amount` | Yes | Signed transaction amount. Spending rows are negative; credits or payments are positive. |
| `Account` | No | Account-like text field when available. |
| `Category` | No | App-assigned category from exact knowledge rules or description inference. |
| `Original Category` | No | Source category preserved for audit when present. |
| `Tags` | No | Optional text tag field when available. |
| `Source File` | No | App-added source file name used to trace combined uploads back to their input CSV. |

## Structural Observations

- Empower exports provide a signed `Amount` and may include a source `Category`, which the app stores as `Original Category`.
- Citi exports split transaction values into `Debit` and `Credit`; the app converts them into signed `Amount`.
- Bank of America exports use `Posted Date` and `Payee`; the app maps them to `Date` and `Description`.
- The app assigns cleaned categories from its own rules for all sources, even when source categories are present.
- Multiple uploaded CSV files are cleaned per source file and combined into one analysis dataset.
- The app excludes credit card payback/payment rows from spending analysis after normalization.

## Recommended Data Contract

Required fields after normalization:

- `Date`
- `Description`
- `Amount`

Supported source value schemas:

- Signed `Amount`
- Separate `Debit` and `Credit`

Recommended validation checks:

- Confirm source columns can be mapped to `Date`, `Description`, and `Amount`.
- Confirm source date values parse as dates.
- Confirm transaction value columns parse as decimals.
- Track how many categories came from exact knowledge rules versus description inference.
- Track missingness by column.
- Avoid storing raw account identifiers, merchant descriptors, transaction examples, or row-level personal spending details in knowledge files unless explicitly needed and approved.
