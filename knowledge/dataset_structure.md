# Dataset Structure

This note documents only the structure of transaction datasets in `data/`.
It intentionally excludes personal spending details, merchant names, account identifiers,
category values, transaction examples, amount totals, and amount statistics.

## Source Formats

- Source location: `data/`
- Formats: CSV, supported PDF statements
- CSV delimiter: comma
- CSV quote character: double quote
- CSV header row: yes
- Grain: transaction-level, with one row per transaction record

## Known Source Schemas

The app currently supports three CSV export shapes and one PDF statement shape. Each source is normalized into the app's canonical transaction schema before analysis. If multiple files are uploaded, the app normalizes each file separately and then combines the cleaned rows.

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

### Amazon Store Card Statement PDF

Observed file pattern: Amazon Store Card PDF statements from Synchrony

| Source Field | Inferred Type | Canonical Field | Structural Notes |
|---|---|---|---|
| Transaction date | Date, `mm/dd` plus statement year | `Date` | Year is inferred from the billing cycle or statement date. |
| Reference number | Text or identifier | `Reference Number` | Preserved for audit but not used for current analysis. |
| Description | Text | `Description` | Merchant descriptor field from the statement transaction table. |
| Amount | Decimal money value | `Amount` | Statement charges are converted to negative spending amounts; payments and credits are converted to positive amounts. |
| Account ending | Text | `Account` | Used to label the source account when available. |
| Item/detail text | Text | `Statement Detail` | Preserved when the PDF exposes detail text after a transaction row. |

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
| `Source File` | No | App-added source file name used to trace combined uploads back to their input file. |
| `Reference Number` | No | Statement-provided reference identifier when available. |
| `Statement Detail` | No | Extra statement detail text when available from supported PDFs. |

## Structural Observations

- Empower exports provide a signed `Amount` and may include a source `Category`, which the app stores as `Original Category`.
- Citi exports split transaction values into `Debit` and `Credit`; the app converts them into signed `Amount`.
- Bank of America exports use `Posted Date` and `Payee`; the app maps them to `Date` and `Description`.
- Amazon Store Card PDF uploads are parsed into CSV-shaped transaction rows before normalization.
- The app assigns cleaned categories from its own rules for all sources, even when source categories are present.
- Multiple uploaded files are cleaned per source file and combined into one analysis dataset.
- The app excludes credit card payback/payment rows from spending analysis after normalization.

## Recommended Data Contract

Required fields after normalization:

- `Date`
- `Description`
- `Amount`

Supported source value schemas:

- Signed `Amount`
- Separate `Debit` and `Credit`
- PDF statement amount converted into signed `Amount`

Recommended validation checks:

- Confirm source columns can be mapped to `Date`, `Description`, and `Amount`.
- Confirm source date values parse as dates.
- Confirm transaction value columns parse as decimals.
- Track how many categories came from exact knowledge rules versus description inference.
- Track missingness by column.
- Avoid storing raw account identifiers, merchant descriptors, transaction examples, or row-level personal spending details in knowledge files unless explicitly needed and approved.
