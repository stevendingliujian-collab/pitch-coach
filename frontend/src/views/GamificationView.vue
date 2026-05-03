<template>
  <div class="gami-view">
    <!-- Header -->
    <div class="page-header">
      <h1 class="page-title">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
        </svg>
        游戏化成就
      </h1>
      <p class="page-desc">通过持续练习解锁徽章，在团队中争夺排行榜位置。</p>
    </div>

    <!-- Streak fire banner -->
    <div v-if="streak && streak.current_streak > 0" class="streak-banner">
      <div class="streak-fire">{{ streak.fire_emoji || '🔥' }}</div>
      <div class="streak-info">
        <div class="streak-count">{{ streak.current_streak }} 连胜</div>
        <div class="streak-msg">{{ streak.message }}</div>
      </div>
      <div class="streak-longest">
        最长连胜 <strong>{{ streak.longest_streak }}</strong>
      </div>
    </div>

    <!-- Stats bar -->
    <div v-if="stats" class="stats-bar">
      <div class="stat-chip">
        <span class="stat-chip-icon">🎯</span>
        <span class="stat-chip-val">{{ stats.total_rehearsals }}</span>
        <span class="stat-chip-label">排练次数</span>
      </div>
      <div class="stat-chip">
        <span class="stat-chip-icon">⭐</span>
        <span class="stat-chip-val">{{ stats.total_points }}</span>
        <span class="stat-chip-label">积分</span>
      </div>
      <div class="stat-chip">
        <span class="stat-chip-icon">🏅</span>
        <span class="stat-chip-val">{{ stats.total_achievements }}</span>
        <span class="stat-chip-label">已解锁徽章</span>
      </div>
      <div class="stat-chip">
        <span class="stat-chip-icon">📈</span>
        <span class="stat-chip-val">{{ stats.avg_rehearsal_score ? stats.avg_rehearsal_score.toFixed(0) : '—' }}</span>
        <span class="stat-chip-label">平均得分</span>
      </div>
      <div class="stat-chip">
        <span class="stat-chip-icon">🥇</span>
        <span class="stat-chip-val">{{ stats.best_rehearsal_score ? stats.best_rehearsal_score.toFixed(0) : '—' }}</span>
        <span class="stat-chip-label">最高得分</span>
      </div>
    </div>

    <!-- Tab nav -->
    <div class="tab-nav">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="tab-btn"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >{{ tab.label }}</button>
    </div>

    <!-- Achievements tab -->
    <div v-if="activeTab === 'achievements'" class="tab-content">
      <div v-if="loadingAchievements" class="loading-state">
        <div class="spinner"></div> 加载中…
      </div>
      <div v-else>
        <!-- Category filter -->
        <div class="category-filters">
          <button
            v-for="cat in categories"
            :key="cat.id"
            class="cat-btn"
            :class="{ active: selectedCategory === cat.id }"
            @click="selectedCategory = cat.id"
          >{{ cat.label }} <span v-if="cat.id !== 'all'" class="cat-count">{{ earnedInCategory(cat.id) }}/{{ totalInCategory(cat.id) }}</span></button>
        </div>

        <div class="achievements-grid">
          <div
            v-for="ach in filteredAchievements"
            :key="ach.id"
            class="ach-card"
            :class="{ earned: ach.earned, locked: !ach.earned }"
          >
            <div class="ach-emoji">{{ ach.icon_emoji }}</div>
            <div class="ach-body">
              <div class="ach-name">{{ ach.name }}</div>
              <div class="ach-desc">{{ ach.description }}</div>
              <div v-if="ach.earned" class="ach-earned-date">
                ✓ 已解锁 {{ formatDate(ach.earned_at!) }}
              </div>
            </div>
            <div class="ach-points" :class="ach.earned ? 'earned-pts' : 'locked-pts'">
              +{{ ach.points }} 分
            </div>
          </div>
        </div>

        <div v-if="filteredAchievements.length === 0" class="empty-state">
          <p>该分类暂无徽章</p>
        </div>
      </div>
    </div>

    <!-- Leaderboard tab -->
    <div v-if="activeTab === 'leaderboard'" class="tab-content">
      <div class="lb-controls">
        <div class="period-btns">
          <button
            v-for="p in periods"
            :key="p.id"
            class="period-btn"
            :class="{ active: selectedPeriod === p.id }"
            @click="selectedPeriod = p.id; loadLeaderboard()"
          >{{ p.label }}</button>
        </div>
        <div v-if="leaderboard" class="lb-meta">
          共 {{ leaderboard.total_participants }} 人参与
          <span v-if="leaderboard.my_rank" class="my-rank-badge">我的排名：#{{ leaderboard.my_rank }}</span>
        </div>
      </div>

      <div v-if="loadingLeaderboard" class="loading-state">
        <div class="spinner"></div> 加载中…
      </div>
      <div v-else-if="leaderboard" class="lb-table-wrap">
        <table class="lb-table">
          <thead>
            <tr>
              <th>排名</th>
              <th>成员</th>
              <th>积分</th>
              <th>排练</th>
              <th>平均分</th>
              <th>连胜</th>
              <th>徽章</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="entry in leaderboard.leaderboard"
              :key="entry.user_id"
              :class="{ 'my-row': entry.rank === leaderboard.my_rank }"
            >
              <td class="rank-cell">
                <span v-if="entry.rank === 1" class="rank-medal gold">🥇</span>
                <span v-else-if="entry.rank === 2" class="rank-medal silver">🥈</span>
                <span v-else-if="entry.rank === 3" class="rank-medal bronze">🥉</span>
                <span v-else class="rank-num">#{{ entry.rank }}</span>
              </td>
              <td class="name-cell">{{ entry.display_name }}</td>
              <td class="pts-cell">
                <span class="pts-badge">{{ entry.total_points }}</span>
              </td>
              <td>{{ entry.total_rehearsals }}</td>
              <td>{{ entry.avg_score ? entry.avg_score.toFixed(0) : '—' }}</td>
              <td>
                <span v-if="entry.current_streak >= 3" class="streak-chip">
                  🔥 {{ entry.current_streak }}
                </span>
                <span v-else>{{ entry.current_streak || 0 }}</span>
              </td>
              <td>{{ entry.total_achievements }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="leaderboard.leaderboard.length === 0" class="empty-state">
          <p>还没有排行榜数据，快去排练吧！</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  gamificationApi,
  type AchievementItem,
  type UserStats,
  type LeaderboardResult,
  type StreakInfo,
} from '@/api/gamification'

const activeTab = ref('achievements')
const tabs = [
  { id: 'achievements', label: '🏅 我的徽章' },
  { id: 'leaderboard', label: '🏆 排行榜' },
]

// ─── Streak ───────────────────────────────────────────────────────────────────

const streak = ref<StreakInfo | null>(null)

// ─── Stats ────────────────────────────────────────────────────────────────────

const stats = ref<UserStats | null>(null)

// ─── Achievements ─────────────────────────────────────────────────────────────

const achievements = ref<AchievementItem[]>([])
const loadingAchievements = ref(false)
const selectedCategory = ref('all')

const categories = [
  { id: 'all', label: '全部' },
  { id: 'rehearsal', label: '排练' },
  { id: 'streak', label: '连胜' },
  { id: 'quality', label: '质量' },
  { id: 'evaluator', label: '评委问答' },
  { id: 'practice', label: '每日练习' },
  { id: 'milestone', label: '里程碑' },
  { id: 'knowledge', label: '知识库' },
]

const filteredAchievements = computed(() => {
  if (selectedCategory.value === 'all') return achievements.value
  return achievements.value.filter(a => a.category === selectedCategory.value)
})

function earnedInCategory(cat: string) {
  return achievements.value.filter(a => a.category === cat && a.earned).length
}

function totalInCategory(cat: string) {
  return achievements.value.filter(a => a.category === cat).length
}

async function loadAchievements() {
  loadingAchievements.value = true
  try {
    const res = await gamificationApi.achievements()
    achievements.value = res.data
  } catch { /* ignore */ } finally {
    loadingAchievements.value = false
  }
}

// ─── Leaderboard ─────────────────────────────────────────────────────────────

const leaderboard = ref<LeaderboardResult | null>(null)
const loadingLeaderboard = ref(false)
const selectedPeriod = ref<'week' | 'month' | 'all_time'>('week')

const periods = [
  { id: 'week' as const, label: '本周' },
  { id: 'month' as const, label: '本月' },
  { id: 'all_time' as const, label: '全部' },
]

async function loadLeaderboard() {
  loadingLeaderboard.value = true
  try {
    const res = await gamificationApi.leaderboard(selectedPeriod.value)
    leaderboard.value = res.data
  } catch { /* ignore */ } finally {
    loadingLeaderboard.value = false
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

// ─── Init ─────────────────────────────────────────────────────────────────────

onMounted(async () => {
  await Promise.all([
    loadAchievements(),
    loadLeaderboard(),
    gamificationApi.stats().then(r => { stats.value = r.data }).catch(() => {}),
    gamificationApi.streak().then(r => { streak.value = r.data }).catch(() => {}),
  ])
})
</script>

<style scoped>
.gami-view { padding: 28px 32px; max-width: 900px; }

/* Header */
.page-header { margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; display: flex; align-items: center; gap: 10px; margin: 0 0 6px; }
.page-title svg { color: #F97316; }
.page-desc { color: #6b7280; font-size: 14px; margin: 0; }

/* Streak banner */
.streak-banner {
  display: flex; align-items: center; gap: 16px;
  background: linear-gradient(135deg, #FFF7ED, #FEF3C7);
  border: 1px solid #FED7AA;
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 20px;
}
.streak-fire { font-size: 36px; line-height: 1; }
.streak-info { flex: 1; }
.streak-count { font-size: 18px; font-weight: 800; color: #EA580C; }
.streak-msg { font-size: 13px; color: #92400E; margin-top: 2px; }
.streak-longest { font-size: 12px; color: #92400E; white-space: nowrap; }
.streak-longest strong { font-weight: 700; }

/* Stats bar */
.stats-bar {
  display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 24px;
}
.stat-chip {
  display: flex; align-items: center; gap: 6px;
  background: white; border: 1px solid #e5e7eb;
  border-radius: 10px; padding: 10px 14px;
  flex: 1; min-width: 100px;
}
.stat-chip-icon { font-size: 18px; }
.stat-chip-val { font-size: 20px; font-weight: 800; color: #1a1a2e; }
.stat-chip-label { font-size: 11px; color: #6b7280; font-weight: 500; }

/* Tabs */
.tab-nav { display: flex; gap: 4px; border-bottom: 1px solid #e5e7eb; margin-bottom: 24px; }
.tab-btn {
  padding: 10px 20px; background: none; border: none;
  border-bottom: 2px solid transparent; font-size: 14px; font-weight: 500;
  color: #6b7280; cursor: pointer; transition: all 0.15s; margin-bottom: -1px;
}
.tab-btn:hover { color: #374151; }
.tab-btn.active { color: #6366F1; border-bottom-color: #6366F1; }

/* Category filters */
.category-filters { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }
.cat-btn {
  display: flex; align-items: center; gap: 4px;
  padding: 5px 12px; border-radius: 20px;
  background: #f3f4f6; border: none;
  font-size: 12px; font-weight: 600; color: #374151; cursor: pointer;
  transition: all 0.15s;
}
.cat-btn:hover { background: #e5e7eb; }
.cat-btn.active { background: #6366F1; color: white; }
.cat-count { background: rgba(0,0,0,0.15); padding: 1px 5px; border-radius: 8px; font-size: 10px; }
.cat-btn.active .cat-count { background: rgba(255,255,255,0.25); }

/* Achievements grid */
.achievements-grid { display: flex; flex-direction: column; gap: 10px; }
.ach-card {
  display: flex; align-items: center; gap: 14px;
  background: white; border-radius: 12px; border: 1.5px solid #e5e7eb;
  padding: 14px 18px; transition: all 0.15s;
}
.ach-card.earned { border-color: #a5b4fc; background: #faf5ff; }
.ach-card.locked { opacity: 0.55; filter: grayscale(40%); }
.ach-emoji { font-size: 28px; flex-shrink: 0; }
.ach-body { flex: 1; min-width: 0; }
.ach-name { font-size: 14px; font-weight: 700; color: #1a1a2e; margin-bottom: 2px; }
.ach-desc { font-size: 12px; color: #6b7280; }
.ach-earned-date { font-size: 11px; color: #7c3aed; margin-top: 4px; font-weight: 600; }
.ach-points { font-size: 13px; font-weight: 700; white-space: nowrap; }
.earned-pts { color: #7c3aed; }
.locked-pts { color: #9ca3af; }

/* Leaderboard */
.lb-controls { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; gap: 12px; flex-wrap: wrap; }
.period-btns { display: flex; gap: 6px; }
.period-btn {
  padding: 6px 14px; border-radius: 20px;
  background: #f3f4f6; border: none;
  font-size: 12px; font-weight: 600; color: #374151; cursor: pointer;
}
.period-btn.active { background: #6366F1; color: white; }
.lb-meta { font-size: 13px; color: #6b7280; display: flex; align-items: center; gap: 10px; }
.my-rank-badge { background: #ede9fe; color: #7c3aed; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 12px; }

.lb-table-wrap { overflow-x: auto; }
.lb-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.lb-table th {
  text-align: left; padding: 10px 12px;
  color: #6b7280; font-size: 12px; font-weight: 600;
  border-bottom: 1px solid #e5e7eb;
}
.lb-table td { padding: 12px; border-bottom: 1px solid #f3f4f6; }
.lb-table tr.my-row td { background: #f5f3ff; font-weight: 600; }
.rank-cell { width: 60px; text-align: center; }
.rank-medal { font-size: 20px; }
.rank-num { font-size: 13px; color: #6b7280; font-weight: 600; }
.name-cell { font-weight: 600; color: #1a1a2e; }
.pts-cell { }
.pts-badge { background: #ede9fe; color: #6366F1; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 12px; }
.streak-chip { display: inline-flex; align-items: center; gap: 3px; background: #fff7ed; color: #ea580c; padding: 2px 8px; border-radius: 10px; font-weight: 700; font-size: 12px; }

/* Loading & empty */
.loading-state { display: flex; align-items: center; gap: 10px; color: #6b7280; padding: 40px; justify-content: center; }
.spinner { width: 20px; height: 20px; border: 2px solid #e5e7eb; border-top-color: #6366F1; border-radius: 50%; animation: spin 0.6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty-state { padding: 40px; text-align: center; color: #6b7280; }

/* Mobile */
@media (max-width: 600px) {
  .gami-view { padding: 16px; }
  .stats-bar { gap: 8px; }
  .stat-chip { min-width: 80px; padding: 8px 10px; }
  .stat-chip-val { font-size: 18px; }
  .streak-banner { flex-wrap: wrap; }
  .lb-table th:nth-child(5),
  .lb-table td:nth-child(5),
  .lb-table th:nth-child(7),
  .lb-table td:nth-child(7) { display: none; }
}
</style>
