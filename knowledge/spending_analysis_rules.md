# Spending Analysis Rules

Use these rules when analyzing the sample transaction dataset.

## Scope

- Analyze spending transactions only.
- Exclude credit card payment or payback transactions from spending summaries, category totals, trends, and insights.
- Do not treat credit card payments as income, refunds, savings, or spending.

## Current Dataset Rule

Rows with `Category` equal to `Credit Card Payments` should be excluded from spending analysis.

## Amount Handling

- Spending rows are generally represented as negative `Amount` values.
- Credit card payments may appear as positive `Amount` values and should be filtered out before spending analysis.
- If future data includes refunds, credits, or reimbursements, review them separately instead of automatically mixing them into spending totals.

## Privacy Boundary

Keep this file focused on analysis rules. Do not add transaction dates, amounts, account identifiers, merchant examples, or row-level personal spending details here.
