<template>
  <div class="chart-wrap">
    <div v-if="chart.type === 'kpi'" class="kpi-card">
      <div class="kpi-label">{{ chart.field }}</div>
      <div class="kpi-value">{{ formattedKpi }}</div>
    </div>
    <div v-else>
      <div class="chart-title">{{ chart.title }}</div>
      <div ref="el" class="chart-canvas"></div>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  chart: { type: Object, required: true },
  rows: { type: Array, required: true },
  columns: { type: Array, required: true },
})

const el = ref(null)
let inst = null

const formattedKpi = ref('')
function formatKpi() {
  const v = props.chart.value
  if (typeof v !== 'number') { formattedKpi.value = String(v); return }
  if (Math.abs(v) >= 10000) {
    formattedKpi.value = (v / 10000).toFixed(2) + ' 万'
  } else {
    formattedKpi.value = v.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
  }
}

function render() {
  if (!el.value || props.chart.type === 'kpi') return
  if (inst) inst.dispose()
  inst = echarts.init(el.value)
  const { type, x, y } = props.chart
  const xi = props.columns.indexOf(x)
  const yi = props.columns.indexOf(y)
  const data = props.rows.map(r => [r[xi], r[yi]])
  const base = {
    grid: { left: 48, right: 24, top: 16, bottom: 40, containLabel: true },
    tooltip: { trigger: 'axis' },
    color: ['#4f7cff'],
  }
  if (type === 'line') {
    inst.setOption({
      ...base,
      xAxis: { type: 'category', data: data.map(d => d[0]), axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', axisLabel: { formatter: v => (v >= 10000 ? (v / 10000) + '万' : v) } },
      series: [{ type: 'line', smooth: true, data: data.map(d => d[1]), areaStyle: { opacity: 0.12 } }],
    })
  } else if (type === 'bar') {
    inst.setOption({
      ...base,
      xAxis: { type: 'category', data: data.map(d => d[0]), axisLabel: { interval: 0, rotate: 20 } },
      yAxis: { type: 'value', axisLabel: { formatter: v => (v >= 10000 ? (v / 10000) + '万' : v) } },
      series: [{ type: 'bar', data: data.map(d => d[1]), itemStyle: { borderRadius: [4, 4, 0, 0] } }],
    })
  }
}

function resize() { inst && inst.resize() }

onMounted(() => { formatKpi(); render(); window.addEventListener('resize', resize) })
onBeforeUnmount(() => { window.removeEventListener('resize', resize); inst && inst.dispose() })
watch(() => props.rows, render, { deep: true })
</script>

<style scoped>
.chart-wrap { margin-top: 12px; }
.chart-title { font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; }
.chart-canvas { width: 100%; height: 280px; }
.kpi-card {
  display: inline-flex; flex-direction: column; gap: 4px;
  padding: 16px 24px; background: linear-gradient(135deg, #eaf1ff, #f5f0ff);
  border-radius: var(--radius); border: 1px solid #dbe5ff;
}
.kpi-label { font-size: 13px; color: var(--text-secondary); }
.kpi-value { font-size: 28px; font-weight: 600; color: var(--accent); font-family: var(--mono); }
</style>