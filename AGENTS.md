# nl2sql-agent 项目规则

## 命名
- 项目名统一为 nl2sql-agent。

## 诚实红线
- 指标必须由 eval 脚本真实产出；禁止编造。
- eval/results.json 与 eval/report.md 生成后禁止修改。

## Git 纪律
- 禁止 force push、reset --hard、rebase、amend 已推送提交。
- commit message 使用阶段前缀 P0 / P1 / P2。

## 技术栈边界
- FastAPI、SQLAlchemy、sqlglot、SQLite/MySQL、Redis、Vue3、ECharts、SSE。
- API Key 仅从环境变量读取。SQL 重试次数最多 2 次。

## 当前阶段
阶段：P0 评测与安全收尾；P1/P2 暂不处理。
