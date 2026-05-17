from __future__ import annotations

from typing import Any


def _is_count_like_column(name: str | None, value: Any) -> bool:
    if not name:
        return False
    key = name.lower()
    if "count" in key or key.endswith("_count") or key.startswith("count_"):
        return True
    # numeric single-value heuristic
    if isinstance(value, int) and value >= 0:
        return True
    return False


def summarize_result(result: Any, sql: str | None = None) -> str:
    """Return a deterministic, concise summary for a query result.

    Rules:
    - If SQL contains an aggregation function like COUNT, treat single-value as a count.
    - If result is a single-row single-column with a column name containing 'count', treat as count.
    - Otherwise report number of rows or the returned scalar value.
    """
    if result is None:
        return "No result returned."

    # SQL-based detection
    if sql:
        sql_lower = sql.lower()
        if any(func in sql_lower for func in ("count(", "sum(", "avg(", "min(", "max(")):
            # If result is a scalar or single-row single-col, describe as aggregation
            if isinstance(result, list) and len(result) == 1 and len(result[0]) == 1:
                value = next(iter(result[0].values()))
                return f"Result: {value}."
            if not isinstance(result, list):
                return f"Result: {result}."

    if isinstance(result, list):
        if not result:
            return "No matching rows were found."

        if len(result) == 1 and len(result[0]) == 1:
            key = next(iter(result[0].keys()))
            value = next(iter(result[0].values()))
            if _is_count_like_column(key, value):
                return f"There are {value} matching records."
            return f"The query returned {value}."

        return f"The query returned {len(result)} rows."

    return f"The query returned {result}."
