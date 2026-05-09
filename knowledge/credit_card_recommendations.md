# Credit Card Recommendations

This file documents the credit card catalog used by the app to estimate annual reward value from
a user's actual spending data and recommend the best-fit card.

## Methodology

### Cash-Back Rewards

1. Group spending by cleaned category from the loaded transaction data.
2. Annualize the category totals based on the date range covered by the data.
3. Apply each card's reward rate per category (cash-back equivalent %) to annualized spend.
4. Apply any per-category annual caps where applicable.
5. Subtract the card's annual fee to get estimated net annual value.
6. Rank cards by estimated net annual value, highest first.
7. For multi-card recommendations, evaluate 2-card through 6-card combinations and assign each
   spending category to the card in the combo with the highest modeled reward value.

Reward rates for points-based cards are converted to an equivalent cash-back % using standard
portal or transfer-partner redemption assumptions documented per card below.

### APR and Minimum-Payment Views

The APR tab is for users who expect to carry a balance. It ranks informational low-APR and 0% intro
APR card options separately from cash-back rewards because interest cost can overwhelm rewards.

The minimum-payment tab models a simplified payoff scenario using a user-entered balance and either
a monthly payment percentage or fixed monthly payment amount. This is an estimate only. Future
purchases, fees, penalty APRs, and promo APR rules can materially change the result.

For APR cards, the app treats the modeled debt as a balance transfer:

- Balance-transfer payoff estimates add the modeled balance-transfer fee to the starting balance
  and use the card's balance-transfer intro APR period.
- After the intro period ends, the model applies the low end of the listed regular APR range.

## Important Limitations

- Estimates are annualized projections from available data and may not reflect seasonal variation.
- Category caps (e.g., Amex Blue Cash 6% on groceries up to $6,000/year) are modeled; spend above
  the cap falls back to the card's default rate.
- Intro bonuses are noted but not modeled in the estimate.
- Statement credits are shown for context but are not deducted from the annual fee in the estimate
  unless the app is explicitly changed to model usable credits.
- Amazon Prime Visa requires an active Amazon Prime membership (~$139/year); this cost is not
  deducted from the estimate.
- Chase Sapphire Reserve's $300 annual travel credit, Capital One Venture X's $300 portal travel
  credit, and Amex Gold's $120 dining + $120 Uber Cash credits are shown but not deducted from the
  annual fee in the estimate.
- Travel portal rates are not broadly modeled unless the app has a category that reliably indicates
  portal-booked travel.
- Points values are estimates; actual value depends on how points are redeemed.
- APR recommendations are not personalized credit offers. Actual APRs depend on creditworthiness,
  issuer underwriting, account terms, and timing.

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
| Capital One Savor Cash Rewards | 1% | 3% dining, entertainment, popular streaming, grocery stores. 5% Capital One Travel hotel/vacation rental/rental car portal bookings noted but not broadly modeled. |
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
| Capital One Venture Rewards | $95 | 2% (2x miles @ 1¢) | 5x Capital One Travel hotel/vacation rental/rental car portal bookings noted but not broadly modeled |
| Capital One Venture X Rewards | $395 | 2% (2x miles @ 1¢) | 10x Capital One Travel hotels/rental cars and 5x flights/vacation rentals noted but not broadly modeled |
| Amex Blue Cash Preferred | $95 | 1% | 6% US supermarkets (up to $6K/yr), 6% streaming, 3% US gas |
| Amex Gold | $250 | 1% (1x MR @ 1¢) | 4% dining & US supermarkets (4x MR), 3% flights (3x MR) |
| Chase Sapphire Reserve | $795 | 1.5% (1x UR @ 1.5¢) | 4.5% dining (3x UR @ 1.5¢), 6% direct flights/hotels represented by the app's coarse Travel category (4x UR @ 1.5¢). 8x Chase Travel portal purchases noted but not broadly modeled. |
| Amex Platinum | $895 | 1% (1x MR @ 1¢) | 5% eligible flights and prepaid hotels through American Express travel channels, represented by the app's coarse Travel category |

### Points Valuation Assumptions

| Card | Points Currency | Assumed Value |
|---|---|---|
| Chase Sapphire Preferred | Ultimate Rewards | 1.25¢/point (Chase Travel portal) |
| Chase Sapphire Reserve | Ultimate Rewards | 1.5¢/point (Chase Travel portal) |
| Amex Gold | Membership Rewards | 1¢/point (conservative; transfer partners can yield 1.5–2¢+) |
| Amex Platinum | Membership Rewards | 1¢/point (conservative; transfer partners can yield 1.5–2¢+) |
| Capital One Venture Rewards | Capital One Miles | 1¢/mile toward travel purchases |
| Capital One Venture X Rewards | Capital One Miles | 1¢/mile toward travel purchases |

## Spending Pattern Guidance

- **High dining spend**: Amex Gold and Chase Sapphire Reserve earn 4–4.5% on dining.
- **High grocery spend**: Amex Blue Cash Preferred (6%) or Amex Gold (4%) outperform flat-rate cards.
- **High Amazon spend**: Amazon Prime Visa earns 5% on Amazon purchases.
- **High travel spend**: Chase Sapphire Reserve, Sapphire Preferred, Capital One Venture, Capital One
  Venture X, and Amex Platinum can add value, but portal-only and direct-booking rates may be
  overstated by the app's coarse `Travel` category.
- **Flat/diverse spend**: Citi Double Cash or Wells Fargo Active Cash (2% flat) often beat
  category-specific cards when no single category dominates. Capital One Venture and Venture X also
  model as flat 2% travel-mile cards, but with annual fees.
- **Annual fee breakeven**: A $95 annual fee card needs ~$4,750 more qualifying spend at 2% bonus
  rate above a no-fee 2% flat card to break even.

## Source Review Notes

Last reviewed on 2026-05-08 against NerdWallet's "Best Credit Cards of May 2026" list, last updated
2026-05-05, NerdWallet balance-transfer and low-interest card pages, CFPB minimum-payment guidance,
plus issuer pages for current Capital One and Chase terms.

- NerdWallet best cards page: https://www.nerdwallet.com/credit-cards/best
- NerdWallet balance transfer cards: https://www.nerdwallet.com/credit-cards/best/balance-transfer
- NerdWallet low interest cards: https://www.nerdwallet.com/credit-cards/best/low-interest
- CFPB minimum payment guidance: https://www.consumerfinance.gov/ask-cfpb/a-box-on-my-credit-card-bill-says-that-i-will-pay-off-the-balance-in-three-years-if-i-pay-a-certain-amount-what-does-that-mean-do-i-have-to-pay-that-much-if-i-pay-that-much-and-make-new-purchases-will-i-still-owe-nothing-after-three-years-en-36/
- Capital One Savor: https://www.capitalone.com/credit-cards/savor/
- Capital One Venture: https://www.capitalone.com/credit-cards/venture/
- Capital One Venture X: https://www.capitalone.com/credit-cards/venture-x/
- Chase Sapphire cards: https://creditcards.chase.com/rewards-credit-cards/sapphire

## Adding or Updating Cards

To add a new card or update rates, update both this file and the `CREDIT_CARD_CATALOG` constant
in `streamlit_app.py`. Keep rate assumptions and caps documented here for audit.
