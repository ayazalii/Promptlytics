"""
insights.py
------------
Builds the markdown shown in the "Insights" tab (Figure 5.4 -- "Query
Summary and Statistical Metrics"). This is a lightweight, descriptive
summary of the result set: how the query was interpreted, basic
statistics on any numeric columns, and a one-line "headline" finding
(e.g. which category had the highest value).

Kept deliberately simple -- no external stats libraries -- consistent with
the report's description of a small student project.
"""

import pandas as pd


def _format_number(value) -> str:
    if isinstance(value, float):
        if value.is_integer():
            return f"{value:,.0f}"
        return f"{value:,.2f}"
    return f"{value:,}"


def _interpretation_line(intent: dict, engine_label: str) -> str:
    itype = intent.get("type")
    measure = intent.get("measure")
    dimension = intent.get("dimension")
    agg_func = intent.get("agg_func")

    if itype == "AGGREGATE":
        what = measure["alias"] if measure else "row count"
        return f"Interpreted as an **AGGREGATE** query -> `{agg_func}` over **{what}**."
    if itype == "GROUP":
        dim = dimension["alias"] if dimension else "an unspecified column"
        what = measure["alias"] if measure else "row count"
        return f"Interpreted as a **GROUP** query -> `{agg_func}` of **{what}**, grouped by **{dim}**."
    if itype == "FILTER":
        if intent.get("filters"):
            col, op, val = intent["filters"][0]
            return f"Interpreted as a **FILTER** query -> rows where `{col} {op} {val}`."
        return "Interpreted as a **FILTER** query."
    return "Interpreted as a general **SELECT** query over the `sales` table."


def generate(df: pd.DataFrame, intent: dict, nl_query: str, engine_label: str) -> str:
    """
    Build the Insights tab markdown for a given query result.

    Parameters
    ----------
    df : pd.DataFrame
        The query result (may be empty).
    intent : dict
        The intent dict returned by nlp.intent_engine.classify().
    nl_query : str
        The original natural language query (for context only).
    engine_label : str
        "Rule-based engine (mock LLM)" or "OpenAI GPT" -- shown so the
        user knows which path produced the SQL.
    """
    lines = []
    lines.append(f"**Query engine:** {engine_label}")
    lines.append("")
    lines.append(_interpretation_line(intent, engine_label))
    lines.append("")

    if df is None or df.empty:
        lines.append("_The query returned no rows._")
        return "\n".join(lines)

    n_rows, n_cols = df.shape
    lines.append(f"**Rows returned:** {n_rows}  |  **Columns:** {', '.join(df.columns)}")
    lines.append("")

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    # Single scalar result (AGGREGATE queries)
    if n_rows == 1 and n_cols == 1:
        col = df.columns[0]
        lines.append(f"### Result")
        lines.append(f"**{col.replace('_', ' ').title()}** = `{_format_number(df.iloc[0][col])}`")
        return "\n".join(lines)

    # Statistics table for numeric columns
    if numeric_cols:
        lines.append("### Statistics")
        lines.append("| Column | Min | Max | Mean | Sum |")
        lines.append("|---|---|---|---|---|")
        for col in numeric_cols:
            series = df[col]
            lines.append(
                f"| {col} | {_format_number(series.min())} | {_format_number(series.max())} "
                f"| {_format_number(series.mean())} | {_format_number(series.sum())} |"
            )
        lines.append("")

    # Headline finding: highest / lowest category for the first numeric column
    label_col = df.columns[0]
    if numeric_cols and not pd.api.types.is_numeric_dtype(df[label_col]) and n_rows > 1:
        value_col = numeric_cols[0]
        top_row = df.loc[df[value_col].idxmax()]
        bottom_row = df.loc[df[value_col].idxmin()]
        lines.append("### Key Insight")
        lines.append(
            f"- **{top_row[label_col]}** has the highest `{value_col}` "
            f"({_format_number(top_row[value_col])})."
        )
        if top_row[label_col] != bottom_row[label_col]:
            lines.append(
                f"- **{bottom_row[label_col]}** has the lowest `{value_col}` "
                f"({_format_number(bottom_row[value_col])})."
            )

    return "\n".join(lines)
