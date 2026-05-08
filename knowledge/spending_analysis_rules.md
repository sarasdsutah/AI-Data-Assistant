# Spending Analysis Rules

Use these rules when analyzing the sample transaction dataset.

## Scope

- Analyze spending transactions only.
- Exclude credit card payment or payback transactions from spending summaries, category totals, trends, and insights.
- Do not treat credit card payments as income, refunds, savings, or spending.
- Exclude investment transfers and internal account transfers from spending summaries, category
  totals, trends, and insights.
- Exclude tax payments from spending summaries, category totals, trends, and insights.

## Current Dataset Rule

Rows should be excluded from spending analysis when the cleaned category, original provider
category, or payment-like transaction description identifies the row as a credit card payment.
Rows should also be excluded when the cleaned category is `Investments`, `Internal Transfers`, or
`Taxes`.

## User-Approved Exclusion Rules

- Treat Betterment transactions as `Investments`, and exclude them from spending analysis.
- Treat My529 transactions as `Investments`, and exclude them from spending analysis.
- Treat Bank of America, Venmo, and Discover Bank transactions as `Internal Transfers`, and exclude
  them from spending analysis.
- Treat tax transactions as `Taxes`, and exclude them from spending analysis.

## Amount Handling

- Spending rows are generally represented as negative `Amount` values.
- Credit card payments may appear as positive `Amount` values and should be filtered out before spending analysis.
- If future data includes refunds, credits, or reimbursements, review them separately instead of automatically mixing them into spending totals.

## Purchase Detail Questions

- When a user asks what they purchased from Amazon, inspect the cleaned table's `Statement Detail` column in addition to `Description`, `Date`, `Category`, and `Spend`.
- For supported Amazon Store Card PDF statements, `Description` may identify the transaction row while `Statement Detail` can contain the purchase-level detail exposed by the statement.
- If `Statement Detail` is blank or unavailable for an Amazon transaction, say that the purchase detail is not available in the uploaded data instead of guessing item names.
- Use `Spend` for dollar totals and use `Statement Detail` only as descriptive evidence about what was purchased.

## Merchant Interpretation Rules

- If `Description` contains `Booking BV`, interpret it as a Booking.com or Booking Holdings travel purchase.
- Treat `Booking BV` as most likely lodging or car rental unless other uploaded data explicitly shows a flight or airline purchase.
- Do not describe `Booking BV` transactions as flight purchases based only on the merchant name.

## Privacy Boundary

Keep this file focused on analysis rules. Do not add transaction dates, amounts, account identifiers, merchant examples, or row-level personal spending details here.
