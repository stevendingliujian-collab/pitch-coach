#!/bin/bash
# dev-up.sh — one-command local bootstrap for the pitch-coach backend.
#
# Brings up the infra dependencies, waits until they are healthy, runs the DB
# migrations, and health-checks the API. Idempotent: safe to re-run.
#
# Usage:
#   ./scripts/dev-up.sh          # deps + migrate + start API + health check
#   ./scripts/dev-up.sh --no-api # deps + migrate only (start uvicorn yourself)
#
# Requires: Docker (compose v2), Python 3.11+, and backend/.env configured.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DB_URL="postgresql+asyncpg://pitchcoach:pitchcoach_dev@localhost:5432/pitchcoach"
API_PORT="${API_PORT:-8000}"
START_API=1
[ "${1:-}" = "--no-api" ] && START_API=0

step() { printf '\n\033[1;36m▶ %s\033[0m\n' "$1"; }
die()  { printf '\033[1;31m✗ %s\033[0m\n' "$1" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || die "Docker 未安装，请先安装 Docker Desktop"
docker info >/dev/null 2>&1 || die "Docker 守护进程未运行，请先启动 Docker"

# 1. .env
if [ ! -f backend/.env ]; then
  step "首次运行：从模板生成 backend/.env"
  cp backend/.env.example backend/.env
  echo "  已生成 backend/.env — 请填入 LLM_API_KEY 后重跑（否则 AI 功能会显式报错）"
fi

# 2. infra
step "启动依赖服务 (postgres / redis / minio / qdrant)"
docker compose up -d postgres redis minio qdrant

step "等待 Postgres 就绪"
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U pitchcoach >/dev/null 2>&1; then
    echo "  Postgres 就绪"; break
  fi
  [ "$i" = 30 ] && die "Postgres 30s 内未就绪"
  sleep 1
done

# 3. migrations
step "运行数据库迁移 (alembic upgrade head)"
( cd backend && DATABASE_URL="$DB_URL" alembic upgrade head )

if [ "$START_API" = 0 ]; then
  step "完成（--no-api）。手动启动：cd backend && uvicorn app.main:app --reload --port $API_PORT"
  exit 0
fi

# 4. API + health check
step "启动 API 并做健康检查"
pkill -f "uvicorn app.main:app.*--port $API_PORT" 2>/dev/null || true
( cd backend && DATABASE_URL="$DB_URL" \
    nohup uvicorn app.main:app --port "$API_PORT" >/tmp/pitchcoach-api.log 2>&1 & )

for i in $(seq 1 20); do
  if curl -sf "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1; then
    printf '\n\033[1;32m✓ API 健康检查通过: http://localhost:%s/health\033[0m\n' "$API_PORT"
    echo "  API 文档: http://localhost:$API_PORT/docs"
    echo "  日志:     tail -f /tmp/pitchcoach-api.log"
    echo
    echo "下一步：另开终端启动 Worker 和前端"
    echo "  cd backend && celery -A app.workers.celery_app worker --loglevel=info"
    echo "  cd frontend && npm install && npm run dev"
    exit 0
  fi
  sleep 1
done
die "API 20s 内未通过健康检查，查看 /tmp/pitchcoach-api.log"
