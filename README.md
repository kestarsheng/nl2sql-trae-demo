# nl2sql-agent

> 一个对话式数据分析智能体：输入自然语言 → 返回可执行 SQL + 结果表格 + 自动图表，端到端流式响应。
>

## ✨ 特性

- **LangGraph 编排**：`retrieve → generate → validate(自愈) → execute` 状态图，校验失败自动回灌错误重试（最多 2 次）
- **sqlglot 强校验**：语法解析 + SQLite 试执行 + 敏感操作拦截 + 数据库报错中文翻译
- **语义层 Top-5 注入**：YAML 描述表/字段中文语义，按问题相关度只注入 Top-5 表，无关表不进 prompt
- **SSE 流式输出**：阶段事件 + SQL 打字机逐字符流 + 结果一次性下发
- **图表自动决策**：日期列→折线图、维度+度量→柱状图、单值→KPI 卡
- **零配置可用**：内置规则引擎兜底，无 LLM Key 也能跑；配 Key 自动切真模型

## 🧱 技术栈

| 层 | 选型 |
|---|---|
| Agent 编排 | LangGraph 0.2 |
| Web 框架 | FastAPI + Uvicorn |
| SQL 校验 | sqlglot 29 |
| 数据库 | SQLite（开箱即用，脚本生成 13 个月销售数据） |
| LLM | OpenAI 兼容协议（OpenAI / 通义千问 DashScope） |
| 前端 | Vue 3 + Vite + ECharts |

## 📁 目录结构

```
nl2sql-agent/
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI + SSE 入口
│   │   ├── agent.py       # LangGraph 工作流
│   │   ├── llm.py         # LLM 适配（有 Key 用真模型，否则规则引擎）
│   │   ├── rules.py       # 规则引擎 NL2SQL（兜底）
│   │   ├── semantic.py    # 语义层 YAML 加载 + Top-5 检索
│   │   ├── validator.py   # sqlglot 校验 + 报错翻译
│   │   └── executor.py    # SQLite 执行 + 图表决策
│   ├── semantic/sales.yaml  # 语义层配置
│   ├── init_db.py         # 生成 sales.db
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.vue                 # 聊天界面
│   └── components/
│       ├── MessageItem.vue     # 消息卡片（阶段时间线+SQL+表格+图表）
│       └── ChartView.vue       # ECharts 渲染
```

## 🚀 快速启动

### 1. 后端

```bash
cd backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
# .venv/bin/python -m pip install -r requirements.txt          # macOS/Linux
.venv/Scripts/python.exe init_db.py                            # 生成 sales.db
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

打开 http://localhost:5173 即可对话。

## 💬 示例问题

- 帮我查一下上个月华南区的销售总额
- 最近30天各区域的销售额排行前5
- 今年按月份的销售趋势
- 上个月华为 Mate 60 卖了多少
- 本月退款总金额

## 🔌 可选：接入真实 LLM

不配 Key 时使用内置规则引擎（开箱即用）。配 Key 后自动切换真模型，sqlglot 自愈循环才真正发挥作用：

```bash
# OpenAI
set OPENAI_API_KEY=sk-xxx            # Windows
# export OPENAI_API_KEY=sk-xxx       # macOS/Linux

# 或通义千问（DashScope，OpenAI 兼容协议）
set DASHSCOPE_API_KEY=sk-xxx
```

## 📡 API

`POST /api/chat`（SSE 流）

```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"上个月华南区销售总额"}'
```

事件类型：`question` / `stage` / `sql` / `token` / `result` / `error` / `done`

## 📝 设计要点

- **语义层检索**：问题与每张表的描述/关键词/字段中文做命中计分，只把 Top-5 表的 DDL 注入 prompt，避免无关表幻觉
- **自愈循环**：sqlglot 校验失败 → 把数据库报错翻译成中文修正提示 → 回灌到生成节点重试，最多 2 次
- **图表决策**：执行后根据列名/类型自动选 line/bar/kpi，前端 ECharts 渲染
- **安全**：拦截 DROP/DELETE/UPDATE/INSERT 等非 SELECT 操作

## P0 评测与安全

- 运行 `python eval/run_eval.py` 生成 `eval/results.json` 与 `eval/report.md`；固定对照集位于 `eval/gold_set.json`。
- 运行 `python eval/security_demo.py` 演示非 SELECT、多语句及自动 LIMIT；`SQL_TIMEOUT_SECONDS` 默认 5 秒，`SQL_MAX_ROWS` 默认 200。
- 基线设置 `NL2SQL_SELF_HEAL=0`，自愈设置 `NL2SQL_SELF_HEAL=1`（默认）。
