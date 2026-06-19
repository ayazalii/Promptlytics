"""
llm.py
-------
OpenAI-powered SQL generation path.

When the user provides a valid OpenAI API key in the UI, this module is
called instead of the rule-based intent engine. It sends the natural
language query plus a compact schema description to GPT, asks for a single
valid SQLite SELECT statement, and returns it along with a mock "intent"
dict so the rest of the pipeline (visualizer, insights) can work unchanged.

The rule-based engine (intent_engine.py + sql_builder.py) is the fallback
used when no key is given -- shown as "mock LLM" in the UI.

ASSUMPTION: The screenshots show an "sk-..." placeholder in the API Key
field. The model used was most likely gpt-3.5-turbo (affordable for a
student project, available at the time of development). gpt-3.5-turbo is
used here. If you have access to gpt-4, swap the MODEL constant below.
"""

import re
import sqlite3

import config

MODEL = "gpt-3.5-turbo"

SYSTEM_PROMPT = f"""You are a SQL query generator for a SQLite database.
The database has a single table named `{config.TABLE_NAME}` with these columns:

  sale_id      INTEGER  (primary key)
  product_name TEXT     (one of: Laptop, Phone, Tablet, Monitor, Keyboard)
  category     TEXT     (always "Electronics")
  quantity     INTEGER
  unit_price   REAL
  total_amount REAL     (quantity * unit_price)
  sale_date    TEXT     (ISO-8601 date: YYYY-MM-DD, data covers Jan-Dec 2023)
  region       TEXT     (one of: North, South, East, West)

Rules:
1. Output ONLY a valid SQLite SELECT statement. No explanation, no markdown.
2. Never use DROP, DELETE, UPDATE, INSERT, ALTER, or TRUNCATE.
3. For monthly grouping use: strftime('%Y-%m', sale_date)
4. Keep the query simple and efficient.
5. Use aliases so column names read clearly (e.g. total_amount AS total_revenue).
"""


def _extract_sql(text: str) -> str:
    """
    Strip any markdown fences and extract just the SQL statement from
    the model's response. GPT-3.5-turbo sometimes wraps its output in
    ```sql ... ``` fences despite being told not to.
    """
    # Remove triple-backtick fences
    text = re.sub(r"```(?:sql)?", "", text, flags=re.IGNORECASE).strip()
    text = text.strip("`").strip()
    # Take the first statement if multiple were somehow returned
    if ";" in text:
        text = text[: text.index(";") + 1]
    return text.strip()


def _validate_sql(sql: str) -> str | None:
    """
    Quick sanity check: parse the SQL against the real schema using
    sqlite3's EXPLAIN. Returns an error message string on failure, None
    on success.
    """
    try:
        conn = sqlite3.connect(config.DB_PATH)
        conn.execute(f"EXPLAIN {sql}")
        conn.close()
        return None
    except sqlite3.Error as exc:
        return str(exc)


def _mock_intent_from_sql(sql: str, nl_query: str) -> dict:
    """
    Build a minimal intent dict from the LLM-generated SQL so that
    visualizer.select_chart() and insights.generate() still receive the
    shape they expect.

    We can't run the full NLP pipeline on a model-generated string (the
    engine is rule-based by design), so we infer a coarse intent type by
    inspecting the SQL text.
    """
    sql_up = sql.upper()
    has_group = "GROUP BY" in sql_up
    has_agg = any(fn in sql_up for fn in ("SUM(", "COUNT(", "AVG(", "MAX(", "MIN("))

    if has_group:
        intent_type = "GROUP"
    elif has_agg:
        intent_type = "AGGREGATE"
    elif "WHERE" in sql_up:
        intent_type = "FILTER"
    else:
        intent_type = "SELECT"

    return {
        "type": intent_type,
        "measure": None,
        "dimension": None,
        "agg_func": None,
        "filters": [],
        "order_direction": "DESC" if "ORDER BY" in sql_up and "DESC" in sql_up else None,
        "explicit_group": has_group,
        "limit": None,
        "error": None,
        "tokens": [],
        "_source": "openai",
    }


def generate_sql(nl_query: str, api_key: str):
    """
    Call the OpenAI Chat Completions API to generate a SQL query.

    Returns
    -------
    (sql, intent, error_message)
        sql           : str   – the generated SELECT statement (or "")
        intent        : dict  – a coarse intent dict for downstream modules
        error_message : str|None – human-readable error, or None on success
    """
    try:
        from openai import OpenAI  # lazy import -- only needed on this path
    except ImportError:
        return "", {}, (
            "The `openai` Python package is not installed. "
            "Run `pip install openai` or leave the API key blank to use the "
            "rule-based engine."
        )

    client = OpenAI(api_key=api_key.strip())

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": nl_query},
            ],
            temperature=0,
            max_tokens=256,
        )
    except Exception as exc:  # openai.OpenAIError and sub-classes
        return "", {}, f"OpenAI API error: {exc}"

    raw = response.choices[0].message.content or ""
    sql = _extract_sql(raw)

    if not sql.strip().lower().startswith("select"):
        return "", {}, (
            f"The model returned an unexpected response: {raw[:200]!r}. "
            "Try rephrasing your query."
        )

    validation_err = _validate_sql(sql)
    if validation_err:
        return "", {}, (
            f"The model generated invalid SQL ({validation_err}). "
            "Try rephrasing your query."
        )

    intent = _mock_intent_from_sql(sql, nl_query)
    return sql, intent, None
