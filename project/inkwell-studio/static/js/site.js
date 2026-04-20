const USER_CACHE_KEY = "bedrock_user_cache";
const USER_TOKEN_CACHE_KEY = "bedrock_user_cache_token";
const FONT_CACHE_KEY = "bedrock_fonts_loaded";
const TOPBAR_COLLAPSE_KEY = "bedrock_topbar_collapsed";
let currentUserPromise = null;

document.addEventListener("DOMContentLoaded", () => {
    setupAuthForms();
    setupDashboard();
    setupWorkspaceDashboard();
    setupWorkspaceDiscover();
    setupGlobalTheme();
    setupTopbarCollapse();
    loadCustomFonts();
    setupNavigation();
    setupWorkspaceSwitcher();
});

function setupTopbarCollapse() {
    const topbar = document.getElementById("global-topbar");
    const collapseBtn = document.getElementById("topbar-collapse-btn");
    const expandBtn = document.getElementById("topbar-expand-btn");

    if (!topbar || !collapseBtn || !expandBtn) {
        return;
    }

    const setCollapsed = (collapsed, persist = true) => {
        document.body.classList.toggle("topbar-collapsed", collapsed);
        collapseBtn.setAttribute("aria-label", collapsed ? "展开顶栏" : "收起顶栏");
        collapseBtn.title = collapsed ? "展开顶栏" : "收起顶栏";
        expandBtn.hidden = !collapsed;

        if (persist) {
            localStorage.setItem(TOPBAR_COLLAPSE_KEY, collapsed ? "1" : "0");
        }
    };

    setCollapsed(localStorage.getItem(TOPBAR_COLLAPSE_KEY) === "1", false);

    collapseBtn.addEventListener("click", () => {
        const collapsed = document.body.classList.toggle("topbar-collapsed");
        setCollapsed(collapsed);
    });

    expandBtn.addEventListener("click", () => {
        setCollapsed(false);
    });
}

function getAccessToken() {
    return localStorage.getItem("bedrock_access");
}

function getCookie(name) {
    const cookies = document.cookie ? document.cookie.split(";") : [];
    for (const raw of cookies) {
        const cookie = raw.trim();
        if (cookie.startsWith(name + "=")) {
            return decodeURIComponent(cookie.slice(name.length + 1));
        }
    }
    return "";
}

async function refreshAccessToken() {
    const refresh = localStorage.getItem("bedrock_refresh");
    if (!refresh) {
        return null;
    }

    try {
        const response = await fetch("/api/auth/refresh/", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({refresh}),
        });

        if (!response.ok) {
            return null;
        }

        const payload = await response.json();
        if (payload.access) {
            localStorage.setItem("bedrock_access", payload.access);
            if (payload.refresh) {
                localStorage.setItem("bedrock_refresh", payload.refresh);
            }
            return payload.access;
        }
    } catch (error) {
        console.error("Refresh token failed:", error);
    }

    return null;
}

async function fetchWithAuthRetry(url, init = {}) {
    const baseHeaders = init.headers instanceof Headers
        ? Object.fromEntries(init.headers.entries())
        : (init.headers || {});
    const method = String(init.method || "GET").toUpperCase();
    const token = getAccessToken();
    const csrfToken = getCookie("csrftoken");
    const unsafeMethod = !["GET", "HEAD", "OPTIONS", "TRACE"].includes(method);
    const csrfHeaders = unsafeMethod && csrfToken ? {"X-CSRFToken": csrfToken} : {};
    const firstHeaders = token
        ? {...baseHeaders, ...csrfHeaders, Authorization: `Bearer ${token}`}
        : {...baseHeaders, ...csrfHeaders};

    let response = await fetch(url, {...init, headers: firstHeaders});
    if (response.status !== 401) {
        return response;
    }

    const newAccess = await refreshAccessToken();
    if (!newAccess) {
        localStorage.removeItem("bedrock_access");
        localStorage.removeItem("bedrock_refresh");
        clearCachedUser();
        return response;
    }

    const retryHeaders = {...baseHeaders, ...csrfHeaders, Authorization: `Bearer ${newAccess}`};
    response = await fetch(url, {...init, headers: retryHeaders});
    return response;
}

function getCachedUser(token) {
    const cachedToken = localStorage.getItem(USER_TOKEN_CACHE_KEY);
    if (cachedToken !== token) {
        return null;
    }

    const raw = localStorage.getItem(USER_CACHE_KEY);
    if (!raw) {
        return null;
    }

    try {
        return JSON.parse(raw);
    } catch {
        return null;
    }
}

function setCachedUser(token, user) {
    localStorage.setItem(USER_TOKEN_CACHE_KEY, token);
    localStorage.setItem(USER_CACHE_KEY, JSON.stringify(user));
}

function clearCachedUser() {
    localStorage.removeItem(USER_TOKEN_CACHE_KEY);
    localStorage.removeItem(USER_CACHE_KEY);
}

async function fetchCurrentUser() {
    const token = getAccessToken();
    if (!token) {
        clearCachedUser();
        return null;
    }

    if (currentUserPromise) {
        return currentUserPromise;
    }

    const cachedUser = getCachedUser(token);
    if (cachedUser) {
        return cachedUser;
    }

    currentUserPromise = (async () => {
        const response = await fetch("/api/auth/me/", {
            headers: {Authorization: `Bearer ${token}`},
        });

        if (!response.ok) {
            console.error("Auth fetch failed:", response.status);
            if (response.status === 401 || response.status === 403) {
                clearCachedUser();
                return null;
            }

            const staleUser = getCachedUser(token);
            return staleUser;
        }

        const user = await response.json();
        setCachedUser(token, user);
        return user;
    })();

    try {
        return await currentUserPromise;
    } catch (error) {
        console.error("Auth fetch failed:", error);
        return getCachedUser(token);
    } finally {
        currentUserPromise = null;
    }
}

function getWorkspaceContext() {
    if (window.BEDROCK_WORKSPACE) {
        return window.BEDROCK_WORKSPACE;
    }

    const contextNode = document.querySelector("[data-workspace-context]");
    if (contextNode) {
        return {
            id: contextNode.dataset.workspaceId,
            title: contextNode.dataset.workspaceTitle,
            icon_url: contextNode.dataset.workspaceIconUrl || "",
            module: contextNode.dataset.workspaceModule,
            chapterId: contextNode.dataset.workspaceChapterId,
        };
    }

    const params = new URLSearchParams(window.location.search);
    const workspaceId = params.get("workspace_id") || params.get("novel_id");
    if (workspaceId) {
        return {
            id: workspaceId,
            title: params.get("workspace_title") || "当前工作区",
            module: params.get("module") || "writing",
            chapterId: params.get("chapter_id"),
        };
    }

    const match = window.location.pathname.match(/^\/workspace\/(\d+)\/(\w+)\/?$/);
    if (match) {
        return {
            id: match[1],
            title: "当前工作区",
            module: match[2],
            chapterId: null,
        };
    }

    return null;
}

async function setupNavigation() {
    const nav = document.getElementById("global-nav");
    if (!nav) {
        return;
    }

    const user = await fetchCurrentUser();
    if (!user) {
        nav.innerHTML = `
            <a href="/">首页</a>
            <a href="/novels/">发现</a>
            <a href="/login/">登录</a>
            <a href="/register/">注册</a>
        `;
        return;
    }

    const isAdmin = user.role === "admin" || user.is_staff || user.is_superuser;
    const adminLink = isAdmin ? '<a href="/admin/">控制台</a>' : "";

    nav.innerHTML = `
        <a href="/dashboard/">工作台</a>
        <a href="/novels/">发现</a>
        ${adminLink}
        <a href="/u/${escapeHtml(user.username)}/">个人</a>
        <a href="#" onclick="logout(event)">退出 (${escapeHtml(user.username)})</a>
    `;
}

async function setupWorkspaceSwitcher() {
    const switcher = document.getElementById("workspace-switcher");
    if (!switcher) {
        return;
    }

    const token = getAccessToken();
    const workspace = getWorkspaceContext();
    if (!token || !workspace) {
        switcher.hidden = true;
        return;
    }

    switcher.hidden = false;
    switcher.innerHTML = `<span class="workspace-switcher-label">${escapeHtml(workspace.title || "当前工作区")}</span>`;

    try {
        const response = await fetchWithAuthRetry("/api/workspaces/?owner=me&ordering=-updated_at");

        if (!response.ok) {
            return;
        }

        const payload = await response.json();
        const workspaces = (Array.isArray(payload) ? payload : payload.results || []).slice(0, 5);
        const summaryIcon = workspaceIconHtml(workspace.title || "当前工作区", workspace.icon_url || "", "switcher");
        const items = workspaces.length
            ? workspaces.map((item) => `
                <a class="workspace-switcher-item ${String(item.id) === String(workspace.id) ? "active" : ""}" href="/workspace/${item.id}/writing/">
                    ${workspaceIconHtml(item.title, item.icon_url || "", "switcher")}
                    <div class="workspace-switcher-item-text">
                        <strong>${escapeHtml(item.title)}</strong>
                        <span>${escapeHtml(item.visibility_label || item.visibility || "")}</span>
                    </div>
                </a>
            `).join("")
            : '<p class="workspace-switcher-empty">还没有工作区</p>';

        switcher.innerHTML = `
            <details class="workspace-switcher-menu">
                <summary>
                    <span class="workspace-switcher-summary-main">
                        ${summaryIcon}
                        <span>${escapeHtml(workspace.title || "当前工作区")}</span>
                    </span>
                    <span class="workspace-switcher-arrow">▾</span>
                </summary>
                <div class="workspace-switcher-panel">
                    <a class="workspace-switcher-create" href="#" onclick="createWorkspace(event)">+ 新建工作区</a>
                    <div class="workspace-switcher-list">
                        ${items}
                    </div>
                </div>
            </details>
        `;
    } catch (error) {
        console.error("Workspace switcher load failed:", error);
    }
}

function logout(event) {
    event.preventDefault();
    localStorage.removeItem("bedrock_access");
    localStorage.removeItem("bedrock_refresh");
    clearCachedUser();
    window.location.href = "/login/";
}

async function createWorkspace(event) {
    if (event) {
        event.preventDefault();
    }

    const token = getAccessToken();
    if (!token) {
        window.location.href = "/login/";
        return;
    }

    const title = window.prompt("请输入工作区名称", "新工作区");
    if (!title) {
        return;
    }

    const response = await fetchWithAuthRetry("/api/workspaces/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({title, summary: ""}),
    });

    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        window.alert(extractMessage(payload) || "创建失败");
        return;
    }

    const workspace = await response.json();
    window.location.href = `/workspace/${workspace.id}/writing/`;
}

async function loadCustomFonts(force = false) {
    if (window[FONT_CACHE_KEY] && !force) {
        return;
    }

    try {
        const token = getAccessToken();
        const response = token
            ? await fetchWithAuthRetry("/api/customization/fonts/")
            : await fetch("/api/customization/fonts/");
        if (!response.ok) {
            return;
        }

        const fonts = await response.json();
        const fontList = Array.isArray(fonts) ? fonts : (fonts.results || []);
        let styleStr = "";

        fontList.forEach((font) => {
            if (font.font_url) {
                styleStr += `
                    @font-face {
                        font-family: '${font.name}';
                        src: url('${font.font_url}');
                        font-display: swap;
                    }
                `;
            }
        });

        const existingStyleElement = document.getElementById("bedrock-custom-fonts");
        if (existingStyleElement) {
            existingStyleElement.remove();
        }

        if (styleStr) {
            const styleElement = document.createElement("style");
            styleElement.id = "bedrock-custom-fonts";
            styleElement.innerHTML = styleStr;
            document.head.appendChild(styleElement);
        }

        window.bedrockCustomFonts = fontList;
        window[FONT_CACHE_KEY] = true;
        window.dispatchEvent(new Event("bedrockFontsLoaded"));
    } catch (error) {
        console.error("Error loading custom fonts:", error);
    }
}

function setupGlobalTheme() {
    const toggleBtn = document.querySelector(".global-theme-toggle");
    const svgPath = toggleBtn ? toggleBtn.querySelector("path") : null;

    if (localStorage.getItem("bedrock-theme") === "dark") {
        document.documentElement.classList.add("dark-mode");
        document.body.classList.add("dark-mode");
        if (svgPath) setSunIcon(svgPath);
    } else if (svgPath) {
        setMoonIcon(svgPath);
    }

    if (toggleBtn) {
        toggleBtn.addEventListener("click", () => {
            document.documentElement.classList.toggle("dark-mode");
            document.body.classList.toggle("dark-mode");
            const isDark = document.body.classList.contains("dark-mode");

            if (isDark) {
                localStorage.setItem("bedrock-theme", "dark");
                if (svgPath) setSunIcon(svgPath);
            } else {
                localStorage.setItem("bedrock-theme", "light");
                if (svgPath) setMoonIcon(svgPath);
            }
        });
    }
}

function setSunIcon(path) {
    path.setAttribute("d", "M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z");
}

function setMoonIcon(path) {
    path.setAttribute("d", "M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z");
}

function setupAuthForms() {
    document.querySelectorAll("[data-auth-form]").forEach((form) => {
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const kind = form.dataset.authForm;
            const message = form.querySelector("[data-form-message]");
            const data = Object.fromEntries(new FormData(form).entries());
            const endpoint = kind === "login" ? "/api/auth/login/" : "/api/auth/register/";

            if (message) {
                message.textContent = "提交中...";
            }

            try {
                const response = await fetch(endpoint, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify(data),
                });
                const payload = await response.json().catch(() => ({}));

                if (!response.ok) {
                    if (message) {
                        message.textContent = extractMessage(payload);
                    }
                    return;
                }

                if (kind === "login") {
                    localStorage.setItem("bedrock_access", payload.access);
                    localStorage.setItem("bedrock_refresh", payload.refresh);
                    clearCachedUser();
                    if (message) {
                        message.textContent = "登录成功，正在跳转...";
                    }
                    const next = new URLSearchParams(window.location.search).get("next");
                    window.location.href = next || "/dashboard/";
                    return;
                }

                if (message) {
                    message.textContent = "注册成功，请返回登录。";
                }
                form.reset();
            } catch (error) {
                if (message) {
                    message.textContent = "请求失败，请检查本地服务是否启动。";
                }
            }
        });
    });
}

async function setupDashboard() {
    const target = document.querySelector("[data-current-user]");
    const usernameDisplay = document.querySelector("[data-username-display]");

    if (!target && !usernameDisplay) {
        return;
    }

    const user = await fetchCurrentUser();
    if (!user) {
        if (target) target.textContent = "未登录，请先前往登录页。";
        if (usernameDisplay) usernameDisplay.textContent = "请登录";
        return;
    }

    if (target) target.textContent = JSON.stringify(user, null, 2);
    if (usernameDisplay) usernameDisplay.textContent = user.username || "";
}

async function setupWorkspaceDashboard() {
    const container = document.querySelector("[data-workspace-list]");
    if (!container) {
        return;
    }

    const user = await fetchCurrentUser();
    if (!user) {
        container.innerHTML = `
            <article class="card workspace-empty-card">
                <h2>请先登录</h2>
                <p>登录后即可创建和管理自己的工作区。</p>
                <a class="button primary" href="/login/">前往登录</a>
            </article>
        `;
        return;
    }

    const response = await fetchWithAuthRetry("/api/workspaces/?owner=me&ordering=-updated_at");

    if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
            container.innerHTML = `
                <article class="card workspace-empty-card">
                    <h2>登录状态已失效</h2>
                    <p>请重新登录后继续管理工作区。</p>
                    <a class="button primary" href="/login/">前往登录</a>
                </article>
            `;
            return;
        }
        container.innerHTML = '<article class="card"><h2>加载失败</h2><p>无法获取工作区列表，请刷新重试。</p></article>';
        return;
    }

    const payload = await response.json();
    const workspaces = Array.isArray(payload) ? payload : payload.results || [];
    if (!workspaces.length) {
        container.innerHTML = `
            <article class="card workspace-empty-card">
                <h2>还没有工作区</h2>
                <p>先创建一个工作区来开始写作。</p>
                <a class="button primary" href="#" onclick="createWorkspace(event)">+ 新建工作区</a>
            </article>
        `;
        return;
    }

    container.innerHTML = workspaces.map((workspace) => `
        <article class="card workspace-card">
            <div class="workspace-card-top">
                <div class="workspace-card-heading">
                    ${workspaceIconHtml(workspace.title, workspace.icon_url || "", "card")}
                    <div>
                    <p class="eyebrow">Workspace</p>
                    <h2>${escapeHtml(workspace.title)}</h2>
                    </div>
                </div>
                <span class="badge">${escapeHtml(workspace.visibility_label || workspace.visibility)}</span>
            </div>
            <p>${escapeHtml(workspace.summary || "暂无简介")}</p>
            <div class="workspace-card-meta">
                <span>最近模块：${escapeHtml(workspace.module_label || workspace.last_open_module || "writing")}</span>
                <span>更新时间：${formatDate(workspace.updated_at)}</span>
            </div>
            <div class="actions">
                <a class="button primary" href="/workspace/${workspace.id}/writing/">进入工作区</a>
                <a class="button secondary" href="/workspace/${workspace.id}/settings/">设置</a>
            </div>
        </article>
    `).join("");
}

async function setupWorkspaceDiscover() {
    const container = document.querySelector("[data-workspace-discover]");
    if (!container) {
        return;
    }

    const response = await fetch("/api/workspaces/?visibility=public&ordering=-updated_at");
    if (!response.ok) {
        container.innerHTML = '<article class="card"><h2>加载失败</h2><p>公开工作区暂时不可用。</p></article>';
        return;
    }

    const payload = await response.json();
    const workspaces = Array.isArray(payload) ? payload : payload.results || [];
    if (!workspaces.length) {
        container.innerHTML = '<article class="card"><h2>暂无公开工作区</h2><p>稍后再来看看。</p></article>';
        return;
    }

    container.innerHTML = workspaces.map((workspace) => `
        <article class="card discover-card">
            <div class="workspace-card-top">
                <div class="workspace-card-heading">
                    ${workspaceIconHtml(workspace.title, workspace.icon_url || "", "card")}
                    <div>
                    <p class="eyebrow">公开工作区</p>
                    <h2>${escapeHtml(workspace.title)}</h2>
                    </div>
                </div>
                <span class="badge">${escapeHtml(workspace.visibility_label || workspace.visibility)}</span>
            </div>
            <p>${escapeHtml(workspace.summary || "暂无简介")}</p>
            <div class="workspace-card-meta">
                <span>作者：${escapeHtml(workspace.author_username || "匿名")}</span>
                <span>更新时间：${formatDate(workspace.updated_at)}</span>
            </div>
            <div class="actions">
                <a class="button primary" href="/reader/?workspace_id=${workspace.id}">阅读</a>
                <a class="button secondary" href="/u/${escapeHtml(workspace.author_username || "")}/">作者主页</a>
            </div>
        </article>
    `).join("");
}

function setupNovelList() {
    if (document.querySelector("[data-novel-list]")) {
        setupWorkspaceDashboard();
    }
}

function extractMessage(payload) {
    if (typeof payload === "string") {
        return payload;
    }
    if (payload && payload.detail) {
        return payload.detail;
    }
    const firstKey = Object.keys(payload || {})[0];
    if (!firstKey) {
        return "请求失败";
    }
    const firstValue = payload[firstKey];
    return Array.isArray(firstValue) ? firstValue[0] : String(firstValue);
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function formatDate(value) {
    if (!value) {
        return "-";
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return new Intl.DateTimeFormat("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    }).format(date);
}

function workspaceIconHtml(title, iconUrl, size = "card") {
    const safeTitle = escapeHtml(title || "#");
    const initial = safeTitle.slice(0, 1).toUpperCase();
    const cls = size === "switcher" ? "workspace-icon workspace-icon-sm" : "workspace-icon workspace-icon-md";

    if (iconUrl) {
        return `<span class="${cls}"><img src="${escapeHtml(iconUrl)}" alt="${safeTitle} 图标" loading="lazy"></span>`;
    }

    return `<span class="${cls} workspace-icon-fallback">${initial}</span>`;
}

window.logout = logout;
window.createWorkspace = createWorkspace;
window.loadCustomFonts = loadCustomFonts;