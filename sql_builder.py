"""
sql_builder.py
---------------
Module 3: SQL Generation (Section 4.3 / 4.4.1, Steps 7-8).

Consumes the intent dict produced by nlp/intent_engine.py and instantiates
one of four SQL templates:

    AGGREGATE : SELECT <AGG>(<col>) AS <alias> FROM sales [WHERE ...]
    GROUP     : SELECT <dim> AS <alias>, <AGG>(<col>) AS <alias2>
                FROM sales [WHERE ...] GROUP BY <dim> [ORDER BY ... LIMIT ...]
    FILTER    : SELECT * FROM sales WHERE <col> <op> ? [LIMIT ...]
    SELECT    : SELECT * FROM sales [LIMIT ...]

Step 8 (parameterized execution): every user-supplied literal value is
returned in a separate `params` tuple -- never interpolated into the SQL
string -- so db.py can pass it straight to sqlite3's `execute(sql, params)`
and avoid SQL injection.
"""

import config

TABLE = config.TABLE_NAME


def _dimension_expr(dimension):
    """
    Return (sql_expression, alias) for a dimension, applying strftime()
    truncation for "month" / "year" date dimensions.
    """
    col = dimension["column"]
    alias = dimension["alias"]
    trunc = dimension.get("time_trunc")
    if trunc == "month":
        return f"strftime('%Y-%m', {col})", alias
    if trunc == "year":
        return f"strftime('%Y', {col})", alias
    return col, alias


def _where_clause(filters):
    """
    Build a "WHERE ..." clause (or "") plus the parameter tuple for a list
    of (column, operator, value) filter conditions, joined with AND.
    """
    if not filters:
        return "", ()

    clauses = []
    params = []
    for col, op, value in filters:
        if op == "BETWEEN":
            clauses.append(f"{col} BETWEEN ? AND ?")
            params.extend([value[0], value[1]])
        else:
            clauses.append(f"{col} {op} ?")
            params.append(value)

    return " WHERE " + " AND ".join(clauses), tuple(params)


def build_sql(intent: dict):
    """
    Translate an intent dict into (sql_string, params_tuple).

    Raises ValueError for intent["type"] == "UNSUPPORTED" -- callers should
    check intent["error"] *before* calling build_sql for unsupported
    queries; this is a defensive fallback.
    """
    if intent["type"] == "UNSUPPORTED":
        raise ValueError(intent.get("error") or "Unsupported query.")

    intent_type = intent["type"]
    measure = intent["measure"]
    dimension = intent["dimension"]
    agg_func = intent["agg_func"]
    filters = intent["filters"]
    order_direction = intent["order_direction"]
    explicit_group = intent["explicit_group"]
    limit = intent["limit"]

    where_sql, params = _where_clause(filters)

    # ------------------------------------------------------------------
    # GROUP template
    # ------------------------------------------------------------------
    if intent_type == "GROUP":
        if dimension is None:
            # No grouping column could be identified -- degrade gracefully
            # to an AGGREGATE query instead of producing invalid SQL.
            intent_type = "AGGREGATE"
        else:
            dim_expr, dim_alias = _dimension_expr(dimension)

            if measure is not None:
                agg_sql = f"{agg_func}({measure['column']}) AS {measure['alias']}"
                order_alias = measure["alias"]
            else:
                agg_sql = f"COUNT(*) AS {config.DEFAULT_COUNT_ALIAS}"
                order_alias = config.DEFAULT_COUNT_ALIAS

            sql = f"SELECT {dim_expr} AS {dim_alias}, {agg_sql} FROM {TABLE}{where_sql} GROUP BY {dim_alias}"

            # ORDER BY / LIMIT are only added when the user used an explicit
            # GROUP keyword ("by"/"per"/...) together with a ranking word
            # ("top"/"highest"/...). A bare "Which region has the highest
            # sales?" (implicit GROUP, no explicit keyword) keeps the
            # database's natural GROUP BY ordering -- see Fig. 5.8.
            if explicit_group and order_direction:
                sql += f" ORDER BY {order_alias} {order_direction}"
            else:
                sql += f" ORDER BY {dim_alias}"

            if limit is not None:
                sql += f" LIMIT {limit}"

            return sql, params

    # ------------------------------------------------------------------
    # AGGREGATE template
    # ------------------------------------------------------------------
    if intent_type == "AGGREGATE":
        if measure is not None:
            agg_sql = f"{agg_func}({measure['column']}) AS {measure['alias']}"
        else:
            agg_sql = f"COUNT(*) AS {config.DEFAULT_COUNT_ALIAS}"

        sql = f"SELECT {agg_sql} FROM {TABLE}{where_sql}"
        return sql, params

    # ------------------------------------------------------------------
    # FILTER template
    # ------------------------------------------------------------------
    if intent_type == "FILTER":
        sql = f"SELECT * FROM {TABLE}{where_sql}"
        if limit is not None:
            sql += f" LIMIT {limit}"
        return sql, params

    # ------------------------------------------------------------------
    # SELECT template (default / fallback)
    # ------------------------------------------------------------------
    sql = f"SELECT * FROM {TABLE}{where_sql}"
    if limit is not None:
        sql += f" LIMIT {limit}"
    return sql, params
