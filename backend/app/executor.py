"""Execute a validated SELECT against the demo SQLite and shape the result for SSE."""
from __future__ import annotations

import sqlite3
import os
import re
import time
from typing import Any

from .semantic import BASE_DIR

DB_PATH = BASE_DIR / "data" / "sales.db"


def execute(sql: str, limit: int = 200) -> dict[str, Any]:
    sql = sql.strip().rstrip(";")
    configured_limit = max(1, int(os.getenv("SQL_MAX_ROWS", limit)))
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql += f" LIMIT {configured_limit}"
    timeout = float(os.getenv("SQL_TIMEOUT_SECONDS", "5"))
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True, timeout=timeout)
    conn.row_factory = sqlite3.Row
    deadline = time.monotonic() + timeout
    conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 1000)
    import threading
    timer = threading.Timer(timeout, conn.interrupt)
    timer.start()
    try:
        cur = conn.execute(sql)
        columns = [d[0] for d in cur.description]
        rows = [list(r) for r in cur.fetchmany(configured_limit)]
    finally:
        timer.cancel()
        conn.close()
    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "truncated": len(rows) == configured_limit,
        "chart": _decide_chart(columns, rows),
    }


def _decide_chart(columns: list[str], rows: list[list[Any]]) -> dict[str, Any] | None:
    if not rows or not columns:
        return None
    date_like = [c for c in columns if any(k in c.lower() for k in ["date", "period", "month", "year"])]
    numeric_idx = [
        i for i, c in enumerate(columns)
        if rows and isinstance(rows[0][i], (int, float))
    ]

    if date_like and numeric_idx:
        x = date_like[0]
        y = columns[numeric_idx[0]]
        return {"type": "line", "x": x, "y": y, "title": f"{y} 随 {x} 变化"}

    if len(columns) == 2 and numeric_idx:
        cat_idx = 0 if numeric_idx[0] == 1 else 1
        val_idx = numeric_idx[0]
        return {
            "type": "bar",
            "x": columns[cat_idx],
            "y": columns[val_idx],
            "title": f"{columns[val_idx]} 排行",
        }

    if len(columns) == 1 and numeric_idx:
        return {"type": "kpi", "field": columns[0], "value": rows[0][0]}

    return None
