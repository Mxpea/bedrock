
# 一、项目概述与核心目标

**项目名称**（暂定）：**Bedrock**（基石）—— 内部小说创作与协同审稿平台

**核心原则**：

- **安全第一**：用户数据加密、密码防爆破、防 XSS/CSRF、文件上传扫描。
- **隐私至上**：作品三级可见性、作者数据隔离、日志脱敏。
- **高扩展性**：分级自定义引擎、模块化设计。

---

## 二、技术栈与架构图

### 2.1 技术栈确认

| 层次 | 技术选型 | 版本/说明 |
| :--- | :--- | :--- |
| **后端框架** | Django | 4.2 LTS |
| **API 层** | Django REST Framework (DRF) | 3.14+ |
| **异步任务** | Celery + Redis | Redis 7.x |
| **数据库** | PostgreSQL | 15+ (需支持 JSONField) |
| **文档转换** | LibreOffice (headless) + python-unoconv | 通过 subprocess 调用 |
| **实时协作** | Y.js WebSocket 服务 (Node.js 微服务) | Hocuspocus 或 y-websocket |
| **Web 服务器** | Nginx | 反向代理 + 静态文件 + 限流 |
| **部署** | Docker + Docker Compose | 生产环境编排 |
| **前端** | React / Vue (可选) | 与后端解耦，通过 DRF API 通信 |

### 2.2 系统架构简图

```text
[用户浏览器]
      |
      | HTTPS
      v
[ Nginx ] (限流、负载均衡、静态资源)
      |
      +------------------+------------------+
      |                  |                  |
      v                  v                  v
[ Django 主服务 ]   [ Y.js 协作服务 ]   [ Celery Worker ]
      |                  |                  |
      |                  |                  +-----> [ LibreOffice 转换器 ]
      v                  v
[ PostgreSQL ]      [ Redis ]
```

---

## 三、项目目录结构

采用 Django 社区推荐的大型项目布局，将配置、应用、静态文件、媒体文件分离。

```text
inkwell-studio/
│
├── config/                         # 项目配置根目录
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py                 # 通用配置
│   │   ├── development.py          # 开发环境配置 (DEBUG=True)
│   │   └── production.py           # 生产环境配置 (从环境变量读取)
│   ├── urls.py                     # 根 URL 路由
│   ├── asgi.py                     # ASGI 入口 (用于 WebSocket)
│   └── wsgi.py                     # WSGI 入口
│
├── apps/                           # Django 应用目录
│   ├── accounts/                   # 用户账户与权限管理
│   │   ├── models.py               # 自定义 User, InviteCode, AuditLog
│   │   ├── views.py                # 登录、注册、邀请码验证
│   │   ├── serializers.py
│   │   ├── permissions.py          # 自定义权限类 (IsAuthor, IsEditor等)
│   │   └── migrations/
│   │
│   ├── novels/                     # 小说核心业务
│   │   ├── models/
│   │   │   ├── novel.py            # Novel, Chapter, VisibilityConfig
│   │   │   ├── wiki.py             # Outline, Setting, Character, WikiBookmark
│   │   │   └── annotation.py       # SentenceComment, HighlightAnchor
│   │   ├── views/
│   │   │   ├── novel_views.py
│   │   │   ├── chapter_views.py
│   │   │   └── wiki_views.py
│   │   ├── tasks.py                # Celery 任务 (文档转换、导出)
│   │   └── utils/
│   │       └── document_converter.py  # 调用 LibreOffice
│   │
│   ├── customization/              # 分级自定义引擎
│   │   ├── models.py               # ThemeConfig, CustomCSSRequest
│   │   ├── css_validator.py        # CSS 白名单过滤逻辑
│   │   └── markdown_extensions.py  # 自定义 Markdown 语法解析器
│   │
│   ├── dashboard/                  # 管理员数据看板
│   │   ├── views.py
│   │   └── analytics.py            # 聚合查询逻辑
│   │
│   └── core/                       # 公共基础功能
│       ├── models.py               # 基础模型 (TimeStampedModel)
│       ├── pagination.py           # 统一分页
│       └── throttling.py           # 自定义限流 (防爆破)
│
├── media/                          # 用户上传文件存储目录 (Git忽略)
│   ├── avatars/
│   ├── novel_covers/
│   ├── wiki_attachments/
│   ├── documents/                  # Word/PDF/PPT 原始文件
│   └── converted/                  # 转换后的 HTML/图片
│
├── static/                         # 静态文件收集目录 (运行 collectstatic 后生成)
│
├── templates/                      # Django 模板 (若需要渲染后台页面)
│   └── admin/                      # 自定义 Admin 模板
│
├── scripts/                        # 运维脚本
│   ├── entrypoint.sh               # Docker 容器启动脚本
│   └── wait-for-it.sh
│
├── logs/                           # 应用日志目录 (Git忽略)
│   ├── django.log
│   └── security.log
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── manage.py
├── .env.example                    # 环境变量示例文件
├── .gitignore
└── README.md
```

---

## 四、安全与隐私保护实施方案

### 4.1 密码安全与防爆破

| 安全点 | 实现策略 |
| :--- | :--- |
| **密码存储** | 使用 Django 内置的 `PBKDF2` 算法 + 盐值 (默认 `PBKDF2PasswordHasher`)，迭代次数设为 **600,000** 以上。 |
| **登录限流** | 使用 `django-axes` 库或自定义 DRF 限流。基于 **IP + 用户名** 组合，失败 5 次后锁定 15 分钟。 |
| **密码强度校验** | 注册时强制：长度 ≥ 10 位，必须包含大小写字母、数字、特殊字符中的至少三类。使用 `django-password-validators`。 |
| **账户锁定** | 连续失败锁定后，需通过邮件验证码解锁（管理员可手动解锁）。 |
| **JWT 安全** | 若使用 JWT (DRF Simple JWT)，Token 有效期设为 **15 分钟**，Refresh Token 有效期 **7 天**，且 Refresh Token 记录在数据库可撤销。 |

### 4.2 数据传输与存储加密

| 层级 | 措施 |
| :--- | :--- |
| **传输层** | 全站强制 **HTTPS** (Nginx 配置 HSTS 头)。API 通信全程加密。 |
| **敏感数据存储** | 用户邮箱、手机号（若有）使用 **AES-256** 加密存储于数据库，密钥存放于环境变量。 |
| **媒体文件访问控制** | 用户上传的文档、图片不直接暴露 URL。使用 **Nginx `X-Accel-Redirect`** 或 Django 视图鉴权后返回临时下载链接。 |
| **数据库连接** | 使用 SSL 连接 PostgreSQL。 |

### 4.3 防 Web 攻击 (OWASP Top 10 防护)

| 攻击类型 | 防护措施 |
| :--- | :--- |
| **XSS** | 前端输出严格转义。后端接收用户内容时使用 **Bleach** 库清洗，仅允许极少数安全标签。对于解锁用户的自定义 HTML，渲染于 **Sandboxed Iframe**。 |
| **CSRF** | DRF 使用 TokenAuthentication (不依赖 Cookie) 或 Django 内置 CSRF 中间件 + `SameSite=Lax` Cookie。 |
| **SQL 注入** | 完全使用 Django ORM 参数化查询，**严禁** `raw()` 拼接字符串。 |
| **文件上传漏洞** | 1. 检查文件幻数 (magic number) 校验真实类型。<br>2. 重命名文件为 UUID。<br>3. 对 Word/PDF 进行病毒扫描（集成 ClamAV 容器）。<br>4. 限制上传大小（如 50MB）。 |
| **恶意 CSS 注入** | 解锁用户提交的 CSS 必须经过 **白名单过滤器**，仅允许：`color`, `background`, `border`, `margin`, `padding`, `font-family`, `transform` 等属性，禁止 `url()`, `@import`, `behavior`。 |

### 4.4 隐私保护与日志审计

| 方面 | 策略 |
| :--- | :--- |
| **日志脱敏** | 日志中严禁记录用户密码、Token、身份证号。使用 `django-structlog` 结构化日志。 |
| **操作审计** | 管理员操作、作者申请解锁高级权限、文档删除等关键行为记录到 `AuditLog` 表。 |
| **数据删除权** | 作者删除作品时，支持 **软删除** (is_deleted=True) 和 **物理删除** (30天后彻底清理媒体文件)。 |
| **IP 匿名化** | 存储 IP 用于防爆破时，仅存储 Hash 值或最后一段掩码处理 (如 `192.168.xxx.xxx`)。 |

### 4.5 Docker 环境安全

- 容器以 **非 root 用户** 运行 Django 进程。
- `.env` 文件不提交 Git，所有密钥通过 Docker secrets 或环境变量注入。
- Nginx 容器只暴露 80/443 端口，应用容器仅内部网络通信。

---

## 五、开发流程与里程碑建议

### 5.1 第一阶段：MVP 核心闭环 (4-6 周)

**目标**：能写、能发、能看。

- ✅ 用户注册/登录 (邀请制开关 + 权限组)
- ✅ 创建作品、写 Markdown 章节、保存草稿、发布章节
- ✅ 三级可见性 (私密/链接/公开)
- ✅ 基础阅读器 (字体切换、夜间模式)
- ✅ 管理员后台基础功能

### 5.2 第二阶段：文档导入与协作 (3-4 周)

- ✅ Word/PDF 上传转换为预览 (LibreOffice + Celery)
- ✅ 划线句子吐槽 (基础版，无复杂锚定逻辑)
- ✅ 作者自有 Wiki (大纲、设定、人物) 增删改查

### 5.3 第三阶段：自定义引擎与高级功能 (5-6 周)

- ✅ 基础视觉自定义 (背景、音效、预设 CSS 变量)
- ✅ 高级用户 CSS 解锁申请与审核流程
- ✅ 划线吐槽位置锚定优化
- ✅ 作者主页自定义 (基础模板)

### 5.4 第四阶段：数据看板与优化 (2-3 周)

- ✅ 管理员数据统计看板
- ✅ 全站搜索优化 (PostgreSQL 全文检索或 Elasticsearch)
- ✅ 性能压测与安全渗透测试

---

## 六、`.gitignore` 配置

针对上述目录结构，提供一份生产级 `.gitignore` 文件，重点排除敏感信息、媒体文件、日志和本地配置。

```gitignore
# .gitignore for Inkwell Studio

# -----------------------------
# Django 核心
# -----------------------------
*.log
*.pot
*.pyc
__pycache__/
db.sqlite3
db.sqlite3-journal
/media
/staticfiles
/static           # 如果 static 是收集后的目录则忽略，但通常保留源码静态文件
*.pid

# -----------------------------
# 敏感配置与环境变量
# -----------------------------
.env
.env.local
.env.*.local
config/settings/local.py
config/settings/production.py   # 若包含敏感密钥则忽略，推荐从环境变量读取

# -----------------------------
# 用户上传数据与转换文件 (隐私重灾区)
# -----------------------------
media/
converted_docs/
documents_upload/
user_exports/

# -----------------------------
# 日志与备份
# -----------------------------
logs/
*.sql
*.tar.gz
backups/

# -----------------------------
# IDE 与操作系统
# -----------------------------
.vscode/
.idea/
*.swp
.DS_Store
Thumbs.db

# -----------------------------
# Docker 相关
# -----------------------------
docker-compose.override.yml
.env.docker

# -----------------------------
# 测试与覆盖率
# -----------------------------
.coverage
htmlcov/
.tox/
.pytest_cache/
```

---

## 七、后续建议

1. **数据库设计文档**：下一步可输出 `apps/novels/models.py` 的核心代码结构，包含 `Novel`, `Chapter`, `WikiCharacter` 等表的字段与关系。
2. **CSS 白名单过滤代码示例**：提供一份 Python 实现的安全 CSS 解析器核心逻辑。
3. **Docker Compose 编排文件**：包含 Django, PostgreSQL, Redis, Nginx, LibreOffice 服务。
