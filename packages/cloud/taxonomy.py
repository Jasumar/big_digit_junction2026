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

# Subcategories inside a category, by Merchant Category Code (the `mcc_codes` reference
# table holds the official names). Covers all 36 MCCs in the S-pankki data. Some
# purchases carry no MCC (about 12% of Transportation), so subcategory totals are minimums.
SUBCATEGORIES = {
    # key: (category, MCC codes)
    "taxi": ("Transportation", ("4121",)),
    "public_transport": ("Transportation", ("4111",)),
    "fuel": ("Transportation", ("5541", "5542")),
    "parking": ("Transportation", ("7523",)),
    "restaurant": ("Restaurants", ("5812",)),
    "fast_food": ("Restaurants", ("5814",)),
    "bar": ("Restaurants", ("5813",)),
    "supermarket": ("Groceries", ("5411",)),
    "convenience_store": ("Groceries", ("5499",)),
    "meat_and_dairy": ("Groceries", ("5422", "5451")),
    "pharmacy": ("Health", ("5912",)),
    "doctor": ("Health", ("8011", "8099")),
    "dentist": ("Health", ("8021",)),
    "electronics": ("Home & Tech", ("5732", "5734")),
    "furniture": ("Home & Tech", ("5712",)),
    "hardware_store": ("Home & Tech", ("5200", "5251")),
    "clothing": ("Lifestyle", ("5651", "5691")),
    "sporting_goods": ("Lifestyle", ("5941",)),
    "books": ("Lifestyle", ("5942",)),
    "toys_and_hobbies": ("Lifestyle", ("5945",)),
    "other_shops": ("Lifestyle", ("5999",)),
    "cinema": ("Entertainment", ("7832",)),
    "events_and_tickets": ("Entertainment", ("7922",)),
    "attractions": ("Entertainment", ("7991", "7996")),
    "recreation": ("Entertainment", ("7999",)),
    "flights": ("Travel", ("4511",)),
    "hotels": ("Travel", ("7011",)),
    "car_rental": ("Travel", ("7512",)),
    "travel_agency": ("Travel", ("4722",)),
}
MCC_SUBCATEGORY = {m: k for k, (_, codes) in SUBCATEGORIES.items() for m in codes}
