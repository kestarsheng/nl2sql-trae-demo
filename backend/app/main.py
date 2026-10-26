"""FastAPI entry: POST /api/chat streams SSE events for an NL2SQL question."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import agent
from .semantic import BASE_DIR

DB_PATH = BASE_DIR / "data" / "sales.db"

app = FastAPI(title="nl2sql-agent", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "db_ready": DB_PATH.exists(),
        "db_path": str(DB_PATH),
    }


@app.post("/api/chat")
async def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question is empty")
    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail="sales.db 不存在，请先运行 python init_db.py")

    question = req.question.strip()

    async def event_stream():
        yield _sse({"type": "question", "question": question})
        try:
            state = await asyncio.to_thread(agent.run, question)
        except Exception as exc:  # noqa: BLE001
            yield _sse({"type": "error", "msg": f"Agent 执行异常：{exc}"})
            yield _sse({"type": "done"})
            return

        for evt in state.get("events", []):
            yield _sse(evt)
            await asyncio.sleep(0.02)

        sql = state.get("sql", "")
        if sql:
            yield _sse({"type": "sql", "sql": sql, "source": state.get("source", "")})
            for ch in sql:
                yield _sse({"type": "token", "ch": ch})
                await asyncio.sleep(0.004)

        if state.get("error"):
            yield _sse({"type": "error", "msg": state["error"]})
        elif state.get("result"):
            yield _sse({"type": "result", **state["result"]})

        yield _sse({"type": "done"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/")
def root() -> dict:
    return {"name": "nl2sql-agent", "endpoints": ["/api/health", "/api/chat"]}
