<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-title">NL2SQL</div>
        <div class="brand-sub">nl2sql-agent</div>
      </div>
      <div class="brand-desc">LangGraph 编排 · sqlglot 自愈 · Top-5 语义层注入</div>

      <div class="section-label">示例问题</div>
      <div class="examples">
        <button
          v-for="q in examples" :key="q"
          class="example-chip"
          :disabled="loading"
          @click="send(q)"
        >{{ q }}</button>
      </div>

      <div class="section-label">技术栈</div>
      <div class="tags">
        <span class="tag">FastAPI</span>
        <span class="tag">LangGraph</span>
        <span class="tag">sqlglot</span>
        <span class="tag">SQLite</span>
        <span class="tag">Vue 3</span>
        <span class="tag">ECharts</span>
        <span class="tag">SSE</span>
      </div>

      <div class="sidebar-footer">
        <span class="status-dot" :class="{ ok: backendOk }"></span>
        {{ backendOk ? '后端已连接' : '后端未连接' }}
      </div>
    </aside>

    <main class="main">
      <header class="topbar">
        <div class="topbar-title">对话式数据分析 · NL2SQL 智能体</div>
        <div class="topbar-hint">输入自然语言，直接得到 SQL + 结果 + 图表</div>
      </header>

      <section class="messages" ref="messagesEl">
        <div v-if="!messages.length" class="empty">
          <div class="empty-title">开始一次数据对话</div>
          <div class="empty-sub">点击左侧示例或在下方输入你的问题</div>
        </div>
        <MessageItem v-for="(m, i) in messages" :key="i" :msg="m" />
      </section>

      <footer class="composer">
        <textarea
          v-model="input"
          class="input"
          rows="1"
          placeholder="例如：帮我查一下上个月华南区的销售总额"
          :disabled="loading"
          @keydown.enter.exact.prevent="sendFromInput"
        ></textarea>
        <button class="send-btn" :disabled="loading || !input.trim()" @click="sendFromInput">
          {{ loading ? '运行中…' : '发送' }}
        </button>
      </footer>
    </main>
  </div>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import MessageItem from './components/MessageItem.vue'

const API_BASE = 'http://localhost:8000'
const examples = [
  '帮我查一下上个月华南区的销售总额',
  '最近30天各区域的销售额排行前5',
  '今年按月份的销售趋势',
  '上个月华为 Mate 60 卖了多少',
  '本月退款总金额',
]

const messages = ref([])
const input = ref('')
const loading = ref(false)
const backendOk = ref(false)
const messagesEl = ref(null)

function scrollBottom() {
  nextTick(() => {
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  })
}

async function checkBackend() {
  try {
    const r = await fetch(`${API_BASE}/api/health`)
    backendOk.value = r.ok
  } catch { backendOk.value = false }
}

function sendFromInput() {
  const q = input.value.trim()
  if (!q || loading.value) return
  input.value = ''
  send(q)
}

async function send(question) {
  if (loading.value) return
  messages.value.push({ role: 'user', content: question })
  const assistant = reactive({
    role: 'assistant', content: '', stages: [], sql: '', sqlTyped: '',
    source: '', result: null, error: null, done: false,
  })
  messages.value.push(assistant)
  loading.value = true
  scrollBottom()

  try {
    const resp = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    })
    if (!resp.ok) { assistant.error = `HTTP ${resp.status}`; assistant.done = true; return }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buf = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const chunks = buf.split('\n\n')
      buf = chunks.pop() || ''
      for (const chunk of chunks) {
        const line = chunk.trim()
        if (!line.startsWith('data:')) continue
        const payload = line.slice(5).trim()
        if (!payload) continue
        handleEvent(JSON.parse(payload), assistant)
        scrollBottom()
      }
    }
  } catch (e) {
    assistant.error = `请求失败：${e.message}`
  } finally {
    assistant.done = true
    loading.value = false
    scrollBottom()
  }
}

function handleEvent(evt, msg) {
  switch (evt.type) {
    case 'stage': msg.stages.push(evt); break
    case 'sql': msg.sql = evt.sql; msg.source = evt.source; break
    case 'token': msg.sqlTyped += evt.ch; break
    case 'result': msg.result = evt; break
    case 'error': msg.error = evt.msg; break
    case 'done': msg.done = true; break
  }
}

onMounted(checkBackend)
</script>

<style scoped>
.layout { display: flex; height: 100%; }

.sidebar {
  width: 260px; flex-shrink: 0; padding: 22px 18px;
  background: var(--bg-sidebar); color: var(--text-on-dark);
  display: flex; flex-direction: column; gap: 14px;
}
.brand-title { font-size: 22px; font-weight: 700; letter-spacing: 0.5px; }
.brand-sub { font-size: 13px; color: var(--text-on-dark-muted); margin-top: 2px; }
.brand-desc { font-size: 11.5px; color: var(--text-on-dark-muted); line-height: 1.5; }
.section-label { font-size: 11px; color: var(--text-on-dark-muted); text-transform: uppercase; letter-spacing: 1px; margin-top: 6px; }
.examples { display: flex; flex-direction: column; gap: 8px; }
.example-chip {
  text-align: left; padding: 9px 11px; border-radius: var(--radius-sm);
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  color: var(--text-on-dark); font-size: 12.5px; line-height: 1.4; transition: all 0.15s;
}
.example-chip:hover:not(:disabled) { background: rgba(79,124,255,0.18); border-color: var(--accent); }
.example-chip:disabled { opacity: 0.5; cursor: not-allowed; }
.tags { display: flex; flex-wrap: wrap; gap: 6px; }
.tag {
  font-size: 11px; padding: 3px 8px; border-radius: 4px;
  background: rgba(255,255,255,0.06); color: var(--text-on-dark-muted);
}
.sidebar-footer { margin-top: auto; font-size: 12px; color: var(--text-on-dark-muted); display: flex; align-items: center; gap: 6px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #f53f3f; }
.status-dot.ok { background: #00b42a; }

.main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.topbar { padding: 14px 28px; border-bottom: 1px solid var(--border); background: var(--bg-card); }
.topbar-title { font-size: 15px; font-weight: 600; }
.topbar-hint { font-size: 12.5px; color: var(--text-muted); margin-top: 2px; }

.messages { flex: 1; overflow-y: auto; padding: 24px 28px; }
.empty { text-align: center; color: var(--text-muted); padding-top: 120px; }
.empty-title { font-size: 18px; color: var(--text-secondary); margin-bottom: 6px; }
.empty-sub { font-size: 13px; }

.composer {
  display: flex; gap: 10px; padding: 14px 28px;
  border-top: 1px solid var(--border); background: var(--bg-card);
}
.input {
  flex: 1; resize: none; padding: 10px 14px; border-radius: var(--radius-sm);
  border: 1px solid var(--border); font-size: 14px; font-family: var(--sans);
  outline: none; max-height: 120px; line-height: 1.5;
}
.input:focus { border-color: var(--accent); }
.send-btn {
  padding: 0 22px; border: none; border-radius: var(--radius-sm);
  background: var(--accent); color: #fff; font-size: 14px; font-weight: 500;
}
.send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
