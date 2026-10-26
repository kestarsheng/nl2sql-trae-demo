"""Semantic layer: load YAML glossary, rank tables by relevance, inject Top-N."""
from __future__ import annotations

from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
SEMANTIC_PATH = BASE_DIR / "semantic" / "sales.yaml"


def load_schema() -> dict:
    with open(SEMANTIC_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return raw["schema"]


def _table_bag(tname: str, tmeta: dict) -> list[str]:
    """Collect every readable string of a table for keyword ranking."""
    bag = [tname, tmeta["description"]] + list(tmeta.get("keywords", []))
    for fmeta in tmeta["fields"].values():
        bag.append(fmeta["desc"])
    return bag


def retrieve_top_tables(question: str, top_n: int = 5) -> list[dict]:
    """Return up to top_n table metadata sorted by relevance to the question."""
    schema = load_schema()
    scored: list[tuple[int, str]] = []
    for tname, tmeta in schema.items():
        score = 0
        bag = _table_bag(tname, tmeta)
        for token in bag:
            if token and token in question:
                score += 1
        for fname in tmeta["fields"].keys():
            if fname in question:
                score += 1
        scored.append((score, tname))
    scored.sort(key=lambda x: -x[0])
    return [
        {"table": tname, "meta": schema[tname], "score": s}
        for s, tname in scored
    ][:top_n]


def build_ddl_prompt(top_tables: list[dict]) -> str:
    """Render injected tables (schema DDL + Chinese field glossary)."""
    lines = []
    for item in top_tables:
        tname, meta = item["table"], item["meta"]
        cols = []
        for fname, fmeta in meta["fields"].items():
            cols.append(f"  {fname} {fmeta['type']} -- {fmeta['desc']}")
        lines.append(f"CREATE TABLE {tname} (\n" + "\n".join(cols) + "\n)")
        lines.append(f"-- {meta['description']}")
    return "\n".join(lines)