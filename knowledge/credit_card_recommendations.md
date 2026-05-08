# Credit Card Recommendations

This file documents the credit card catalog used by the app to estimate annual reward value from
a user's actual spending data and recommend the best-fit card.

## Methodology

1. Group spending by cleaned category from the loaded transaction data.
2. Annualize the category totals based on the date range covered by the data.
3. Apply each card's reward rate per category (cash-back equivalent %) to annualized spend.
4. Apply any per-category annual caps where applicable.
5. Subtract the card's annual fee to get estimated net annual value.
6. Rank cards by estimated net annual value, highest first.

Reward rates for points-based cards are converted to an equivalent cash-back % using standard
portal or transfer-partner redemption assumptions documented per card below.

## Important Limitations

- Estimates are annualized projections from available data and may not reflect seasonal variation.
- Category caps (e.g., Amex Blue Cash 6% on groceries up to $6,000/year) are modeled; spend above
  the cap falls back to the card's default rate.
- Intro bonuses, rotating category cards, and statement credits are noted but not modeled in the
  estimate.
- Amazon Prime Visa requires an active Amazon Prime membership (~$139/year); this cost is not
  deducted from the estimate.
- Chase Sapphire Reserve's $300 annual travel credit and Amex Gold's $120 dining + $120 Uber Cash
  credits are not deducted from the annual fee in the estimate.
- Points values are estimates; actual value depends on how points are redeemed.

## App Category to Card Reward Mapping

The app assigns reward rates by matching cleaned spending categories to each card's bonus tiers.
Categories not matched to a bonus tier earn the card's default rate.

| App Category | Reward Tier |
|---|---|
| `Restaurants` | Dining |
| `Coffee & Drinks` | Dining |
| `Food Delivery` | Dining |
| `Groceries` | Supermarkets/Groceries |
| `Gasoline/Fuel` | Gas |
| `Travel` | Travel |
| `Parking` | Transit/Travel |
| `Amazon Shopping` | Amazon/Online Retail |
| `Online Service & Subscriptions` | Streaming/Online Services |
| `Entertainment` | Entertainment |
| All other categories | Default rate |

## Credit Card Catalog

### No Annual Fee Cards

| Card | Default Rate | Bonus Categories |
|---|---|---|
| Citi Double Cash | 2% | None (flat 2% on everything) |
| Wells Fargo Active Cash | 2% | None (flat 2% on everything) |
| Chase Freedom Unlimited | 1.5% | 3% dining |
| Capital One SavorOne | 1% | 3% dining, entertainment, streaming, grocery stores |
| Discover It Cash Back | 1% | 5% rotating categories per quarter (up to $1,500/quarter combined). Modeled schedule: Q1 dining, Q2 gas & home improvement, Q3 groceries, Q4 Amazon & online shopping. Rewards estimated quarter by quarter against actual spending — $1,500/quarter cap applied per quarter. Actual Discover categories vary year to year. |
| Amex Blue Cash Everyday | 1% | 3% US supermarkets (up to $6K/yr), 3% US online retail, 3% US gas |
| Costco Anywhere Visa | 1% | 4% gas (up to $7K/yr), 3% dining & travel, 2% Costco purchases |
| Amazon Store Card | 0% (unusable outside Amazon) | 5% on Amazon purchases (Prime members). Only usable at Amazon. |
| Amazon Prime Visa | 1% | 5% Amazon & Whole Foods, 2% dining, gas & transit |

| BofA Unlimited Cash Rewards | 1.5% | Flat 1.5% on all purchases. No caps, no annual fee. |
| BofA Customized Cash Rewards | 1% | 3% on one chosen category (gas, online shopping, dining, travel, drug stores, or home improvement), 2% grocery & wholesale clubs. $2,500/quarter combined cap on 3%+2% categories. |

### Annual Fee Cards

| Card | Annual Fee | Default Rate | Bonus Categories |
|---|---|---|---|
| Chase Sapphire Preferred | $95 | 1.25% (1x UR @ 1.25¢) | 3.75% dining & streaming (3x UR), 2.5% travel (2x UR) |
| Amex Blue Cash Preferred | $95 | 1% | 6% US supermarkets (up to $6K/yr), 6% streaming, 3% US gas |
| Amex Gold | $250 | 1% (1x MR @ 1¢) | 4% dining & US supermarkets (4x MR), 3% flights (3x MR) |
| Chase Sapphire Reserve | $550 | 1.5% (1x UR @ 1.5¢) | 4.5% dining & travel (3x UR @ 1.5¢) |

### Points Valuation Assumptions

| Card | Points Currency | Assumed Value |
|---|---|---|
| Chase Sapphire Preferred | Ultimate Rewards | 1.25¢/point (Chase Travel portal) |
| Chase Sapphire Reserve | Ultimate Rewards | 1.5¢/point (Chase Travel portal) |
| Amex Gold | Membership Rewards | 1¢/point (conservative; transfer partners can yield 1.5–2¢+) |

## Spending Pattern Guidance

- **High dining spend**: Amex Gold and Chase Sapphire Reserve earn 4–4.5% on dining.
- **High grocery spend**: Amex Blue Cash Preferred (6%) or Amex Gold (4%) outperform flat-rate cards.
- **High Amazon spend**: Amazon Prime Visa earns 5% on Amazon purchases.
- **High travel spend**: Chase Sapphire Reserve (4.5%) or Sapphire Preferred (2.5%) add travel value.
- **Flat/diverse spend**: Citi Double Cash or Wells Fargo Active Cash (2% flat) often beat
  category-specific cards when no single category dominates.
- **Annual fee breakeven**: A $95 annual fee card needs ~$4,750 more qualifying spend at 2% bonus
  rate above a no-fee 2% flat card to break even.

## Adding or Updating Cards

To add a new card or update rates, update both this file and the `CREDIT_CARD_CATALOG` constant
in `streamlit_app.py`. Keep rate assumptions and caps documented here for audit.
