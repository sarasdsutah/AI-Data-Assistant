from __future__ import annotations

import io
import os
import re
from datetime import date, datetime
from itertools import combinations
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
CATEGORY_RULES_PATH = KNOWLEDGE_DIR / "category_normalization_rules.md"
SPENDING_ANALYSIS_RULES_PATH = KNOWLEDGE_DIR / "spending_analysis_rules.md"
CARD_RECOMMENDATIONS_PATH = KNOWLEDGE_DIR / "credit_card_recommendations.md"
EXCLUDED_SPENDING_CATEGORIES = {"Credit Card Payments", "Internal Transfers", "Investments", "Taxes"}
BANK_ACCOUNT_KEYWORDS = frozenset(["bank account", "checking", "savings", "high yield", "money market", "debit", "hysa", "brokerage", "investment account"])
ACCOUNT_CARD_OVERRIDES: dict[str, str] = {
    "credit card - ending in 4346": "BofA Unlimited Cash Rewards",
}
CREDIT_CARD_KEYWORDS = frozenset(["visa", "mastercard", "card", "credit", "amex", "discover", "rewards", "sapphire", "freedom", "preferred", "reserve", "prime store"])
REQUIRED_COLUMNS = ["Date", "Description"]
OPTIONAL_TEXT_COLUMNS = ["Account", "Category", "Tags"]
SOURCE_FILE_COLUMN = "Source File"
SUPPORTED_UPLOAD_TYPES = ["csv", "pdf"]
DEFAULT_CATEGORY = "Other"
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
CHAT_TRANSACTION_CONTEXT_CHAR_LIMIT = 120_000
CARD_RECOMMENDATION_CONTEXT_CHAR_LIMIT = 120_000
COMBO_CARD_COUNTS = [2, 3, 4, 5, 6]
PERCENT_BALANCE_PAYMENT_FLOOR = 20.0
AMAZON_REFERENCE_PATTERN = r"[A-Z]\d{6}[A-Z0-9]{10}"
AMAZON_REFERENCED_TRANSACTION_PATTERN = re.compile(
    rf"(?P<date>\d{{2}}/\d{{2}})"
    rf"(?P<reference>{AMAZON_REFERENCE_PATTERN})"
    rf"(?P<description>.*?)"
    rf"(?P<amount>-?\$[\d,]+\.\d{{2}})",
    re.DOTALL,
)
AMAZON_UNREFERENCED_TRANSACTION_PATTERN = re.compile(
    r"(?P<date>\d{2}/\d{2})\s*"
    r"(?P<description>(?:INTEREST CHARGE|LATE FEE|MINIMUM INTEREST CHARGE|RETURNED PAYMENT FEE)"
    r"[A-Z0-9 &'./-]*?)"
    r"(?P<amount>-?\$[\d,]+\.\d{2})",
    re.DOTALL,
)
INFERRED_CATEGORY_RULES = [
    ("Investments", ["betterment", "my529"]),
    ("Internal Transfers", ["bank of america", "venmo", "discover bank"]),
    ("Credit Card Payments", ["autopay", "auto-pmt", "payment", "pmt"]),
    ("Parking", ["parking", "garage", "ccri", "honk"]),
    ("Gasoline/Fuel", ["costco gas station"]),
    ("Groceries", ["grocery", "groceries", "market", "supermarket", "costco", "walmart", "wal-mart", "target", "dollar tree", "trader joe", "smith", "ocean mart", "harmons", "yami", "yamibuy", "winco food", "mochinut", "7-eleven", "maverik"]),
    ("Gasoline/Fuel", ["gas", "fuel", "gasoline", "holiday", "pilot_"]),
    ("Online Service & Subscriptions", ["us mobile", "apple.com/bill", "prime", "audible", "medium.com", "ring.com", "openai", "chatgpt", "netflix", "neflix", "disney plus", "disney+", "disneyplus", "youtube premium", "youtubepremium", "uber one", "dashpass", "door dash pass", "doordash pass", "grubhub+", "instacart+", "ipsy"]),
    ("Amazon Shopping", ["amazon", "amzn"]),
    ("Travel", ["travel", "booking", "hotel", "airline", "air lines", "korean air", "united airlines", "delta air", "cheapoair", "southwest airlines", "american airlines", "airport railroad", "airport", "seoul kr", "rent-a-car"]),
    ("Coffee & Drinks", ["coffee", "tea", "milk tea", "boba", "beans & brews", "tiger sugar", "starbucks", "meet fresh", "liquor", "wine", "alcohol"]),
    ("Food Delivery", ["uber eats", "ubereats", "doordash", "door dash", "grubhub", "postmates", "seamless", "delivery.com"]),
    ("Restaurants", ["restaurant", "food", "cafe", "bistro", "sushi", "bbq", "taco", "kitchen", "bakery", "tapas", "greek", "familymart", "tst*", "spitz", "sawadee", "cheesecake", "wiseguys", "concessions", "chick-fil-a", "cluckers", "mcdonald", "indochine", "halalepenos", "grill bar", "ramen", "carmines", "pizzeria"]),
    ("Online Service & Subscriptions", ["online", "software", "cloud", "hosting", "domain", "sourcegraph", "namecheap", "name-cheap", "patreon", "digitalocean"]),
    ("Postage & Shipping & Printing", ["postage", "shipping", "printing", "usps", "ups store", "postnet"]),
    ("Charitable Giving", ["charity", "charitable", "rescue committee"]),
    ("Housing/Rent", ["rentapplication", "rent application"]),
    ("Career Growth", ["interview", "career", "course", "computing", "school", "tuition", "university", "udacity", "scholastic"]),
    ("Entertainment", ["video", "comedy", "theater", "movie", "cinema", "megaplex", "youtube", "state parks", "national park", "disney"]),
    ("Insurance", ["insurance", "lemonade", "trawick"]),
    ("Home Improvement", ["home depot", "heating", "lowe's", "lowes", "wayfair", "nursery", "ikea"]),
    ("Personal Care", ["pharmacy", "spa", "personal care", "walgreens", "hammam", "camera shy", "patrick ta", "partrick ta", "perfumes", "fragrancene"]),
    ("Clothing/Shoes/Others", ["clothing", "shoes", "nike", "j.crew", "j. crew", "gap", "carter", "outlet", "nordstrom", "marshalls", "macy", "tj maxx", "shein", "temu", "skims"]),
    ("Child/Dependent", ["child", "dependent", "kids", "care.com", "dancing", "thanksgiving point", "brghtwhl"]),
    ("Automotive", ["automotive", "toll", "udot", "tire", "fab freddy"]),
    ("Other General Merchandise", ["dollar"]),
]
SOURCE_CATEGORY_FALLBACK_RULES = {
    "Clothing/Shoes": "Clothing/Shoes/Others",
    "Education": "Career Growth",
    "Dues & Subscriptions": "Online Service & Subscriptions",
    "Online Services": "Online Service & Subscriptions",
    "Other Expenses": "Other",
    "Postage & Shipping": "Postage & Shipping & Printing",
    "Printing": "Postage & Shipping & Printing",
    "Subscriptions": "Online Service & Subscriptions",
}
SOURCE_CATEGORY_OVERRIDE_RULES = {
    "Cable/Satellite": "Online Service & Subscriptions",
    "Phone Billing": "Online Service & Subscriptions",
    "Phone Bills": "Online Service & Subscriptions",
}
CREDIT_CARD_CATALOG: list[dict] = [
    {
        "name": "Citi Double Cash",
        "issuer": "Citi",
        "annual_fee": 0,
        "category_rates": {},
        "category_caps": {},
        "default_rate": 0.02,
        "notes": "2% on all purchases. No annual fee.",
    },
    {
        "name": "Wells Fargo Active Cash",
        "issuer": "Wells Fargo",
        "annual_fee": 0,
        "category_rates": {},
        "category_caps": {},
        "default_rate": 0.02,
        "notes": "2% cash rewards on all purchases. No annual fee.",
    },
    {
        "name": "Chase Freedom Unlimited",
        "issuer": "Chase",
        "annual_fee": 0,
        "category_rates": {
            "Restaurants": 0.03,
            "Coffee & Drinks": 0.03,
            "Food Delivery": 0.03,
        },
        "category_caps": {},
        "default_rate": 0.015,
        "notes": "3% dining, 1.5% on everything else. No annual fee.",
    },
    {
        "name": "Capital One Savor Cash Rewards",
        "issuer": "Capital One",
        "annual_fee": 0,
        "category_rates": {
            "Restaurants": 0.03,
            "Coffee & Drinks": 0.03,
            "Food Delivery": 0.03,
            "Entertainment": 0.03,
            "Online Service & Subscriptions": 0.03,
            "Groceries": 0.03,
        },
        "category_caps": {},
        "default_rate": 0.01,
        "notes": "3% dining, entertainment, popular streaming, and grocery stores; 5% hotels/vacation rentals/rental cars booked through Capital One Travel; 1% elsewhere. No annual fee. Portal-only travel bonus is not broadly modeled.",
    },
    {
        "name": "Capital One Venture Rewards",
        "issuer": "Capital One",
        "annual_fee": 95,
        "category_rates": {},
        "category_caps": {},
        "default_rate": 0.02,
        "notes": "2x miles on every purchase, modeled at 1 cent per mile. 5x on hotels, vacation rentals, and rental cars booked through Capital One Travel is not broadly modeled. $95 annual fee.",
    },
    {
        "name": "Capital One Venture X Rewards",
        "issuer": "Capital One",
        "annual_fee": 395,
        "statement_credits": 300,
        "statement_credits_detail": "$300 Capital One Travel credit; 10,000 anniversary miles noted but not included as a statement credit",
        "category_rates": {},
        "category_caps": {},
        "default_rate": 0.02,
        "notes": "2x miles on every purchase, modeled at 1 cent per mile. 10x hotels/rental cars and 5x flights/vacation rentals through Capital One Travel are not broadly modeled. $395 annual fee, includes $300 portal travel credit and 10,000 anniversary miles.",
    },
    {
        "name": "Discover It Cash Back",
        "issuer": "Discover",
        "annual_fee": 0,
        "category_rates": {},
        "category_caps": {},
        "default_rate": 0.01,
        "quarterly_bonus_rate": 0.05,
        "quarterly_cap": 1500.0,
        "quarterly_categories": {
            1: ["Restaurants", "Coffee & Drinks", "Food Delivery"],
            2: ["Gasoline/Fuel", "Home Improvement"],
            3: ["Groceries"],
            4: ["Amazon Shopping", "Groceries", "Online Service & Subscriptions"],
        },
        "notes": "5% on rotating categories each quarter (up to $1,500/quarter), 1% elsewhere. "
                 "Q1: dining. Q2: gas & home improvement. Q3: groceries. Q4: Amazon & online shopping. "
                 "No annual fee. Actual quarterly categories vary year to year.",
    },
    {
        "name": "Amex Blue Cash Everyday",
        "issuer": "American Express",
        "annual_fee": 0,
        "category_rates": {
            "Groceries": 0.03,
            "Amazon Shopping": 0.03,
            "Gasoline/Fuel": 0.03,
        },
        "category_caps": {
            "Groceries": 6000.0,
        },
        "default_rate": 0.01,
        "notes": "3% US supermarkets (up to $6K/yr), 3% US online retail, 3% US gas. 1% elsewhere. No annual fee.",
    },
    {
        "name": "BofA Unlimited Cash Rewards",
        "issuer": "Bank of America",
        "annual_fee": 0,
        "category_rates": {},
        "category_caps": {},
        "default_rate": 0.015,
        "notes": "1.5% cash back on all purchases. No caps, no annual fee.",
    },
    {
        "name": "BofA Customized Cash Rewards (Dining)",
        "issuer": "Bank of America",
        "annual_fee": 0,
        "category_rates": {
            "Restaurants": 0.03,
            "Coffee & Drinks": 0.03,
            "Food Delivery": 0.03,
            "Groceries": 0.02,
        },
        "category_caps": {
            "Restaurants": 10000.0,
            "Coffee & Drinks": 10000.0,
            "Food Delivery": 10000.0,
            "Groceries": 10000.0,
        },
        "default_rate": 0.01,
        "notes": "3% on dining, 2% grocery & wholesale clubs (combined $2,500/quarter cap), 1% elsewhere. No annual fee. Choice category set to Dining.",
    },
    {
        "name": "Costco Anywhere Visa",
        "issuer": "Citi",
        "annual_fee": 0,
        "category_rates": {
            "Gasoline/Fuel": 0.04,
            "Restaurants": 0.03,
            "Coffee & Drinks": 0.03,
            "Food Delivery": 0.03,
            "Travel": 0.03,
            "Groceries": 0.02,
        },
        "category_caps": {
            "Gasoline/Fuel": 7000.0,
        },
        "default_rate": 0.01,
        "notes": "4% gas (up to $7K/yr), 3% dining & travel, 2% Costco purchases, 1% elsewhere. No annual fee (requires Costco membership ~$65/yr).",
    },
    {
        "name": "Amazon Store Card",
        "issuer": "Synchrony",
        "annual_fee": 0,
        "category_rates": {
            "Amazon Shopping": 0.05,
        },
        "category_caps": {},
        "default_rate": 0.0,
        "all_spending_rate": 0.05,
        "notes": "5% on Amazon purchases (Prime members). Only usable at Amazon — cannot earn rewards on other spending. No annual fee.",
    },
    {
        "name": "Amazon Prime Visa",
        "issuer": "Chase",
        "annual_fee": 0,
        "category_rates": {
            "Amazon Shopping": 0.05,
            "Restaurants": 0.02,
            "Coffee & Drinks": 0.02,
            "Food Delivery": 0.02,
            "Gasoline/Fuel": 0.02,
            "Parking": 0.02,
        },
        "category_caps": {},
        "default_rate": 0.01,
        "notes": "5% Amazon & Whole Foods, 2% dining/gas/transit, 1% elsewhere. No annual fee (requires Amazon Prime ~$139/yr).",
    },
    {
        "name": "Chase Sapphire Preferred",
        "issuer": "Chase",
        "annual_fee": 95,
        "category_rates": {
            "Restaurants": 0.0375,
            "Coffee & Drinks": 0.0375,
            "Food Delivery": 0.0375,
            "Travel": 0.025,
            "Online Service & Subscriptions": 0.0375,
        },
        "category_caps": {},
        "default_rate": 0.0125,
        "notes": "3x dining & streaming, 2x travel. Points at 1.25¢ via Chase portal. $95 annual fee.",
    },
    {
        "name": "Amex Blue Cash Preferred",
        "issuer": "American Express",
        "annual_fee": 95,
        "category_rates": {
            "Groceries": 0.06,
            "Online Service & Subscriptions": 0.06,
            "Gasoline/Fuel": 0.03,
        },
        "category_caps": {
            "Groceries": 6000.0,
        },
        "default_rate": 0.01,
        "notes": "6% US supermarkets (up to $6K/yr), 6% streaming, 3% US gas. 1% elsewhere. $95 annual fee.",
    },
    {
        "name": "Amex Gold",
        "issuer": "American Express",
        "annual_fee": 250,
        "statement_credits": 240,
        "statement_credits_detail": "$120 dining credit + $120 Uber Cash",
        "category_rates": {
            "Restaurants": 0.04,
            "Coffee & Drinks": 0.04,
            "Food Delivery": 0.04,
            "Groceries": 0.04,
            "Travel": 0.03,
        },
        "category_caps": {
            "Groceries": 25000.0,
        },
        "default_rate": 0.01,
        "notes": "4x dining & US supermarkets, 3x flights. MR points at 1¢ (transfer partners worth more). $250 annual fee (includes $120 dining + $120 Uber Cash credits).",
    },
    {
        "name": "Chase Sapphire Reserve",
        "issuer": "Chase",
        "annual_fee": 795,
        "statement_credits": 300,
        "statement_credits_detail": "$300 travel credit; other limited travel, dining, lifestyle, and entertainment credits not modeled",
        "category_rates": {
            "Restaurants": 0.045,
            "Coffee & Drinks": 0.045,
            "Food Delivery": 0.045,
            "Travel": 0.06,
            "Parking": 0.015,
        },
        "category_caps": {},
        "default_rate": 0.015,
        "notes": "3x dining and 4x direct flights/hotels modeled at 1.5¢ per point; 8x Chase Travel portal purchases and other limited credits are not broadly modeled. $795 annual fee.",
    },
    {
        "name": "Amex Platinum",
        "issuer": "American Express",
        "annual_fee": 895,
        "category_rates": {
            "Travel": 0.05,
        },
        "category_caps": {},
        "default_rate": 0.01,
        "notes": "5x eligible flights and prepaid hotels through American Express travel channels, represented with the app's coarse Travel category; 1x elsewhere. $895 annual fee. Statement credits and lounge benefits are not modeled.",
    },
]

APR_CARD_CATALOG: list[dict] = [
    {
        "name": "BankAmericard credit card",
        "issuer": "Bank of America",
        "annual_fee": 0,
        "purchase_intro_apr": "0% for 21 billing cycles",
        "balance_transfer_intro_apr": "0% for 21 billing cycles on transfers made in the first 60 days",
        "regular_apr": "14.99%-25.99% Variable APR",
        "regular_apr_min": 0.1499,
        "purchase_intro_months": 21,
        "balance_transfer_intro_months": 21,
        "balance_transfer_fee": "5%",
        "balance_transfer_fee_rate": 0.05,
        "balance_transfer_fee_min": 0.0,
        "rewards": "None",
        "best_for": "Lowest listed regular APR range in this low-APR set.",
    },
    {
        "name": "U.S. Bank Shield Visa",
        "issuer": "U.S. Bank",
        "annual_fee": 0,
        "purchase_intro_apr": "0% for 21 billing cycles",
        "balance_transfer_intro_apr": "0% for 21 billing cycles",
        "regular_apr": "16.99%-27.99% Variable APR",
        "regular_apr_min": 0.1699,
        "purchase_intro_months": 21,
        "balance_transfer_intro_months": 21,
        "balance_transfer_fee": "5%, minimum $5",
        "balance_transfer_fee_rate": 0.05,
        "balance_transfer_fee_min": 5.0,
        "rewards": "4% on eligible prepaid travel booked in the Travel Center",
        "best_for": "Long 0% APR window with limited travel-center rewards.",
    },
    {
        "name": "Citi Simplicity Card",
        "issuer": "Citi",
        "annual_fee": 0,
        "purchase_intro_apr": "0% for 18 months",
        "balance_transfer_intro_apr": "0% for 18 months",
        "regular_apr": "17.49%-28.24% Variable APR",
        "regular_apr_min": 0.1749,
        "purchase_intro_months": 18,
        "balance_transfer_intro_months": 18,
        "balance_transfer_fee": "3% intro fee, then 5%",
        "balance_transfer_fee_rate": 0.03,
        "balance_transfer_fee_min": 5.0,
        "rewards": "None",
        "best_for": "Long intro APR plus no late fees.",
    },
    {
        "name": "Wells Fargo Reflect Card",
        "issuer": "Wells Fargo",
        "annual_fee": 0,
        "purchase_intro_apr": "0% for 21 months",
        "balance_transfer_intro_apr": "0% for 21 months on qualifying transfers",
        "regular_apr": "17.49%, 23.99%, or 28.24% Variable APR",
        "regular_apr_min": 0.1749,
        "purchase_intro_months": 21,
        "balance_transfer_intro_months": 21,
        "balance_transfer_fee": "5%, minimum $5",
        "balance_transfer_fee_rate": 0.05,
        "balance_transfer_fee_min": 5.0,
        "rewards": "None",
        "best_for": "Long purchase and balance-transfer intro APR period.",
    },
    {
        "name": "Citi Double Cash",
        "issuer": "Citi",
        "annual_fee": 0,
        "purchase_intro_apr": "None",
        "balance_transfer_intro_apr": "0% for 18 months",
        "regular_apr": "17.49%-27.49% Variable APR",
        "regular_apr_min": 0.1749,
        "purchase_intro_months": 0,
        "balance_transfer_intro_months": 18,
        "balance_transfer_fee": "3% intro fee, then 5%",
        "balance_transfer_fee_rate": 0.03,
        "balance_transfer_fee_min": 5.0,
        "rewards": "2% cash back when paid off",
        "best_for": "Balance transfer plus long-term flat cash-back value after debt is paid.",
    },
]

CATEGORY_COLOR_RANGE = [
    "#4E79A7",
    "#F28E2B",
    "#E15759",
    "#76B7B2",
    "#59A14F",
    "#EDC948",
    "#B07AA1",
    "#FF9DA7",
    "#9C755F",
    "#BAB0AC",
    "#1F77B4",
    "#FF7F0E",
    "#2CA02C",
    "#D62728",
    "#9467BD",
    "#8C564B",
    "#E377C2",
    "#7F7F7F",
    "#BCBD22",
    "#17BECF",
    "#A0CBE8",
    "#FFBE7D",
    "#8CD17D",
    "#B6992D",
]


st.set_page_config(
    page_title="Credit Card Spending Assistant",
    layout="wide",
)


def file_cache_signature(path: Path) -> tuple[int, int]:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return (0, 0)
    return (stat.st_mtime_ns, stat.st_size)


@st.cache_data
def load_category_rules(path: str, file_signature: tuple[int, int] | None = None) -> dict[str, str]:
    rules: dict[str, str] = {}
    rules_path = Path(path)
    if not rules_path.exists():
        return rules

    row_pattern = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|")
    for line in rules_path.read_text(encoding="utf-8").splitlines():
        match = row_pattern.match(line)
        if match:
            description, category = match.groups()
            rules[description] = category
    return rules


@st.cache_data
def load_knowledge_text(path: str, file_signature: tuple[int, int] | None = None) -> str:
    knowledge_path = Path(path)
    if not knowledge_path.exists():
        return ""
    return knowledge_path.read_text(encoding="utf-8").strip()


@st.cache_data
def read_csv_from_path(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def read_csv_from_upload(uploaded_file) -> pd.DataFrame:
    return pd.read_csv(uploaded_file)


@st.cache_data
def read_pdf_from_path(path: str) -> pd.DataFrame:
    pdf_path = Path(path)
    return read_pdf_from_bytes(pdf_path.name, pdf_path.read_bytes())


@st.cache_data
def read_pdf_from_bytes(source_name: str, data: bytes) -> pd.DataFrame:
    return parse_statement_pdf_bytes(data, source_name)


def read_source_from_path(path: str) -> pd.DataFrame:
    source_path = Path(path)
    suffix = source_path.suffix.lower()
    if suffix == ".csv":
        return read_csv_from_path(path)
    if suffix == ".pdf":
        return read_pdf_from_path(path)
    raise ValueError(f"Unsupported file type for {source_path.name}. Upload a CSV or PDF file.")


def read_source_from_upload(uploaded_file) -> pd.DataFrame:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".csv":
        return read_csv_from_upload(uploaded_file)
    if suffix == ".pdf":
        return read_pdf_from_bytes(uploaded_file.name, uploaded_file.getvalue())
    raise ValueError(f"Unsupported file type for {uploaded_file.name}. Upload a CSV or PDF file.")


def parse_statement_pdf_bytes(data: bytes, source_name: str) -> pd.DataFrame:
    text = extract_pdf_text(data, source_name)
    if not text.strip():
        raise ValueError(
            f"{source_name}: no extractable text was found. Scanned PDF statements are not supported yet."
        )

    if is_amazon_store_card_statement(text):
        return parse_amazon_store_card_statement_text(text)

    raise ValueError(
        f"{source_name}: unsupported PDF statement. "
        "Currently supported PDF uploads are Amazon Store Card statements from Synchrony."
    )


def extract_pdf_text(data: bytes, source_name: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError(
            "PDF support requires pypdf. Install project dependencies with `pip install -e .`."
        ) from exc

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise ValueError(f"{source_name}: could not read the PDF file.") from exc

    page_text: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            page_text.append(page.extract_text() or "")
        except Exception as exc:
            raise ValueError(f"{source_name}: could not extract text from PDF page {page_number}.") from exc
    return "\n".join(page_text)


def is_amazon_store_card_statement(text: str) -> bool:
    normalized = text.lower()
    amazon_markers = ["amazon.syf.com", "synchrony bank/amazon", "prime store card"]
    return "transaction detail" in normalized and any(marker in normalized for marker in amazon_markers)


def parse_amazon_store_card_statement_text(text: str) -> pd.DataFrame:
    cycle_start, cycle_end = extract_amazon_billing_cycle(text)
    statement_date = cycle_end or extract_amazon_statement_date(text)
    account = extract_amazon_account_label(text)

    referenced_matches = list(AMAZON_REFERENCED_TRANSACTION_PATTERN.finditer(text))
    rows: list[dict[str, object]] = []
    for index, match in enumerate(referenced_matches):
        next_start = referenced_matches[index + 1].start() if index + 1 < len(referenced_matches) else len(text)
        detail_text = clean_amazon_statement_detail(text[match.end() : next_start])
        statement_amount = parse_statement_money(match.group("amount"))
        rows.append(
            {
                "_Position": match.start(),
                "Date": resolve_statement_transaction_date(
                    match.group("date"),
                    cycle_start,
                    cycle_end,
                    statement_date,
                ),
                "Description": clean_pdf_text_fragment(match.group("description")),
                "Amount": -statement_amount,
                "Account": account,
                "Category": "",
                "Tags": "",
                "Reference Number": match.group("reference"),
                "Statement Detail": detail_text,
            }
        )

    for match in AMAZON_UNREFERENCED_TRANSACTION_PATTERN.finditer(text):
        statement_amount = parse_statement_money(match.group("amount"))
        if statement_amount == 0:
            continue
        rows.append(
            {
                "_Position": match.start(),
                "Date": resolve_statement_transaction_date(
                    match.group("date"),
                    cycle_start,
                    cycle_end,
                    statement_date,
                ),
                "Description": clean_pdf_text_fragment(match.group("description")),
                "Amount": -statement_amount,
                "Account": account,
                "Category": "",
                "Tags": "",
                "Reference Number": "",
                "Statement Detail": "",
            }
        )

    if not rows:
        raise ValueError("No transaction rows were found in the Amazon Store Card statement.")

    df = pd.DataFrame(rows).sort_values("_Position").drop(columns=["_Position"]).reset_index(drop=True)
    df["Amount"] = df["Amount"].where(df["Amount"] != -0.0, 0.0)
    return df


def extract_amazon_billing_cycle(text: str) -> tuple[date | None, date | None]:
    match = re.search(
        r"Billing Cycle from\s+(\d{2}/\d{2}/\d{4})\s+to\s+(\d{2}/\d{2}/\d{4})",
        text,
    )
    if not match:
        return None, None
    return parse_statement_date(match.group(1)), parse_statement_date(match.group(2))


def extract_amazon_statement_date(text: str) -> date | None:
    for pattern in [
        r"New Balance as of\s+(\d{2}/\d{2}/\d{4})",
        r"Payment Due Date:?\s*(\d{2}/\d{2}/\d{4})",
    ]:
        match = re.search(pattern, text)
        if match:
            return parse_statement_date(match.group(1))
    return None


def extract_amazon_account_label(text: str) -> str:
    match = re.search(r"Account Number ending in\s+(\d{4})", text)
    if not match:
        return "Amazon Store Card"
    return f"Amazon Store Card ending in {match.group(1)}"


def parse_statement_date(value: str) -> date:
    return datetime.strptime(value, "%m/%d/%Y").date()


def resolve_statement_transaction_date(
    month_day: str,
    cycle_start: date | None,
    cycle_end: date | None,
    statement_date: date | None,
) -> str:
    month, day = [int(part) for part in month_day.split("/")]
    candidate_years: list[int] = []
    if cycle_start is not None:
        candidate_years.append(cycle_start.year)
    if cycle_end is not None:
        candidate_years.append(cycle_end.year)
    if statement_date is not None:
        candidate_years.append(statement_date.year)
        if month > statement_date.month:
            candidate_years.append(statement_date.year - 1)

    seen_years: set[int] = set()
    for year in candidate_years:
        if year in seen_years:
            continue
        seen_years.add(year)
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        if cycle_start is not None and cycle_end is not None:
            if cycle_start <= candidate <= cycle_end:
                return candidate.isoformat()
        else:
            return candidate.isoformat()

    if statement_date is not None:
        year = statement_date.year - 1 if month > statement_date.month else statement_date.year
        return date(year, month, day).isoformat()
    return month_day


def parse_statement_money(value: str) -> float:
    cleaned = value.strip().replace("$", "").replace(",", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = f"-{cleaned[1:-1]}"
    return float(cleaned)


def clean_pdf_text_fragment(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def clean_amazon_statement_detail(value: str) -> str:
    detail = re.split(
        r"Total Fees Charged This Period|Total Interest Charged This Period|"
        r"\d{4} Year-to-Date Fees and Interest|Interest Charge Calculation|Cardholder News and Information",
        value,
        maxsplit=1,
    )[0]
    detail = re.sub(
        r"\b(?:Payments|Purchases and Other Debits|Purchases/Debits)\s*[-+]?\$[\d,]+\.\d{2}",
        " ",
        detail,
        flags=re.IGNORECASE,
    )
    detail = re.sub(r"\(Continued on next page\)", " ", detail, flags=re.IGNORECASE)
    detail = re.sub(
        r"PAGE\s+\d+\s+of\s+\d+\s+Visit.*?Transaction Detail\s*\(Continued\)"
        r"DateReference #Description\s+Amount",
        " ",
        detail,
        flags=re.IGNORECASE | re.DOTALL,
    )
    detail = re.sub(
        r"Transaction Detail\s*\(Continued\)DateReference #Description\s+Amount",
        " ",
        detail,
        flags=re.IGNORECASE,
    )
    return clean_pdf_text_fragment(detail)


def prepare_transaction_sources(
    sources: list[tuple[str, pd.DataFrame]],
    category_rules: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cleaned_frames: list[pd.DataFrame] = []
    spending_frames: list[pd.DataFrame] = []
    excluded_frames: list[pd.DataFrame] = []

    for source_name, raw_source_df in sources:
        source_df = raw_source_df.copy()
        source_df[SOURCE_FILE_COLUMN] = source_name
        try:
            df, spending_df, excluded_df = prepare_transactions(source_df, category_rules)
        except ValueError as exc:
            raise ValueError(f"{source_name}: {exc}") from exc

        cleaned_frames.append(df)
        spending_frames.append(spending_df)
        excluded_frames.append(excluded_df)

    combined_df = concat_frames(cleaned_frames)
    combined_spending_df = concat_frames(spending_frames)
    combined_excluded_df = concat_frames(excluded_frames)
    for frame in [combined_df, combined_spending_df, combined_excluded_df]:
        frame.attrs["source_count"] = len(sources)

    return combined_df, combined_spending_df, combined_excluded_df


def concat_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def count_source_files(df: pd.DataFrame) -> int:
    if "source_count" in df.attrs:
        return int(df.attrs["source_count"])
    if SOURCE_FILE_COLUMN in df.columns:
        return int(df[SOURCE_FILE_COLUMN].nunique())
    return 1


def prepare_transactions(raw_df: pd.DataFrame, category_rules: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = normalize_transaction_schema(raw_df)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if "Amount" not in df.columns:
        missing_columns.append("Amount or Debit/Credit")
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Missing required column(s): {missing}")

    for column in OPTIONAL_TEXT_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    df["Description"] = df["Description"].fillna("").astype(str)
    df["Original Category"] = df["Category"].fillna("").astype(str).str.strip()

    inferred_categories = df["Description"].apply(infer_category)
    exact_rule_categories = df["Description"].map(category_rules)
    conditional_rule_categories = apply_conditional_category_rules(df)
    source_override_categories = df["Original Category"].map(SOURCE_CATEGORY_OVERRIDE_RULES)
    knowledge_rule_categories = (
        exact_rule_categories
        .fillna(conditional_rule_categories)
        .fillna(source_override_categories)
    )
    source_categories = df["Original Category"].replace("", pd.NA).replace(SOURCE_CATEGORY_FALLBACK_RULES)
    inferred_category_mask = knowledge_rule_categories.isna() & inferred_categories.ne(DEFAULT_CATEGORY)
    source_category_mask = (
        knowledge_rule_categories.isna()
        & inferred_categories.eq(DEFAULT_CATEGORY)
        & source_categories.notna()
    )

    df["Category"] = knowledge_rule_categories.fillna(inferred_categories)
    df.loc[source_category_mask, "Category"] = source_categories[source_category_mask]
    df["Category"] = df["Category"].fillna(DEFAULT_CATEGORY).replace("", DEFAULT_CATEGORY)
    df["Category Normalized"] = (
        (df["Original Category"] != "")
        & (df["Category"] != df["Original Category"])
    )
    df["Category Inferred"] = inferred_category_mask
    df["Category Source"] = "default"
    df.loc[inferred_category_mask, "Category Source"] = "inferred"
    df.loc[source_category_mask, "Category Source"] = "source category"
    df.loc[knowledge_rule_categories.notna(), "Category Source"] = "knowledge rule"

    valid_amount = df["Amount"].notna()
    payment_mask = payment_transaction_mask(df)
    spending_mask = (
        valid_amount
        & (df["Amount"] < 0)
        & ~payment_mask
    )
    spending_df = df.loc[spending_mask].copy()
    spending_df["Spend"] = spending_df["Amount"].abs()
    excluded_df = df.loc[~spending_mask].copy()
    return df, spending_df, excluded_df


def payment_transaction_mask(df: pd.DataFrame) -> pd.Series:
    excluded_categories = {category.lower() for category in EXCLUDED_SPENDING_CATEGORIES}
    category_mask = df["Category"].fillna("").astype(str).str.strip().str.lower().isin(excluded_categories)
    original_category_mask = (
        df["Original Category"].fillna("").astype(str).str.strip().str.lower().isin(excluded_categories)
    )
    description_mask = (
        df["Description"]
        .fillna("")
        .astype(str)
        .str.contains(r"\b(?:autopay|auto-pmt|payment|pmt|payback)\b", case=False, regex=True)
    )
    return category_mask | original_category_mask | description_mask


def normalize_transaction_schema(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.copy()
    df.columns = [str(column).strip() for column in df.columns]

    if "Date" not in df.columns and "Posted Date" in df.columns:
        df["Date"] = df["Posted Date"]

    if "Description" not in df.columns and "Payee" in df.columns:
        df["Description"] = df["Payee"]

    if "Amount" not in df.columns and {"Debit", "Credit"}.issubset(df.columns):
        debit = parse_money_series(df["Debit"]).fillna(0)
        credit = parse_money_series(df["Credit"]).fillna(0)
        df["Amount"] = credit - debit
    elif "Amount" in df.columns:
        df["Amount"] = parse_money_series(df["Amount"])

    if "Account" not in df.columns and "Member Name" in df.columns:
        df["Account"] = df["Member Name"]

    return df


def parse_money_series(series: pd.Series) -> pd.Series:
    cleaned = (
        series.fillna("")
        .astype(str)
        .str.strip()
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    )
    return pd.to_numeric(cleaned.replace("", pd.NA), errors="coerce")


def apply_conditional_category_rules(df: pd.DataFrame) -> pd.Series:
    categories = pd.Series(pd.NA, index=df.index, dtype="object")
    exact_apple_small_charge = (
        df["Description"].str.strip().str.casefold().eq("apple")
        & df["Amount"].abs().lt(100)
    )
    categories.loc[exact_apple_small_charge] = "Online Service & Subscriptions"
    return categories


def infer_category(description: object) -> str:
    text = str(description).strip().lower()
    if not text:
        return DEFAULT_CATEGORY

    for category, keywords in INFERRED_CATEGORY_RULES:
        if any(keyword in text for keyword in keywords):
            return category
    return DEFAULT_CATEGORY


def filter_spending_by_date(spending_df: pd.DataFrame, start_date: date | None, end_date: date | None) -> pd.DataFrame:
    if spending_df.empty or start_date is None or end_date is None:
        return spending_df

    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    return spending_df[
        spending_df["Date"].notna()
        & (spending_df["Date"] >= start)
        & (spending_df["Date"] <= end)
    ].copy()


def money(value: float) -> str:
    return f"${value:,.2f}"


def active_theme_text_color() -> str:
    theme_type = ""
    try:
        theme_type = str(st.context.theme.get("type") or "")
    except Exception:
        theme_type = ""

    if not theme_type or theme_type.lower() == "none":
        theme_type = str(st.get_option("theme.base") or "")

    return "#FFFFFF" if theme_type.lower() == "dark" else "#000000"


def base_category_color_domain() -> list[str]:
    domain: list[str] = []

    for category, _keywords in INFERRED_CATEGORY_RULES:
        if category not in domain:
            domain.append(category)
    if DEFAULT_CATEGORY not in domain:
        domain.append(DEFAULT_CATEGORY)
    return domain


def category_color_domain(categories: object | None = None) -> list[str]:
    base_domain = base_category_color_domain()
    if categories is None:
        return base_domain

    present_categories = pd.Series(categories).dropna().astype(str).unique().tolist()
    present_category_set = set(present_categories)
    domain = [category for category in base_domain if category in present_category_set]
    for category in present_categories:
        if category not in domain:
            domain.append(category)

    return domain


def category_color_scale(categories: object | None = None) -> alt.Scale:
    domain = category_color_domain(categories)
    return alt.Scale(
        domain=domain,
        range=[category_color(category) for category in domain],
    )


def category_color(category: str) -> str:
    domain = base_category_color_domain()
    try:
        index = domain.index(category)
    except ValueError:
        index = len(domain)
    return CATEGORY_COLOR_RANGE[index % len(CATEGORY_COLOR_RANGE)]


def date_range_text(spending_df: pd.DataFrame) -> str:
    valid_dates = spending_df["Date"].dropna()
    if valid_dates.empty:
        return "No valid dates"
    return f"{valid_dates.min().date()} to {valid_dates.max().date()}"


def category_summary(spending_df: pd.DataFrame) -> pd.DataFrame:
    if spending_df.empty:
        return pd.DataFrame(columns=["Category", "Transactions", "Spend"])

    summary = (
        spending_df.groupby("Category", dropna=False)
        .agg(Transactions=("Spend", "size"), Spend=("Spend", "sum"))
        .reset_index()
        .sort_values("Spend", ascending=False)
    )
    return summary


def monthly_summary(spending_df: pd.DataFrame) -> pd.DataFrame:
    dated = spending_df.dropna(subset=["Date"]).copy()
    if dated.empty:
        return pd.DataFrame(columns=["Month", "Transactions", "Spend"])

    dated["Month"] = dated["Date"].dt.to_period("M").astype(str)
    return (
        dated.groupby("Month")
        .agg(Transactions=("Spend", "size"), Spend=("Spend", "sum"))
        .reset_index()
        .sort_values("Month")
    )


def monthly_category_summary(spending_df: pd.DataFrame) -> pd.DataFrame:
    dated = spending_df.dropna(subset=["Date"]).copy()
    if dated.empty:
        return pd.DataFrame(columns=["Month", "Category", "Transactions", "Spend"])

    dated["Month"] = dated["Date"].dt.to_period("M").astype(str)
    return (
        dated.groupby(["Month", "Category"], dropna=False)
        .agg(Transactions=("Spend", "size"), Spend=("Spend", "sum"))
        .reset_index()
        .sort_values(["Month", "Spend"], ascending=[True, False])
    )


def build_overview(spending_df: pd.DataFrame) -> str:
    if spending_df.empty:
        return "No spending rows are available."

    categories = category_summary(spending_df)
    top = categories.iloc[0]
    category_count = spending_df["Category"].nunique()
    return (
        f"Spending analysis covers {len(spending_df):,} transactions from {date_range_text(spending_df)}. "
        f"Total spending is {money(spending_df['Spend'].sum())}. "
        f"The dataset includes {category_count:,} spending categories. "
        f"The largest category is {top['Category']} at {money(float(top['Spend']))}."
    )


def build_category_answer(spending_df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    categories = category_summary(spending_df)
    if categories.empty:
        return "No spending categories are available.", categories

    top_rows = categories.head(5)
    top_text = "; ".join(
        f"{row.Category}: {money(float(row.Spend))}"
        for row in top_rows.itertuples(index=False)
    )
    answer = f"Top spending categories are {top_text}."
    return answer, categories


def build_time_answer(spending_df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    months = monthly_summary(spending_df)
    if months.empty:
        return "No valid dates are available for trend analysis.", months

    peak = months.sort_values("Spend", ascending=False).iloc[0]
    answer = (
        f"Monthly spending is available for {len(months)} month(s). "
        f"The highest month in this sample is {peak['Month']} at {money(float(peak['Spend']))}."
    )
    return answer, months


def build_specific_category_answer(spending_df: pd.DataFrame, category: str) -> tuple[str, pd.DataFrame]:
    filtered = spending_df[spending_df["Category"].str.lower() == category.lower()]
    if filtered.empty:
        return f"No spending rows are currently categorized as {category}.", pd.DataFrame()

    answer = (
        f"{category} has {len(filtered):,} transaction(s), totaling {money(filtered['Spend'].sum())}. "
        f"Average transaction size is {money(filtered['Spend'].mean())}."
    )
    summary = (
        filtered.groupby("Description")
        .agg(Transactions=("Spend", "size"), Spend=("Spend", "sum"))
        .reset_index()
        .sort_values("Spend", ascending=False)
    )
    return answer, summary


def build_data_quality_answer(df: pd.DataFrame, spending_df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    exact_rules = int((df["Category Source"] == "knowledge rule").sum())
    inferred = int(df["Category Inferred"].sum())
    source_categories = int((df["Category Source"] == "source category").sum())
    recategorized = int(df["Category Normalized"].sum())
    invalid_dates = int(df["Date"].isna().sum())
    invalid_amounts = int(df["Amount"].isna().sum())
    source_count = count_source_files(df)
    answer = (
        f"The loaded dataset has {len(df):,} total rows across {source_count:,} source file(s). "
        f"{len(spending_df):,} rows are available for spending analysis. "
        f"{exact_rules:,} rows used exact knowledge rules. "
        f"{inferred:,} rows used inferred categories. "
        f"{source_categories:,} rows kept source categories after no inference rule matched. "
        f"{recategorized:,} provider categories were replaced by app categories. "
        f"Invalid dates: {invalid_dates:,}. Invalid amounts: {invalid_amounts:,}."
    )
    checks = pd.DataFrame(
        [
            {"Check": "Source files", "Count": source_count},
            {"Check": "Rows loaded", "Count": len(df)},
            {"Check": "Rows used for spending analysis", "Count": len(spending_df)},
            {"Check": "Rows using exact knowledge rules", "Count": exact_rules},
            {"Check": "Rows using inferred categories", "Count": inferred},
            {"Check": "Rows using source category fallback", "Count": source_categories},
            {"Check": "Provider categories replaced", "Count": recategorized},
            {"Check": "Rows with invalid dates", "Count": invalid_dates},
            {"Check": "Rows with invalid amounts", "Count": invalid_amounts},
        ]
    )
    return answer, checks


def load_local_env(path: Path = BASE_DIR / ".env") -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_openai_model() -> str:
    load_local_env()
    return os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)


def dataframe_csv_text(df: pd.DataFrame, columns: list[str]) -> str:
    export_columns = [column for column in columns if column in df.columns]
    export_df = df[export_columns].copy()
    if "Date" in export_df.columns:
        export_df["Date"] = pd.to_datetime(export_df["Date"], errors="coerce").dt.date.astype(str)
    return export_df.to_csv(index=False)


def build_chat_dataset_context(df: pd.DataFrame, spending_df: pd.DataFrame) -> str:
    quality_answer, quality_checks = build_data_quality_answer(df, spending_df)
    spending_analysis_rules = load_knowledge_text(
        str(SPENDING_ANALYSIS_RULES_PATH),
        file_cache_signature(SPENDING_ANALYSIS_RULES_PATH),
    )
    card_recommendations_knowledge = load_knowledge_text(
        str(CARD_RECOMMENDATIONS_PATH),
        file_cache_signature(CARD_RECOMMENDATIONS_PATH),
    )
    category_csv = category_summary(spending_df).to_csv(index=False)
    monthly_csv = monthly_summary(spending_df).to_csv(index=False)
    monthly_category_csv = monthly_category_summary(spending_df).to_csv(index=False)
    transaction_csv = dataframe_csv_text(
        spending_df.sort_values(["Date", "Spend"], ascending=[False, False]),
        [
            "Date",
            SOURCE_FILE_COLUMN,
            "Account",
            "Description",
            "Statement Detail",
            "Category",
            "Category Source",
            "Amount",
            "Spend",
        ],
    )
    if len(transaction_csv) > CHAT_TRANSACTION_CONTEXT_CHAR_LIMIT:
        transaction_csv = (
            transaction_csv[:CHAT_TRANSACTION_CONTEXT_CHAR_LIMIT]
            + "\n[Transaction CSV truncated because it exceeded the chat context budget.]\n"
        )

    return f"""Current cleaned spending dataset context

Important analysis rules:
- Treat `Spend` as the positive USD spending amount.
- Credit card payment/payback rows have already been excluded from the spending CSV.
- Use the CSV and summaries below as the source of truth. If the data does not support an answer, say so.
- Do not invent merchants, categories, dates, or amounts.
- When estimating annual rewards, group spending by the cleaned `Category` column and apply reward rates using that category. Do not re-infer or override categories from merchant descriptions.

Knowledge analysis rules:
{spending_analysis_rules or "No additional knowledge analysis rules loaded."}

Credit card reward knowledge:
{card_recommendations_knowledge or "No credit card reward knowledge loaded."}

Overview:
{build_overview(spending_df)}

Data quality:
{quality_answer}

Data quality checks CSV:
{quality_checks.to_csv(index=False)}

Category summary CSV:
{category_csv}

Monthly summary CSV:
{monthly_csv}

Monthly category summary CSV:
{monthly_category_csv}

Cleaned spending transaction CSV:
{transaction_csv}
"""


def recent_chat_history(messages: list[dict[str, str]], limit: int = 8) -> str:
    if not messages:
        return "No previous chat messages."

    recent_messages = messages[-limit:]
    lines = []
    for message in recent_messages:
        role = message.get("role", "unknown")
        content = str(message.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "No previous chat messages."


def ask_openai_spending_question(
    question: str,
    df: pd.DataFrame,
    spending_df: pd.DataFrame,
    previous_messages: list[dict[str, str]],
) -> str:
    load_local_env()
    if not os.getenv("OPENAI_API_KEY"):
        return "OpenAI API key not found. Add `OPENAI_API_KEY=...` to `.env` and rerun the app."

    try:
        from openai import OpenAI
    except ImportError:
        return "OpenAI Python SDK is not installed. Run `pip install -e .` and rerun the app."

    model = get_openai_model()
    client = OpenAI()
    dataset_context = build_chat_dataset_context(df, spending_df)
    prompt = f"""{dataset_context}

Recent chat history:
{recent_chat_history(previous_messages)}

User question:
{question}
"""

    try:
        response = client.responses.create(
            model=model,
            instructions=(
                "You are a personal credit card spending analysis assistant. "
                "Answer using only the provided cleaned transaction data and summaries. "
                "Keep answers concise, use USD formatting, call out date ranges when relevant, "
                "and never include credit card payment rows in spending totals."
            ),
            input=prompt,
            max_output_tokens=800,
        )
    except Exception as exc:
        return f"OpenAI API request failed: {exc}"

    answer = getattr(response, "output_text", "").strip()
    return answer or "OpenAI returned an empty response."


def answer_question(question: str, df: pd.DataFrame, spending_df: pd.DataFrame) -> tuple[str, pd.DataFrame | None, str]:
    normalized_question = question.strip().lower()
    if not normalized_question:
        return build_overview(spending_df), category_summary(spending_df), "Spending by Category"

    if any(term in normalized_question for term in ["quality", "clean", "normalize", "excluded", "payment", "payback"]):
        answer, table = build_data_quality_answer(df, spending_df)
        return answer, table, "Data Checks"

    if any(term in normalized_question for term in ["online service", "online services", "subscription", "subscriptions", "phone", "phone bill", "phone billing", "mobile", "us mobile", "apple.com/bill", "prime", "medium", "ring", "openai", "chatgpt", "disney plus", "disney+", "youtube premium"]):
        answer, table = build_specific_category_answer(spending_df, "Online Service & Subscriptions")
        return answer, table, "Online Service & Subscriptions"

    if any(term in normalized_question for term in ["month", "monthly", "date", "trend", "time"]):
        answer, table = build_time_answer(spending_df)
        return answer, table, "Monthly Spend"

    category_terms = {
        "Groceries": ["grocery", "groceries", "online grocery", "online groceries", "yami", "yamibuy"],
        "Coffee & Drinks": ["tea", "coffee", "milk tea", "tiger sugar", "meet fresh", "wine", "alcohol", "liquor"],
        "Food Delivery": ["delivery", "food delivery", "uber eats", "ubereats", "doordash", "door dash", "grubhub", "postmates", "seamless"],
        "Parking": ["parking", "airgarage", "ccri"],
        "Career Growth": ["career", "interview", "growth"],
    }
    for category, terms in category_terms.items():
        if any(term in normalized_question for term in terms):
            answer, table = build_specific_category_answer(spending_df, category)
            return answer, table, category

    if any(term in normalized_question for term in ["category", "categories", "top", "largest", "biggest"]):
        answer, table = build_category_answer(spending_df)
        return answer, table, "Spending by Category"

    return build_overview(spending_df), category_summary(spending_df), "Spending by Category"


def render_metric_row(spending_df: pd.DataFrame) -> None:
    total_spend = spending_df["Spend"].sum() if not spending_df.empty else 0.0
    avg_transaction = spending_df["Spend"].mean() if not spending_df.empty else 0.0

    st.markdown(
        f"""
        <section class="date-range-section">
          <div class="date-range-label">Date Range</div>
          <div class="date-range-value">{date_range_text(spending_df)}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Spend", money(total_spend))
    col2.metric("Transactions", f"{len(spending_df):,}")
    col3.metric("Avg Transaction", money(avg_transaction))


def render_spending_date_filter(
    spending_df: pd.DataFrame,
    label: str = "Filter spending date range",
    key: str = "spending_summary_date_range",
) -> pd.DataFrame:
    valid_dates = spending_df["Date"].dropna()
    if valid_dates.empty:
        return spending_df

    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()
    selected_range = st.date_input(
        label,
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key=key,
    )
    if not isinstance(selected_range, tuple) or len(selected_range) != 2:
        st.stop()

    selected_start, selected_end = selected_range
    if not isinstance(selected_start, date) or not isinstance(selected_end, date):
        st.stop()
    if selected_start > selected_end:
        st.error("Start date must be before or equal to end date.")
        st.stop()

    return filter_spending_by_date(spending_df, selected_start, selected_end)


def render_global_styles() -> None:
    st.markdown(
        """
        <style>
          .date-range-section {
            padding: 0 0 1rem 0;
            margin: 0.25rem 0 1.25rem 0;
            border-bottom: 1px solid rgba(49, 51, 63, 0.18);
          }
          .date-range-label {
            font-size: 1.15rem;
            font-weight: 700;
            line-height: 1.2;
            margin: 0 0 0.2rem 0;
          }
          .date-range-value {
            font-size: 1.75rem;
            font-weight: 650;
            line-height: 1.15;
            margin: 0;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_table(table: pd.DataFrame | None) -> None:
    if table is None or table.empty:
        return

    display = table.copy()
    if "Spend" in display.columns:
        display["Spend"] = display["Spend"].map(money)
    st.dataframe(display, hide_index=True, use_container_width=True)


def transaction_detail_display(details: pd.DataFrame) -> pd.DataFrame:
    detail_columns = ["Date", SOURCE_FILE_COLUMN, "Description", "Statement Detail", "Category", "Spend"]
    detail_columns = [column for column in detail_columns if column in details.columns]
    display = details[detail_columns].copy()
    if "Date" in display.columns:
        display["Date"] = display["Date"].dt.date
    return display


def render_transaction_detail_table(details: pd.DataFrame) -> None:
    st.dataframe(
        transaction_detail_display(details),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Category": st.column_config.TextColumn("Cleaned Category"),
            "Spend": st.column_config.NumberColumn("Spend", format="$%.2f"),
        },
    )


def latest_month_tabs(details: pd.DataFrame, count: int = 3) -> list[tuple[str, pd.DataFrame]]:
    dated = details.dropna(subset=["Date"]).copy()
    if dated.empty:
        return []

    dated["Transaction Month"] = dated["Date"].dt.to_period("M")
    latest_months = sorted(dated["Transaction Month"].unique(), reverse=True)[:count]
    tabs: list[tuple[str, pd.DataFrame]] = []
    for month in latest_months:
        month_details = dated[dated["Transaction Month"] == month].drop(columns=["Transaction Month"])
        label = month.to_timestamp().strftime("%B %Y")
        tabs.append((label, month_details))
    return tabs


def latest_month_spending_tabs(spending_df: pd.DataFrame, count: int = 3) -> list[tuple[str, pd.DataFrame]]:
    dated = spending_df.dropna(subset=["Date"]).copy()
    if dated.empty:
        return []

    dated["Transaction Month"] = dated["Date"].dt.to_period("M")
    latest_months = sorted(dated["Transaction Month"].unique(), reverse=True)[:count]
    tabs: list[tuple[str, pd.DataFrame]] = []
    for month in latest_months:
        month_spending = dated[dated["Transaction Month"] == month].drop(columns=["Transaction Month"])
        label = month.to_timestamp().strftime("%B %Y")
        tabs.append((label, month_spending))
    return tabs


def render_category_summary_selection(display: pd.DataFrame, key: str) -> str | None:
    selection = st.dataframe(
        display,
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key=key,
        column_config={
            "Spend": st.column_config.NumberColumn("Spend", format="$%.2f"),
        },
    )

    selected_rows = selection.selection.rows if selection.selection else []
    if not selected_rows:
        return None
    selected_index = selected_rows[0]
    if selected_index >= len(display):
        return None
    return str(display.iloc[selected_index]["Category"])


def render_summary_table(table: pd.DataFrame | None, spending_df: pd.DataFrame) -> None:
    if table is None or table.empty:
        return
    if "Category" not in table.columns or "Spend" not in table.columns:
        render_table(table)
        return

    display = table.sort_values("Spend", ascending=False).reset_index(drop=True)
    st.caption("Select a category row to view its transactions.")
    monthly_summary_tabs = latest_month_spending_tabs(spending_df)
    tab_specs = [("All", display)] + [
        (label, category_summary(month_spending))
        for label, month_spending in monthly_summary_tabs
    ]
    tabs = st.tabs([label for label, _ in tab_specs])

    selected_category = None
    for index, (tab, (label, summary)) in enumerate(zip(tabs, tab_specs)):
        with tab:
            if summary.empty:
                st.caption("No spending rows are available for this period.")
                continue
            selected = render_category_summary_selection(
                summary.sort_values("Spend", ascending=False).reset_index(drop=True),
                f"category_summary_table_{index}",
            )
            if selected is not None:
                selected_category = selected

    if selected_category is None:
        return

    details = spending_df[spending_df["Category"] == selected_category].copy()
    if details.empty:
        return

    details = details.sort_values(["Date", "Spend"], ascending=[False, False])
    st.markdown(f"**Transactions: {selected_category}**")
    monthly_tabs = latest_month_tabs(details)
    tab_labels = ["All"] + [label for label, _ in monthly_tabs]
    tabs = st.tabs(tab_labels)
    with tabs[0]:
        render_transaction_detail_table(details)

    for tab, (label, month_details) in zip(tabs[1:], monthly_tabs):
        with tab:
            st.markdown(f"**{label}**")
            render_transaction_detail_table(month_details)


def render_spending_category_filter(spending_df: pd.DataFrame) -> str | None:
    categories = category_summary(spending_df)
    if categories.empty:
        return None

    options = categories["Category"].astype(str).tolist()
    key = "spending_summary_category"
    if st.session_state.get(key) not in options and key in st.session_state:
        del st.session_state[key]

    return st.selectbox(
        "Filter spending category",
        options,
        index=0,
        key=key,
    )


def render_selected_category_summary(spending_df: pd.DataFrame, category: str | None) -> None:
    if spending_df.empty or category is None:
        st.write("No spending rows are available.")
        return

    selected_spending = spending_df[spending_df["Category"] == category].copy()
    if selected_spending.empty:
        st.write(f"No spending rows are currently categorized as {category}.")
        return

    st.write(
        f"{category} has {len(selected_spending):,} transaction(s), "
        f"totaling {money(selected_spending['Spend'].sum())}."
    )

    category_months = monthly_summary(selected_spending)
    if not category_months.empty:
        st.markdown(f"**Monthly Spend: {category}**")
        render_selected_category_monthly_chart(category_months, category)

    details = selected_spending.sort_values(["Date", "Spend"], ascending=[False, False])
    st.markdown(f"**Transactions: {category}**")
    render_transaction_detail_table(details)


def render_selected_category_monthly_chart(category_months: pd.DataFrame, category: str) -> None:
    month_order = category_months["Month"].tolist()
    max_monthly_spend = float(category_months["Spend"].max()) if not category_months.empty else 0.0
    y_domain_max = max_monthly_spend * 1.14 if max_monthly_spend > 0 else 1
    text_color = active_theme_text_color()

    bars = (
        alt.Chart(category_months)
        .mark_bar(color=category_color(category))
        .encode(
            x=alt.X(
                "Month:N",
                title="Month",
                sort=month_order,
                axis=alt.Axis(grid=False, domain=False),
            ),
            y=alt.Y(
                "Spend:Q",
                title="Spend",
                axis=alt.Axis(format="$,.0f", grid=False, domain=False),
                scale=alt.Scale(domain=[0, y_domain_max]),
            ),
            tooltip=[
                alt.Tooltip("Month:N", title="Month"),
                alt.Tooltip("Spend:Q", title="Spend", format="$,.2f"),
                alt.Tooltip("Transactions:Q", title="Transactions"),
            ],
        )
    )
    labels = (
        alt.Chart(category_months)
        .mark_text(dy=-8, fontSize=12, fontWeight=600, color=text_color)
        .encode(
            x=alt.X("Month:N", sort=month_order),
            y=alt.Y("Spend:Q", scale=alt.Scale(domain=[0, y_domain_max])),
            text=alt.Text("Spend:Q", format="$,.2f"),
        )
    )
    chart = (
        alt.layer(bars, labels)
        .properties(height=320)
        .configure_axis(grid=False)
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(chart, use_container_width=True)


def render_chart(table: pd.DataFrame | None, title: str) -> None:
    if table is None or table.empty or "Spend" not in table.columns:
        return

    chart_table = table.copy()
    label_column = "Category" if "Category" in chart_table.columns else "Month"
    if label_column not in chart_table.columns:
        return

    if label_column == "Category":
        chart_table = chart_table.sort_values("Spend", ascending=False)
        chart = (
            alt.Chart(chart_table)
            .mark_bar()
            .encode(
                x=alt.X(
                    "Category:N",
                    title="Category",
                    sort=alt.SortField(field="Spend", order="descending"),
                ),
                y=alt.Y("Spend:Q", title="Spend"),
                tooltip=[
                    alt.Tooltip("Category:N", title="Category"),
                    alt.Tooltip("Spend:Q", title="Spend", format="$,.2f"),
                    alt.Tooltip("Transactions:Q", title="Transactions"),
                ],
                color=alt.Color(
                    "Category:N",
                    legend=None,
                    scale=category_color_scale(chart_table["Category"]),
                ),
            )
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)
        return

    st.bar_chart(
        chart_table.set_index(label_column)["Spend"],
        use_container_width=True,
    )


def render_monthly_category_chart(spending_df: pd.DataFrame) -> None:
    monthly_category = monthly_category_summary(spending_df)
    if monthly_category.empty:
        return

    month_order = sorted(monthly_category["Month"].unique())
    monthly_totals = monthly_summary(spending_df)
    max_monthly_spend = float(monthly_totals["Spend"].max()) if not monthly_totals.empty else 0.0
    y_domain_max = max_monthly_spend * 1.12 if max_monthly_spend > 0 else 1
    text_color = active_theme_text_color()
    category_highlight = alt.selection_point(
        fields=["Category"],
        bind="legend",
        name="category_highlight",
    )

    bars = (
        alt.Chart(monthly_category)
        .mark_bar()
        .encode(
            x=alt.X(
                "Month:N",
                title="Month",
                sort=month_order,
                axis=alt.Axis(grid=False, domain=False),
            ),
            y=alt.Y(
                "Spend:Q",
                title="Spend",
                axis=alt.Axis(format="$,.0f", grid=False, domain=False),
                scale=alt.Scale(domain=[0, y_domain_max]),
            ),
            color=alt.Color(
                "Category:N",
                title="Category",
                scale=category_color_scale(monthly_category["Category"]),
            ),
            tooltip=[
                alt.Tooltip("Month:N", title="Month"),
                alt.Tooltip("Category:N", title="Category"),
                alt.Tooltip("Spend:Q", title="Spend", format="$,.2f"),
                alt.Tooltip("Transactions:Q", title="Transactions"),
            ],
            opacity=alt.condition(category_highlight, alt.value(1.0), alt.value(0.2)),
        )
        .add_params(category_highlight)
    )
    labels = (
        alt.Chart(monthly_totals)
        .mark_text(dy=-8, fontSize=12, fontWeight=600, color=text_color)
        .encode(
            x=alt.X("Month:N", sort=month_order),
            y=alt.Y("Spend:Q", scale=alt.Scale(domain=[0, y_domain_max])),
            text=alt.Text("Spend:Q", format="$,.2f"),
        )
    )
    chart = (
        alt.layer(bars, labels)
        .properties(height=480)
        .configure_legend(orient="bottom", columns=4)
        .configure_axis(grid=False)
        .configure_view(strokeWidth=0)
    )

    st.subheader("Month Over Month Spending")
    st.caption("Category colors use the cleaned spending categories.")
    st.altair_chart(chart, use_container_width=True)


def render_category_total_chart(spending_df: pd.DataFrame) -> None:
    category_totals = category_summary(spending_df)
    if category_totals.empty:
        return

    category_order = category_totals["Category"].tolist()
    max_category_spend = float(category_totals["Spend"].max()) if not category_totals.empty else 0.0
    x_domain_max = max_category_spend * 1.14 if max_category_spend > 0 else 1
    chart_height = max(430, len(category_totals) * 36)
    text_color = active_theme_text_color()

    bars = (
        alt.Chart(category_totals)
        .mark_bar()
        .encode(
            x=alt.X(
                "Spend:Q",
                title=None,
                axis=alt.Axis(
                    labels=False,
                    ticks=False,
                    grid=False,
                    domain=False,
                    titleColor=text_color,
                ),
                scale=alt.Scale(domain=[0, x_domain_max]),
            ),
            y=alt.Y(
                "Category:N",
                title="Category",
                sort=category_order,
                axis=alt.Axis(
                    grid=False,
                    domain=False,
                    labelColor=text_color,
                    labelLimit=260,
                    labelPadding=8,
                    titleColor=text_color,
                ),
            ),
            color=alt.Color(
                "Category:N",
                legend=None,
                scale=category_color_scale(category_totals["Category"]),
            ),
            tooltip=[
                alt.Tooltip("Category:N", title="Category"),
                alt.Tooltip("Spend:Q", title="Spend", format="$,.2f"),
                alt.Tooltip("Transactions:Q", title="Transactions"),
            ],
        )
    )
    labels = (
        alt.Chart(category_totals)
        .mark_text(
            align="left",
            baseline="middle",
            dx=6,
            fontSize=12,
            fontWeight=600,
            color=text_color,
        )
        .encode(
            x=alt.X("Spend:Q", scale=alt.Scale(domain=[0, x_domain_max])),
            y=alt.Y("Category:N", sort=category_order),
            text=alt.Text("Spend:Q", format="$,.2f"),
        )
    )
    chart = (
        alt.layer(bars, labels)
        .properties(height=chart_height)
        .configure_axis(grid=False)
        .configure_view(strokeWidth=0)
    )

    st.altair_chart(chart, use_container_width=True)


def format_source_names(source_names: list[str]) -> str:
    if not source_names:
        return "No dataset"
    if len(source_names) == 1:
        return source_names[0]

    preview = ", ".join(source_names[:3])
    if len(source_names) > 3:
        preview = f"{preview}, +{len(source_names) - 3} more"
    return f"{len(source_names)} files: {preview}"


def pluralize_count(count: int, singular: str, plural: str | None = None) -> str:
    if plural is None:
        plural = f"{singular}s"
    return f"{count} {singular if count == 1 else plural}"


def join_summary_parts(parts: list[str]) -> str:
    if len(parts) <= 1:
        return "".join(parts)
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return f"{', '.join(parts[:-1])}, and {parts[-1]}"


def format_upload_summary(uploaded_files) -> str:
    total_count = len(uploaded_files)
    csv_count = sum(1 for uploaded_file in uploaded_files if Path(uploaded_file.name).suffix.lower() == ".csv")
    pdf_count = sum(1 for uploaded_file in uploaded_files if Path(uploaded_file.name).suffix.lower() == ".pdf")

    parts: list[str] = []
    if csv_count:
        parts.append(pluralize_count(csv_count, "CSV transaction file"))
    if pdf_count:
        parts.append(pluralize_count(pdf_count, "statement PDF file"))

    if not parts:
        return f"Loaded {pluralize_count(total_count, 'file')}."
    if len(parts) == 1:
        return f"Loaded {parts[0]}."

    return f"Loaded {pluralize_count(total_count, 'file')}, including {join_summary_parts(parts)}."


def make_unique_source_names(source_names: list[str]) -> list[str]:
    totals: dict[str, int] = {}
    for source_name in source_names:
        totals[source_name] = totals.get(source_name, 0) + 1

    seen: dict[str, int] = {}
    unique_names: list[str] = []
    for source_name in source_names:
        seen[source_name] = seen.get(source_name, 0) + 1
        if totals[source_name] == 1:
            unique_names.append(source_name)
        else:
            unique_names.append(f"{source_name} ({seen[source_name]})")
    return unique_names


def classify_account(account: str) -> str:
    lower = account.strip().lower()
    if not lower:
        return "unknown"
    if any(kw in lower for kw in CREDIT_CARD_KEYWORDS):
        return "credit_card"
    if any(kw in lower for kw in BANK_ACCOUNT_KEYWORDS):
        return "bank_account"
    return "unknown"


def filter_credit_card_eligible_spending(spending_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split spending into (credit_card_eligible, bank_only).

    A transaction is bank-only when its Description never appears in any non-bank-account
    transaction, meaning it can't be paid by credit card.
    """
    if spending_df.empty or "Account" not in spending_df.columns:
        return spending_df, pd.DataFrame(columns=spending_df.columns)

    account_types = spending_df["Account"].fillna("").astype(str).map(classify_account)

    if not (account_types == "bank_account").any():
        return spending_df, pd.DataFrame(columns=spending_df.columns)

    cc_descriptions = set(
        spending_df.loc[account_types != "bank_account", "Description"].unique()
    )
    bank_only_mask = (account_types == "bank_account") & ~spending_df["Description"].isin(cc_descriptions)

    return spending_df[~bank_only_mask].copy(), spending_df[bank_only_mask].copy()


def annualization_factor(spending_df: pd.DataFrame) -> float:
    valid_dates = spending_df["Date"].dropna()
    if valid_dates.empty:
        return 1.0
    days = max((valid_dates.max() - valid_dates.min()).days + 1, 1)
    return 365.0 / days


def _standard_card_rewards(category: str, annualized_spend: float, card: dict) -> float:
    rate = card["category_rates"].get(category, card["default_rate"])
    cap = card["category_caps"].get(category)
    if cap is not None:
        return min(annualized_spend, cap) * rate + max(annualized_spend - cap, 0.0) * card["default_rate"]
    return annualized_spend * rate


def _best_rewards_across_cards(category: str, annualized_spend: float, cards: list[dict]) -> float:
    return max((_standard_card_rewards(category, annualized_spend, c) for c in cards), default=0.0)


def _quarterly_df(spending_df: pd.DataFrame) -> pd.DataFrame:
    df = spending_df.dropna(subset=["Date"]).copy()
    df["_Q"] = df["Date"].dt.quarter
    df["_Y"] = df["Date"].dt.year
    return df


def _estimate_quarterly_rewards(spending_df: pd.DataFrame, card: dict, factor: float) -> float:
    df = _quarterly_df(spending_df)
    if df.empty:
        return 0.0
    quarterly_cats = card["quarterly_categories"]
    cap = card["quarterly_cap"]
    bonus_rate = card["quarterly_bonus_rate"]
    default_rate = card["default_rate"]
    total = 0.0
    for (_, quarter), qdf in df.groupby(["_Y", "_Q"]):
        bonus_cats = set(quarterly_cats.get(quarter, []))
        cat_spends = qdf.groupby("Category")["Spend"].sum()
        bonus_spend = float(cat_spends[cat_spends.index.isin(bonus_cats)].sum())
        other_spend = float(cat_spends[~cat_spends.index.isin(bonus_cats)].sum())
        capped = min(bonus_spend, cap)
        overflow = max(bonus_spend - cap, 0.0)
        total += capped * bonus_rate + overflow * default_rate + other_spend * default_rate
    return total * factor


def estimate_card_annual_rewards(spending_df: pd.DataFrame, card: dict, factor: float | None = None) -> float:
    if spending_df.empty:
        return 0.0
    if factor is None:
        factor = annualization_factor(spending_df)
    if "quarterly_categories" in card:
        return _estimate_quarterly_rewards(spending_df, card, factor)
    default_rate = card.get("default_rate", 0.01)
    total = 0.0
    for category, spend in spending_df.groupby("Category")["Spend"].sum().items():
        total += _standard_card_rewards(str(category), float(spend) * factor, card)
    return total


def detect_credit_card_accounts(spending_df: pd.DataFrame) -> list[str]:
    if "Account" not in spending_df.columns:
        return []
    accounts = spending_df["Account"].fillna("").astype(str).unique()
    return sorted(a for a in accounts if a and classify_account(a) in ("credit_card", "unknown"))


def auto_match_account_to_card(account: str) -> str | None:
    account_lower = account.strip().lower()
    if account_lower in ACCOUNT_CARD_OVERRIDES:
        return ACCOUNT_CARD_OVERRIDES[account_lower]
    if "savor" in account_lower:
        return "Capital One Savor Cash Rewards"
    if "venture x" in account_lower:
        return "Capital One Venture X Rewards"
    if "venture" in account_lower:
        return "Capital One Venture Rewards"
    if "unlimited cash" in account_lower:
        return "BofA Unlimited Cash Rewards"
    if "customized cash" in account_lower or "custom cash" in account_lower:
        return "BofA Customized Cash Rewards (Dining)"
    if "discover it" in account_lower or ("discover" in account_lower and "bank" not in account_lower):
        return "Discover It Cash Back"
    for card in CREDIT_CARD_CATALOG:
        if card["name"].lower() in account_lower:
            return card["name"]
    return None


def build_card_recommendations(spending_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for card in CREDIT_CARD_CATALOG:
        annual_rewards = estimate_card_annual_rewards(spending_df, card)
        annual_fee = card["annual_fee"]
        statement_credits = card.get("statement_credits", 0)
        rows.append({
            "Card": card["name"],
            "Issuer": card["issuer"],
            "Est. Annual Rewards": annual_rewards,
            "Annual Fee": annual_fee,
            "Statement Credits": statement_credits if statement_credits else None,
            "Est. Net Value": annual_rewards - annual_fee,
        })
    return (
        pd.DataFrame(rows)
        .sort_values("Est. Net Value", ascending=False)
        .reset_index(drop=True)
    )


def build_card_category_breakdown(spending_df: pd.DataFrame, card: dict) -> pd.DataFrame:
    if spending_df.empty:
        return pd.DataFrame()
    factor = annualization_factor(spending_df)
    default_rate = card.get("default_rate", 0.01)
    rows = []

    if "quarterly_categories" in card:
        quarterly_cats = card["quarterly_categories"]
        bonus_rate = card["quarterly_bonus_rate"]
        cap = card["quarterly_cap"]
        all_bonus_cats: set[str] = {cat for cats in quarterly_cats.values() for cat in cats}
        active_quarters: dict[str, list[int]] = {}
        for q, cats in quarterly_cats.items():
            for cat in cats:
                active_quarters.setdefault(cat, []).append(q)
        df = _quarterly_df(spending_df)
        cat_rewards: dict[str, float] = {}
        cat_annualized: dict[str, float] = {}
        for (_, quarter), qdf in df.groupby(["_Y", "_Q"]):
            bonus_cats = set(quarterly_cats.get(quarter, []))
            cat_spends = qdf.groupby("Category")["Spend"].sum()
            bonus_spend = float(cat_spends[cat_spends.index.isin(bonus_cats)].sum())
            remaining = cap
            for category, spend in cat_spends.items():
                category = str(category)
                annualized = float(spend) * factor
                cat_annualized[category] = cat_annualized.get(category, 0.0) + annualized
                if category in bonus_cats and remaining > 0:
                    b = min(annualized, remaining)
                    ov = max(annualized - remaining, 0.0)
                    r = b * bonus_rate + ov * default_rate
                    remaining = max(remaining - annualized, 0.0)
                else:
                    r = annualized * default_rate
                cat_rewards[category] = cat_rewards.get(category, 0.0) + r
        for category, rewards in cat_rewards.items():
            ann_spend = cat_annualized.get(category, 0.0)
            eff_rate = rewards / ann_spend if ann_spend > 0 else default_rate
            qs = active_quarters.get(category, [])
            rate_label = f"{eff_rate * 100:.2g}% (5% in Q{'/Q'.join(str(q) for q in sorted(qs))})" if qs else f"{eff_rate * 100:.2g}%"
            rows.append({
                "Category": category,
                "Rate": rate_label,
                "Est. Annual Spend": ann_spend,
                "Est. Annual Rewards": rewards,
            })
    else:
        for category, spend in spending_df.groupby("Category")["Spend"].sum().items():
            category = str(category)
            annualized = float(spend) * factor
            rewards = _standard_card_rewards(category, annualized, card)
            rate = card["category_rates"].get(category, default_rate)
            rows.append({
                "Category": category,
                "Rate": f"{rate * 100:.2g}%",
                "Est. Annual Spend": annualized,
                "Est. Annual Rewards": rewards,
            })

    return (
        pd.DataFrame(rows)
        .sort_values("Est. Annual Rewards", ascending=False)
        .reset_index(drop=True)
    )


def estimate_combo_annual_rewards(spending_df: pd.DataFrame, cards: list[dict]) -> float:
    if spending_df.empty:
        return 0.0
    factor = annualization_factor(spending_df)
    standard_cards = [c for c in cards if "quarterly_categories" not in c]
    quarterly_cards = [c for c in cards if "quarterly_categories" in c]

    if not quarterly_cards:
        total = 0.0
        for category, spend in spending_df.groupby("Category")["Spend"].sum().items():
            total += _best_rewards_across_cards(str(category), float(spend) * factor, cards)
        return total

    # Process quarter by quarter to respect each quarterly card's per-quarter cap
    df = _quarterly_df(spending_df)
    if df.empty:
        return 0.0
    total = 0.0
    for (_, quarter), qdf in df.groupby(["_Y", "_Q"]):
        cat_spends = {
            str(cat): float(spend) * factor
            for cat, spend in qdf.groupby("Category")["Spend"].sum().items()
        }
        # Baseline: best rewards from standard cards only
        quarter_rewards = {
            cat: _best_rewards_across_cards(cat, spend, standard_cards)
            for cat, spend in cat_spends.items()
        }
        # Try to improve each category using quarterly cards
        for qc in quarterly_cards:
            bonus_cats = set(qc["quarterly_categories"].get(quarter, []))
            remaining_cap = qc["quarterly_cap"]
            bonus_rate = qc["quarterly_bonus_rate"]
            default_rate = qc["default_rate"]
            # Prioritise categories with the highest marginal gain per dollar
            candidates = []
            for cat in bonus_cats:
                if cat not in cat_spends:
                    continue
                spend = cat_spends[cat]
                std = quarter_rewards[cat]
                marginal_rate = bonus_rate - (std / spend if spend > 0 else 0)
                if marginal_rate > 0:
                    candidates.append((marginal_rate, cat, spend, std))
            candidates.sort(reverse=True)
            for _, cat, spend, std in candidates:
                if remaining_cap <= 0:
                    break
                bonus_spend = min(spend, remaining_cap)
                overflow = max(spend - remaining_cap, 0.0)
                qc_rewards = bonus_spend * bonus_rate + overflow * default_rate
                std_overflow = _best_rewards_across_cards(cat, overflow, standard_cards) if overflow > 0 else 0.0
                combined = bonus_spend * bonus_rate + std_overflow
                if combined > std:
                    quarter_rewards[cat] = combined
                remaining_cap = max(remaining_cap - spend, 0.0)
        total += sum(quarter_rewards.values())
    return total


def build_card_category_reward_lookup(spending_df: pd.DataFrame) -> tuple[list[str], dict[str, dict[str, float]]]:
    categories = spending_df["Category"].dropna().astype(str).unique().tolist()
    reward_lookup: dict[str, dict[str, float]] = {}

    for card in CREDIT_CARD_CATALOG:
        breakdown = build_card_category_breakdown(spending_df, card)
        rewards: dict[str, float] = {category: 0.0 for category in categories}
        if not breakdown.empty:
            for row in breakdown.to_dict("records"):
                rewards[str(row["Category"])] = float(row["Est. Annual Rewards"])
        reward_lookup[card["name"]] = rewards

    return categories, reward_lookup


def estimate_combo_annual_rewards_from_lookup(
    categories: list[str],
    reward_lookup: dict[str, dict[str, float]],
    cards: list[dict],
) -> float:
    card_names = [card["name"] for card in cards]
    total = 0.0
    for category in categories:
        total += max(
            (reward_lookup.get(card_name, {}).get(category, 0.0) for card_name in card_names),
            default=0.0,
        )
    return total


def build_combo_recommendations(spending_df: pd.DataFrame, card_count: int, top_n: int = 5) -> tuple[pd.DataFrame, list[list[dict]]]:
    ranked: list[tuple[float, float, float, float, list[dict]]] = []
    categories, reward_lookup = build_card_category_reward_lookup(spending_df)
    for combo in combinations(CREDIT_CARD_CATALOG, card_count):
        combo_list = list(combo)
        annual_rewards = estimate_combo_annual_rewards_from_lookup(categories, reward_lookup, combo_list)
        total_fee = sum(card["annual_fee"] for card in combo_list)
        statement_credits = sum(card.get("statement_credits", 0) for card in combo_list)
        net_value = annual_rewards - total_fee
        ranked.append((net_value, annual_rewards, total_fee, statement_credits, combo_list))
    ranked.sort(key=lambda x: x[0], reverse=True)

    rows = []
    card_combos: list[list[dict]] = []
    for net_value, annual_rewards, total_fee, statement_credits, combo_list in ranked[:top_n]:
        rows.append({
            "Cards": " + ".join(c["name"] for c in combo_list),
            "Est. Annual Rewards": annual_rewards,
            "Total Annual Fees": total_fee,
            "Statement Credits": statement_credits if statement_credits else None,
            "Est. Net Value": net_value,
        })
        card_combos.append(combo_list)
    return pd.DataFrame(rows), card_combos


def _quarterly_rewards_by_category(spending_df: pd.DataFrame, card: dict, factor: float) -> dict[str, float]:
    df = _quarterly_df(spending_df)
    if df.empty:
        return {}
    quarterly_cats = card["quarterly_categories"]
    cap = card["quarterly_cap"]
    bonus_rate = card["quarterly_bonus_rate"]
    default_rate = card["default_rate"]
    cat_rewards: dict[str, float] = {}
    for (_, quarter), qdf in df.groupby(["_Y", "_Q"]):
        bonus_cats = set(quarterly_cats.get(quarter, []))
        remaining = cap
        for category, spend in qdf.groupby("Category")["Spend"].sum().items():
            category = str(category)
            annualized = float(spend) * factor
            if category in bonus_cats and remaining > 0:
                b = min(annualized, remaining)
                r = b * bonus_rate + max(annualized - remaining, 0.0) * default_rate
                remaining = max(remaining - annualized, 0.0)
            else:
                r = annualized * default_rate
            cat_rewards[category] = cat_rewards.get(category, 0.0) + r
    return cat_rewards


def build_combo_category_breakdown(spending_df: pd.DataFrame, cards: list[dict]) -> pd.DataFrame:
    if spending_df.empty:
        return pd.DataFrame()
    factor = annualization_factor(spending_df)

    # Pre-compute per-category rewards for each card
    card_cat_rewards: dict[str, dict[str, float]] = {}
    for card in cards:
        if "quarterly_categories" in card:
            card_cat_rewards[card["name"]] = _quarterly_rewards_by_category(spending_df, card, factor)
        else:
            card_cat_rewards[card["name"]] = {}

    all_categories = spending_df["Category"].dropna().astype(str).unique()
    cat_annualized = {
        str(cat): float(spend) * factor
        for cat, spend in spending_df.groupby("Category")["Spend"].sum().items()
    }

    # Build lookup: card_name -> quarterly_categories for quarterly cards in this combo
    quarterly_cat_map: dict[str, dict[int, list[str]]] = {
        card["name"]: card["quarterly_categories"]
        for card in cards if "quarterly_categories" in card
    }

    rows = []
    for category in all_categories:
        annualized = cat_annualized.get(category, 0.0)
        best_rewards = 0.0
        best_card_name = ""
        best_rate = 0.0
        for card in cards:
            if "quarterly_categories" in card:
                rewards = card_cat_rewards[card["name"]].get(category, annualized * card["default_rate"])
            else:
                rewards = _standard_card_rewards(category, annualized, card)
            eff_rate = rewards / annualized if annualized > 0 else 0.0
            if rewards > best_rewards:
                best_rewards = rewards
                best_card_name = card["name"]
                best_rate = eff_rate

        # Determine when to use this card
        if best_card_name in quarterly_cat_map:
            active_quarters = sorted(
                q for q, cats in quarterly_cat_map[best_card_name].items()
                if category in cats
            )
            if active_quarters:
                quarter_labels = {1: "Q1 (Jan–Mar)", 2: "Q2 (Apr–Jun)", 3: "Q3 (Jul–Sep)", 4: "Q4 (Oct–Dec)"}
                when = " & ".join(quarter_labels[q] for q in active_quarters)
            else:
                when = "Annual"
        else:
            when = "Annual"

        rows.append({
            "Category": category,
            "Use Card": best_card_name,
            "When to Use": when,
            "Rate": f"{best_rate * 100:.2g}%",
            "Est. Annual Spend": annualized,
            "Est. Annual Rewards": best_rewards,
        })
    return (
        pd.DataFrame(rows)
        .sort_values("Est. Annual Rewards", ascending=False)
        .reset_index(drop=True)
    )


def format_reward_rate(rate: float) -> str:
    return f"{rate * 100:.2g}%"


def format_card_mapping(mapping: dict) -> str:
    if not mapping:
        return ""
    return "; ".join(
        f"{category}: {value}" for category, value in mapping.items()
    )


def card_catalog_context_csv() -> str:
    rows = []
    for card in CREDIT_CARD_CATALOG:
        quarterly_categories = card.get("quarterly_categories", {})
        quarterly_text = "; ".join(
            f"Q{quarter}: {', '.join(categories)}"
            for quarter, categories in quarterly_categories.items()
        )
        rows.append({
            "Card": card["name"],
            "Issuer": card["issuer"],
            "Annual Fee": card["annual_fee"],
            "Statement Credits": card.get("statement_credits", 0),
            "Statement Credits Detail": card.get("statement_credits_detail", ""),
            "Default Rate": format_reward_rate(card.get("default_rate", 0.0)),
            "Category Rates": format_card_mapping({
                category: format_reward_rate(rate)
                for category, rate in card.get("category_rates", {}).items()
            }),
            "Category Caps": format_card_mapping({
                category: f"${cap:,.0f}/yr"
                for category, cap in card.get("category_caps", {}).items()
            }),
            "Quarterly Bonus Rate": format_reward_rate(card.get("quarterly_bonus_rate", 0.0))
            if "quarterly_bonus_rate" in card else "",
            "Quarterly Cap": f"${card['quarterly_cap']:,.0f}/quarter" if "quarterly_cap" in card else "",
            "Quarterly Categories": quarterly_text,
            "Current Account All Spending Rate": format_reward_rate(card["all_spending_rate"])
            if "all_spending_rate" in card else "",
            "Notes": card.get("notes", ""),
        })
    return pd.DataFrame(rows).to_csv(index=False)


def annualized_category_summary(spending_df: pd.DataFrame) -> pd.DataFrame:
    summary = category_summary(spending_df)
    if summary.empty:
        return pd.DataFrame(columns=["Category", "Transactions", "Spend", "Est. Annual Spend"])
    factor = annualization_factor(spending_df)
    summary["Est. Annual Spend"] = summary["Spend"] * factor
    return summary


def build_current_card_accounts_context_df(
    eligible_df: pd.DataFrame,
    account_card_map: dict[str, str],
) -> pd.DataFrame:
    rows = []
    factor = annualization_factor(eligible_df)
    for account in detect_credit_card_accounts(eligible_df):
        account_df = eligible_df[eligible_df["Account"].fillna("").astype(str) == account]
        observed_spend = float(account_df["Spend"].sum()) if not account_df.empty else 0.0
        rows.append({
            "Account": account,
            "Auto Matched Card": auto_match_account_to_card(account) or "",
            "Selected Card": account_card_map.get(account, ""),
            "Observed Spend": observed_spend,
            "Est. Annual Spend": observed_spend * factor,
            "Transactions": len(account_df),
        })
    return pd.DataFrame(rows)


def build_current_card_performance_df(
    eligible_df: pd.DataFrame,
    account_card_map: dict[str, str],
) -> pd.DataFrame:
    if eligible_df.empty or not account_card_map:
        return pd.DataFrame(
            columns=["Account", "Card", "Est. Annual Rewards", "Annual Fee", "Statement Credits", "Est. Net Value"]
        )

    global_factor = annualization_factor(eligible_df)
    rows = []
    for account, card_name in account_card_map.items():
        card = next((c for c in CREDIT_CARD_CATALOG if c["name"] == card_name), None)
        if card is None:
            continue
        account_df = eligible_df[eligible_df["Account"].fillna("").astype(str) == account]
        if "all_spending_rate" in card:
            annual_rewards = float(account_df["Spend"].sum()) * global_factor * card["all_spending_rate"]
        else:
            annual_rewards = estimate_card_annual_rewards(account_df, card, factor=global_factor)
        rows.append({
            "Account": account,
            "Card": card_name,
            "Est. Annual Rewards": annual_rewards,
            "Annual Fee": float(card["annual_fee"]),
            "Statement Credits": card.get("statement_credits") or None,
            "Est. Net Value": annual_rewards - card["annual_fee"],
        })

    if not rows:
        return pd.DataFrame(
            columns=["Account", "Card", "Est. Annual Rewards", "Annual Fee", "Statement Credits", "Est. Net Value"]
        )

    rows.append({
        "Account": "Total",
        "Card": "",
        "Est. Annual Rewards": sum(r["Est. Annual Rewards"] for r in rows),
        "Annual Fee": sum(r["Annual Fee"] for r in rows),
        "Statement Credits": sum(float(r["Statement Credits"] or 0) for r in rows) or None,
        "Est. Net Value": sum(r["Est. Net Value"] for r in rows),
    })
    return pd.DataFrame(rows)


def current_total_net_value(current_performance: pd.DataFrame) -> float | None:
    if current_performance.empty or "Est. Net Value" not in current_performance.columns:
        return None

    if "Account" in current_performance.columns:
        total_rows = current_performance[current_performance["Account"].astype(str) == "Total"]
        if not total_rows.empty:
            return float(total_rows.iloc[0]["Est. Net Value"])

    return float(current_performance["Est. Net Value"].sum())


def application_decision(delta: float | None) -> str:
    if delta is None:
        return "Select current cards to compare"
    if delta >= 100:
        return "Yes - meaningful estimated gain"
    if delta > 0:
        return "Maybe - small estimated gain"
    if delta == 0:
        return "No - no net-value improvement"
    return "No - current setup is better"


def combo_option_label(card_count: int) -> str:
    return f"Best {card_count}-card combo"


def combo_tab_label(card_count: int) -> str:
    return f"Best {card_count}-Card Combo"


def combo_assignment_caption(card_count: int) -> str:
    combo_name = {2: "pair", 3: "trio"}.get(card_count, f"{card_count}-card combo")
    return f"Each spending category is assigned to whichever card in the {combo_name} earns the highest rate for it."


def build_application_value_summary(spending_df: pd.DataFrame, account_card_map: dict[str, str]) -> pd.DataFrame:
    current_performance = build_current_card_performance_df(spending_df, account_card_map)
    current_net = current_total_net_value(current_performance)
    rows: list[dict[str, object]] = []

    if current_net is not None:
        rows.append({
            "Option": "Current selected cards",
            "Cards": "Current setup",
            "Est. Net Value": current_net,
            "Gain vs Current": 0.0,
            "Decision": "Baseline",
        })

    single_recs = build_card_recommendations(spending_df)
    if not single_recs.empty:
        top_single = single_recs.iloc[0]
        single_net = float(top_single["Est. Net Value"])
        delta = single_net - current_net if current_net is not None else None
        rows.append({
            "Option": "Best single card",
            "Cards": top_single["Card"],
            "Est. Net Value": single_net,
            "Gain vs Current": delta,
            "Decision": application_decision(delta),
        })

    for card_count in COMBO_CARD_COUNTS:
        combo_recs, _card_combos = build_combo_recommendations(spending_df, card_count, top_n=1)
        if combo_recs.empty:
            continue
        top_combo = combo_recs.iloc[0]
        combo_net = float(top_combo["Est. Net Value"])
        delta = combo_net - current_net if current_net is not None else None
        rows.append({
            "Option": combo_option_label(card_count),
            "Cards": top_combo["Cards"],
            "Est. Net Value": combo_net,
            "Gain vs Current": delta,
            "Decision": application_decision(delta),
        })

    return pd.DataFrame(rows)


def render_application_value_summary(spending_df: pd.DataFrame, account_card_map: dict[str, str]) -> None:
    summary = build_application_value_summary(spending_df, account_card_map)
    if summary.empty:
        return

    st.subheader("Should You Apply?")
    current_rows = summary[summary["Option"] == "Current selected cards"]
    comparison_rows = summary[summary["Option"] != "Current selected cards"].copy()

    if current_rows.empty:
        st.caption(
            "Select your current cards above to compare the top recommendations against your current total net value."
        )
    elif not comparison_rows.empty:
        best_option = comparison_rows.sort_values("Est. Net Value", ascending=False).iloc[0]
        best_delta = float(best_option["Gain vs Current"])
        if best_delta > 0:
            st.success(
                f"{best_option['Option']} has the highest estimated net value: "
                f"{money(float(best_option['Est. Net Value']))}, about {money(best_delta)} more per year "
                "than your selected current cards."
            )
        else:
            st.info(
                "Based on estimated annual net value, your selected current cards are already competitive. "
                f"The best new option is {money(abs(best_delta))} lower per year."
            )

    st.dataframe(
        summary,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Est. Net Value": st.column_config.NumberColumn("Est. Net Value", format="$%.2f"),
            "Gain vs Current": st.column_config.NumberColumn("Gain vs Current", format="$%.2f"),
        },
    )
    st.caption(
        "This compares modeled annual rewards minus annual fees. Statement credits, signup bonuses, "
        "approval odds, and credit-score impact are not included in the net-value decision."
    )


def payoff_time_text(payoff: dict[str, float | int | bool]) -> str:
    return f"{float(payoff['years']):.1f} years" if payoff["paid_off"] else "50+ years"


def balance_transfer_fee(balance: float, card: dict) -> float:
    if balance <= 0:
        return 0.0
    fee_rate = float(card.get("balance_transfer_fee_rate", 0.0) or 0.0)
    fee_min = float(card.get("balance_transfer_fee_min", 0.0) or 0.0)
    if fee_rate <= 0:
        return 0.0
    return max(balance * fee_rate, fee_min)


def balance_transfer_intro_months(card: dict) -> int:
    return int(card.get("balance_transfer_intro_months", 0) or 0)


def simulate_payment_payoff_with_intro(
    balance: float,
    regular_apr: float,
    intro_months: int,
    payment_method: str,
    minimum_percent: float | None = None,
    monthly_payment_amount: float | None = None,
    upfront_fee: float = 0.0,
    percent_payment_floor: float = PERCENT_BALANCE_PAYMENT_FLOOR,
    max_months: int = 600,
) -> dict[str, float | int | bool]:
    current_balance = max(balance, 0.0) + max(upfront_fee, 0.0)
    regular_monthly_rate = max(regular_apr, 0.0) / 12.0
    total_interest = 0.0
    total_paid = 0.0
    months = 0

    if current_balance > 0 and payment_method == "Fixed dollar amount" and float(monthly_payment_amount or 0.0) <= 0:
        return {
            "months": max_months,
            "years": max_months / 12.0,
            "total_interest": 0.0,
            "total_paid": 0.0,
            "remaining_balance": current_balance,
            "paid_off": False,
            "starting_balance": current_balance,
            "upfront_fee": max(upfront_fee, 0.0),
        }

    while current_balance > 0.01 and months < max_months:
        beginning_balance = current_balance
        monthly_rate = 0.0 if months < intro_months else regular_monthly_rate
        interest = beginning_balance * monthly_rate
        amount_due = beginning_balance + interest

        if payment_method == "Percent of balance":
            percent_payment = beginning_balance * (float(minimum_percent or 0.0) / 100.0)
            payment = max(percent_payment, max(percent_payment_floor, 0.0))
        else:
            payment = float(monthly_payment_amount or 0.0)

        if payment <= interest and amount_due > payment and monthly_rate > 0:
            total_interest += interest
            months += 1
            return {
                "months": max_months,
                "years": max_months / 12.0,
                "total_interest": total_interest,
                "total_paid": total_paid,
                "remaining_balance": amount_due,
                "paid_off": False,
                "starting_balance": max(balance, 0.0) + max(upfront_fee, 0.0),
                "upfront_fee": max(upfront_fee, 0.0),
            }

        payment = min(max(payment, 0.0), amount_due)
        current_balance = amount_due - payment
        total_interest += interest
        total_paid += payment
        months += 1

    return {
        "months": months,
        "years": months / 12.0,
        "total_interest": total_interest,
        "total_paid": total_paid,
        "remaining_balance": current_balance,
        "paid_off": current_balance <= 0.01,
        "starting_balance": max(balance, 0.0) + max(upfront_fee, 0.0),
        "upfront_fee": max(upfront_fee, 0.0),
    }


def payment_detail_text(
    payment_method: str,
    minimum_percent: float | None = None,
    monthly_payment_amount: float | None = None,
) -> str:
    if payment_method == "Percent of balance":
        percent = float(minimum_percent or 0.0)
        return f"{percent:.1f}% of balance, {money(PERCENT_BALANCE_PAYMENT_FLOOR)} min"
    return f"{money(float(monthly_payment_amount or 0.0))} monthly"


def current_apr_baseline_df(
    balance: float,
    current_apr_percent: float,
    payment_method: str,
    minimum_percent: float | None = None,
    monthly_payment_amount: float | None = None,
) -> pd.DataFrame:
    current_apr = max(float(current_apr_percent), 0.0) / 100.0
    payoff = simulate_payment_payoff_with_intro(
        balance,
        current_apr,
        intro_months=0,
        payment_method=payment_method,
        minimum_percent=minimum_percent,
        monthly_payment_amount=monthly_payment_amount,
    )
    paid_off = bool(payoff["paid_off"])
    return pd.DataFrame([{
        "Current Balance": money(balance),
        "Current APR": f"{current_apr_percent:.2f}%",
        "Monthly Interest Rate": f"{current_apr / 12.0:.3%}",
        "Payment Detail": payment_detail_text(payment_method, minimum_percent, monthly_payment_amount),
        "Estimated Interest": money(float(payoff["total_interest"])) if paid_off else "Not paid off",
        "Total Amount of Payments": money(float(payoff["total_paid"])) if paid_off else "Not paid off",
        "Estimated Payoff Time": payoff_time_text(payoff),
    }])


def apr_cards_df(
    balance: float | None = None,
    payment_method: str | None = None,
    minimum_percent: float | None = None,
    monthly_payment_amount: float | None = None,
    current_apr_percent: float | None = None,
) -> pd.DataFrame:
    rows = []
    has_payoff_inputs = balance is not None and payment_method is not None

    def payoff_fields(regular_apr: float, intro_months: int, transfer_fee: float) -> dict:
        if payment_method == "Percent of balance":
            percent = float(minimum_percent or 0.0)
            payoff = simulate_payment_payoff_with_intro(
                balance or 0.0,
                regular_apr,
                intro_months,
                payment_method or "",
                minimum_percent=percent,
                upfront_fee=transfer_fee,
            )
            monthly_payment_display = payment_detail_text(payment_method or "", percent)
        else:
            payment_amount = float(monthly_payment_amount or 0.0)
            payoff = simulate_payment_payoff_with_intro(
                balance or 0.0,
                regular_apr,
                intro_months,
                payment_method or "",
                monthly_payment_amount=payment_amount,
                upfront_fee=transfer_fee,
            )
            monthly_payment_display = payment_detail_text(payment_method or "", monthly_payment_amount=payment_amount)

        starting_balance = float(payoff["starting_balance"])
        intro_payoff_payment = starting_balance / intro_months if intro_months > 0 else None
        apr_months_used = max(int(payoff["months"]) - intro_months, 0)
        estimated_interest = float(payoff["total_interest"]) if payoff["paid_off"] else None
        total_cost = estimated_interest + transfer_fee if estimated_interest is not None else None
        return {
            "Monthly Payment": monthly_payment_display,
            "Intro Months Used": intro_months,
            "APR Months Used": apr_months_used,
            "Monthly Payment to Avoid Interest": intro_payoff_payment,
            "Regular APR After Intro": regular_apr,
            "Estimated Transfer Fee": transfer_fee,
            "Starting Balance After Fee": starting_balance,
            "Estimated Interest": estimated_interest,
            "Total Cost": total_cost,
            "Estimated Payoff Time": payoff_time_text(payoff),
        }

    if has_payoff_inputs and current_apr_percent is not None:
        current_apr = max(float(current_apr_percent), 0.0) / 100.0
        current_row = {
            "Card": "Your current credit card",
            "Issuer": "Current",
            "Annual Fee": None,
            "Balance Transfer Intro APR": "No intro APR",
            "Regular APR": f"{float(current_apr_percent):.2f}%",
            "Balance Transfer Fee": "$0",
            "Rewards": "Current card payoff comparison",
        }
        current_row.update(payoff_fields(current_apr, 0, 0.0))
        rows.append(current_row)

    for card in APR_CARD_CATALOG:
        row = {
            "Card": card["name"],
            "Issuer": card["issuer"],
            "Annual Fee": card["annual_fee"],
            "Balance Transfer Intro APR": card["balance_transfer_intro_apr"],
            "Regular APR": card["regular_apr"],
            "Balance Transfer Fee": card["balance_transfer_fee"],
            "Rewards": card["rewards"],
        }
        if has_payoff_inputs:
            regular_apr = float(card["regular_apr_min"])
            intro_months = balance_transfer_intro_months(card)
            transfer_fee = balance_transfer_fee(balance, card)
            row.update(payoff_fields(regular_apr, intro_months, transfer_fee))
        rows.append(row)
    return pd.DataFrame(rows)


def render_best_apr_recommendations(
    balance: float | None = None,
    payment_method: str | None = None,
    minimum_percent: float | None = None,
    monthly_payment_amount: float | None = None,
    current_apr_percent: float | None = None,
) -> None:
    st.subheader("Best APR Options")
    st.caption(
        "Use this view when you expect to carry a balance. Exact APR and approval terms depend on "
        "creditworthiness and issuer underwriting; balance-transfer fee and intro APR terms should be "
        "verified before applying."
    )
    apr_df = apr_cards_df(balance, payment_method, minimum_percent, monthly_payment_amount, current_apr_percent)
    st.dataframe(
        apr_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Annual Fee": st.column_config.NumberColumn("Annual Fee", format="$%.0f"),
            "Regular APR After Intro": st.column_config.NumberColumn("Regular APR After Intro", format="%.2%"),
            "Monthly Payment to Avoid Interest": st.column_config.NumberColumn("Monthly Payment to Avoid Interest", format="$%.2f"),
            "Estimated Transfer Fee": st.column_config.NumberColumn("Estimated Transfer Fee", format="$%.2f"),
            "Starting Balance After Fee": st.column_config.NumberColumn("Starting Balance After Fee", format="$%.2f"),
            "Estimated Interest": st.column_config.NumberColumn("Estimated Interest", format="$%.2f"),
            "Total Cost": st.column_config.NumberColumn("Total Cost", format="$%.2f"),
        },
    )


def render_best_apr_summary(apr_df: pd.DataFrame, current_apr_percent: float, balance: float, payment_method: str) -> None:
    if apr_df.empty or "Total Cost" not in apr_df.columns:
        return

    card_options = apr_df[apr_df["Card"] != "Your current credit card"].copy()
    card_options = card_options[pd.notna(card_options["Total Cost"])]
    if card_options.empty:
        st.warning(
            "Based on your current APR, balance, and payment style, none of the modeled card options fully "
            "pay off within the model window. Try a higher monthly payment to compare lowest-cost cards."
        )
        return

    lowest_cost = float(card_options["Total Cost"].min())
    best_options = card_options[card_options["Total Cost"] == lowest_cost].sort_values("Card")
    best_card_names = best_options["Card"].tolist()
    if len(best_card_names) == 1:
        card_text = best_card_names[0]
    elif len(best_card_names) == 2:
        card_text = " and ".join(best_card_names)
    else:
        card_text = ", ".join(best_card_names[:-1]) + f", and {best_card_names[-1]}"

    payoff_time = best_options.iloc[0]["Estimated Payoff Time"]
    baseline = apr_df[apr_df["Card"] == "Your current credit card"]
    savings_text = ""
    if not baseline.empty and pd.notna(baseline.iloc[0].get("Total Cost")):
        baseline_cost = float(baseline.iloc[0]["Total Cost"])
        savings = baseline_cost - lowest_cost
        if savings > 0:
            savings_text = f" That is about {money(savings)} less than staying with your current card."

    st.markdown(
        f"**Lowest cost summary:** Based on your current APR ({current_apr_percent:.2f}%), "
        f"credit card balance ({money(balance)}), and payment style ({payment_method}), we believe "
        f"{card_text} could offer the lowest modeled cost: {money(lowest_cost)} total cost with an estimated "
        f"payoff time of {payoff_time}.{savings_text}"
    )


def simulate_minimum_payment_payoff(
    balance: float,
    apr: float,
    minimum_percent: float,
    minimum_floor: float,
    max_months: int = 600,
) -> dict[str, float | int | bool]:
    current_balance = max(balance, 0.0)
    monthly_rate = max(apr, 0.0) / 12.0
    total_interest = 0.0
    total_paid = 0.0
    months = 0

    while current_balance > 0.01 and months < max_months:
        interest = current_balance * monthly_rate
        current_balance += interest
        minimum_payment = max(current_balance * minimum_percent, minimum_floor)
        payment = min(minimum_payment, current_balance)
        current_balance -= payment
        total_interest += interest
        total_paid += payment
        months += 1

    return {
        "months": months,
        "years": months / 12.0,
        "total_interest": total_interest,
        "total_paid": total_paid,
        "remaining_balance": current_balance,
        "paid_off": current_balance <= 0.01,
    }


def simulate_fixed_payment_payoff(
    balance: float,
    apr: float,
    monthly_payment: float,
    max_months: int = 600,
) -> dict[str, float | int | bool]:
    current_balance = max(balance, 0.0)
    payment_amount = max(monthly_payment, 0.0)
    monthly_rate = max(apr, 0.0) / 12.0
    total_interest = 0.0
    total_paid = 0.0
    months = 0

    if current_balance > 0 and payment_amount <= 0:
        return {
            "months": max_months,
            "years": max_months / 12.0,
            "total_interest": 0.0,
            "total_paid": 0.0,
            "remaining_balance": current_balance,
            "paid_off": False,
        }

    while current_balance > 0.01 and months < max_months:
        interest = current_balance * monthly_rate
        current_balance += interest
        if payment_amount <= interest and current_balance > payment_amount:
            total_interest += interest
            months += 1
            return {
                "months": max_months,
                "years": max_months / 12.0,
                "total_interest": total_interest,
                "total_paid": total_paid,
                "remaining_balance": current_balance,
                "paid_off": False,
            }
        payment = min(payment_amount, current_balance)
        current_balance -= payment
        total_interest += interest
        total_paid += payment
        months += 1

    return {
        "months": months,
        "years": months / 12.0,
        "total_interest": total_interest,
        "total_paid": total_paid,
        "remaining_balance": current_balance,
        "paid_off": current_balance <= 0.01,
    }


def render_minimum_payment_recommendations(spending_df: pd.DataFrame) -> None:
    st.subheader("If You Usually Pay the Minimum or a Partial Payment")
    st.warning(
        "For minimum or partial-payment behavior, optimize for interest cost first. Rewards cards can be a bad fit "
        "if you regularly carry a balance."
    )

    st.markdown("**Current card details**")
    current_apr_percent = st.number_input(
        "What's your current credit card APR (%)?",
        min_value=0.0,
        max_value=100.0,
        value=24.99,
        step=0.1,
        format="%.2f",
        key="current_credit_card_apr",
    )

    st.markdown("**Payment details**")
    balance = st.number_input(
        "Current credit card balance",
        min_value=0.0,
        value=5000.0,
        step=100.0,
        format="%.2f",
        key="minimum_payment_balance",
    )

    method_col, amount_col, _ = st.columns([1.35, 1.05, 2.6], gap="small")
    with method_col:
        payment_method = st.radio(
            "Payment style",
            ["Percent of balance", "Fixed dollar amount"],
            horizontal=True,
            key="minimum_payment_method",
        )
    with amount_col:
        if payment_method == "Percent of balance":
            minimum_percent = st.number_input(
                "Percent of balance to pay each month",
                min_value=0.1,
                max_value=100.0,
                value=2.0,
                step=0.1,
                format="%.1f",
                key="minimum_payment_percent",
            )
            monthly_payment_amount = 0.0
        else:
            minimum_percent = 0.0
            monthly_payment_amount = st.number_input(
                "Dollar amount to pay each month",
                min_value=0.0,
                value=250.0,
                step=25.0,
                format="%.2f",
                key="minimum_payment_amount",
            )

    st.markdown("**Current card payoff baseline**")
    st.dataframe(
        current_apr_baseline_df(
            balance=balance,
            current_apr_percent=current_apr_percent,
            payment_method=payment_method,
            minimum_percent=minimum_percent,
            monthly_payment_amount=monthly_payment_amount,
        ),
        hide_index=True,
        use_container_width=True,
    )
    apr_df = apr_cards_df(
        balance=balance,
        payment_method=payment_method,
        minimum_percent=minimum_percent,
        monthly_payment_amount=monthly_payment_amount,
        current_apr_percent=current_apr_percent,
    )
    render_best_apr_summary(
        apr_df=apr_df,
        current_apr_percent=current_apr_percent,
        balance=balance,
        payment_method=payment_method,
    )

    render_best_apr_recommendations(
        balance=balance,
        payment_method=payment_method,
        minimum_percent=minimum_percent,
        monthly_payment_amount=monthly_payment_amount,
        current_apr_percent=current_apr_percent,
    )


def single_card_breakdowns_context(spending_df: pd.DataFrame, recs: pd.DataFrame, count: int = 5) -> str:
    if recs.empty:
        return "No single-card recommendation rows are available."

    sections = []
    for card_name in recs.head(count)["Card"].tolist():
        card = next((c for c in CREDIT_CARD_CATALOG if c["name"] == card_name), None)
        if card is None:
            continue
        breakdown = build_card_category_breakdown(spending_df, card)
        if breakdown.empty:
            continue
        sections.append(f"{card_name} category rewards CSV:\n{breakdown.to_csv(index=False)}")
    return "\n".join(sections) if sections else "No single-card category breakdowns are available."


def combo_breakdowns_context(
    spending_df: pd.DataFrame,
    combos_df: pd.DataFrame,
    card_combos: list[list[dict]],
    count: int = 3,
) -> str:
    if combos_df.empty or not card_combos:
        return "No combo recommendation rows are available."

    sections = []
    for index, combo in enumerate(card_combos[:count]):
        label = str(combos_df.iloc[index]["Cards"]) if index < len(combos_df) else " + ".join(
            card["name"] for card in combo
        )
        breakdown = build_combo_category_breakdown(spending_df, combo)
        if breakdown.empty:
            continue
        sections.append(f"{label} category assignments CSV:\n{breakdown.to_csv(index=False)}")
    return "\n".join(sections) if sections else "No combo category breakdowns are available."


def build_card_recommendation_context(
    all_spending_df: pd.DataFrame,
    eligible_df: pd.DataFrame,
    bank_only_df: pd.DataFrame,
    account_card_map: dict[str, str],
) -> str:
    recommendation_knowledge = load_knowledge_text(
        str(CARD_RECOMMENDATIONS_PATH),
        file_cache_signature(CARD_RECOMMENDATIONS_PATH),
    )
    recs = build_card_recommendations(eligible_df)
    combo_context_sections = []
    for card_count in COMBO_CARD_COUNTS:
        combos_df, card_combos = build_combo_recommendations(eligible_df, card_count)
        combo_context_sections.append(
            f"""Best {card_count}-card combo recommendations CSV:
{combos_df.to_csv(index=False)}

Top {card_count}-card combo category assignments:
{combo_breakdowns_context(eligible_df, combos_df, card_combos, count=2)}
"""
        )
    current_accounts = build_current_card_accounts_context_df(eligible_df, account_card_map)
    current_performance = build_current_card_performance_df(eligible_df, account_card_map)

    eligible_factor = annualization_factor(eligible_df)
    all_spend = float(all_spending_df["Spend"].sum()) if not all_spending_df.empty else 0.0
    eligible_spend = float(eligible_df["Spend"].sum()) if not eligible_df.empty else 0.0
    bank_only_spend = float(bank_only_df["Spend"].sum()) if not bank_only_df.empty else 0.0

    context = f"""Credit card recommendation context

Scope rules:
- This tab answers only credit card recommendation questions.
- Use the cleaned `Category` column for reward estimates. Do not re-infer categories from merchant names.
- Credit card payments/paybacks were already removed from spending.
- Recommendation tables use credit-card-eligible spending only. Bank-account-only merchants are excluded.
- Reward estimates are annualized to a full year using the observed eligible spending date range.
- Statement credits are shown for reference but are not deducted from estimated net value in this app.
- Use the tables below as the source of truth. If a question cannot be answered from them, say so.

Credit card reward knowledge:
{recommendation_knowledge or "No credit card reward knowledge loaded."}

Spending window:
All spending rows: {len(all_spending_df):,}
All spending date range: {date_range_text(all_spending_df)}
All observed spending: {money(all_spend)}
Eligible spending rows: {len(eligible_df):,}
Eligible spending date range: {date_range_text(eligible_df)}
Eligible observed spending: {money(eligible_spend)}
Eligible annualization factor: {eligible_factor:.4f}
Bank-only excluded rows: {len(bank_only_df):,}
Bank-only excluded observed spending: {money(bank_only_spend)}

Eligible annualized category summary CSV:
{annualized_category_summary(eligible_df).to_csv(index=False)}

Bank-only excluded category summary CSV:
{annualized_category_summary(bank_only_df).to_csv(index=False)}

Detected current card accounts CSV:
{current_accounts.to_csv(index=False)}

Selected current card performance CSV:
{current_performance.to_csv(index=False)}

Card catalog and reward assumptions CSV:
{card_catalog_context_csv()}

Best single card recommendations CSV:
{recs.to_csv(index=False)}

Top single card category breakdowns:
{single_card_breakdowns_context(eligible_df, recs)}

Best 2- through 6-card combo recommendations and category assignments:
{"".join(combo_context_sections)}
"""
    if len(context) > CARD_RECOMMENDATION_CONTEXT_CHAR_LIMIT:
        context = (
            context[:CARD_RECOMMENDATION_CONTEXT_CHAR_LIMIT]
            + "\n[Credit card recommendation context truncated because it exceeded the chat context budget.]\n"
        )
    return context


def ask_openai_card_recommendation_question(
    question: str,
    all_spending_df: pd.DataFrame,
    eligible_df: pd.DataFrame,
    bank_only_df: pd.DataFrame,
    account_card_map: dict[str, str],
    previous_messages: list[dict[str, str]],
) -> str:
    load_local_env()
    if not os.getenv("OPENAI_API_KEY"):
        return "OpenAI API key not found. Add `OPENAI_API_KEY=...` to `.env` and rerun the app."

    try:
        from openai import OpenAI
    except ImportError:
        return "OpenAI Python SDK is not installed. Run `pip install -e .` and rerun the app."

    model = get_openai_model()
    client = OpenAI()
    recommendation_context = build_card_recommendation_context(
        all_spending_df,
        eligible_df,
        bank_only_df,
        account_card_map,
    )
    prompt = f"""{recommendation_context}

Recent chat history:
{recent_chat_history(previous_messages)}

User question:
{question}
"""

    try:
        response = client.responses.create(
            model=model,
            instructions=(
                "You are a credit card recommendation assistant. "
                "Only answer questions about card recommendations, reward estimates, card combinations, "
                "current-card performance, annualization, reward assumptions, or eligible spending needed "
                "for those recommendations. If the user asks about unrelated spending analysis or another "
                "topic, briefly say you can only answer credit card recommendation questions in this tab. "
                "Use only the provided context, do not invent reward rates, and keep answers concise."
            ),
            input=prompt,
            max_output_tokens=900,
        )
    except Exception as exc:
        return f"OpenAI API request failed: {exc}"

    answer = getattr(response, "output_text", "").strip()
    return answer or "OpenAI returned an empty response."


def render_recommendation_chat(
    all_spending_df: pd.DataFrame,
    eligible_df: pd.DataFrame,
    bank_only_df: pd.DataFrame,
    account_card_map: dict[str, str],
    input_key: str = "recommendation_chat_input",
) -> None:
    selected_cards_signature = "|".join(
        f"{account}={card}" for account, card in sorted(account_card_map.items())
    )
    recommendation_signature = (
        f"{len(all_spending_df)}:{len(eligible_df)}:"
        f"{eligible_df['Spend'].sum() if not eligible_df.empty else 0}:"
        f"{date_range_text(eligible_df)}:{selected_cards_signature}"
    )

    if st.session_state.get("recommendation_data_signature") != recommendation_signature:
        st.session_state.recommendation_data_signature = recommendation_signature
        st.session_state.recommendation_messages = [
            {
                "role": "assistant",
                "content": (
                    "Ask a credit card recommendation question. I will answer using the card catalog, "
                    "reward assumptions, and cleaned spending data loaded in this app."
                ),
            }
        ]
    elif "recommendation_messages" not in st.session_state:
        st.session_state.recommendation_messages = [
            {
                "role": "assistant",
                "content": (
                    "Ask a credit card recommendation question. I will answer using the card catalog, "
                    "reward assumptions, and cleaned spending data loaded in this app."
                ),
            }
        ]

    st.subheader("Chat")
    with st.container(height=420, border=True, autoscroll=True):
        for message in st.session_state.recommendation_messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    question = st.chat_input(
        "Ask a credit card recommendation question",
        key=input_key,
    )
    if question:
        previous_messages = list(st.session_state.recommendation_messages)
        st.session_state.recommendation_messages.append({"role": "user", "content": question})
        with st.spinner("Asking OpenAI..."):
            answer = ask_openai_card_recommendation_question(
                question,
                all_spending_df,
                eligible_df,
                bank_only_df,
                account_card_map,
                previous_messages,
            )
        st.session_state.recommendation_messages.append({"role": "assistant", "content": answer})
        st.rerun()


def render_combo_section(
    spending_df: pd.DataFrame,
    card_count: int,
    all_spending_df: pd.DataFrame,
    bank_only_df: pd.DataFrame,
    account_card_map: dict[str, str],
) -> None:
    st.caption(combo_assignment_caption(card_count))
    combos_df, card_combos = build_combo_recommendations(spending_df, card_count)
    if combos_df.empty:
        return
    st.dataframe(
        combos_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Est. Annual Rewards": st.column_config.NumberColumn("Est. Annual Rewards", format="$%.2f"),
            "Total Annual Fees": st.column_config.NumberColumn("Total Annual Fees", format="$%.0f"),
            "Statement Credits": st.column_config.NumberColumn("Statement Credits", format="$%.0f"),
            "Est. Net Value": st.column_config.NumberColumn("Est. Net Value", format="$%.2f"),
        },
    )
    combo_labels = combos_df["Cards"].tolist()
    selected_label = st.selectbox(
        "Show category breakdown for:",
        combo_labels,
        key=f"combo_{card_count}_breakdown_select",
    )
    selected_idx = combo_labels.index(selected_label)
    selected_combo = card_combos[selected_idx]
    breakdown = build_combo_category_breakdown(spending_df, selected_combo)
    breakdown_col, chat_col = st.columns([1.2, 0.8], gap="large")
    with breakdown_col:
        if not breakdown.empty:
            st.markdown(f"**Category assignments: {selected_label}**")
            st.dataframe(
                breakdown,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Est. Annual Spend": st.column_config.NumberColumn("Est. Annual Spend", format="$%.2f"),
                    "Est. Annual Rewards": st.column_config.NumberColumn("Est. Annual Rewards", format="$%.2f"),
                },
            )
    with chat_col:
        render_recommendation_chat(
            all_spending_df,
            spending_df,
            bank_only_df,
            account_card_map,
            input_key=f"recommendation_chat_input_combo_{card_count}",
        )


def render_current_card_performance(eligible_df: pd.DataFrame) -> dict[str, str]:
    st.subheader("Your Current Cards")

    cc_accounts = detect_credit_card_accounts(eligible_df)
    if not cc_accounts:
        st.info("No credit card accounts detected in the loaded data.")
        return {}

    card_options = ["— select card —"] + [c["name"] for c in CREDIT_CARD_CATALOG]

    account_card_map: dict[str, str] = {}
    for account in cc_accounts:
        auto = auto_match_account_to_card(account)
        default_idx = card_options.index(auto) if auto and auto in card_options else 0
        key = f"current_card_{account}"
        if st.session_state.get(key) not in card_options and key in st.session_state:
            del st.session_state[key]
        selected = st.selectbox(
            f"Account: **{account}**",
            card_options,
            index=default_idx,
            key=key,
        )
        if selected != "— select card —":
            account_card_map[account] = selected

    if not account_card_map:
        st.caption("Select a card for each account above to see current reward estimates.")
        return {}

    current_performance = build_current_card_performance_df(eligible_df, account_card_map)
    if current_performance.empty:
        return account_card_map
    st.dataframe(
        current_performance,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Est. Annual Rewards": st.column_config.NumberColumn("Est. Annual Rewards", format="$%.2f"),
            "Annual Fee": st.column_config.NumberColumn("Annual Fee", format="$%.0f"),
            "Statement Credits": st.column_config.NumberColumn("Statement Credits", format="$%.0f"),
            "Est. Net Value": st.column_config.NumberColumn("Est. Net Value", format="$%.2f"),
        },
    )
    return account_card_map


def render_card_recommendations(spending_df: pd.DataFrame) -> None:
    if spending_df.empty:
        st.write("No spending data available for recommendations.")
        return

    valid_dates = spending_df["Date"].dropna()
    if valid_dates.empty:
        return

    all_spending_df = spending_df
    eligible_df, bank_only_df = filter_credit_card_eligible_spending(spending_df)

    days = (valid_dates.max() - valid_dates.min()).days + 1
    months = days / 30.44
    st.caption(
        f"Estimates based on {months:.1f} months of data, annualized to a full year. "
        "Reward rates use cash-back equivalent values. Caps are modeled; intro bonuses and "
        "statement credits are noted per card but not deducted from the fee."
    )

    if not bank_only_df.empty:
        excluded_spend = bank_only_df["Spend"].sum()
        excluded_categories = bank_only_df["Category"].value_counts().head(5)
        category_list = ", ".join(
            f"{cat} ({count})" for cat, count in excluded_categories.items()
        )
        st.warning(
            f"**{len(bank_only_df):,} transactions (${excluded_spend:,.2f} annualized) excluded** — "
            f"these merchants only appear in bank account transactions and cannot be paid by credit card. "
            f"Top excluded categories: {category_list}."
        )

    spending_df = eligible_df

    tab_rewards, tab_apr = st.tabs([
        "Cash Back Rewards",
        "Best APR",
    ])

    with tab_rewards:
        account_card_map = render_current_card_performance(spending_df)
        st.divider()
        render_application_value_summary(spending_df, account_card_map)
        st.divider()

        tabs = st.tabs(["Best Single Card"] + [combo_tab_label(count) for count in COMBO_CARD_COUNTS])
        tab_single = tabs[0]

        with tab_single:
            recs = build_card_recommendations(spending_df)
            st.dataframe(
                recs,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Est. Annual Rewards": st.column_config.NumberColumn("Est. Annual Rewards", format="$%.2f"),
                    "Annual Fee": st.column_config.NumberColumn("Annual Fee", format="$%.0f"),
                    "Statement Credits": st.column_config.NumberColumn("Statement Credits", format="$%.0f"),
                    "Est. Net Value": st.column_config.NumberColumn("Est. Net Value", format="$%.2f"),
                },
            )
            top_card_names = recs.head(5)["Card"].tolist()
            selected_card_name = st.selectbox(
                "Show earnings breakdown for:",
                top_card_names,
                key="single_card_breakdown_select",
            )
            selected_card_def = next((c for c in CREDIT_CARD_CATALOG if c["name"] == selected_card_name), None)
            breakdown_col, chat_col = st.columns([1.2, 0.8], gap="large")
            with breakdown_col:
                if selected_card_def:
                    st.caption(selected_card_def["notes"])
                    breakdown = build_card_category_breakdown(spending_df, selected_card_def)
                    if not breakdown.empty:
                        st.markdown(f"**Earnings breakdown: {selected_card_name}**")
                        st.dataframe(
                            breakdown,
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "Est. Annual Spend": st.column_config.NumberColumn("Est. Annual Spend", format="$%.2f"),
                                "Est. Annual Rewards": st.column_config.NumberColumn("Est. Annual Rewards", format="$%.2f"),
                            },
                        )
            with chat_col:
                render_recommendation_chat(
                    all_spending_df,
                    spending_df,
                    bank_only_df,
                    account_card_map,
                    input_key="recommendation_chat_input_single",
                )

        for tab, card_count in zip(tabs[1:], COMBO_CARD_COUNTS):
            with tab:
                render_combo_section(
                    spending_df,
                    card_count=card_count,
                    all_spending_df=all_spending_df,
                    bank_only_df=bank_only_df,
                    account_card_map=account_card_map,
                )

    with tab_apr:
        render_minimum_payment_recommendations(spending_df)


def main() -> None:
    render_global_styles()
    st.title("Credit Card Spending Assistant")

    category_rules = load_category_rules(
        str(CATEGORY_RULES_PATH),
        file_cache_signature(CATEGORY_RULES_PATH),
    )

    with st.sidebar:
        st.header("Data")
        uploaded_files = st.file_uploader(
            "CSV files or Amazon Store Card PDF statements",
            type=SUPPORTED_UPLOAD_TYPES,
            accept_multiple_files=True,
        )
        if uploaded_files is None:
            uploaded_files = []
        has_uploaded_files = len(uploaded_files) > 0
        show_rows = st.toggle("Show cleaned transaction table", value=False)

        if has_uploaded_files:
            st.success(format_upload_summary(uploaded_files))
        else:
            st.info("Upload one or more CSV or supported PDF files to start.")

    try:
        if uploaded_files:
            uploaded_source_names = make_unique_source_names(
                [uploaded_file.name for uploaded_file in uploaded_files]
            )
            transaction_sources = [
                (source_name, read_source_from_upload(uploaded_file))
                for source_name, uploaded_file in zip(uploaded_source_names, uploaded_files)
            ]
            data_name = format_source_names(uploaded_source_names)
        else:
            st.stop()

        df, spending_df, excluded_df = prepare_transaction_sources(transaction_sources, category_rules)
    except (ValueError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        st.error(str(exc))
        st.stop()

    source_count = count_source_files(df)
    with st.sidebar:
        st.download_button(
            "Download cleaned CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="cleaned_combined_transactions.csv" if source_count > 1 else "cleaned_transactions.csv",
            mime="text/csv",
            key="cleaned_csv_download",
        )

    tab_summary, tab_recs = st.tabs(["Summary", "Credit Card Recommendations"])

    with tab_summary:
        render_metric_row(spending_df)
        render_monthly_category_chart(spending_df)
        st.subheader("Spending by Category")
        category_chart_spending_df = render_spending_date_filter(
            spending_df,
            label="Filter category spend date range",
            key="category_spend_date_range",
        )
        render_category_total_chart(category_chart_spending_df)

        left, right = st.columns([0.9, 1.1], gap="large")

        with left:
            st.subheader("Spending Category Analyzer")
            filtered_spending_df = render_spending_date_filter(spending_df)
            selected_summary_category = render_spending_category_filter(filtered_spending_df)

        data_signature = f"{data_name}:{len(df)}:{filtered_spending_df['Spend'].sum() if not filtered_spending_df.empty else 0}:{date_range_text(filtered_spending_df)}"

        if st.session_state.get("data_signature") != data_signature:
            st.session_state.data_signature = data_signature
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": "Ask a spending question. I will answer using the cleaned transaction data loaded in this app.",
                }
            ]
        elif "messages" not in st.session_state:
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": "Ask a spending question. I will answer using the cleaned transaction data loaded in this app.",
                }
            ]

        with left:
            render_selected_category_summary(filtered_spending_df, selected_summary_category)

        with right:
            st.subheader("Chat")
            with st.container(height=420, border=True, autoscroll=True):
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.write(message["content"])

            question = st.chat_input("Ask a spending question", key="summary_chat_input")
            if question:
                previous_messages = list(st.session_state.messages)
                st.session_state.messages.append({"role": "user", "content": question})
                with st.spinner("Asking OpenAI..."):
                    answer = ask_openai_spending_question(question, df, filtered_spending_df, previous_messages)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.rerun()

        if show_rows:
            st.subheader("Cleaned Transaction Table")
            cleaned_columns = [
                "Date",
                SOURCE_FILE_COLUMN,
                "Account",
                "Description",
                "Statement Detail",
                "Reference Number",
                "Category",
                "Category Source",
                "Spend",
            ]
            cleaned_columns = [column for column in cleaned_columns if column in filtered_spending_df.columns]
            cleaned_display = filtered_spending_df[cleaned_columns].copy()
            cleaned_display["Date"] = cleaned_display["Date"].dt.date
            cleaned_display["Spend"] = cleaned_display["Spend"].map(money)
            st.dataframe(
                cleaned_display,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Category": st.column_config.TextColumn("Cleaned Category"),
                },
            )

        st.caption(f"Dataset: {data_name}")

    with tab_recs:
        render_card_recommendations(spending_df)


if __name__ == "__main__":
    main()
