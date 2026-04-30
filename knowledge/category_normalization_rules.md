# Category Normalization Rules

Use these user-approved rules when cleaning or analyzing the sample transaction dataset.
Apply the rules by exact `Description` match unless a future note says otherwise.

This file stores category-cleaning knowledge only. Do not add transaction dates, amounts,
account identifiers, or row-level spending details here.

## Exact-Match Category Rules

| Description | Normalized Category | Rationale |
|---|---|---|
| `Tiger Sugar` | `Coffee & Drinks` | Coffee, tea, or drink spending. |
| `Tea Imports` | `Coffee & Drinks` | Coffee, tea, or drink spending. |
| `State Liquor Store` | `Coffee & Drinks` | Drink spending. |
| `Interview Query Interviewquerca` | `Career Growth` | Career growth-related spending. |
| `Airgarage` | `Parking` | Parking spending. |
| `Ccri By Upma Salt Lake Citut` | `Parking` | Parking spending. |

## Usage Notes

- These rules override the original provider-generated categories.
- Keep category labels consistent across all rows with the same `Description`.
- If a future transaction has a similar but not exact description, review it before applying the rule automatically.
