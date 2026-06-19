"""
config.py
---------
Central configuration for Promptlytics.

Holds:
  - Database paths and the SALES table schema (Table 3.1 of the project report)
  - The four rule-based keyword dictionaries used by the NLP intent engine
    (Section 4.3, Module 2 / Section 4.4.1 of the project report)
  - Column synonym maps that translate natural-language terms to actual
    SALES table columns (and the friendly aliases used for chart axes)
  - Known categorical values for the seeded demo dataset, used during
    entity extraction for FILTER queries (Step 6 of Algorithm 4.4.1)

Everything an NLP/SQL module needs to know about "the schema" lives here,
so the rest of the codebase never hard-codes column names.
"""

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "promptlytics.db")

# ---------------------------------------------------------------------------
# Schema (Table 3.1 — SALES Table Schema)
# ---------------------------------------------------------------------------
TABLE_NAME = "sales"

SCHEMA_COLUMNS = [
    "sale_id",      # INTEGER PRIMARY KEY AUTOINCREMENT
    "product_name", # TEXT NOT NULL
    "category",     # TEXT NOT NULL
    "quantity",     # INTEGER NOT NULL
    "unit_price",   # REAL NOT NULL
    "total_amount", # REAL NOT NULL (quantity * unit_price)
    "sale_date",    # TEXT NOT NULL (YYYY-MM-DD)
    "region",       # TEXT NOT NULL
]

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    sale_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT    NOT NULL,
    category     TEXT    NOT NULL,
    quantity     INTEGER NOT NULL,
    unit_price   REAL    NOT NULL,
    total_amount REAL    NOT NULL,
    sale_date    TEXT    NOT NULL,
    region       TEXT    NOT NULL
);
"""

# ---------------------------------------------------------------------------
# Demo dataset catalog
#
# ASSUMPTION: The report (Section 3.5) states the demo dataset spans "six
# product categories, four regions, and twelve months". The screenshots,
# however, show a 5-slice donut chart for "quantity sold by product"
# (Monitor 22.7%, Tablet 22.5%, Keyboard 22%, Laptop 18.2%, Phone 14.5%),
# which only works if the product catalog stays small (<=8 distinct
# products, per the Rule-3 pie-chart threshold in Section 4.4.2).
#
# To stay faithful to the screenshots, the seeded dataset uses a single
# "Electronics" category with these 5 products. CATEGORIES below is kept
# for schema completeness / extensibility (e.g. for a future CSV upload
# feature), but only "Electronics" is populated by seed_database.py.
# ---------------------------------------------------------------------------
CATEGORIES = ["Electronics", "Clothing", "Furniture", "Groceries", "Books", "Toys"]

PRODUCT_CATALOG = {
    "Electronics": {
        "Laptop":   (28000, 42000),
        "Phone":    (15000, 28000),
        "Tablet":   (10000, 18000),
        "Monitor":  (6000, 11000),
        "Keyboard": (800, 2500),
    }
}

REGIONS = ["North", "South", "East", "West"]

# Flat lists used by the intent engine for categorical value matching
CATEGORICAL_VALUES = {
    "region": REGIONS,
    "category": list(PRODUCT_CATALOG.keys()),
    "product_name": [p for cat in PRODUCT_CATALOG.values() for p in cat.keys()],
}

# ---------------------------------------------------------------------------
# NLP Module 2 — Keyword dictionaries (Section 4.3 / 4.4.1, verbatim)
# ---------------------------------------------------------------------------
AGGREGATE_KEYWORDS = {
    "count": "COUNT",
    "total": "SUM",
    "sum": "SUM",
    "average": "AVG",
    "avg": "AVG",
    "maximum": "MAX",
    "max": "MAX",
    "minimum": "MIN",
    "min": "MIN",
}

ORDER_KEYWORDS = {
    "top": "DESC",
    "highest": "DESC",
    "most": "DESC",
    "lowest": "ASC",
    "least": "ASC",
    "rank": "DESC",
    "sort": "DESC",
}

GROUP_KEYWORDS = {"by", "per", "each", "group", "category", "every"}

FILTER_KEYWORDS = {
    "where": None,
    "filter": None,
    "greater": ">",
    "above": ">",
    "more": ">",
    "less": "<",
    "below": "<",
    "fewer": "<",
    "equal": "=",
    "between": "BETWEEN",
    "only": "=",
}

# Extra phrase-level patterns checked on the raw (lowercased) query before
# tokenization. These cover common phrasings ("how many", "over time",
# "trend") that don't fit neatly into the single-token dictionaries above
# but are needed to reproduce the report's test cases and the screenshots.
COUNT_PHRASES = ["how many", "number of", "no. of", "count of"]
TIME_TREND_PHRASES = ["trend", "over time", "monthly", "by month", "per month", "each month"]

# Words that, if present anywhere in the query, mark it as a destructive /
# unsupported operation (Test Case TC-10: "Delete all records ..." -> rejected)
UNSUPPORTED_OPERATIONS = {"delete", "drop", "update", "insert", "alter", "truncate", "remove"}

# ---------------------------------------------------------------------------
# Column synonyms — maps NL tokens to schema columns (Step 6, Algorithm 4.4.1)
#
# Two "kinds":
#   measure   -> a numeric column that can be aggregated. Carries a
#                 `default_agg` used when the query doesn't specify one
#                 (e.g. "quantity sold by product" -> SUM(quantity)).
#   dimension -> a column suitable for GROUP BY / SELECT / WHERE. Date-like
#                 dimensions carry `time_trunc` ("month"/"year") so the SQL
#                 builder applies strftime() truncation.
#
# NOTE: "sales" is intentionally NOT mapped to a measure. In the report's
# test cases it sometimes means "revenue" (TC-09 "Revenue breakdown...") and
# sometimes means "transaction count" (Fig. 5.8 "Which region has the
# highest sales?" -> COUNT(*) AS num_transactions). Leaving it unmapped lets
# the engine fall back to COUNT(*) whenever no explicit measure word
# ("revenue", "quantity", "price", ...) is present -- which matches both
# the screenshots and TC-02/TC-08.
# ---------------------------------------------------------------------------
COLUMN_SYNONYMS = {
    # --- measures (aggregatable numeric columns) ---
    "revenue":  {"column": "total_amount", "alias": "total_revenue", "kind": "measure", "default_agg": "SUM"},
    "income":   {"column": "total_amount", "alias": "total_revenue", "kind": "measure", "default_agg": "SUM"},
    "amount":   {"column": "total_amount", "alias": "total_revenue", "kind": "measure", "default_agg": "SUM"},
    "earnings": {"column": "total_amount", "alias": "total_revenue", "kind": "measure", "default_agg": "SUM"},

    "quantity":   {"column": "quantity", "alias": "total_quantity", "kind": "measure", "default_agg": "SUM"},
    "quantities": {"column": "quantity", "alias": "total_quantity", "kind": "measure", "default_agg": "SUM"},
    "units":      {"column": "quantity", "alias": "total_quantity", "kind": "measure", "default_agg": "SUM"},
    "qty":        {"column": "quantity", "alias": "total_quantity", "kind": "measure", "default_agg": "SUM"},
    "sold":       {"column": "quantity", "alias": "total_quantity", "kind": "measure", "default_agg": "SUM"},

    "price":  {"column": "unit_price", "alias": "unit_price", "kind": "measure", "default_agg": "AVG"},
    "prices": {"column": "unit_price", "alias": "unit_price", "kind": "measure", "default_agg": "AVG"},
    "cost":   {"column": "unit_price", "alias": "unit_price", "kind": "measure", "default_agg": "AVG"},

    # --- dimensions (groupable / filterable columns) ---
    "product":  {"column": "product_name", "alias": "product", "kind": "dimension"},
    "products": {"column": "product_name", "alias": "product", "kind": "dimension"},
    "item":     {"column": "product_name", "alias": "product", "kind": "dimension"},
    "items":    {"column": "product_name", "alias": "product", "kind": "dimension"},

    "category":   {"column": "category", "alias": "category", "kind": "dimension"},
    "categories": {"column": "category", "alias": "category", "kind": "dimension"},

    "region":  {"column": "region", "alias": "region", "kind": "dimension"},
    "regions": {"column": "region", "alias": "region", "kind": "dimension"},

    "date":  {"column": "sale_date", "alias": "sale_date", "kind": "dimension", "time_trunc": None},
    "dates": {"column": "sale_date", "alias": "sale_date", "kind": "dimension", "time_trunc": None},

    "month":   {"column": "sale_date", "alias": "month", "kind": "dimension", "time_trunc": "month"},
    "monthly": {"column": "sale_date", "alias": "month", "kind": "dimension", "time_trunc": "month"},

    "year": {"column": "sale_date", "alias": "year", "kind": "dimension", "time_trunc": "year"},
}

# Used by the intent engine when a "trend / over time / monthly" phrase is
# detected but no explicit dimension token was matched.
MONTH_DIMENSION = COLUMN_SYNONYMS["month"]

# When the dominant intent is AGGREGATE/GROUP but no specific measure column
# is mentioned (e.g. "Which region has the highest sales?" or
# "How many sales records are there?"), fall back to COUNT(*).
DEFAULT_COUNT_ALIAS = "num_transactions"

# Columns considered "categorical" (used by the chart-selection module to
# decide cardinality thresholds for pie vs. bar charts).
CATEGORICAL_COLUMNS = {"product_name", "category", "region"}
