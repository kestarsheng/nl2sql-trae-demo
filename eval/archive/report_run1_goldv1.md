# nl2sql-agent P0 评测报告

## 评测集核验

评测集 v1（重写记录见 `eval/gold_audit.md`）：50 条全部唯一、问题与 SQL 语义严格对应；50/50 SQL 在只读种子库真实执行成功。结构分类：单表 20、多表 JOIN 15、聚合分组 10、时间条件 5。

| 分类 | 数量 | 判定规则 |
|---|---:|---|
| 单表查询 | 20 | 一个物理表，无 JOIN |
| 多表 JOIN | 15 | 至少两个表，含 JOIN |
| 聚合分组 | 10 | 聚合函数 + GROUP BY |
| 时间条件 | 5 | 日期/年份过滤 |
| 合计 | 50 | gold SQL 全部执行通过 |

## NL2SQL 评测

模型模式：LLM（OpenAI 兼容端点）；基线关闭自愈，自愈组开启报错回灌重试。结果正确率按多重集合比较（行序不敏感）。

| 模式 | 语法通过率 | 执行成功率 | 结果正确率 | 生成来源分布 | 耗时 |
|---|---:|---:|---:|---|---:|
| 关闭自愈基线 | 100.0% | 100.0% | 98.0% | {"llm": 49, "rules(fallback)": 1} | 312.6s |
| 开启自愈 | 100.0% | 100.0% | 98.0% | {"llm": 50} | 315.5s |

## Token 对比

评测集前 20 题的 schema 注入文本，tiktoken `cl100k_base`：

- 全量 schema 平均：391.0 tokens
- Top-5 平均：319.5 tokens
- token 减少：18.3%

统计范围仅包括注入的 schema DDL，不包含问题和固定提示词。

## Gold 执行证明

`python eval/verify_gold.py` 实际输出：`PASS: 50/50 gold SQL executed successfully; categories single_table=20, multi_table_join=15, aggregation_grouping=10, time_condition=5`。

## 安全演示

由 run_eval 以同一解释器实际运行 `eval/security_demo.py` 并捕获输出：

```text
DELETE (False, '安全拦截：仅允许 SELECT 查询。')
UPDATE (False, '安全拦截：仅允许 SELECT 查询。')
multi_statement (False, '安全拦截：仅允许单条 SELECT。')
limit_injection (True, '')
timeout OperationalError interrupted 0.02s
```

无 LIMIT 查询由 executor 自动附加默认 LIMIT 200；超时演示由脚本内部缩短 SQL_TIMEOUT_SECONDS 触发。
