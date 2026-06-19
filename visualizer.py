"""
visualizer.py
--------------
Module 5: Visualization (Section 4.3 / 4.4.2).

select_chart(df, intent, nl_query) inspects the query result DataFrame and
the classified intent to pick one of: Indicator (single value), Line,
Pie/Donut, Bar, or Table -- then builds a themed Plotly figure matching the
dark "premium SaaS" aesthetic seen in the screenshots.

Decision order (documented as an extension of the report's 5 rules +
default, reordered/extended to reproduce the screenshots -- see the
in-line comments on each branch for the corresponding report rule):

    0. 1 row x 1 column                         -> Indicator (big number)
    1. ranking query (top/highest/lowest, ...)  -> Bar               (ext.)
    2. first col is date-like, second numeric   -> Line   (Rule 2)
    3. GROUP intent, <=8 unique values in dim    -> Pie    (Rule 3)
    4. GROUP intent, >8 unique values in dim     -> Bar    (Rule 4)
    5. exactly 2 cols, 2nd numeric, <=20 unique  -> Bar    (Rule 1)
    6. anything else (>2 cols / non-numeric)     -> Table  (Rule 5)
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


# --- Dark "premium SaaS" theme, matched to the provided screenshots -------
BG_COLOR = "#0f1420"
GRID_COLOR = "#262b40"
TEXT_COLOR = "#c7d2fe"
TITLE_COLOR = "#818cf8"
ACCENT = "#6366f1"
ACCENT_LIGHT = "#818cf8"
ACCENT_MARKER = "#4f46e5"

PIE_COLORS = ["#818cf8", "#6366f1", "#a5b4fc", "#4338ca", "#c7d2fe", "#4f46e5", "#312e81", "#e0e7ff"]


def _title_from_query(nl_query: str) -> str:
    """
    Recreate the chart titles seen in the screenshots, e.g.
    "what is the monthly revenue trend?" -> "What Is The Monthly Revenue Trend?"
    """
    return nl_query.strip().title()


def _apply_theme(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(color=TITLE_COLOR, size=20, family="Arial, sans-serif")),
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        font=dict(color=TEXT_COLOR, family="Arial, sans-serif"),
        margin=dict(l=60, r=30, t=70, b=60),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_COLOR)),
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, showline=False)
    fig.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, showline=False)
    return fig


def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message, showarrow=False,
        font=dict(size=16, color=TEXT_COLOR), xref="paper", yref="paper", x=0.5, y=0.5,
    )
    fig.update_layout(
        paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=20, b=20),
    )
    return fig


def _is_date_like(series: pd.Series) -> bool:
    if pd.api.types.is_numeric_dtype(series):
        return False
    try:
        pd.to_datetime(series, errors="raise")
        return True
    except (ValueError, TypeError):
        return False


# --- Individual chart builders ---------------------------------------------

def _build_indicator(df: pd.DataFrame, title: str) -> go.Figure:
    col = df.columns[0]
    value = df.iloc[0][col]
    fig = go.Figure(go.Indicator(
        mode="number",
        value=float(value) if pd.api.types.is_number(value) else 0,
        number={"font": {"color": ACCENT_LIGHT, "size": 56}, "valueformat": ",.2f"},
        title={"text": col.replace("_", " ").title(), "font": {"color": TEXT_COLOR, "size": 18}},
    ))
    return _apply_theme(fig, title)


def _build_line(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> go.Figure:
    plot_df = df.copy()
    plot_df[x_col] = pd.to_datetime(plot_df[x_col])
    fig = px.line(plot_df, x=x_col, y=y_col, markers=True)
    fig.update_traces(line=dict(color=ACCENT, width=3), marker=dict(color=ACCENT_LIGHT, size=8))
    return _apply_theme(fig, title)


def _build_pie(df: pd.DataFrame, names_col: str, values_col: str, title: str) -> go.Figure:
    fig = px.pie(df, names=names_col, values=values_col, hole=0.45, color_discrete_sequence=PIE_COLORS)
    fig.update_traces(textinfo="percent", textfont=dict(color="#0f1420", size=13))
    return _apply_theme(fig, title)


def _build_bar(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> go.Figure:
    fig = px.bar(df, x=x_col, y=y_col)
    fig.update_traces(marker_color=ACCENT_LIGHT)
    return _apply_theme(fig, title)


def _build_table(df: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=[c.replace("_", " ").title() for c in df.columns],
            fill_color=ACCENT_MARKER, font=dict(color="#e0e7ff", size=13), align="left",
        ),
        cells=dict(
            values=[df[c] for c in df.columns],
            fill_color=BG_COLOR, font=dict(color=TEXT_COLOR, size=12), align="left",
            height=28,
        ),
    )])
    fig.update_layout(
        title=dict(text=title, font=dict(color=TITLE_COLOR, size=20)),
        paper_bgcolor=BG_COLOR, margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig


# --- Public entry point -----------------------------------------------------

def select_chart(df: pd.DataFrame, intent: dict, nl_query: str) -> go.Figure:
    title = _title_from_query(nl_query)

    if df is None or df.empty:
        return _empty_figure("No data returned for this query.")

    n_rows, n_cols = df.shape

    # Rule 0: a single scalar result (e.g. "What is the total revenue?")
    if n_rows == 1 and n_cols == 1:
        return _build_indicator(df, title)

    col0 = df.columns[0]
    col1 = df.columns[1] if n_cols > 1 else None
    second_is_numeric = n_cols >= 2 and pd.api.types.is_numeric_dtype(df[col1])

    # Extension rule: an explicit ranking query ("top", "highest",
    # "lowest", ...) is always rendered as a Bar chart, even when the
    # grouping column has few enough unique values that Rule 3 would
    # otherwise pick a Pie chart (Figure 5.8 vs Figure 5.10).
    if intent.get("order_direction") and n_cols == 2 and second_is_numeric:
        return _build_bar(df, col0, col1, title)

    # Rule 2: date-like first column + numeric second column -> Line chart
    if n_cols == 2 and _is_date_like(df[col0]) and second_is_numeric:
        return _build_line(df, col0, col1, title)

    # Rules 3 / 4: GROUP intent -> Pie if <=8 unique values, else Bar
    if intent.get("type") == "GROUP" and n_cols == 2 and second_is_numeric:
        if df[col0].nunique() <= 8:
            return _build_pie(df, col0, col1, title)
        return _build_bar(df, col0, col1, title)

    # Rule 1: generic 2-column result, 2nd numeric, <=20 unique categories -> Bar
    if n_cols == 2 and second_is_numeric and df[col0].nunique() <= 20:
        return _build_bar(df, col0, col1, title)

    # Rule 5 / default: anything else -> Table
    return _build_table(df, title)
