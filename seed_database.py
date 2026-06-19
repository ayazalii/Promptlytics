"""
seed_database.py
-----------------
Creates the SQLite database file and populates the `sales` table with a
synthetic dataset matching Table 3.1 (SALES Table Schema) and Section 3.5
("pre-populated with synthetic data covering ... four regions, and twelve
months of transactions").

ASSUMPTION (documented in config.py): the product catalog is limited to 5
Electronics products (Laptop, Phone, Tablet, Monitor, Keyboard) so that
"Show quantity sold by product" stays under the <=8-unique-values pie-chart
threshold (Section 4.4.2, Rule 3) -- matching Figure 5.10's 5-slice donut
chart. Run this script directly to (re)generate the database:

    python seed_database.py

This script is also called automatically (once) by db.get_connection() the
first time the app runs, if data/promptlytics.db does not yet exist.

NOTE: a fixed random seed (42) is used so the dataset is reproducible
across machines, but the *exact* figures (e.g. "$174k in September") from
the original screenshots cannot be reproduced byte-for-byte without the
original seed script/random state -- only the overall shape (12-month
trend, 5-product breakdown, 4-region comparison) is preserved.
"""

import os
import random
import sqlite3
from datetime import date, timedelta

import config

random.seed(42)

MONTHS_2023 = [date(2023, m, 1) for m in range(1, 13)]
TRANSACTIONS_PER_MONTH_RANGE = (20, 35)


def _days_in_month(d: date) -> int:
    if d.month == 12:
        next_month = date(d.year + 1, 1, 1)
    else:
        next_month = date(d.year, d.month + 1, 1)
    return (next_month - d).days


def _generate_rows():
    rows = []
    products = config.PRODUCT_CATALOG["Electronics"]
    product_names = list(products.keys())

    for month_start in MONTHS_2023:
        n_transactions = random.randint(*TRANSACTIONS_PER_MONTH_RANGE)
        days = _days_in_month(month_start)

        for _ in range(n_transactions):
            product = random.choice(product_names)
            low, high = products[product]
            unit_price = round(random.uniform(low, high), 2)
            quantity = random.randint(1, 8)
            total_amount = round(unit_price * quantity, 2)
            region = random.choice(config.REGIONS)
            sale_date = month_start + timedelta(days=random.randint(0, days - 1))

            rows.append(
                (
                    product,
                    "Electronics",
                    quantity,
                    unit_price,
                    total_amount,
                    sale_date.isoformat(),
                    region,
                )
            )

    return rows


def seed(db_path: str = None, overwrite: bool = False):
    """
    Create the database (if needed) and populate the sales table.

    Parameters
    ----------
    db_path : str
        Path to the SQLite file. Defaults to config.DB_PATH.
    overwrite : bool
        If True, existing rows are deleted and regenerated. If False
        (default), seeding is skipped when the table already has data.
    """
    db_path = db_path or config.DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(config.CREATE_TABLE_SQL)

        cur = conn.execute(f"SELECT COUNT(*) FROM {config.TABLE_NAME}")
        existing = cur.fetchone()[0]

        if existing and not overwrite:
            print(f"'{config.TABLE_NAME}' already has {existing} rows -- skipping seed.")
            return

        if overwrite:
            conn.execute(f"DELETE FROM {config.TABLE_NAME}")

        rows = _generate_rows()
        conn.executemany(
            f"""
            INSERT INTO {config.TABLE_NAME}
                (product_name, category, quantity, unit_price, total_amount, sale_date, region)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
        print(f"Seeded {len(rows)} rows into '{config.TABLE_NAME}' at {db_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    seed(overwrite=True)
