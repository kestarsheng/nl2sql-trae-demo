"""SQL validation + self-healing: parse with sqlglot, dry-run against SQLite,
translate the database error into a Chinese correction hint for the next retry.
"""
from __future__ import annotations

import sqlite3
import re
import time

import sqlglot
from sqlglot.errors import ParseError

from .semantic import BASE_DIR

DB_PATH = BASE_DIR / "data" / "sales.db"


def _open_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def validate_and_dry_run(sql: str) -> tuple[bool, str]:
    """Return (ok, hint). hint is empty when ok, else a Chinese correction tip."""
    try:
        statements = sqlglot.parse(sql, read="sqlite")
    except ParseError as exc:
        return False, f"SQL 语法解析失败：{exc}"
    if len(statements) != 1 or statements[0] is None:
        return False, "安全拦截：仅允许单条 SELECT。"
    if statements[0].key != "select":
        return False, "安全拦截：仅允许 SELECT 查询。"
    sql = sql.strip().rstrip(";")
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql += " LIMIT 200"

    try:
        conn = _open_conn()
        deadline = time.monotonic() + 5
        conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 1000)
        try:
            conn.execute(f"EXPLAIN QUERY PLAN {sql}").fetchall()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        msg = str(exc)
        if "interrupted" in msg.lower():
            return False, "执行超时：查询超过 5 秒限制，已中断。"
        hint = _translate_sqlite_error(msg)
        return False, hint
    return True, ""


def _translate_sqlite_error(msg: str) -> str:
    if "no such table" in msg:
        return f"数据库报错：{msg}。请检查表名是否在注入的语义层内，避免幻觉出不存在的表。"
    if "no such column" in msg:
        return f"数据库报错：{msg}。请使用语义层中已声明的字段名，注意表别名前缀。"
    if "misuse of aggregate" in msg or "no such function" in msg:
        return f"数据库报错：{msg}。聚合函数需配合 GROUP BY 使用，或检查函数名拼写。"
    return f"数据库报错：{msg}。请基于报错信息修正 SQL 后重试。"
