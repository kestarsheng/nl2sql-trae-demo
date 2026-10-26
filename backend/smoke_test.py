"""Quick smoke test for the NL2SQL agent (no server needed)."""
from __future__ import annotations

import json

from app import agent


def main() -> None:
    questions = [
        "帮我查一下上个月华南区的销售总额",
        "最近30天各区域的销售额排行前5",
        "今年按月份的销售趋势",
        "上个月华为 Mate 60 卖了多少",
        "本月退款总金额",
    ]
    for q in questions:
        print("=" * 70)
        print("Q:", q)
        state = agent.run(q)
        for evt in state.get("events", []):
            print(f"  [{evt.get('stage', evt.get('type'))}] {evt.get('msg', '')}")
        print("  SQL :", state.get("sql"))
        res = state.get("result")
        if res:
            print(f"  rows={res['row_count']} cols={res['columns']} chart={res['chart']}")
            for r in res["rows"][:3]:
                print("    ", r)
        if state.get("error"):
            print("  ERROR:", state["error"])


if __name__ == "__main__":
    main()