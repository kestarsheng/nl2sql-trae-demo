"""Generate the demo SQLite database (sales + auxiliary tables).

Run from the backend/ directory:
    python init_db.py
"""
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "sales.db"

REGIONS = ["华南", "华东", "华北", "西南", "华中"]

PRODUCTS = [
    ("华为 Mate 60", "手机"),
    ("iPhone 15", "手机"),
    ("小米 14", "手机"),
    ("MacBook Air", "电脑"),
    ("ThinkPad X1", "电脑"),
    ("海尔冰箱", "家电"),
    ("格力空调", "家电"),
    ("顾家沙发", "家居"),
    ("慕思床垫", "家居"),
]

STORES = [
    ("深圳万象城店", "深圳"),
    ("上海南京路店", "上海"),
    ("北京朝阳店", "北京"),
    ("成都春熙路店", "成都"),
    ("武汉光谷店", "武汉"),
]

CUSTOMERS = [
    ("张伟", "金卡"),
    ("李娜", "银卡"),
    ("王芳", "金卡"),
    ("刘强", "普通"),
    ("陈静", "银卡"),
]


def month_bounds(ref: date) -> tuple[date, date]:
    """Return (first_day_of_ref_month, first_day_of_next_month)."""
    first = ref.replace(day=1)
    if first.month == 12:
        nxt = first.replace(year=first.year + 1, month=1)
    else:
        nxt = first.replace(month=first.month + 1)
    return first, nxt


def subtract_months(ref: date, n: int) -> date:
    """Subtract n months from ref, clamping day to month length."""
    total = ref.year * 12 + (ref.month - 1) - n
    year, month = divmod(total, 12)
    return date(year, month + 1, 1)


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE dim_region (
            region_id   INTEGER PRIMARY KEY,
            region_name TEXT NOT NULL
        );
        CREATE TABLE dim_product (
            product_id  INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            category    TEXT NOT NULL
        );
        CREATE TABLE dim_store (
            store_id   INTEGER PRIMARY KEY,
            store_name TEXT NOT NULL,
            city       TEXT NOT NULL
        );
        CREATE TABLE dim_customer (
            customer_id   INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            level         TEXT NOT NULL
        );
        CREATE TABLE fact_sales (
            sale_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_date  TEXT NOT NULL,
            region_id  INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity   INTEGER NOT NULL,
            amount     REAL NOT NULL
        );
        CREATE TABLE fact_refund (
            refund_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            refund_date   TEXT NOT NULL,
            order_id      INTEGER NOT NULL,
            refund_amount REAL NOT NULL,
            reason        TEXT NOT NULL
        );
        """
    )

    cur.executemany(
        "INSERT INTO dim_region(region_id, region_name) VALUES (?, ?)",
        [(i + 1, r) for i, r in enumerate(REGIONS)],
    )
    cur.executemany(
        "INSERT INTO dim_product(product_id, product_name, category) VALUES (?, ?, ?)",
        [(i + 1, p[0], p[1]) for i, p in enumerate(PRODUCTS)],
    )
    cur.executemany(
        "INSERT INTO dim_store(store_id, store_name, city) VALUES (?, ?, ?)",
        [(i + 1, s[0], s[1]) for i, s in enumerate(STORES)],
    )
    cur.executemany(
        "INSERT INTO dim_customer(customer_id, customer_name, level) VALUES (?, ?, ?)",
        [(i + 1, c[0], c[1]) for i, c in enumerate(CUSTOMERS)],
    )

    rng = random.Random(20261018)
    today = date.today()
    start = subtract_months(today, 12)
    end = today

    price_table = {i + 1: rng.uniform(200, 12000) for i in range(len(PRODUCTS))}
    day = start
    sale_id = 1
    while day <= end:
        orders = rng.randint(2, 6)
        for _ in range(orders):
            region_id = rng.randint(1, len(REGIONS))
            product_id = rng.randint(1, len(PRODUCTS))
            qty = rng.randint(1, 40)
            unit = price_table[product_id]
            amount = round(qty * unit * rng.uniform(0.85, 1.15), 2)
            cur.execute(
                "INSERT INTO fact_sales(sale_id, sale_date, region_id, product_id, quantity, amount) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (sale_id, day.isoformat(), region_id, product_id, qty, amount),
            )
            sale_id += 1
            if rng.random() < 0.02:
                cur.execute(
                    "INSERT INTO fact_refund(refund_date, order_id, refund_amount, reason) "
                    "VALUES (?, ?, ?, ?)",
                    (day.isoformat(), sale_id, round(amount * 0.9, 2), "七天无理由"),
                )
            if rng.random() < 0.03:
                cur.execute(
                    "INSERT INTO fact_refund(refund_date, order_id, refund_amount, reason) "
                    "VALUES (?, ?, ?, ?)",
                    (day.isoformat(), sale_id, round(amount * 0.5, 2), "质量问题"),
                )
        day += timedelta(days=1)

    conn.commit()
    rows = cur.execute("SELECT COUNT(*), SUM(amount) FROM fact_sales").fetchone()
    refunds = cur.execute("SELECT COUNT(*) FROM fact_refund").fetchone()[0]
    conn.close()
    print(f"[init_db] DB ready: {DB_PATH}")
    print(f"[init_db] fact_sales rows={rows[0]} total_amount={rows[1]:.0f} refunds={refunds}")


if __name__ == "__main__":
    main()