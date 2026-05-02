# OTD AI 述标教练

## 快速启动

### 1. 配置环境变量

```bash
cd backend
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

### 2. 启动后端服务（Docker）

```bash
# 在项目根目录
docker compose up -d postgres redis minio

# 运行数据库迁移
cd backend
pip install -r requirements.txt
DATABASE_URL=postgresql+psycopg2://pitchcoach:pitchcoach_dev@localhost:5432/pitchcoach \
  alembic upgrade head

# 启动 API 服务
uvicorn app.main:app --reload --port 8000

# 启动 Celery Worker（新终端）
celery -A app.workers.celery_app worker --loglevel=info
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### 4. 访问

- 前端：http://localhost:5173
- API 文档：http://localhost:8000/docs
- MinIO 控制台：http://localhost:9001 (minioadmin / minioadmin123)

## 项目结构

```
pitch-coach/
├── backend/          # FastAPI + Python 后端
│   ├── app/
│   │   ├── api/v1/   # REST 路由
│   │   ├── models/   # SQLAlchemy ORM
│   │   ├── services/ # ppt_parser, llm_adapter, scoring_engine
│   │   ├── workers/  # Celery 异步任务
│   │   └── core/     # 配置、鉴权、存储、脱敏、WebSocket
│   └── migrations/   # Alembic 迁移
└── frontend/         # Vue 3 + TypeScript 前端
    └── src/
        ├── views/    # 页面
        ├── components/ # 组件（PlanTab 左右分栏核心）
        ├── stores/   # Pinia 状态
        ├── api/      # API 封装
        └── composables/ # useAppMode, useWebSocket
```

## 当前阶段：Phase 0a（F1 验证版）

已完成：
- ✅ 完整后端架构（FastAPI + Celery + PostgreSQL + MinIO）
- ✅ 所有数据库表 + Alembic 迁移
- ✅ PPT 上传 → 解析 → LLM 方案生成完整流水线
- ✅ 数据脱敏 + 还原（PII 不出境）
- ✅ WebSocket 实时进度推送
- ✅ 前端完整脚手架 + 登录/注册
- ✅ 项目列表 + 新建项目
- ✅ PlanView 左右分栏（PPT缩略图 + 逐页讲解要点）
- ✅ 方案编辑 + 人工修改标记

下一步（Phase 0b）：
- F3 排练录音（MediaRecorder + WebM/Opus）
- ASR 转录（Paraformer-Large）
- 规则评分引擎（填充词 + 语速 + 时间控制）
- 评分报告页面
