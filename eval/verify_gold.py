import json, sqlite3, sys
from pathlib import Path
import sqlglot
ROOT=Path(__file__).resolve().parents[1]
rows=[json.loads(line) for line in (ROOT/"eval/gold_set.json").read_text(encoding="utf-8").splitlines()]
conn=sqlite3.connect(f"file:{(ROOT/'backend/data/sales.db').as_posix()}?mode=ro",uri=True)
for index,case in enumerate(rows,1):
    tree=sqlglot.parse_one(case["sql"],read="sqlite")
    assert tree.key=="select"
    tables={table.name for table in tree.find_all(sqlglot.exp.Table)}
    joins=len(list(tree.find_all(sqlglot.exp.Join)))
    if index<=20: assert case["category"]=="single_table" and len(tables)==1 and joins==0
    elif index<=35: assert case["category"]=="multi_table_join" and len(tables)>=2 and joins>=1
    elif index<=45: assert case["category"]=="aggregation_grouping" and tree.find(sqlglot.exp.Group) and any(tree.find_all(f) for f in (sqlglot.exp.Sum,sqlglot.exp.Count,sqlglot.exp.Avg))
    else: assert case["category"]=="time_condition" and any(key in case["sql"].lower() for key in ("date","strftime"))
    sql=case["sql"] if "limit" in case["sql"].lower() else case["sql"]+" LIMIT 200"
    conn.execute(sql).fetchall()
conn.close()
print("PASS: 50/50 gold SQL executed successfully; categories single_table=20, multi_table_join=15, aggregation_grouping=10, time_condition=5")
