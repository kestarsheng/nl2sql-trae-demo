<template>
  <div class="msg" :class="msg.role">
    <div v-if="msg.role === 'user'" class="bubble user-bubble">{{ msg.content }}</div>
    <div v-else class="assistant-card">
      <div v-if="msg.stages.length" class="timeline">
        <div v-for="(s, i) in msg.stages" :key="i" class="stage" :class="stageClass(s)">
          <span class="dot"></span>
          <span class="stage-text">{{ s.msg }}</span>
        </div>
      </div>

      <div v-if="msg.sql" class="code-block">
        <div class="code-header">
          <span class="code-tag">SQL</span>
          <span v-if="msg.source" class="code-source">来源：{{ msg.source }}</span>
        </div>
        <pre class="code-body"><code>{{ msg.sqlTyped }}<span v-if="!msg.done" class="caret">▋</span></code></pre>
      </div>

      <div v-if="msg.error" class="error-box">{{ msg.error }}</div>

      <template v-if="msg.result">
        <div class="result-meta">
          返回 {{ msg.result.row_count }} 行
          <span v-if="msg.result.truncated" class="muted">（已截断）</span>
        </div>
        <table v-if="msg.result.rows.length" class="result-table">
          <thead>
            <tr><th v-for="(c, i) in msg.result.columns" :key="i">{{ c }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="(row, ri) in msg.result.rows" :key="ri" :class="{ alt: ri % 2 }">
              <td v-for="(cell, ci) in row" :key="ci">{{ formatCell(cell) }}</td>
            </tr>
          </tbody>
        </table>
        <ChartView v-if="msg.result.chart" :chart="msg.result.chart" :rows="msg.result.rows" :columns="msg.result.columns" />
      </template>

      <div v-if="!msg.done && !msg.sql && !msg.stages.length" class="thinking">
        <span class="pulse"></span> Agent 思考中…
      </div>
    </div>
  </div>
</template>

<script setup>
import ChartView from './ChartView.vue'

const props = defineProps({ msg: { type: Object, required: true } })

function stageClass(s) {
  if (s.stage === 'validate' && s.ok === false) return 'fail'
  if (s.stage === 'generate' && s.attempt > 1) return 'retry'
  return 'ok'
}

function formatCell(v) {
  if (typeof v === 'number') {
    if (Math.abs(v) >= 10000) return (v / 10000).toFixed(2) + ' 万'
    return v.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
  }
  return v
}
</script>

<style scoped>
.msg { display: flex; margin-bottom: 18px; }
.msg.user { justify-content: flex-end; }
.msg.assistant { justify-content: flex-start; }

.user-bubble {
  max-width: 70%; padding: 10px 14px; border-radius: 14px;
  background: var(--accent); color: #fff; line-height: 1.5;
}

.assistant-card {
  max-width: 92%; width: 100%; padding: 16px 18px;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--radius); box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}

.timeline { margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px dashed var(--border); }
.stage { display: flex; align-items: center; gap: 8px; padding: 3px 0; font-size: 12.5px; color: var(--text-secondary); }
.dot { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); flex-shrink: 0; }
.stage.ok .dot { background: var(--success); }
.stage.fail .dot { background: var(--error); }
.stage.fail .stage-text { color: var(--error); }
.stage.retry .dot { background: var(--warn); }

.code-block { margin: 10px 0; border-radius: var(--radius-sm); overflow: hidden; border: 1px solid var(--border-dark); }
.code-header {
  display: flex; align-items: center; gap: 10px; padding: 6px 12px;
  background: var(--bg-code-header); color: var(--text-on-dark-muted); font-size: 12px;
}
.code-tag { color: #c8a4ff; font-weight: 600; }
.code-body {
  margin: 0; padding: 14px 16px; background: var(--bg-code); color: #d4d8e0;
  font-family: var(--mono); font-size: 13px; line-height: 1.6; overflow-x: auto;
}
.caret { color: var(--accent); animation: blink 1s steps(2) infinite; }
@keyframes blink { 50% { opacity: 0; } }

.error-box {
  margin: 10px 0; padding: 10px 12px; border-radius: var(--radius-sm);
  background: #fff2f0; border: 1px solid #ffccc7; color: var(--error); font-size: 13px;
}

.result-meta { font-size: 12.5px; color: var(--text-muted); margin: 12px 0 6px; }
.muted { color: var(--text-muted); }

.result-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 4px; }
.result-table th {
  text-align: left; padding: 8px 10px; background: #f2f3f5; color: var(--text-secondary);
  font-weight: 600; border-bottom: 1px solid var(--border); white-space: nowrap;
}
.result-table td { padding: 8px 10px; border-bottom: 1px solid var(--border); font-family: var(--mono); }
.result-table tr.alt td { background: var(--bg-row-alt); }

.thinking { display: flex; align-items: center; gap: 8px; color: var(--text-muted); font-size: 13px; }
.pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); animation: pulse 1.2s infinite; }
@keyframes pulse { 0%,100% { opacity: 0.3; } 50% { opacity: 1; } }
</style>