# Category Inference Rules

Use these rules when cleaning transaction CSVs or supported PDF statements, including files that
already contain a source `Category` column.

## Category Assignment Order

The app assigns the cleaned `Category` in this order:

- Apply exact `Description` matches from `category_normalization_rules.md`.
- Apply conditional rules that depend on description and amount.
- Apply source-category override rules listed below.
- Apply user-approved description rules listed below.
- Apply broader keyword inference rules from `Description`.
- If no inference rule matches and the uploaded file has a non-empty source `Category`, keep that
  source category as the cleaned `Category`.
- If no exact rule, inference rule, or source category is available, set the category to `Other`.

Existing source categories are always preserved in `Original Category` for audit.

## Conditional Transaction Rules

Apply these rules when both description and transaction amount are needed:

| Condition | Cleaned Category | Spending treatment |
|---|---|---|
| Exact `Apple` description and absolute amount less than `$100` | `Online Service & Subscriptions` | Include in spending |

## Source Category Override Rules

Apply these source-category rules before broader description inference:

| Source Category | Cleaned Category | Spending treatment |
|---|---|---|
| `Cable/Satellite` | `Online Service & Subscriptions` | Include in spending |
| `Phone Billing` or `Phone Bills` | `Online Service & Subscriptions` | Include in spending |

## User-Approved Description Rules

Apply these high-priority description rules before broader category inference and before
source-category fallback:

| Description contains | Cleaned Category | Spending treatment |
|---|---|---|
| `yami` or `yamibuy` | `Groceries` | Include in spending |
| `mochinut` | `Groceries` | Include in spending |
| `winco food` | `Groceries` | Include in spending |
| `7-eleven` | `Groceries` | Include in spending |
| `maverik` | `Groceries` | Include in spending |
| `costco gas station` or `costco gas stations` | `Gasoline/Fuel` | Include in spending |
| `megaplex` | `Entertainment` | Include in spending |
| `meet fresh` | `Coffee & Drinks` | Include in spending |
| `ipsy` | `Online Service & Subscriptions` | Include in spending |
| `netflix` or `neflix` | `Online Service & Subscriptions` | Include in spending |
| `ikea` without `restaurant` | `Home Improvement` | Include in spending |
| `macy` | `Clothing/Shoes/Others` | Include in spending |
| `tj maxx` | `Clothing/Shoes/Others` | Include in spending |
| `shein` | `Clothing/Shoes/Others` | Include in spending |
| `skims` | `Clothing/Shoes/Others` | Include in spending |
| `namecheap` or `name-cheap` | `Online Service & Subscriptions` | Include in spending |
| `carmines` | `Restaurants` | Include in spending |
| `pizzeria` | `Restaurants` | Include in spending |
| `patrick ta` or `partrick ta` | `Personal Care` | Include in spending |
| `perfumes` | `Personal Care` | Include in spending |
| `fragrancene` | `Personal Care` | Include in spending |
| `seoul kr` | `Travel` | Include in spending |
| `temu` | `Clothing/Shoes/Others` | Include in spending |
| `school`, `tuition`, `university`, `udacity`, or `scholastic` | `Career Growth` | Include in spending |
| `us mobile` | `Online Service & Subscriptions` | Include in spending |
| `betterment` | `Investments` | Exclude from spending |
| `my529` | `Investments` | Exclude from spending |
| `bank of america` | `Internal Transfers` | Exclude from spending |
| `venmo` | `Internal Transfers` | Exclude from spending |
| `discover bank` | `Internal Transfers` | Exclude from spending |
| `brghtwhl` | `Child/Dependent` | Include in spending |
| `korean airlines` or `korean air` | `Travel` | Include in spending |
| `united airlines` | `Travel` | Include in spending |
| `delta air` | `Travel` | Include in spending |
| `cheapoair` | `Travel` | Include in spending |
| `southwest airlines` | `Travel` | Include in spending |
| `american airlines` | `Travel` | Include in spending |
| `airport railroad` | `Travel` | Include in spending |
| `airport` | `Travel` | Include in spending |

`Investments` and `Internal Transfers` are excluded from spending analysis.

## Source Category Normalization

Apply these rules when source-category fallback is used:

| Source Category | Cleaned Category | Spending treatment |
|---|---|---|
| `Clothing/Shoes` | `Clothing/Shoes/Others` | Include in spending |
| `Dues & Subscriptions` | `Online Service & Subscriptions` | Include in spending |
| `Education` | `Career Growth` | Include in spending |
| `Online Services` | `Online Service & Subscriptions` | Include in spending |
| `Other Expenses` | `Other` | Include in spending |
| `Postage & Shipping` | `Postage & Shipping & Printing` | Include in spending |
| `Printing` | `Postage & Shipping & Printing` | Include in spending |
| `Subscriptions` | `Online Service & Subscriptions` | Include in spending |

## Inferred Category Families

The current app uses keyword patterns for these category families.

### Spending Categories

- `Parking`
- `Gasoline/Fuel`
- `Online Service & Subscriptions`
- `Amazon Shopping`
- `Groceries`
- `Coffee & Drinks`
- `Food Delivery`
- `Restaurants`
- `Postage & Shipping & Printing`
- `Charitable Giving`
- `Housing/Rent`
- `Career Growth`
- `Entertainment`
- `Insurance`
- `Home Improvement`
- `Personal Care`
- `Clothing/Shoes/Others`
- `Child/Dependent`
- `Travel`
- `Automotive`
- `Other General Merchandise`

### Excluded Categories

- `Credit Card Payments`
- `Investments`
- `Internal Transfers`

### Fallback Category

- `Other`

## Category Notes

`Career Growth` includes professional development, courses, computing education, school, tuition,
university, Udacity, Scholastic, and source categories labeled `Education`.

`Coffee & Drinks` includes coffee, tea, boba, dessert drink, and drink-focused merchants, including
Meet Fresh.

`Food Delivery` is intended for real delivery orders from delivery apps, such as Uber Eats,
DoorDash, Grubhub, Postmates, or Seamless.

`Online Service & Subscriptions` combines recurring subscriptions and online service purchases,
including Apple bills, Prime, Audible, Medium, Ring, OpenAI/ChatGPT, Netflix, Disney Plus,
YouTube Premium, Ipsy, Namecheap, DigitalOcean, Patreon, app memberships, and infrastructure-style
online services. Source categories labeled `Cable/Satellite`, `Dues & Subscriptions`, or
`Online Services` are normalized to `Online Service & Subscriptions`. Phone billing transactions,
including US Mobile and source categories labeled `Phone Billing` or `Phone Bills`, are also
normalized to this category. Exact `Apple` descriptions with absolute amount less than `$100` are
also normalized to this category.

`Postage & Shipping & Printing` combines postage, shipping, mailing, and printing expenses,
including source categories labeled `Postage & Shipping` or `Printing`.

`Restaurants` includes restaurants, pizzerias, and user-approved restaurant merchants such as
Carmines and The Pie Pizzeria.

`Entertainment` is intended for one-time leisure purchases, movie theaters/cinemas, and event
spending, not recurring streaming or membership subscriptions.

`Child/Dependent` includes child-related activities and dependent-care purchases, including
Thanksgiving Point and Brightwheel/Brghtwhl child care transactions.

`Travel` includes lodging, car rental, airline, airport, airport railroad, travel booking platform,
and user-approved travel-location purchases such as descriptions containing `Seoul Kr`. A
`Booking BV` description should be treated as a Booking.com or Booking Holdings travel purchase,
usually lodging or car rental, and should not be interpreted as a flight purchase unless the
source data explicitly indicates a flight or airline.

`Home Improvement` includes home repair, home goods, garden, nursery, and home improvement store
purchases, including IKEA purchases that are not IKEA restaurant transactions. Do not use broad
`air` matching for this category because airline and airport transactions should be treated as
`Travel`.

`Clothing/Shoes/Others` includes clothing, shoes, apparel, and miscellaneous apparel-like
retailers, including Macy's, TJ Maxx, Shein, Skims, and Temu.

`Personal Care` includes pharmacy, spa, beauty, fragrance, perfume, and personal care merchants,
including Patrick Ta, Perfumes, and Fragrancene.

`Groceries` includes grocery stores, supermarkets, broad household grocery merchants such as
Costco, Walmart, Target, Dollar Tree, Yami/Yamibuy, WinCo Foods, 7-Eleven, Maverik, and
user-approved grocery-shopping merchants such as Mochinut when no earlier, more specific inference
rule applies.

`Gasoline/Fuel` includes fuel purchases, including Costco Gas Station(s). This rule runs before the
broad Costco grocery rule.

`Amazon Shopping` is intended for Amazon retail purchases, while Amazon membership or recurring
subscription charges should remain under `Online Service & Subscriptions`.

`Other General Merchandise` is intended for broad non-grocery retail purchases from non-Amazon
merchants when no more specific category applies.

## Empower Source Category Fallbacks

When the app falls back to the uploaded Empower category, keep the source label as written instead
of collapsing it into `Other`. Observed Empower source categories include:

- `Automotive`
- `Business Miscellaneous`
- `Cable/Satellite`
- `Charitable Giving`
- `Child/Dependent`
- `Clothing/Shoes`
- `Credit Card Payments`
- `Deposits`
- `Dues & Subscriptions`
- `Education`
- `Electronics`
- `Entertainment`
- `Gasoline/Fuel`
- `General Merchandise`
- `Gifts`
- `Groceries`
- `Healthcare/Medical`
- `Home Improvement`
- `Home Maintenance`
- `Insurance`
- `Investment Income`
- `Mortgages`
- `Online Services`
- `Other Expenses`
- `Other Income`
- `Paychecks/Salary`
- `Personal Care`
- `Postage & Shipping`
- `Printing`
- `Refunds & Reimbursements`
- `Restaurants`
- `Rewards`
- `Savings`
- `Service Charges/Fees`
- `Taxes`
- `Transfers`
- `Travel`
- `Utilities`

## Privacy Boundary

Keep this file focused on inference behavior and category families. Do not add transaction dates,
account identifiers, row-level amounts, or row-level spending details here.
