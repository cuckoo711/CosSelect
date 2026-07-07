# 团片选片协作系统 (CosSelect)

为 Cosplay 团片拍摄团队打造的私密、轻量、移动优先的协作选片工具。团长上传原片，参与者通过口令加入后进行评分、批注、点赞与喜欢标记，快速达成选片共识。

## 特性

- **私密访问**：无公开分享，参与者需 8 位口令进入（24 小时有效，可随时重置）
- **免注册**：参与者用昵称识别身份，相同昵称自动恢复历史评分/批注/喜欢
- **团长管理**：无限级分类（折叠展开 + 拖动排序）、批量上传、缩略图异步生成、统计看板、CSV 导出
- **移动优先预览器**：触摸滑动切换、双指缩放、查看原图确认、`el-rate` 半星评分、批注（团长自动置顶）、点赞、私密喜欢、原图下载
- **暗色简约主题**：参考 Jellyfin 配色
- **异步缩略图**：Celery + Redis 队列生成（≤1200px 宽、≤500KB、去除 Exif），未生成时降级显示原图

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | FastAPI · SQLAlchemy 2.0 · PostgreSQL · Celery · Redis · Pillow |
| 前端 | Vue 3 · Vite · TypeScript · Element Plus · Pinia · Axios |
| 部署 | Docker Compose（postgres · redis · backend · worker · frontend/nginx）|

## 快速开始（Docker）

```bash
cd CosSelect
cp .env.example .env
# 编辑 .env：至少修改 POSTGRES_PASSWORD 和 SECRET_KEY
#   SECRET_KEY 生成：openssl rand -hex 32
# 如 8080 被占用，修改 HTTP_PORT

docker compose up -d --build
```

访问 `http://<服务器IP>:<HTTP_PORT>`（默认 8080）。

### 服务组成

| 服务 | 说明 |
|------|------|
| `postgres` | 数据库（数据卷 `pgdata`）|
| `redis` | Celery broker / backend（数据卷 `redisdata`）|
| `backend` | FastAPI（内部 8000）|
| `worker` | Celery worker，生成缩略图 |
| `frontend` | Nginx，托管 SPA 并反代 `/api` 到 backend，宿主暴露 `HTTP_PORT` |

原图与缩略图存于数据卷 `photodata`（容器内 `/data/spaces`）。

## 使用流程

1. **团长**：门户选「我是团长」→ 创建空间 → **保存管理密钥**（后续管理凭证）与口令。
2. 进入「分类与上传」：建分类、拖动排序、批量上传图片。
3. **参与者**：门户选「我是参与者」→ 输入口令 → 设置昵称 → 进入。
4. 网格中点击缩略图打开预览器：评分（必选、可改）、批注、点赞、喜欢、查看/下载原图，左右滑动切换。
5. **团长**在「统计看板」查看排名并导出 CSV。

> 团长身份靠**管理密钥**校验（请求头 `X-Manage-Key`）；参与者靠加入时下发的令牌（`X-Participant-Token`）。重置口令不会清除任何数据。

## 本地开发

### 后端

```bash
cd backend
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -e .
# 快速起服务（默认连本机 PG/Redis，可用 .env 覆盖）
.venv/bin/uvicorn app.main:app --reload --port 8000
# worker
.venv/bin/celery -A app.celery_app.celery_app worker --loglevel=info
```

无需外部服务的冒烟测试（SQLite，缩略图同步降级生成）：

```bash
cd backend && .venv/bin/python smoke_test.py
```

### 前端

```bash
cd frontend
pnpm install
pnpm dev          # http://localhost:5173，已代理 /api 到 localhost:8000
pnpm build        # 类型检查 + 生产构建
```

## 主要 API

统一响应格式：`{ "code": 0, "data": ..., "msg": "success" }`（`code != 0` 表示业务错误）。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/spaces` | 创建空间（返回 space_id + invite_code + manage_key）|
| POST | `/api/spaces/{id}/regenerate-code` | 重置口令 |
| POST | `/api/spaces/verify-code` | 按口令查找空间 |
| POST | `/api/spaces/{id}/participants` | 加入（昵称唯一 / 恢复身份）|
| GET/POST/PUT/DELETE | `/api/spaces/{id}/categories...` | 分类增改删 + `reorder/batch` 排序 |
| POST | `/api/spaces/{id}/photos/upload` | 批量上传 |
| GET | `/api/spaces/{id}/photos?category_id&sort` | 列表（sort: score/time/count）|
| GET | `/api/spaces/{id}/photos/{pid}` | 详情（含评分、批注）|
| GET | `/api/spaces/{id}/photos/{pid}/thumbnail\|original` | 缩略图 / 原图（`?download=true` 下载）|
| POST | `/api/spaces/{id}/photos/{pid}/ratings` | 评分（0.5 步进，唯一可改）|
| GET/POST/PUT/DELETE | `/api/spaces/{id}/.../comments...` | 批注（团长自动置顶，仅本人可改删）|
| POST | `/api/spaces/{id}/comments/{cid}/like` | 赞同切换 |
| POST | `/api/spaces/{id}/photos/{pid}/favorite` | 喜欢切换（私密）|
| GET | `/api/spaces/{id}/stats` · `/export` | 统计看板 · CSV 导出 |

## 生产部署提示

- 上传大图：前端 nginx 已设 `client_max_body_size 200m`；如经宝塔/外层 Nginx 反代，需同步放大。
- 建议在外层用 HTTPS 反向代理到 `frontend` 容器端口。
- 务必修改 `.env` 中的 `SECRET_KEY` 与数据库密码。
