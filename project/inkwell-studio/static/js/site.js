document.addEventListener("DOMContentLoaded", () => {
    setupAuthForms();
    setupDashboard();
    setupNovelList();
    setupGlobalTheme();
    loadCustomFonts();
    setupNavigation();
});

function setupNavigation() {
    const nav = document.getElementById("global-nav");
    if (!nav) return;

    const token = localStorage.getItem("bedrock_access");
    if (!token) {
        // 未登录访客：首页、发现、关于 | 登录 / 注册
        nav.innerHTML = `
            <a href="/">首页</a>
            <a href="/novels/">发现</a>
            <a href="#">关于</a>
            <a href="/login/">登录</a>
            <a href="/register/">注册</a>
        `;
        return;
    }

    // 已登录状态：拉取用户信息决定角色菜单
    fetch("/api/auth/me/", {
        headers: {Authorization: `Bearer ${token}`},
    })
    .then((response) => {
        if (!response.ok) throw new Error("Unauthorized");
        return response.json();
    })
    .then((user) => {
        if (user.role === 'admin') {
            nav.innerHTML = `
                <a href="/dashboard/">管理面板</a>
                <a href="/novels/">全站作品</a>
                <a href="#">用户管理</a>
                <a href="/u/${user.username}/">个人空间</a>
                <a href="#" onclick="logout(event)">退出 (${user.username})</a>
            `;
        } else if (user.role === 'author') {
            nav.innerHTML = `
                <a href="/dashboard/">创作工坊</a>
                <a href="/novels/">我的作品</a>
                <a href="/u/${user.username}/">个人空间</a>
                <a href="#" onclick="logout(event)">退出 (${user.username})</a>
            `;
        } else {
            // 普通读者
            nav.innerHTML = `
                <a href="/">首页</a>
                <a href="/novels/">发现</a>
                <a href="#">我的书架</a>
                <a href="/u/${user.username}/">个人空间</a>
                <a href="#" onclick="logout(event)">退出 (${user.username})</a>
            `;
        }
    })
    .catch(() => {
        // 报错则退回未登录态
        nav.innerHTML = `
            <a href="/">首页</a>
            <a href="/novels/">发现</a>
            <a href="#">关于</a>
            <a href="/login/">登录</a>
            <a href="/register/">注册</a>
        `;
    });
}

function logout(e) {
    e.preventDefault();
    localStorage.removeItem("bedrock_access");
    localStorage.removeItem("bedrock_refresh");
    window.location.href = "/login/";
}

async function loadCustomFonts() {
    try {
        const response = await fetch("/api/customization/fonts/");
        if (!response.ok) return;
        const fonts = await response.json();
        const fontList = Array.isArray(fonts) ? fonts : (fonts.results || []);
        
        let styleStr = '';
        fontList.forEach(font => {
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
        
        if (styleStr) {
            const styleElement = document.createElement('style');
            styleElement.id = 'bedrock-custom-fonts';
            styleElement.innerHTML = styleStr;
            document.head.appendChild(styleElement);
        }
        
        // Dispatch event for UI components to pick up new fonts
        window.bedrockCustomFonts = fontList;
        window.dispatchEvent(new Event('bedrockFontsLoaded'));
    } catch (e) {
        console.error('Error loading custom fonts:', e);
    }
}

function setupGlobalTheme() {
    const toggleBtn = document.querySelector('.global-theme-toggle');
    const svgPath = toggleBtn ? toggleBtn.querySelector('path') : null;

    // Load from local storage
    if (localStorage.getItem('bedrock-theme') === 'dark') {
        document.documentElement.classList.add('dark-mode');
        document.body.classList.add('dark-mode');
        if (svgPath) setSunIcon(svgPath);
    } else {
        if (svgPath) setMoonIcon(svgPath);
    }

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            document.documentElement.classList.toggle('dark-mode');
            document.body.classList.toggle('dark-mode');
            const isDark = document.body.classList.contains('dark-mode');

            if (isDark) {
                localStorage.setItem('bedrock-theme', 'dark');
                if (svgPath) setSunIcon(svgPath);
            } else {
                localStorage.setItem('bedrock-theme', 'light');
                if (svgPath) setMoonIcon(svgPath);
            }
        });
    }
}

function setSunIcon(path) {
    path.setAttribute('d', 'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z');
}

function setMoonIcon(path) {
    path.setAttribute('d', 'M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z');
}

function setupAuthForms() {
    document.querySelectorAll("[data-auth-form]").forEach((form) => {
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const kind = form.dataset.authForm;
            const message = form.querySelector("[data-form-message]");
            const data = Object.fromEntries(new FormData(form).entries());
            const endpoint = kind === "login" ? "/api/auth/login/" : "/api/auth/register/";

            message.textContent = "提交中...";

            try {
                const response = await fetch(endpoint, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify(data),
                });
                const payload = await response.json();

                if (!response.ok) {
                    message.textContent = extractMessage(payload);
                    return;
                }

                if (kind === "login") {
                    localStorage.setItem("bedrock_access", payload.access);
                    localStorage.setItem("bedrock_refresh", payload.refresh);
                    message.textContent = "登录成功，正在跳转...";
                    window.location.href = "/dashboard/";
                    return;
                }

                message.textContent = "注册成功，请返回登录。";
                form.reset();
            } catch (error) {
                message.textContent = "请求失败，请检查本地服务是否启动。";
            }
        });
    });
}

function setupDashboard() {
    const target = document.querySelector("[data-current-user]");
    const usernameDisplay = document.querySelector("[data-username-display]");
    
    if (!target && !usernameDisplay) {
        return;
    }

    const token = localStorage.getItem("bedrock_access");
    if (!token) {
        if (target) target.textContent = "未登录，请先前往登录页。";
        if (usernameDisplay) usernameDisplay.textContent = "请登录";
        return;
    }

    fetch("/api/auth/me/", {
        headers: {Authorization: `Bearer ${token}`},
    })
        .then((response) => response.json())
        .then((payload) => {
            if (target) target.textContent = JSON.stringify(payload, null, 2);
            if (usernameDisplay) usernameDisplay.textContent = payload.username || "";
        })
        .catch(() => {
            if (target) target.textContent = "加载失败。";
            if (usernameDisplay) usernameDisplay.textContent = "加载失败";
        });
}

function setupNovelList() {
    const container = document.querySelector("[data-novel-list]");
    if (!container) {
        return;
    }

    const token = localStorage.getItem("bedrock_access");
    if (!token) {
        container.innerHTML = '<p class="text-muted">请先登录后查看你的作品。</p>';
        return;
    }

    fetch("/api/novels/", {
        headers: {Authorization: `Bearer ${token}`},
    })
        .then((response) => response.json())
        .then((payload) => {
            const novels = Array.isArray(payload) ? payload : payload.results || [];
            if (!novels.length) {
                container.innerHTML = '<p class="text-muted">暂无作品，开始创建你的第一本小说吧。</p>';
                return;
            }

            container.innerHTML = novels
                .map((novel) => `
                    <article class="card" style="display: flex; flex-direction: column;">
                        <h3 style="margin: 0 0 8px; font-size: 1.15rem;">${escapeHtml(novel.title)}</h3>
                        <p style="margin: 0 0 16px; font-size: 0.95rem; color: var(--muted); flex: 1;">${escapeHtml(novel.summary || "暂无简介")}</p>
                        <div style="margin-top: auto; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--line); padding-top: 12px;">
                            <span class="badge" style="font-size: 0.8rem; background: var(--bg-soft); padding: 4px 8px; border-radius: 4px;">${escapeHtml(novel.visibility)}</span>
                            <div style="display: flex; gap: 8px;">
                                <a href="/reader/?novel_id=${novel.id}" class="button secondary small" style="min-width: unset;">阅读</a>
                                <a href="/editor/?novel_id=${novel.id}" class="button primary small" style="min-width: unset;">写作</a>
                            </div>
                        </div>
                    </article>
                `)
                .join("");
        })
        .catch(() => {
            container.innerHTML = '<p class="text-danger">加载失败，请刷新重试。</p>';
        });
}

function extractMessage(payload) {
    if (typeof payload === "string") {
        return payload;
    }
    if (payload.detail) {
        return payload.detail;
    }
    const firstKey = Object.keys(payload)[0];
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
