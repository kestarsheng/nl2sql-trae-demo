"""LLM adapter: prefer a real OpenAI-compatible endpoint when an API key is set,
otherwise fall back to the rule-based generator so the demo runs offline.

Supported env vars:
    OPENAI_API_KEY + OPENAI_BASE_URL (optional, defaults to OpenAI)
    DASHSCOPE_API_KEY  -> uses Qwen via the OpenAI-compatible endpoint
"""
from __future__ import annotations

import os

import httpx

from . import rules
from .semantic import build_ddl_prompt, retrieve_top_tables

_OPENAI_KEY = os.getenv("OPENAI_API_KEY", "").strip()
_DASHSCOPE_KEY = os.getenv("DASHSCOPE_API_KEY", "").strip()
_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip()
_MODEL = os.getenv("NL2SQL_MODEL", "").strip()


def _active_endpoint() -> tuple[str, str, str] | None:
    if _OPENAI_KEY:
        base = _BASE_URL or "https://api.openai.com/v1"
        return base, _OPENAI_KEY, _MODEL or "gpt-4o-mini"
    if _DASHSCOPE_KEY:
        base = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        return base, _DASHSCOPE_KEY, _MODEL or "qwen3.8-max"
    return None


def is_llm_enabled() -> bool:
    return _active_endpoint() is not None


def _build_prompt(question: str) -> str:
    top = retrieve_top_tables(question, top_n=5)
    ddl = build_ddl_prompt(top)
    return (
        "你是 NL2SQL 助手，只输出一条可在 SQLite 执行的 SQL，不要解释、不要 markdown 围栏。\n"
        "可用表结构（仅注入与问题最相关的 Top-5 表，无关表不要使用）：\n"
        f"{ddl}\n\n"
        "示例：问'上个月华南区销售总额' -> "
        "SELECT SUM(amount) AS 销售额 FROM fact_sales JOIN dim_region ON ... "
        "WHERE dim_region.region_name='华南' AND sale_date>='...' AND sale_date<'...'\n\n"
        f"问题：{question}\nSQL："
    )


def generate_sql(question: str, error_hint: str | None = None) -> tuple[str, str]:
    """Return (sql, source) where source is 'llm' or 'rules' or 'rules(fallback)'.

    When error_hint is provided (self-healing retry), it is appended to the
    LLM prompt so the model can correct its previous SQL.
    """
    endpoint = _active_endpoint()
    if endpoint is None:
        sql = rules.generate_sql(question)
        if not sql:
            raise ValueError("规则引擎无法解析该问题，请换种说法或配置 LLM API Key。")
        return sql, "rules"

    base, key, model = endpoint
    prompt = _build_prompt(question)
    if error_hint:
        prompt = (
            f"上一次生成的 SQL 执行报错：{error_hint}\n"
            "请基于报错修正 SQL，只输出一条可在 SQLite 执行的 SQL。\n" + prompt
        )
    try:
        resp = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 512,
            },
            timeout=20.0,
            trust_env=True,
        )
        resp.raise_for_status()
        sql = resp.json()["choices"][0]["message"]["content"].strip()
        sql = sql.replace("```sql", "").replace("```", "").strip()
        return sql, "llm"
    except Exception as exc:  # noqa: BLE001
        sql = rules.generate_sql(question)
        if not sql:
            raise ValueError(f"LLM 调用失败且规则引擎无法解析：{exc}") from exc
        return sql, "rules(fallback)"
