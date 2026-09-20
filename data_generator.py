import random
import uuid
from datetime import datetime, timedelta, timezone


# ============================================================
# CUSTOMER MASTER DATA
# ============================================================

CUSTOMERS = [
    {
        "customer_id": 1001,
        "customer_name": "Rahul Sharma",
        "customer_email": "rahul.sharma@example.com",
        "customer_city": "Kolkata",
        "customer_state": "West Bengal",
        "customer_segment": "Premium"
    },
    {
        "customer_id": 1002,
        "customer_name": "Priya Das",
        "customer_email": "priya.das@example.com",
        "customer_city": "Kolkata",
        "customer_state": "West Bengal",
        "customer_segment": "Regular"
    },
    {
        "customer_id": 1003,
        "customer_name": "Amit Singh",
        "customer_email": "amit.singh@example.com",
        "customer_city": "Delhi",
        "customer_state": "Delhi",
        "customer_segment": "Premium"
    },
    {
        "customer_id": 1004,
        "customer_name": "Sneha Patel",
        "customer_email": "sneha.patel@example.com",
        "customer_city": "Mumbai",
        "customer_state": "Maharashtra",
        "customer_segment": "Regular"
    },
    {
        "customer_id": 1005,
        "customer_name": "Arjun Reddy",
        "customer_email": "arjun.reddy@example.com",
        "customer_city": "Hyderabad",
        "customer_state": "Telangana",
        "customer_segment": "New"
    },
    {
        "customer_id": 1006,
        "customer_name": "Riya Sen",
        "customer_email": "riya.sen@example.com",
        "customer_city": "Bengaluru",
        "customer_state": "Karnataka",
        "customer_segment": "Premium"
    },
    {
        "customer_id": 1007,
        "customer_name": "Vikram Mehta",
        "customer_email": "vikram.mehta@example.com",
        "customer_city": "Pune",
        "customer_state": "Maharashtra",
        "customer_segment": "Regular"
    },
    {
        "customer_id": 1008,
        "customer_name": "Ananya Roy",
        "customer_email": "ananya.roy@example.com",
        "customer_city": "Kolkata",
        "customer_state": "West Bengal",
        "customer_segment": "New"
    },
    {
        "customer_id": 1009,
        "customer_name": "Karan Verma",
        "customer_email": "karan.verma@example.com",
        "customer_city": "Delhi",
        "customer_state": "Delhi",
        "customer_segment": "Regular"
    },
    {
        "customer_id": 1010,
        "customer_name": "Neha Kapoor",
        "customer_email": "neha.kapoor@example.com",
        "customer_city": "Mumbai",
        "customer_state": "Maharashtra",
        "customer_segment": "Premium"
    }
]


# ============================================================
# PRODUCT MASTER DATA
# ============================================================

PRODUCTS = [
    {
        "product_id": "P101",
        "product_name": "Rider T-Shirt",
        "category": "Apparel",
        "unit_price": 899
    },
    {
        "product_id": "P102",
        "product_name": "Riding Helmet",
        "category": "Safety Gear",
        "unit_price": 3500
    },
    {
        "product_id": "P103",
        "product_name": "Riding Gloves",
        "category": "Safety Gear",
        "unit_price": 1200
    },
    {
        "product_id": "P104",
        "product_name": "Riding Jacket",
        "category": "Riding Gear",
        "unit_price": 4500
    },
    {
        "product_id": "P105",
        "product_name": "Riding Boots",
        "category": "Riding Gear",
        "unit_price": 3200
    },
    {
        "product_id": "P106",
        "product_name": "Rider Backpack",
        "category": "Accessories",
        "unit_price": 2200
    },
    {
        "product_id": "P107",
        "product_name": "Phone Holder",
        "category": "Accessories",
        "unit_price": 700
    },
    {
        "product_id": "P108",
        "product_name": "Riding Jeans",
        "category": "Apparel",
        "unit_price": 2800
    },
    {
        "product_id": "P109",
        "product_name": "Rain Jacket",
        "category": "Riding Gear",
        "unit_price": 1900
    },
    {
        "product_id": "P110",
        "product_name": "Tank Bag",
        "category": "Accessories",
        "unit_price": 1600
    }
]


# ============================================================
# OTHER MASTER DATA
# ============================================================

PAYMENT_METHODS = [
    "UPI",
    "CREDIT_CARD",
    "DEBIT_CARD",
    "NET_BANKING",
    "COD"
]


# COMPLETED intentionally has a higher probability
ORDER_STATUSES = [
    "COMPLETED",
    "COMPLETED",
    "COMPLETED",
    "COMPLETED",
    "PENDING",
    "CANCELLED"
]


# Only these fields will receive random nulls during normal
# dirty-data generation.
NULLABLE_FIELDS = [
    "customer_name",
    "customer_email",
    "customer_city",
    "customer_state",
    "customer_segment",
    "product_name",
    "category",
    "discount",
    "payment_method",
    "order_status"
]


# ============================================================
# DATE VALIDATION
# ============================================================

def validate_dates(start_date, end_date):
    """
    Validate and convert input dates.

    Expected format:
        YYYY-MM-DD
    """

    try:
        start = datetime.strptime(
            start_date,
            "%Y-%m-%d"
        ).replace(tzinfo=timezone.utc)

        end = datetime.strptime(
            end_date,
            "%Y-%m-%d"
        ).replace(tzinfo=timezone.utc)

    except ValueError:
        raise ValueError(
            "Dates must be in YYYY-MM-DD format."
        )

    if start > end:
        raise ValueError(
            "start_date cannot be greater than end_date."
        )

    return start, end


# ============================================================
# RANDOM TIMESTAMP GENERATOR
# ============================================================

def generate_random_timestamp(start, end):
    """
    Generate a random timestamp between start and end.

    The complete end date is included.
    """

    end_inclusive = end + timedelta(days=1)

    total_seconds = int(
        (end_inclusive - start).total_seconds()
    )

    random_seconds = random.randrange(total_seconds)

    return start + timedelta(seconds=random_seconds)


# ============================================================
# NULL INJECTION
# ============================================================

def inject_random_nulls(
    record,
    include_nulls=False,
    null_probability=0.05
):
    """
    Randomly replace selected fields with None.

    null_probability:
        0.05 = approximately 5% chance per nullable field.
    """

    if not include_nulls:
        return record

    for field in NULLABLE_FIELDS:

        if random.random() < null_probability:
            record[field] = None

    return record


# ============================================================
# SINGLE PURCHASE GENERATOR
# ============================================================

def generate_purchase(
    start,
    end,
    include_nulls=False,
    null_probability=0.05
):
    """
    Generate one denormalized purchase record.
    """

    customer = random.choice(CUSTOMERS)
    product = random.choice(PRODUCTS)

    quantity = random.randint(1, 5)

    unit_price = product["unit_price"]

    gross_amount = unit_price * quantity

    discount = random.choice([
        0,
        0,
        0,
        0,
        100,
        200,
        500
    ])

    # Prevent discount from making total negative
    discount = min(discount, gross_amount)

    total_amount = gross_amount - discount

    purchase_timestamp = generate_random_timestamp(
        start,
        end
    )

    # Simulate source-system creation/update timestamps
    created_at = purchase_timestamp

    updated_at = created_at + timedelta(
        minutes=random.randint(0, 1440)
    )

    purchase = {

        # ----------------------------------------------------
        # TRANSACTION
        # ----------------------------------------------------

        "purchase_id": str(uuid.uuid4()),

        "purchase_timestamp":
            purchase_timestamp.isoformat(),

        "created_at":
            created_at.isoformat(),

        "updated_at":
            updated_at.isoformat(),


        # ----------------------------------------------------
        # CUSTOMER
        # ----------------------------------------------------

        "customer_id":
            customer["customer_id"],

        "customer_name":
            customer["customer_name"],

        "customer_email":
            customer["customer_email"],

        "customer_city":
            customer["customer_city"],

        "customer_state":
            customer["customer_state"],

        "customer_segment":
            customer["customer_segment"],


        # ----------------------------------------------------
        # PRODUCT
        # ----------------------------------------------------

        "product_id":
            product["product_id"],

        "product_name":
            product["product_name"],

        "category":
            product["category"],


        # ----------------------------------------------------
        # PURCHASE MEASURES
        # ----------------------------------------------------

        "quantity":
            quantity,

        "unit_price":
            unit_price,

        "gross_amount":
            gross_amount,

        "discount":
            discount,

        "total_amount":
            total_amount,


        # ----------------------------------------------------
        # OTHER TRANSACTION ATTRIBUTES
        # ----------------------------------------------------

        "payment_method":
            random.choice(PAYMENT_METHODS),

        "order_status":
            random.choice(ORDER_STATUSES)
    }


    # Inject dirty/null data after creating
    # the valid transaction.
    purchase = inject_random_nulls(
        purchase,
        include_nulls,
        null_probability
    )

    return purchase


# ============================================================
# MAIN DATASET GENERATOR
# ============================================================

def generate_purchases(
    start_date,
    end_date,
    num_records,
    include_nulls=False,
    null_probability=0.05
):
    """
    Generate purchase dataset.

    Parameters
    ----------
    start_date : str
        YYYY-MM-DD

    end_date : str
        YYYY-MM-DD

    num_records : int
        Number of purchase records to generate.

    include_nulls : bool
        Whether random nulls should be introduced.

    null_probability : float
        Probability of each nullable field becoming null.
        Example:
            0.05 = 5%

    Returns
    -------
    list[dict]
        Generated purchase records.
    """

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if num_records <= 0:
        raise ValueError(
            "num_records must be greater than 0."
        )

    if not 0 <= null_probability <= 1:
        raise ValueError(
            "null_probability must be between 0 and 1."
        )

    start, end = validate_dates(
        start_date,
        end_date
    )


    # --------------------------------------------------------
    # GENERATE DATA
    # --------------------------------------------------------

    purchases = []

    for _ in range(num_records):

        purchase = generate_purchase(
            start=start,
            end=end,
            include_nulls=include_nulls,
            null_probability=null_probability
        )

        purchases.append(purchase)


    # --------------------------------------------------------
    # SORT BY PURCHASE TIMESTAMP
    # --------------------------------------------------------

    purchases.sort(
        key=lambda x: x["purchase_timestamp"]
    )

    return purchases


# ============================================================
# TEST / LOCAL EXECUTION
# ============================================================

if __name__ == "__main__":

    data = generate_purchases(
        start_date="2025-01-01",
        end_date="2025-12-31",
        num_records=100,
        include_nulls=True,
        null_probability=0.05
    )

    print(
        f"Generated {len(data)} purchase records.\n"
    )

    # Print first 5 records
    for record in data[:5]:
        print(record)