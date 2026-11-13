"""What the data means: which categories are spending, and the three coach buckets.

Shared surface (see packages/cloud/README.md). Both the seed script and the
calculation tools read it, so the meaning of a category lives in one place.
"""

ESSENTIALS = "essentials"
NECESSITIES = "necessities"
EVERYDAY = "everyday"

BUCKET_LABELS = {
    ESSENTIALS: "Regular essentials",
    NECESSITIES: "Unexpected necessities",
    EVERYDAY: "Everyday spending",
}

# category -> bucket. Only these categories count as spending.
CATEGORY_BUCKET = {
    "Housing": ESSENTIALS,
    "Utilities": ESSENTIALS,
    "Groceries": ESSENTIALS,
    "Transportation": ESSENTIALS,
    "Health": NECESSITIES,
    "Home & Tech": NECESSITIES,
    "Restaurants": EVERYDAY,
    "Entertainment": EVERYDAY,
    "Lifestyle": EVERYDAY,
    "Travel": EVERYDAY,
}

SPEND_CATEGORIES = tuple(CATEGORY_BUCKET)
INCOME_CATEGORIES = ("Salary", "Other Income")
# Money moved between the customer's own pots; neither spending nor income.
TRANSFER_CATEGORIES = ("Salary Sweep", "Invest Deposit", "Invest Withdraw")

AGE_BANDS = ("<25", "25-34", "35-44", "45-54", "55-64", "65+")


def age_band(age: int) -> str:
    if age < 25:
        return "<25"
    if age < 35:
        return "25-34"
    if age < 45:
        return "35-44"
    if age < 55:
        return "45-54"
    if age < 65:
        return "55-64"
    return "65+"
