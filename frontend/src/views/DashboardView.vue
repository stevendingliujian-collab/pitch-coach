<template>
  <div class="dashboard-page v2-page">
    <div class="v2-topbar">
      <span class="page-title">进步看板</span>
      <div class="v2-topbar-flex" />
      <div class="trend-days-picker">
        <button
          v-for="d in [7, 14, 30]"
          :key="d"
          class="day-btn"
          :class="{ active: trendDays === d }"
          @click="changeTrendDays(d)"
        >{{ d }}天</button>
      </div>
    </div>

    <div v-if="loading" class="dash-loading">
      <el-skeleton :rows="10" animated />
    </div>

    <div v-else class="dash-content">
      <!-- KPI cards -->
      <div class="kpi-grid">
        <div class="kpi-card" v-for="kpi in kpiCards" :key="kpi.key">
          <div class="kpi-icon" :style="{ background: kpi.iconBg }">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" v-html="kpi.icon" />
          </div>
          <div class="kpi-body">
            <div class="kpi-num" :class="kpi.numClass">
              {{ kpi.value }}
            </div>
            <div class="kpi-label">{{ kpi.label }}</div>
          </div>
          <div v-if="kpi.badge" class="kpi-badge" :class="kpi.badgeType">{{ kpi.badge }}</div>
        </div>
      </div>

      <!-- Charts row -->
      <div class="charts-row">
        <!-- Trend chart (pure CSS/SVG sparkline) -->
        <div class="chart-card trend-card">
          <div class="chart-header">
            <span class="chart-title">排练趋势</span>
            <span class="chart-sub">过去 {{ trendDays }} 天</span>
          </div>
          <div class="trend-chart" ref="chartEl">
            <svg :width="chartW" height="120" class="trend-svg">
              <!-- Grid lines -->
              <line v-for="y in [30, 60, 90]" :key="y" :x1="0" :y1="y" :x2="chartW" :y2="y"
                stroke="rgba(0,0,0,0.05)" stroke-width="1"/>
              <!-- Score area -->
              <path v-if="scorePath && scoreArea" :d="scoreArea!" fill="rgba(99,102,241,0.08)" />
              <path v-if="scorePath" :d="scorePath" fill="none" stroke="#6366F1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <!-- Rehearsal bars -->
              <rect
                v-for="(pt, i) in trendPoints"
                :key="i"
                :x="barX(i)"
                :y="120 - barH(pt.rehearsals)"
                :width="barW"
                :height="barH(pt.rehearsals)"
                :fill="pt.rehearsals > 0 ? 'rgba(34,197,94,0.5)' : 'transparent'"
                rx="1"
              />
              <!-- Hover dots for score -->
              <template v-for="(pt, i) in trendPoints" :key="'dot-'+i">
                <circle
                  v-if="pt.avg_score !== null"
                  :cx="dotX(i)"
                  :cy="dotY(pt.avg_score) ?? 0"
                  r="3" fill="#6366F1" stroke="#fff" stroke-width="1.5"
                />
              </template>
            </svg>
            <div class="trend-legend">
              <span class="legend-score">—— 平均得分</span>
              <span class="legend-bar">▮ 排练次数</span>
            </div>
          </div>
        </div>

        <!-- Member leaderboard -->
        <div class="chart-card members-card">
          <div class="chart-header">
            <span class="chart-title">成员排行榜</span>
          </div>
          <div v-if="!members.length" class="no-data">暂无排练数据</div>
          <div v-else class="members-list">
            <div
              v-for="member in members.slice(0, 8)"
              :key="member.user_id"
              class="member-row"
            >
              <div class="member-rank" :class="rankClass(member.rank)">{{ member.rank }}</div>
              <div class="member-info">
                <div class="member-name">{{ member.name }}</div>
                <div class="member-meta">
                  {{ member.rehearsal_count }}次 ·
                  最近: {{ member.last_rehearsed ? formatRelative(member.last_rehearsed) : '—' }}
                </div>
              </div>
              <div class="member-score-wrap">
                <div class="member-score" :class="scoreColorClass(member.avg_score)">
                  {{ member.avg_score !== null ? member.avg_score : '—' }}
                </div>
                <div class="member-score-bar">
                  <div
                    class="member-score-fill"
                    :style="{
                      width: (member.avg_score || 0) + '%',
                      background: scoreBarColor(member.avg_score),
                    }"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Task readiness table -->
      <div class="chart-card tasks-card">
        <div class="chart-header">
          <span class="chart-title">项目就绪度</span>
          <span class="chart-sub">按述标日期排序</span>
        </div>
        <div v-if="!tasks.length" class="no-data">暂无项目数据</div>
        <div v-else class="tasks-table">
          <div class="tasks-header">
            <span class="tc-name">项目名称</span>
            <span class="tc-date">述标日期</span>
            <span class="tc-count">排练次数</span>
            <span class="tc-score">最高分</span>
            <span class="tc-readiness">就绪度</span>
            <span class="tc-action"></span>
          </div>
          <div
            v-for="task in tasks"
            :key="task.task_id"
            class="tasks-row"
            :class="urgencyClass(task)"
          >
            <span class="tc-name">
              <span class="task-name">{{ task.name }}</span>
              <span v-if="task.customer_name" class="task-customer">{{ task.customer_name }}</span>
            </span>
            <span class="tc-date">
              <span v-if="task.bid_date">
                {{ task.bid_date }}
                <span v-if="task.days_until_bid !== null && task.days_until_bid >= 0"
                  class="days-left"
                  :class="{ urgent: task.days_until_bid <= 3 }"
                >{{ task.days_until_bid }}天后</span>
                <span v-else-if="task.days_until_bid !== null" class="days-left past">已过</span>
              </span>
              <span v-else>—</span>
            </span>
            <span class="tc-count">{{ task.rehearsal_count }}</span>
            <span class="tc-score" :class="scoreColorClass(task.best_score)">
              {{ task.best_score !== null ? task.best_score : '—' }}
            </span>
            <span class="tc-readiness">
              <div class="readiness-bar">
                <div
                  class="readiness-fill"
                  :style="{
                    width: task.readiness_score + '%',
                    background: readinessColor(task.readiness_score),
                  }"
                />
              </div>
              <span class="readiness-num" :class="readinessClass(task.readiness_score)">
                {{ task.readiness_score }}%
              </span>
            </span>
            <span class="tc-action">
              <router-link :to="`/projects/${task.task_id}`" class="go-btn">详情</router-link>
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { dashboardApi, type DashboardOverview, type TrendPoint, type MemberStat, type TaskReadiness } from '@/api/dashboard'

const loading = ref(true)
const overview = ref<DashboardOverview | null>(null)
const trendData = ref<{ days: number; points: TrendPoint[] } | null>(null)
const members = ref<MemberStat[]>([])
const tasks = ref<TaskReadiness[]>([])
const trendDays = ref(30)
const chartEl = ref<HTMLElement | null>(null)
const chartW = ref(500)

onMounted(async () => {
  const [ovRes, trendRes, membersRes, tasksRes] = await Promise.allSettled([
    dashboardApi.getOverview(),
    dashboardApi.getTrend(trendDays.value),
    dashboardApi.getMembers(),
    dashboardApi.getTasks(),
  ])
  if (ovRes.status === 'fulfilled') overview.value = ovRes.value.data
  if (trendRes.status === 'fulfilled') trendData.value = trendRes.value.data
  if (membersRes.status === 'fulfilled') members.value = membersRes.value.data
  if (tasksRes.status === 'fulfilled') tasks.value = tasksRes.value.data
  loading.value = false

  await nextTick()
  updateChartWidth()
  window.addEventListener('resize', updateChartWidth)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateChartWidth)
})

function updateChartWidth() {
  if (chartEl.value) {
    chartW.value = chartEl.value.clientWidth || 500
  }
}

async function changeTrendDays(d: number) {
  trendDays.value = d
  try {
    const res = await dashboardApi.getTrend(d)
    trendData.value = res.data
  } catch {}
}

// ── KPI cards ────────────────────────────────────────────────────────────────

const kpiCards = computed(() => {
  const ov = overview.value
  return [
    {
      key: 'tasks',
      label: '进行中项目',
      value: ov?.total_tasks ?? '—',
      icon: '<rect x="2" y="2" width="6" height="7" rx="1"/><rect x="10" y="2" width="4" height="3" rx="1"/><rect x="10" y="8" width="4" height="6" rx="1"/><rect x="2" y="11" width="6" height="3" rx="1"/>',
      iconBg: 'rgba(99,102,241,0.1)',
      numClass: '',
      badge: null,
      badgeType: '',
    },
    {
      key: 'month',
      label: '本月排练',
      value: ov?.month_rehearsals ?? '—',
      icon: '<circle cx="8" cy="8" r="6.5"/><polygon points="6.5 5.5 11 8 6.5 10.5" fill="currentColor" stroke="none"/>',
      iconBg: 'rgba(34,197,94,0.1)',
      numClass: 'green',
      badge: ov?.year_month || null,
      badgeType: 'gray',
    },
    {
      key: 'avg',
      label: '平均得分',
      value: ov?.avg_score !== null && ov?.avg_score !== undefined ? ov.avg_score : '—',
      icon: '<polyline points="2 12 6 8 9 11 14 4"/><line x1="14" y1="4" x2="14" y2="7"/><line x1="11" y1="4" x2="14" y2="4"/>',
      iconBg: 'rgba(249,115,22,0.1)',
      numClass: scoreColorClass(ov?.avg_score ?? null),
      badge: null,
      badgeType: '',
    },
    {
      key: 'best',
      label: '最高得分',
      value: ov?.best_score !== null && ov?.best_score !== undefined ? ov.best_score : '—',
      icon: '<polygon points="8 2 9.6 5.8 14 6.3 11 9.1 12 13.4 8 11.3 4 13.4 5 9.1 2 6.3 6.4 5.8"/>',
      iconBg: 'rgba(168,85,247,0.1)',
      numClass: scoreColorClass(ov?.best_score ?? null),
      badge: null,
      badgeType: '',
    },
    {
      key: 'upcoming',
      label: '7天内述标',
      value: ov?.upcoming_bids_7d ?? '—',
      icon: '<rect x="1" y="2" width="14" height="12" rx="1.5"/><line x1="1" y1="6" x2="15" y2="6"/><line x1="4" y1="1" x2="4" y2="3"/><line x1="12" y1="1" x2="12" y2="3"/>',
      iconBg: ov?.upcoming_bids_7d ? 'rgba(239,68,68,0.1)' : 'rgba(0,0,0,0.06)',
      numClass: ov?.upcoming_bids_7d ? 'red' : '',
      badge: ov?.upcoming_bids_7d ? '⚠️ 紧急' : null,
      badgeType: 'red',
    },
  ]
})

// ── SVG chart ────────────────────────────────────────────────────────────────

const trendPoints = computed(() => trendData.value?.points ?? [])
const maxRehearsal = computed(() => Math.max(1, ...trendPoints.value.map(p => p.rehearsals)))

const barW = computed(() => {
  const n = trendPoints.value.length || 1
  return Math.max(2, (chartW.value / n) * 0.4)
})

function barX(i: number) {
  const n = trendPoints.value.length
  const step = chartW.value / n
  return step * i + step * 0.3
}

function barH(count: number) {
  return (count / maxRehearsal.value) * 60  // max 60px bar
}

function dotX(i: number) {
  const n = trendPoints.value.length
  const step = chartW.value / n
  return step * i + step / 2
}

function dotY(score: number | null) {
  if (score === null) return null
  // Map 0-100 score to 90-10px (inverted)
  return 90 - (score / 100) * 80
}

const scorePath = computed(() => {
  const pts = trendPoints.value.filter(p => p.avg_score !== null)
  if (pts.length < 2) return null
  const n = trendPoints.value.length

  const step = chartW.value / n
  const coords = trendPoints.value
    .map((pt, i) => pt.avg_score !== null
      ? { x: step * i + step / 2, y: 90 - (pt.avg_score / 100) * 80 }
      : null
    )
    .filter(Boolean) as { x: number; y: number }[]

  if (!coords.length) return null
  let d = `M ${coords[0].x} ${coords[0].y}`
  for (let i = 1; i < coords.length; i++) {
    const prev = coords[i - 1]
    const curr = coords[i]
    const cpx = (prev.x + curr.x) / 2
    d += ` C ${cpx} ${prev.y} ${cpx} ${curr.y} ${curr.x} ${curr.y}`
  }
  return d
})

const scoreArea = computed(() => {
  if (!scorePath.value) return null
  const pts = trendPoints.value
  const n = pts.length
  const step = chartW.value / n
  const last = pts[pts.length - 1]
  const lastX = step * (n - 1) + step / 2
  const firstX = step / 2
  return scorePath.value + ` L ${lastX} 120 L ${firstX} 120 Z`
})

// ── Helpers ──────────────────────────────────────────────────────────────────

function scoreColorClass(score: number | null) {
  if (score === null) return ''
  if (score >= 80) return 'green'
  if (score >= 60) return 'orange'
  return 'red'
}

function scoreBarColor(score: number | null) {
  if (!score) return '#D1D3DA'
  if (score >= 80) return '#22C55E'
  if (score >= 60) return '#F97316'
  return '#EF4444'
}

function rankClass(rank: number) {
  if (rank === 1) return 'gold'
  if (rank === 2) return 'silver'
  if (rank === 3) return 'bronze'
  return ''
}

function readinessColor(score: number) {
  if (score >= 70) return '#22C55E'
  if (score >= 40) return '#F97316'
  return '#EF4444'
}

function readinessClass(score: number) {
  if (score >= 70) return 'green'
  if (score >= 40) return 'orange'
  return 'red'
}

function urgencyClass(task: TaskReadiness) {
  if (task.days_until_bid !== null && task.days_until_bid >= 0 && task.days_until_bid <= 3) return 'urgent-row'
  return ''
}

function formatRelative(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const diff = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24))
  if (diff === 0) return '今天'
  if (diff === 1) return '昨天'
  if (diff < 7) return `${diff}天前`
  return `${d.getMonth() + 1}/${d.getDate()}`
}
</script>

<style scoped>
.dashboard-page { background: var(--bg-content); }
.page-title { font-size: 15px; font-weight: 700; color: var(--t-primary); }
.dash-loading { padding: 32px 24px; }
.dash-content { padding: 20px 24px 60px; display: flex; flex-direction: column; gap: 20px; }

/* ── Trend days picker ────────────────────────── */
.trend-days-picker { display: flex; gap: 2px; }
.day-btn {
  padding: 4px 12px; border-radius: 6px;
  font-size: 12.5px; font-weight: 600;
  border: none; background: transparent; color: var(--t-muted);
  cursor: pointer; transition: all 0.15s;
}
.day-btn:hover { background: rgba(0,0,0,0.05); color: var(--t-primary); }
.day-btn.active { background: rgba(99,102,241,0.1); color: #6366F1; }

/* ── KPI grid ─────────────────────────────────── */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}
.kpi-card {
  background: #fff; border-radius: 12px;
  border: 1px solid var(--border, rgba(0,0,0,0.07));
  padding: 16px;
  display: flex; align-items: center; gap: 12px;
  position: relative;
}
.kpi-icon {
  width: 36px; height: 36px; border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.kpi-icon svg { width: 16px; height: 16px; color: #6366F1; }
.kpi-body { flex: 1; min-width: 0; }
.kpi-num { font-size: 26px; font-weight: 800; color: var(--t-primary); line-height: 1; }
.kpi-num.green { color: #22C55E; }
.kpi-num.orange { color: #F97316; }
.kpi-num.red { color: #EF4444; }
.kpi-label { font-size: 11.5px; color: var(--t-muted); margin-top: 2px; }
.kpi-badge {
  position: absolute; top: 8px; right: 8px;
  padding: 2px 7px; border-radius: 20px;
  font-size: 10px; font-weight: 700;
}
.kpi-badge.gray { background: rgba(0,0,0,0.06); color: var(--t-muted); }
.kpi-badge.red { background: rgba(239,68,68,0.1); color: #DC2626; }

/* ── Charts row ───────────────────────────────── */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 16px;
}
.chart-card {
  background: #fff; border-radius: 14px;
  border: 1px solid var(--border, rgba(0,0,0,0.07));
  overflow: hidden;
}
.chart-header {
  display: flex; align-items: center; gap: 10px;
  padding: 16px 20px 12px;
  border-bottom: 1px solid var(--border, rgba(0,0,0,0.07));
}
.chart-title { font-size: 14px; font-weight: 800; color: var(--t-primary); }
.chart-sub { font-size: 12px; color: var(--t-muted); }
.no-data { padding: 32px; text-align: center; font-size: 13px; color: var(--t-faint); }

/* ── Trend chart ──────────────────────────────── */
.trend-chart { padding: 12px 16px 8px; }
.trend-svg { display: block; width: 100%; }
.trend-legend { display: flex; gap: 16px; margin-top: 6px; }
.legend-score { font-size: 11px; color: #6366F1; font-weight: 600; }
.legend-bar { font-size: 11px; color: rgba(34,197,94,0.7); font-weight: 600; }

/* ── Members leaderboard ──────────────────────── */
.members-list { padding: 8px; }
.member-row {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; border-radius: 8px; transition: background 0.1s;
}
.member-row:hover { background: var(--bg-content, #F5F5F7); }
.member-rank {
  width: 22px; height: 22px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 800; flex-shrink: 0;
  background: rgba(0,0,0,0.06); color: var(--t-muted);
}
.member-rank.gold { background: rgba(245,158,11,0.15); color: #B45309; }
.member-rank.silver { background: rgba(148,163,184,0.2); color: #64748B; }
.member-rank.bronze { background: rgba(180,119,60,0.15); color: #92400E; }
.member-info { flex: 1; min-width: 0; }
.member-name { font-size: 13px; font-weight: 600; color: var(--t-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.member-meta { font-size: 11px; color: var(--t-faint); }
.member-score-wrap { width: 80px; flex-shrink: 0; }
.member-score { font-size: 15px; font-weight: 800; text-align: right; }
.member-score.green { color: #22C55E; }
.member-score.orange { color: #F97316; }
.member-score.red { color: #EF4444; }
.member-score-bar {
  height: 3px; border-radius: 2px;
  background: rgba(0,0,0,0.07); overflow: hidden; margin-top: 3px;
}
.member-score-fill { height: 100%; border-radius: 2px; transition: width 0.4s; }

/* ── Tasks table ──────────────────────────────── */
.tasks-card { }
.tasks-table { }
.tasks-header {
  display: grid;
  grid-template-columns: 1fr 130px 80px 70px 160px 60px;
  padding: 8px 20px;
  font-size: 11.5px; font-weight: 700;
  color: var(--t-muted); text-transform: uppercase; letter-spacing: 0.4px;
  background: var(--bg-content, #F5F5F7);
  border-bottom: 1px solid var(--border, rgba(0,0,0,0.06));
}
.tasks-row {
  display: grid;
  grid-template-columns: 1fr 130px 80px 70px 160px 60px;
  padding: 12px 20px;
  font-size: 13px;
  border-bottom: 1px solid var(--border, rgba(0,0,0,0.04));
  align-items: center;
}
.tasks-row:last-child { border-bottom: none; }
.tasks-row:hover { background: var(--bg-content, #F5F5F7); }
.tasks-row.urgent-row { background: rgba(239,68,68,0.02); }

.task-name { font-weight: 600; color: var(--t-primary); display: block; }
.task-customer { font-size: 11.5px; color: var(--t-muted); }
.days-left { font-size: 11px; font-weight: 700; color: #22C55E; margin-left: 4px; }
.days-left.urgent { color: #EF4444; }
.days-left.past { color: var(--t-faint); }

.tc-count { text-align: center; color: var(--t-muted); }
.tc-score { text-align: center; font-weight: 700; }
.tc-score.green { color: #22C55E; }
.tc-score.orange { color: #F97316; }
.tc-score.red { color: #EF4444; }

.readiness-bar {
  height: 4px; border-radius: 2px;
  background: rgba(0,0,0,0.07); overflow: hidden; margin-bottom: 3px;
}
.readiness-fill { height: 100%; border-radius: 2px; transition: width 0.4s; }
.readiness-num { font-size: 12px; font-weight: 700; }
.readiness-num.green { color: #22C55E; }
.readiness-num.orange { color: #F97316; }
.readiness-num.red { color: #EF4444; }

.go-btn {
  padding: 5px 12px; border-radius: 7px;
  background: rgba(99,102,241,0.08); color: #6366F1;
  font-size: 12px; font-weight: 700; text-decoration: none;
  transition: background 0.15s;
}
.go-btn:hover { background: rgba(99,102,241,0.16); }

/* Colors */
.green { color: #22C55E; }
.orange { color: #F97316; }
.red { color: #EF4444; }

@media (max-width: 1024px) {
  .kpi-grid { grid-template-columns: repeat(3, 1fr); }
  .charts-row { grid-template-columns: 1fr; }
  .tasks-header, .tasks-row { grid-template-columns: 1fr 90px 70px 150px 50px; }
  .tc-count { display: none; }
}
@media (max-width: 640px) {
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
