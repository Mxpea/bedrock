# Bedrock (MVP Backend)

基于 Django 4.2 + DRF + PostgreSQL + Celery + Redis 的小说创作与审稿平台后端第一版。

## 已实现能力

- 邀请码可选注册 + JWT 登录刷新
- 自定义用户模型与角色字段（author/editor/admin）
- 小说与章节 CRUD
- 作品可见性：private/link/public
- 软删除作品
- 登录限流（IP + username）
- Markdown 内容存储与基础安全 HTML 渲染
- Celery 异步任务占位（文档转 HTML 流程接口）

## 快速启动（Docker）

1. 复制环境变量

```bash
cp .env.example .env
```

1. 启动服务

```bash
docker compose up --build
```

1. 访问

- API 根路径: `http://localhost/api/`
- 管理后台: `http://localhost/admin/`

## 本地运行（非 Docker）

本地运行默认使用开发配置：SQLite + Celery 同步执行（无需 Redis/PostgreSQL）。

### 一键启动（推荐）

```powershell
./scripts/start_local.ps1
```

可选参数：

- `-SkipInstall` 跳过依赖安装
- `-SkipMigrate` 跳过迁移
- `-UsePostgres` 使用本地 PostgreSQL（不使用 SQLite）

如果 PowerShell 执行策略受限，也可以使用：

```powershell
./scripts/start_local.bat
```

### 1) 创建并激活虚拟环境（Windows PowerShell）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) 安装依赖

```powershell
pip install -r requirements.txt
```

如果你要用本地 PostgreSQL，再额外安装：

```powershell
pip install -r requirements-postgres.txt
```

### 3) 设置开发环境变量

```powershell
$env:DJANGO_SETTINGS_MODULE="config.settings.development"
$env:DEV_USE_SQLITE="True"
```

### 4) 迁移并创建管理员

```powershell
python manage.py migrate
python manage.py createsuperuser
```

### 5) 启动服务

```powershell
python manage.py runserver 0.0.0.0:8000
```

访问地址：

- API 根路径: `http://127.0.0.1:8000/api/`
- 管理后台: `http://127.0.0.1:8000/admin/`

### 可选：切回本地 PostgreSQL

如果你本机已安装 PostgreSQL，可以设置：

```powershell
$env:DEV_USE_SQLITE="False"
$env:POSTGRES_DB="bedrock"
$env:POSTGRES_USER="bedrock"
$env:POSTGRES_PASSWORD="bedrock"
$env:POSTGRES_HOST="127.0.0.1"
$env:POSTGRES_PORT="5432"
python manage.py migrate
```

## 关键接口

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET /api/auth/me/`
- `GET/POST /api/novels/`
- `GET/PATCH/DELETE /api/novels/{id}/`
- `GET/POST /api/chapters/`

## 说明

- 当前版本聚焦后端 MVP 闭环，Y.js 协作服务、ClamAV、CSS 白名单引擎、审计看板等作为下一阶段扩展。
- `apps/novels/tasks.py` 的转换逻辑目前是占位实现，后续可替换为 LibreOffice headless 实际转换。
