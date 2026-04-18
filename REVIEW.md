# Inkwell Studio — 完整代码评审报告

> 评审日期：2026-04-18  
> 代码路径：`project/inkwell-studio/`  
> 技术栈：Django 4.2 · DRF 3.15 · SimpleJWT · Celery · PostgreSQL · Redis · Bleach · Pillow

---

## 目录

1. [总体评价](#1-总体评价)
2. [安全问题（Security）](#2-安全问题security)
3. [功能缺陷（Bugs）](#3-功能缺陷bugs)
4. [性能问题（Performance）](#4-性能问题performance)
5. [代码质量（Code Quality）](#5-代码质量code-quality)
6. [配置与部署（Config / DevOps）](#6-配置与部署config--devops)
7. [问题汇总表](#7-问题汇总表)
8. [修复建议（Quick-fix 示例）](#8-修复建议quick-fix-示例)

---

## 1. 总体评价

Inkwell Studio 是一个架构清晰、功能覆盖较完整的小说创作平台后端。整体设计具备以下亮点：

- **分层清晰**：apps / config / templates / static 职责分明。
- **安全意识较强**：引入 Bleach 对 HTML 进行白名单过滤，JWT 令牌轮换 + 黑名单，限流策略（LoginThrottle + BurstUserThrottle），CSS 危险规则检测。
- **可扩展性好**：Celery 任务框架、AdvancedStyleGrant 分级授权、PlatformSetting 全局开关均预留了扩展空间。
- **管理功能完备**：Adminpanel 包含完整的用户管理、工作区管理、内容审核、CSS 审核、数据分析、运维工具。

但也存在若干安全隐患、功能缺陷和代码质量问题，需要关注并修复。

---

## 2. 安全问题（Security）

### 🔴 S-1 · SVG 上传未经净化，存在存储型 XSS 风险

**位置**：`apps/novels/views.py` 第 193 行（`ChapterViewSet.upload_image`）

```python
if ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
```

SVG 是 XML 格式，可内嵌 `<script>` 标签或 `onload` 属性。服务端直接存储并通过 `/media/` 对外提供时，浏览器会执行其中的脚本，造成存储型 XSS。

**修复建议**：
- 方案一（推荐）：禁止上传 SVG，从允许列表中移除 `".svg"`。
- 方案二：通过 `cairosvg` 或 `Pillow` 将 SVG 光栅化为 PNG 后存储。

---

### 🔴 S-2 · `custom_html` 字段缺少 HTML 净化，存在 XSS 风险

**位置**：`apps/customization/models.py` `AuthorHomepageConfig.custom_html`  
**位置**：`apps/customization/serializers.py` `AuthorHomepageConfigSerializer`

模型对 `custom_html` 字段没有任何净化。尽管前端可能使用沙盒 iframe，但序列化器中仅验证了 `custom_css`（通过 `validate_advanced_css`），完全没有对 `custom_html` 做 Bleach 过滤。如果该 HTML 被渲染到页面，攻击者可插入恶意脚本。

**修复建议**：在序列化器中添加 `validate_custom_html` 方法，使用 Bleach 白名单过滤或完全禁止直接 HTML 输入（改用模板参数化方案）。

```python
def validate_custom_html(self, value):
    if not value:
        return value
    allowed_tags = ["p", "br", "strong", "em", "a", "ul", "ol", "li", "h1", "h2", "h3", "img"]
    allowed_attrs = {"a": ["href", "title"], "img": ["src", "alt"]}
    return bleach.clean(value, tags=allowed_tags, attributes=allowed_attrs, strip=True)
```

---

### 🟠 S-3 · 文件上传依赖客户端 Content-Type，可被伪造

**位置**：`apps/novels/views.py`（`upload_icon`、`upload_image`、`upload_avatar`）  
**位置**：`apps/customization/views.py`（`upload_background`）

所有文件类型校验均通过 `image_file.content_type.startswith("image/")` 进行，但该值来自客户端请求头（`Content-Type` 字段），攻击者可将恶意文件的 `Content-Type` 设置为 `image/png` 绕过检查。

**修复建议**：使用 `python-magic` 读取文件前几个字节（magic bytes）来判断真实文件类型：

```python
import magic
mime = magic.from_buffer(image_file.read(2048), mime=True)
image_file.seek(0)
if not mime.startswith("image/"):
    return Response({"detail": "仅支持图片文件"}, status=400)
```

---

### 🟠 S-4 · `PBKDF2_ITERATIONS` 设置实际未生效

**位置**：`config/settings/base.py` 第 139 行

```python
PBKDF2_ITERATIONS = int(os.getenv("PBKDF2_ITERATIONS", "600000"))
```

Django 的 `PBKDF2PasswordHasher` 使用自身类变量 `iterations` 而**非** Django 设置中的 `PBKDF2_ITERATIONS`。这个设置值从未被传递给 hasher，因此实际运行的迭代次数是 hasher 的默认值（Django 4.2 中为 720,000），与意图值 600,000 不同。

**修复建议**：如需精确控制迭代次数，应在 `settings/base.py` 中定义子类：

```python
PASSWORD_HASHERS = [
    "config.hashers.CustomPBKDF2PasswordHasher",
]
```

并创建 `config/hashers.py`：

```python
from django.contrib.auth.hashers import PBKDF2PasswordHasher
import os

class CustomPBKDF2PasswordHasher(PBKDF2PasswordHasher):
    iterations = int(os.getenv("PBKDF2_ITERATIONS", "600000"))
```

---

### 🟠 S-5 · Bleach 允许 `data:` 协议，可用于 XSS/钓鱼

**位置**：`apps/customization/markdown_extensions.py` 第 63 行

```python
ALLOWED_PROTOCOLS = ["http", "https", "mailto", "data"]
```

允许 `data:` 协议意味着用户可以在链接或图片 `src` 中写入 `data:text/html,...` 或 `data:application/javascript,...`，在部分浏览器版本中可被利用执行脚本或进行内容劫持。

**修复建议**：移除 `"data"` 协议，除非有明确业务场景需要（如 base64 内嵌图片），此时应仅在 `img[src]` 限定范围内允许。

```python
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]
```

---

### 🟡 S-6 · 管理员操作缺少 CSRF 保护验证提示

**位置**：`apps/adminpanel/views.py`（所有 POST 视图）

所有管理面板 POST 操作（封禁用户、强制下线工作区、删除内容等）使用 Django 会话认证，CSRF 由中间件保护，这是正确的。但审计日志（`write_audit`）记录了大量关键操作，而**没有二次确认机制**（如针对敏感操作要求重新输入密码）。这不是一个代码 bug，但属于纵深防御不足。

---

## 3. 功能缺陷（Bugs）

### 🔴 B-1 · `InviteCode.used_at` 从未被赋值

**位置**：`apps/accounts/serializers.py` 第 54-57 行

```python
if invite:
    invite.used_by = user
    invite.is_active = False
    invite.save(update_fields=["used_by", "is_active", "updated_at"])
```

模型中定义了 `used_at = models.DateTimeField(null=True, blank=True)` 字段，但在邀请码被使用时永远不会写入时间戳。

**修复建议**：

```python
from django.utils import timezone

if invite:
    invite.used_by = user
    invite.is_active = False
    invite.used_at = timezone.now()
    invite.save(update_fields=["used_by", "is_active", "used_at", "updated_at"])
```

---

### 🟠 B-2 · `WorkspaceManageView.post` 中 `clear_cache` 动作无效

**位置**：`apps/adminpanel/views.py` 第 114-115 行

```python
elif action == "clear_cache":
    messages.success(request, "已执行缓存清理（当前为全局缓存级）")
```

`clear_cache` 只显示了成功消息，但**没有实际调用 `cache.clear()`**。与此对比，`OpsToolsView` 中的 `clear_cache` 动作则正确调用了 `cache.clear()`。

**修复建议**：

```python
elif action == "clear_cache":
    cache.clear()
    messages.success(request, "已执行缓存清理（当前为全局缓存级）")
```

---

### 🟠 B-3 · 章节 `unique_together (novel, order)` 导致重排序时出现 IntegrityError

**位置**：`apps/novels/models.py` 第 56 行

```python
unique_together = ("novel", "order")
```

当用户需要对章节重新排序时（例如调换章节 order=2 和 order=3），必须先把其中一个设为临时值。但由于 `unique_together` 约束，直接批量更新会触发数据库约束错误。代码中目前没有章节重排序的专门处理逻辑。

**修复建议**：使用数据库事务并采用"偏移量先移走，再最终设置"的两步策略，或换用 `DEFERRED` 约束（PostgreSQL 支持）。另一方案是移除数据库层约束，改由应用层保证顺序唯一性。

---

### 🟠 B-4 · `Character.reorder` 的 `bulk_update` 不会更新 `updated_at`

**位置**：`apps/novels/views.py` 第 283-284 行

```python
Character.objects.bulk_update(update_items, ["sort_order", "updated_at"])
```

由于 `TimeStampedModel.updated_at` 使用 `auto_now=True`，Django 的 `bulk_update` **不会自动填充该字段**——`auto_now` 仅在 `save()` 调用时生效。这里将 `"updated_at"` 加入 `fields` 列表但实际值未被赋予新时间，更新时间不会改变。

**修复建议**：在 `bulk_update` 前手动设置 `updated_at`：

```python
from django.utils import timezone
now = timezone.now()
for obj in update_items:
    obj.sort_order = ...
    obj.updated_at = now
Character.objects.bulk_update(update_items, ["sort_order", "updated_at"])
```

---

### 🟡 B-5 · `CharacterViewSet` 接受任意 `ordering` 字段名

**位置**：`apps/novels/views.py` 第 239-241 行

```python
ordering = (self.request.GET.get("ordering") or "").strip()
if ordering:
    return queryset.order_by(ordering)
```

`ordering` 字段直接来自 GET 参数，没有与 `ordering_fields` 白名单做校验。攻击者可传入敏感字段名（如 `novel__author__password`）尝试基于排序的信息泄露，或传入无效字段导致 Django ORM 抛出异常（500 错误）。

**修复建议**：使用白名单过滤：

```python
ALLOWED_ORDERINGS = {"sort_order", "-sort_order", "created_at", "-created_at", "name", "-name", "updated_at", "-updated_at"}
ordering = (self.request.GET.get("ordering") or "").strip()
if ordering and ordering in ALLOWED_ORDERINGS:
    return queryset.order_by(ordering)
```

---

### 🟡 B-6 · `NovelViewSet` 在 URL 路由中被重复注册

**位置**：`config/urls.py` 第 20-22 行

```python
router.register(r"novels", NovelViewSet, basename="novel")
router.register(r"workspaces", NovelViewSet, basename="workspace")
```

同一个 ViewSet 被注册了两次，产生完全重复的 API 端点（`/api/novels/` 和 `/api/workspaces/` 功能完全相同），造成 API 文档混乱，维护成本加倍，也可能产生权限绕过的误解。

**修复建议**：选择一个统一的 URL 前缀，或通过别名 + 路由配置让两个路径指向不同的序列化器。

---

### 🟡 B-7 · `OpsToolsView` 服务状态为硬编码假数据

**位置**：`apps/adminpanel/views.py` 第 601-602 行

```python
"doc_service_status": "healthy",
"search_service_status": "healthy",
```

这两个状态值永远显示 "healthy"，不反映真实服务状态，会误导运维人员。

**修复建议**：实现真实健康检查，或直接移除这两个字段，等有实际服务时再添加。

---

## 4. 性能问题（Performance）

### 🟠 P-1 · `CharacterSerializer` 每次请求对每个角色调用 `compute_chapter_mentions()` 三次

**位置**：`apps/novels/serializers.py` 第 105-117 行

```python
def get_mention_chapters(self, obj):
    return obj.compute_chapter_mentions()         # 第1次

def get_appearances_count(self, obj):
    return len(obj.compute_chapter_mentions())    # 第2次

def to_representation(self, instance):
    data = super().to_representation(instance)
    mentions = instance.compute_chapter_mentions()  # 第3次
    ...
```

每次调用 `compute_chapter_mentions()` 都会查询该小说的**所有章节**并进行正则匹配。对于一个有 50 个角色、100 章的小说，列表 API 会执行 **50 × 3 = 150 次**全量章节查询。

**修复建议**：在 `to_representation` 中计算一次并缓存，或使用 `@cached_property`：

```python
def to_representation(self, instance):
    data = super().to_representation(instance)
    mentions = instance.compute_chapter_mentions()   # 只算一次
    data["chapter_mentions"] = mentions
    data["mention_chapters"] = mentions
    data["appearances_count"] = len(mentions)
    return data
```

并将 `get_mention_chapters` 和 `get_appearances_count` 方法改为直接从 `to_representation` 的结果读取，避免重复计算。

---

### 🟡 P-2 · `AnalyticsView` 对同一时间范围多次查询相似数据集

**位置**：`apps/adminpanel/views.py` 第 558-573 行

`new_workspaces` 和 `workspace_series` 都基于同一个 `Novel` 时间范围过滤器，但执行了两次独立的查询。建议合并为一个聚合查询，或使用数据库视图缓存统计结果。

---

### 🟡 P-3 · `AdminDashboardView` 中 `recent_workspaces` 未分页，加载全量数据

**位置**：`apps/adminpanel/views.py` 第 81 行

```python
"recent_workspaces": Novel.objects.filter(is_deleted=False).select_related("author").order_by("-created_at")[:8],
```

这个 `[:8]` 在 Python 层截取而非数据库层 LIMIT，对于大数据集会加载超出需要的数据。实际上 Django ORM 的切片会生成 SQL LIMIT，这里是正确的。但需要确认 `select_related` 是否包含了所有模板所需字段，避免 N+1。（当前是正确的，属于低优先级确认项。）

---

## 5. 代码质量（Code Quality）

### 🟡 Q-1 · `Novel.workspace_name` 属性与序列化器字段冗余

**位置**：`apps/novels/models.py` 第 42-43 行 / `apps/novels/serializers.py` 第 8 行

```python
# models.py
@property
def workspace_name(self) -> str:
    return self.title

# serializers.py
workspace_name = serializers.CharField(source="title", read_only=True)
```

两处都表示 `title`，完全冗余。`NovelSerializer` 同时暴露了 `title` 和 `workspace_name` 两个相同值的字段，增加了 API 响应体积和客户端困惑。

**修复建议**：统一使用 `title`，移除 `workspace_name` 属性和序列化字段（或仅保留其一并做好文档说明）。

---

### 🟡 Q-2 · `PlatformSetting.get_solo()` 使用 `pk=1` 强依赖硬编码主键

**位置**：`apps/adminpanel/models.py` 第 26-28 行

```python
@classmethod
def get_solo(cls):
    obj, _ = cls.objects.get_or_create(pk=1)
    return obj
```

若数据被迁移或重建，`pk=1` 可能不再指向正确记录，导致静默创建重复记录。

**修复建议**：使用 `first_or_create` 模式或专门的单例字段（`is_solo=True`）查询：

```python
@classmethod
def get_solo(cls):
    obj = cls.objects.first()
    if obj is None:
        obj = cls.objects.create()
    return obj
```

---

### 🟡 Q-3 · `validate_invite_code` 中的宽泛 `except Exception` 吞没所有错误

**位置**：`apps/accounts/serializers.py` 第 23-27 行

```python
try:
    from apps.adminpanel.models import PlatformSetting
    setting = PlatformSetting.get_solo()
    require_invite = setting.registration_mode == PlatformSetting.RegistrationMode.INVITE_ONLY
except Exception:
    require_invite = False
```

数据库连接失败、迁移未完成、配置错误等情况都会被静默处理为"不需要邀请码"，可能造成未授权注册。

**修复建议**：缩小捕获范围到 `PlatformSetting.DoesNotExist` 或具体的数据库异常，其余情况向上抛出或记录日志。

---

### 🟡 Q-4 · `LoginView` 重复调用 `authenticate` 导致第二次密码验证

**位置**：`apps/accounts/views.py` 第 25-34 行

```python
def post(self, request, *args, **kwargs):
    response = super().post(request, *args, **kwargs)   # JWT 已做一次认证
    if response.status_code == 200:
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(request=request, username=username, password=password)  # 再做一次
        if user is not None:
            auth_login(request, user)
```

`TokenObtainPairView` 已在内部完成了用户认证。这里为了同时维护 Session 再次调用 `authenticate`，会导致两次密码 hash 验证（性能损耗），且如果密码在两次调用间被修改（极端并发场景），行为可能不一致。

**修复建议**：从 JWT view 继承并获取已验证的 user 对象，而不是再次调用 `authenticate`。或者明确注释说明此处的 Session 绑定意图。

---

### 🟡 Q-5 · 管理角色判断逻辑分散且不一致

多处代码使用不同方式判断管理员：

```python
# 方式1 (views.py perform_update)
is_admin = user.is_superuser or user.is_staff or getattr(user, "role", "") == "admin"

# 方式2 (permissions.py)
return bool(user and user.is_authenticated and (user.is_staff or getattr(user, "role", "") == "admin"))

# 方式3 (adminpanel views.py test_func)
return user.is_authenticated and (user.is_superuser or user.is_staff or getattr(user, "role", "") == "admin")
```

三种写法略有差异（方式2没有检查 `is_superuser`）。建议将此逻辑集中到 User 模型方法或单一工具函数中：

```python
# apps/accounts/models.py
def is_admin_user(self) -> bool:
    return self.is_superuser or self.is_staff or self.role == self.Role.ADMIN
```

---

### 🟡 Q-6 · `Chapter.save()` 每次保存都重新渲染 Markdown，即使内容未变化

**位置**：`apps/novels/models.py` 第 71-77 行

```python
def save(self, *args, **kwargs):
    if self._author_has_advanced_markdown_access():
        self.content_html = sanitize_advanced_content(self.content_md)
    else:
        self.content_html = sanitize_standard_content(self.content_md)
    super().save(*args, **kwargs)
```

无论更新的是什么字段（哪怕只是 `order` 或 `is_published`），都会重新渲染整个 Markdown，还包括一次权限查询（`AdvancedStyleGrant`）。

**修复建议**：仅在 `content_md` 实际变化时重新渲染，可通过 `update_fields` 判断：

```python
def save(self, *args, **kwargs):
    update_fields = kwargs.get("update_fields")
    if update_fields is None or "content_md" in update_fields:
        if self._author_has_advanced_markdown_access():
            self.content_html = sanitize_advanced_content(self.content_md)
        else:
            self.content_html = sanitize_standard_content(self.content_md)
        if update_fields is not None and "content_html" not in update_fields:
            kwargs["update_fields"] = list(update_fields) + ["content_html"]
    super().save(*args, **kwargs)
```

---

### 🟢 Q-7 · `CustomFontSerializer` 在 `create` 中访问 `request.user` 但未处理 `request` 为 None 的情况

**位置**：`apps/customization/serializers.py` 第 23-26 行

```python
def create(self, validated_data):
    request = self.context.get("request")
    validated_data["uploader"] = request.user   # 若 request 为 None，此处会 AttributeError
    return super().create(validated_data)
```

在 serializer 被脱离请求上下文（如测试、后台任务）调用时会抛出异常。`CustomFontViewSet.perform_create` 已正确传递了 `uploader`，因此 serializer 中的这段重复设置逻辑可以移除。

---

## 6. 配置与部署（Config / DevOps）

### 🟠 D-1 · Production 配置过于简单，缺少必要安全设置

**位置**：`config/settings/production.py`

```python
from .base import *  # noqa
DEBUG = False
```

生产配置除了关闭 DEBUG 外什么都没有。缺少：
- `ALLOWED_HOSTS` 显式设置（当前靠环境变量，无默认兜底）
- `SECURE_SSL_REDIRECT = True`
- `SECURE_HSTS_SECONDS`（HTTP Strict Transport Security）
- `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
- `SECURE_HSTS_PRELOAD = True`
- `SESSION_COOKIE_AGE` 限制
- 日志配置（生产环境的错误应记录到文件或外部服务）

**修复建议**：在 production.py 中明确设置上述配置项。

---

### 🟠 D-2 · Dockerfile 安装 LibreOffice 但任务代码仅为占位符

**位置**：`Dockerfile` 第 10 行 / `apps/novels/tasks.py`

```dockerfile
RUN apt-get install -y libreoffice
```

LibreOffice 安装包约 **~300MB**，但 `convert_document_to_html` 任务仅输出一个 HTML 占位字符串，实际没有调用 LibreOffice。这会：
- 显著增加镜像构建时间和镜像大小。
- 在生产环境保留了一个未使用的、攻击面较大的软件。

**修复建议**：在任务未实现前，从 Dockerfile 中移除 `libreoffice` 安装步骤。

---

### 🟡 D-3 · `.env.example` 使用弱默认凭据

**位置**：`.env.example`

```
POSTGRES_PASSWORD=bedrock
DJANGO_SECRET_KEY=change-me
```

开发者克隆项目后可能直接使用 `.env.example` 而不修改密码，特别是在 CI/CD 流水线或开发容器中。

**修复建议**：在 README 中明确标注这些值必须替换，并在启动脚本中添加对 `DJANGO_SECRET_KEY=change-me` 的检测：

```python
# settings/base.py
if SECRET_KEY == "unsafe-dev-key" and not DEBUG:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production!")
```

---

### 🟡 D-4 · Development 设置允许所有 Host，未受限制

**位置**：`config/settings/development.py` 第 5 行

```python
ALLOWED_HOSTS = ["*"]
```

虽然开发环境通常在本地运行，但通配符 ALLOWED_HOSTS 可能导致 HTTP Host 头注入漏洞，建议明确指定：

```python
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]
```

---

### 🟡 D-5 · `docker-compose.yml` 未配置数据库健康检查，服务启动顺序可能出错

**位置**：`docker-compose.yml`

`web` 服务通过 `depends_on: [db, redis]` 等待数据库，但 `depends_on` 只等待容器**启动**，不等待服务**就绪**。PostgreSQL 完全初始化需要几秒，可能导致 `web` 服务在数据库就绪前尝试连接而失败。

**修复建议**：添加健康检查：

```yaml
db:
  image: postgres:15
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-bedrock}"]
    interval: 5s
    timeout: 5s
    retries: 5
  ...

web:
  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_started
```

---

### 🟢 D-6 · `requirements-postgres.txt` 的用途不明确

**位置**：`requirements-postgres.txt`（文件存在但内容未见于主 requirements.txt）

需确认该文件是否被 Dockerfile 正确引入，避免生产环境缺少 PostgreSQL 驱动（`psycopg2` 或 `psycopg2-binary`）导致连接失败。

---

## 7. 问题汇总表

| 编号 | 严重程度 | 分类 | 标题 | 位置 |
|------|--------|------|------|------|
| S-1 | 🔴 高危 | 安全 | SVG 上传未净化，存储型 XSS | novels/views.py |
| S-2 | 🔴 高危 | 安全 | `custom_html` 缺少 Bleach 过滤 | customization/serializers.py |
| S-3 | 🟠 中危 | 安全 | Content-Type 可被伪造 | 多处文件上传视图 |
| S-4 | 🟠 中危 | 安全 | PBKDF2 迭代次数设置未生效 | settings/base.py |
| S-5 | 🟠 中危 | 安全 | Bleach 允许 `data:` 协议 | markdown_extensions.py |
| S-6 | 🟡 低危 | 安全 | 管理敏感操作缺少二次确认 | adminpanel/views.py |
| B-1 | 🔴 高危 | Bug | `InviteCode.used_at` 永远不被赋值 | accounts/serializers.py |
| B-2 | 🟠 中危 | Bug | `clear_cache` 动作无实际效果 | adminpanel/views.py |
| B-3 | 🟠 中危 | Bug | 章节 unique_together 导致重排序报错 | novels/models.py |
| B-4 | 🟠 中危 | Bug | `bulk_update` 不更新 `auto_now` 字段 | novels/views.py |
| B-5 | 🟡 低危 | Bug | 任意 ordering 字段名漏洞 | novels/views.py |
| B-6 | 🟡 低危 | Bug | NovelViewSet 重复注册 | config/urls.py |
| B-7 | 🟡 低危 | Bug | 服务状态硬编码为 "healthy" | adminpanel/views.py |
| P-1 | 🟠 中危 | 性能 | compute_chapter_mentions() 每请求调用3次 | novels/serializers.py |
| P-2 | 🟡 低危 | 性能 | 分析视图重复查询相似数据集 | adminpanel/views.py |
| Q-1 | 🟡 低危 | 质量 | workspace_name 属性与字段冗余 | novels/models.py |
| Q-2 | 🟡 低危 | 质量 | get_solo() 硬编码 pk=1 | adminpanel/models.py |
| Q-3 | 🟡 低危 | 质量 | except Exception 吞没错误 | accounts/serializers.py |
| Q-4 | 🟡 低危 | 质量 | LoginView 重复调用 authenticate | accounts/views.py |
| Q-5 | 🟡 低危 | 质量 | 管理员判断逻辑分散不一致 | 多处 |
| Q-6 | 🟡 低危 | 质量 | Chapter.save() 无条件重渲染 Markdown | novels/models.py |
| Q-7 | 🟢 建议 | 质量 | CustomFontSerializer request 未判空 | customization/serializers.py |
| D-1 | 🟠 中危 | 部署 | Production 配置缺少安全 Headers | settings/production.py |
| D-2 | 🟠 中危 | 部署 | Dockerfile 包含未使用的 LibreOffice | Dockerfile |
| D-3 | 🟡 低危 | 部署 | .env.example 使用弱默认凭据 | .env.example |
| D-4 | 🟡 低危 | 部署 | Development ALLOWED_HOSTS 过于宽松 | settings/development.py |
| D-5 | 🟡 低危 | 部署 | docker-compose 缺少数据库健康检查 | docker-compose.yml |
| D-6 | 🟢 建议 | 部署 | requirements-postgres.txt 用途不明 | requirements-postgres.txt |

---

## 8. 修复建议（Quick-fix 示例）

### 快速修复 S-1：禁用 SVG 上传

```python
# apps/novels/views.py - upload_image action
if ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:   # 移除 ".svg"
    return Response({"detail": "不支持的图片格式"}, status=status.HTTP_400_BAD_REQUEST)
```

### 快速修复 B-1：记录邀请码使用时间

```python
# apps/accounts/serializers.py
from django.utils import timezone

if invite:
    invite.used_by = user
    invite.is_active = False
    invite.used_at = timezone.now()
    invite.save(update_fields=["used_by", "is_active", "used_at", "updated_at"])
```

### 快速修复 B-2：使 clear_cache 真正清理缓存

```python
# apps/adminpanel/views.py - WorkspaceManageView.post
elif action == "clear_cache":
    from django.core.cache import cache
    cache.clear()
    messages.success(request, "已执行缓存清理（当前为全局缓存级）")
```

### 快速修复 P-1：避免重复调用 compute_chapter_mentions

```python
# apps/novels/serializers.py - CharacterSerializer
def to_representation(self, instance):
    data = super().to_representation(instance)
    mentions = instance.compute_chapter_mentions()  # 只计算一次
    data["chapter_mentions"] = mentions
    data["mention_chapters"] = mentions
    data["appearances_count"] = len(mentions)
    return data

# 移除 get_mention_chapters 和 get_appearances_count 方法（其逻辑已在 to_representation 中覆盖）
```

### 快速修复 D-1：完善 Production 配置

```python
# config/settings/production.py
from .base import *  # noqa
import os

DEBUG = False

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_AGE = 86400  # 24 hours

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": "/app/logs/django-error.log",
        },
    },
    "root": {
        "handlers": ["file"],
        "level": "ERROR",
    },
}
```

---

*报告由 GitHub Copilot 生成，供开发团队参考，修复优先级请结合实际业务风险评估。*
