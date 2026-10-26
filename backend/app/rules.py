"""Rule-based NL2SQL generator (zero-dependency fallback when no LLM key is set).

The generator understands a small but representative subset of business
questions against the demo schema (fact_sales / fact_refund + dims).
It is intentionally template-driven so the demo runs out of the box.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

REGIONS = ["华南", "华东", "华北", "西南", "华中"]
PRODUCTS = [
    "华为 Mate 60", "iPhone 15", "小米 14",
    "MacBook Air", "ThinkPad X1",
    "海尔冰箱", "格力空调",
    "顾家沙发", "慕思床垫",
]
CATEGORIES = ["手机", "电脑", "家电", "家居"]


def _month_bounds(ref: date) -> tuple[str, str]:
    first = ref.replace(day=1)
    if first.month == 12:
        nxt = first.replace(year=first.year + 1, month=1)
    else:
        nxt = first.replace(month=first.month + 1)
    return first.isoformat(), nxt.isoformat()


def _time_window(q: str) -> tuple[str | None, str | None, str | None]:
    """Return (where_clause_fragment, group_hint, label) for the time intent."""
    today = date.today()
    if "上月" in q or "上个月" in q or "上1个月" in q:
        if today.month == 1:
            ref = date(today.year - 1, 12, 1)
        else:
            ref = date(today.year, today.month - 1, 1)
        s, e = _month_bounds(ref)
        return (f"sale_date >= '{s}' AND sale_date < '{e}'", None, f"上月({s[:7]})")
    if "本月" in q or "这个月" in q:
        s, e = _month_bounds(today)
        return (f"sale_date >= '{s}' AND sale_date < '{e}'", None, f"本月({s[:7]})")
    m = re.search(r"最近\s*(\d+)\s*天", q) or re.search(r"近\s*(\d+)\s*天", q)
    if m:
        n = int(m.group(1))
        start = (today - timedelta(days=n)).isoformat()
        return (f"sale_date >= '{start}'", None, f"近{n}天")
    if "今年" in q:
        return (f"strftime('%Y', sale_date) = '{today.year}'", None, f"今年({today.year})")
    if "去年" in q:
        return (f"strftime('%Y', sale_date) = '{today.year - 1}'", None, f"去年({today.year - 1})")
    return (None, None, "全部时间")


def _metric(q: str) -> tuple[str, str]:
    if any(k in q for k in ["退款", "退货", "退单"]):
        if "金额" in q or "总额" in q or "多少" in q:
            return "SUM(refund_amount)", "退款金额"
        return "COUNT(*)", "退款单数"
    if any(k in q for k in ["订单数", "多少单", "多少笔", "订单量", "笔数"]):
        return "COUNT(*)", "订单数"
    if any(k in q for k in ["销量", "数量", "卖了多少", "件数", "多少件"]):
        return "SUM(quantity)", "销量"
    return "SUM(amount)", "销售额"


def _group_by(q: str) -> tuple[str | None, str | None, str | None]:
    """Return (group_clause, extra_select, x_label_field_alias)."""
    if "按月" in q or "每月" in q or "按月份" in q or "趋势" in q or "走势" in q:
        return "strftime('%Y-%m', sale_date)", "strftime('%Y-%m', sale_date) AS period", "period"
    if "按区域" in q or "各区" in q or "每个区域" in q or "按地区" in q:
        return "dim_region.region_name", "dim_region.region_name AS region", "region"
    if "按产品" in q or "各产品" in q or "每个产品" in q:
        return "dim_product.product_name", "dim_product.product_name AS product", "product"
    if "按品类" in q or "按类别" in q or "各类" in q or "每个品类" in q:
        return "dim_product.category", "dim_product.category AS category", "category"
    return (None, None, None)


def _topn(q: str) -> int | None:
    m = re.search(r"(?:top|前|排名前)\s*(\d+)", q)
    if m:
        return int(m.group(1))
    if "前十" in q or "前10" in q:
        return 10
    if "前五" in q or "前5" in q:
        return 5
    return None


def _region_filter(q: str) -> str | None:
    for r in REGIONS:
        if r in q:
            return f"dim_region.region_name = '{r}'"
    return None


def _product_filter(q: str) -> str | None:
    for p in PRODUCTS:
        if p in q:
            return f"dim_product.product_name = '{p}'"
    for c in CATEGORIES:
        if c in q:
            return f"dim_product.category = '{c}'"
    return None


def generate_sql(question: str) -> str | None:
    q = question.strip()
    metric, metric_label = _metric(q)
    is_refund = metric.startswith("SUM(refund") or metric == "COUNT(*)" and "退款" in q

    if is_refund:
        where_parts = []
        tw, _, _ = _time_window(q)
        if tw:
            where_parts.append(tw.replace("sale_date", "refund_date"))
        where = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
        return f"SELECT {metric} AS {metric_label} FROM fact_refund{where}"

    group_field, extra_select, x_alias = _group_by(q)
    topn = _topn(q)
    region_f = _region_filter(q)
    product_f = _product_filter(q)
    tw, _, _ = _time_window(q)

    where_parts = []
    if region_f:
        where_parts.append(region_f)
    if product_f:
        where_parts.append(product_f)
    if tw:
        where_parts.append(tw)
    where = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""

    joins = "FROM fact_sales JOIN dim_region ON fact_sales.region_id = dim_region.region_id JOIN dim_product ON fact_sales.product_id = dim_product.product_id"

    if group_field:
        select = f"{extra_select}, {metric} AS {metric_label}"
        sql = f"SELECT {select} {joins}{where} GROUP BY {group_field} ORDER BY {metric} DESC"
    else:
        sql = f"SELECT {metric} AS {metric_label} {joins}{where}"

    if topn and group_field:
        sql += f" LIMIT {topn}"
    return sql