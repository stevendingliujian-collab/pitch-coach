import { api } from './index'

export interface AchievementItem {
  id: number
  code: string
  name: string
  description: string
  icon_emoji: string
  category: string
  points: number
  earned: boolean
  earned_at: string | null
}

export interface UserStats {
  total_rehearsals: number
  total_practice_sessions: number
  total_qa_sessions: number
  best_rehearsal_score: number
  avg_rehearsal_score: number
  current_streak: number
  longest_streak: number
  total_points: number
  total_achievements: number
  last_activity_at: string | null
}

export interface LeaderboardEntry {
  rank: number
  user_id: number
  display_name: string
  avatar: string | null
  total_points: number
  total_rehearsals: number
  best_score: number
  avg_score: number
  current_streak: number
  total_achievements: number
}

export interface LeaderboardResult {
  period: string
  leaderboard: LeaderboardEntry[]
  my_rank: number | null
  total_participants: number
}

export interface StreakInfo {
  current_streak: number
  longest_streak: number
  fire_level: number
  fire_emoji: string
  message: string
}

export interface NewBadge {
  code: string
  name: string
  description: string
  icon_emoji: string
  points: number
}

export const gamificationApi = {
  achievements: () => api.get<AchievementItem[]>('/gamification/achievements'),
  stats: () => api.get<UserStats>('/gamification/stats'),
  leaderboard: (period: 'week' | 'month' | 'all_time' = 'week') =>
    api.get<LeaderboardResult>('/gamification/leaderboard', { params: { period } }),
  streak: () => api.get<StreakInfo>('/gamification/streak'),
}
