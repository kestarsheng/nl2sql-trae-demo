"""LangGraph orchestration: retrieve -> generate -> validate (self-heal) -> execute.

The graph is the real LangGraph StateGraph; SSE event streaming is layered on
top in main.py by replaying the per-stage messages collected in state['events'].
"""
from __future__ import annotations

import os
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from . import executor, llm, validator
from .semantic import retrieve_top_tables

MAX_RETRIES = 2
SELF_HEAL_ENABLED = os.getenv("NL2SQL_SELF_HEAL", "1") != "0"


class AgentState(TypedDict, total=False):
    question: str
    top_tables: list[dict]
    sql: str
    source: str
    retries: int
    last_error: str
    result: dict[str, Any] | None
    error: str | None
    events: list[dict[str, Any]]


def _emit(state: AgentState, event: dict[str, Any]) -> None:
    state.setdefault("events", []).append(event)


def retrieve_context(state: AgentState) -> dict[str, Any]:
    top = retrieve_top_tables(state["question"], top_n=5)
    tables = [{"table": t["table"], "score": t["score"]} for t in top]
    _emit(state, {
        "type": "stage",
        "stage": "retrieve",
        "msg": f"语义层检索完成，注入 Top-{len(top)} 张表：{', '.join(t['table'] for t in top)}",
        "tables": tables,
    })
    return {"top_tables": top}


def generate_sql(state: AgentState) -> dict[str, Any]:
    error_hint = state.get("last_error")
    attempt = state.get("retries", 0) + 1
    try:
        sql, source = llm.generate_sql(state["question"], error_hint=error_hint)
    except ValueError as exc:
        _emit(state, {"type": "stage", "stage": "generate", "msg": f"生成失败：{exc}"})
        return {"sql": "", "source": "none", "error": str(exc), "retries": attempt}
    tag = f"第 {attempt} 次生成" if attempt > 1 else "生成 SQL"
    _emit(state, {
        "type": "stage",
        "stage": "generate",
        "msg": f"{tag}（来源：{source}）",
        "sql": sql,
        "attempt": attempt,
    })
    return {"sql": sql, "source": source, "retries": attempt, "error": None}


def validate_sql(state: AgentState) -> dict[str, Any]:
    sql = state.get("sql", "")
    if not sql:
        return {"last_error": state.get("error", "空 SQL")}
    ok, hint = validator.validate_and_dry_run(sql)
    if ok:
        _emit(state, {"type": "stage", "stage": "validate", "msg": "sqlglot 校验 + 试执行通过", "ok": True})
        return {"last_error": ""}
    _emit(state, {
        "type": "stage",
        "stage": "validate",
        "msg": f"校验失败，准备自愈重试：{hint}",
        "ok": False,
        "hint": hint,
    })
    return {"last_error": hint}


def route_after_validate(state: AgentState) -> str:
    if SELF_HEAL_ENABLED and state.get("last_error") and state.get("retries", 0) < MAX_RETRIES:
        return "retry"
    return "done"


def execute_sql(state: AgentState) -> dict[str, Any]:
    sql = state.get("sql", "")
    last_error = state.get("last_error", "")
    if last_error and not sql:
        _emit(state, {"type": "stage", "stage": "execute", "msg": f"放弃执行：{last_error}"})
        return {"result": None, "error": last_error}
    if last_error:
        _emit(state, {"type": "stage", "stage": "execute", "msg": f"已达重试上限，最后错误：{last_error}"})
        return {"result": None, "error": last_error}
    try:
        result = executor.execute(sql)
        _emit(state, {
            "type": "stage",
            "stage": "execute",
            "msg": f"执行完成，返回 {result['row_count']} 行",
        })
        return {"result": result, "error": None}
    except Exception as exc:  # noqa: BLE001
        _emit(state, {"type": "stage", "stage": "execute", "msg": f"执行异常：{exc}"})
        return {"result": None, "error": str(exc)}


def build_app():
    workflow = StateGraph(AgentState)
    workflow.add_node("retrieve_context", retrieve_context)
    workflow.add_node("generate_sql", generate_sql)
    workflow.add_node("validate_sql", validate_sql)
    workflow.add_node("execute_sql", execute_sql)

    workflow.set_entry_point("retrieve_context")
    workflow.add_edge("retrieve_context", "generate_sql")
    workflow.add_edge("generate_sql", "validate_sql")
    workflow.add_conditional_edges(
        "validate_sql",
        route_after_validate,
        {"retry": "generate_sql", "done": "execute_sql"},
    )
    workflow.add_edge("execute_sql", END)
    return workflow.compile()


agent_app = build_app()


def run(question: str) -> AgentState:
    return agent_app.invoke({"question": question, "retries": 0, "events": []})
