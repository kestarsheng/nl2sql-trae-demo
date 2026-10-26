# Gold 集复核记录（v1）

## v0 缺陷（复核发现，v1 已修复）

1. **单表组大面积重复**：原 1–20 条中有约 11 条为同一问题「查询销售订单编号、日期、销量和金额」，SQL 完全相同（`SELECT ... FROM fact_sales LIMIT 20`），模型背下一条 SQL 即可得分，评测失真。
2. **问答脱节**：原第 6/8/11/12/16/18/20 条问题问的是退款，SQL 查的却是 fact_sales 销售字段，语义不对应。
3. **跨档重复**：原 23 与 38、32 与 36 为完全相同的 SQL 却分属两档；34 与 37 近重复。
4. dim_store / dim_customer 两张表在原 50 条中完全未被覆盖。

## v1 重写原则

- 50 条问题与 SQL **全部唯一**，逐条保证问题语义与 SQL 严格对应。
- 多行结果的 gold SQL 一律带确定性 `ORDER BY`（比较为多重集合相等，行序不敏感，但排序仍消除歧义）。
- 不出全表大结果集的题（fact_sales 行数 1400+，避免 LIMIT 截断歧义）。
- 覆盖全部 6 张表：fact_sales / fact_refund / dim_region / dim_product / dim_store / dim_customer。
- 分档判定（verify_gold.py 结构断言）：单表 20（单表无 JOIN）、多表 JOIN 15（≥2 表含 JOIN）、聚合分组 10（聚合函数 + GROUP BY）、时间条件 5（date/strftime 过滤）。
- 判分口径：结果正确率 = 模型 SQL 与 gold SQL 执行结果的多重集合相等（行序不敏感）。

## 验证

`python eval/verify_gold.py`：50/50 gold SQL 在只读种子库执行成功，分类断言全部通过。

## v1.1 修订（真模型评测回检发现）

- 第 3 题：问句未提"编号"，gold 却 SELECT store_id（冒烟运行发现）→ 问句改为含"门店编号"。
- 第 4 题：问句为"姓名和会员等级"，gold 却 SELECT customer_id, customer_name, level；真模型按问句如实输出两列被判错（首次正式评测发现，基线与自愈组同错）→ gold SQL 改为 SELECT customer_name, level。
- 教训：问答的列集合必须逐字对应，模型忠实于问句反而是对的。该缺陷由评测本身咬出，正是评测集存在的意义。

## 正式产物重跑说明

首次正式评测（gold v1）产物归档于 `eval/archive/results_run1_goldv1.json`、`report_run1_goldv1.md`；gold v1.1 修复后经 `eval/run_full_eval.ps1` 重新生成正式产物。重跑是官方脚本全量重跑，非手改报告。

