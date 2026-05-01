# Category Inference Rules

Use these rules when cleaning transaction CSVs or supported PDF statements, including files that
already contain a source `Category` column.

## Behavior

- Exact-match rules in `category_normalization_rules.md` run first.
- If no exact rule applies, the app infers a category from `Description`.
- If no inference rule matches, the category is set to `Other`.
- Existing source categories are preserved only in `Original Category` for audit. They do not
  determine the cleaned `Category`.

## Inferred Category Families

The current app uses keyword patterns for these category families:

- `Credit Card Payments`
- `Parking`
- `Gasoline/Fuel`
- `Subscriptions`
- `Amazon Shopping`
- `Groceries`
- `Coffee & Drinks`
- `Food Delivery`
- `Restaurants`
- `Online Services`
- `Charitable Giving`
- `Housing/Rent`
- `Career Growth`
- `Entertainment`
- `Education`
- `Insurance`
- `Home Improvement`
- `Personal Care`
- `Clothing/Shoes`
- `Child/Dependent`
- `Travel`
- `Automotive`
- `Amazon Shopping`
- `Other General Merchandise`
- `Other`

`Food Delivery` is intended for real delivery orders from delivery apps, such as Uber Eats,
DoorDash, Grubhub, Postmates, or Seamless.

`Subscriptions` is intended for recurring monthly or yearly purchases, including Apple bills,
Prime, Audible, Medium, Ring, OpenAI/ChatGPT, Disney Plus, YouTube Premium, and app membership fees
such as Uber One, DashPass, Grubhub+, or Instacart+.

`Online Services` is intended for non-recurring or infrastructure-style online services, not
services treated as monthly subscriptions.

`Entertainment` is intended for one-time leisure purchases, not recurring streaming or membership
subscriptions.

`Child/Dependent` includes child-related activities and dependent-care purchases, including
Thanksgiving Point.

`Groceries` includes grocery stores, supermarkets, and broad household grocery merchants such as
Costco, Walmart, Target, and Dollar Tree when no earlier, more specific inference rule applies.

`Amazon Shopping` is intended for Amazon retail purchases, while Amazon membership or recurring
subscription charges should remain under `Subscriptions`.

`Other General Merchandise` is intended for broad non-grocery retail purchases from non-Amazon
merchants when no more specific category applies.

## Privacy Boundary

Keep this file focused on inference behavior and category families. Do not add transaction dates,
amounts, account identifiers, or row-level personal spending details here.
