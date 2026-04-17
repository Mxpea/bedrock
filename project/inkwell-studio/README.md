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

## 快速启动

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
