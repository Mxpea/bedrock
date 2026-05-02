(function () {
    function getCookie(name) {
        const cookies = document.cookie ? document.cookie.split(';') : [];
        for (const raw of cookies) {
            const cookie = raw.trim();
            if (cookie.startsWith(name + '=')) {
                return decodeURIComponent(cookie.slice(name.length + 1));
            }
        }
        return '';
    }

    function parseCsv(text) {
        return (text || '')
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean);
    }

    function normalizeFolderPath(text) {
        return String(text || '')
            .split('/')
            .map((part) => part.trim())
            .filter(Boolean)
            .join('/');
    }

    function escapeHtml(text) {
        return String(text || '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }

    async function requestJson(url, init = {}) {
        const request = {
            credentials: 'same-origin',
            ...init,
        };

        const response = typeof fetchWithAuthRetry === 'function'
            ? await fetchWithAuthRetry(url, request)
            : await fetch(url, request);

        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const detail = data && (data.detail || data.message || data.error);
            if (detail) {
                throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
            }

            if (data && typeof data === 'object') {
                const firstField = Object.keys(data)[0];
                const value = data[firstField];
                if (Array.isArray(value) && value.length) {
                    throw new Error(String(value[0]));
                }
                if (typeof value === 'string' && value.trim()) {
                    throw new Error(value);
                }
            }

            throw new Error('请求失败（HTTP ' + response.status + '）');
        }
        return data;
    }

    async function requestFormJson(url, formData, init = {}) {
        const request = {
            credentials: 'same-origin',
            method: 'POST',
            body: formData,
            ...init,
        };

        const response = typeof fetchWithAuthRetry === 'function'
            ? await fetchWithAuthRetry(url, request)
            : await fetch(url, request);

        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const detail = data && (data.detail || data.message || data.error);
            throw new Error(detail || ('请求失败（HTTP ' + response.status + '）'));
        }
        return data;
    }

    document.addEventListener('DOMContentLoaded', async () => {
        const app = document.getElementById('worldview-v2-app');
        if (!app) {
            return;
        }
        if (app.dataset.wvInitialized === '1') {
            return;
        }
        app.dataset.wvInitialized = '1';

        const apiBase = app.dataset.apiBase;
        const renderPreviewApi = '/api/chapters/render_preview/';
        const uploadImageApi = '/api/chapters/upload_image/';
        const workspaceId = app.dataset.workspaceId;
        const csrftoken = getCookie('csrftoken');

        const el = {
            search: document.getElementById('wv-search'),
            create: document.getElementById('wv-create'),
            createFolder: document.getElementById('wv-create-folder'),
            folderTree: document.getElementById('wv-folder-tree'),
            openSearch: document.getElementById('wv-open-search'),
            closeSearch: document.getElementById('wv-close-search'),
            categories: document.getElementById('wv-categories'),
            tags: document.getElementById('wv-tags'),
            count: document.getElementById('wv-count'),
            results: document.getElementById('wv-results'),
            name: document.getElementById('wv-name'),
            category: document.getElementById('wv-category'),
            aliases: document.getElementById('wv-aliases'),
            folderPath: document.getElementById('wv-folder-path'),
            tagsInput: document.getElementById('wv-tags-input'),
            content: document.getElementById('wv-content'),
            contentPreview: document.getElementById('wv-content-preview'),
            contentViewBtn: document.getElementById('wv-content-view'),
            contentEditBtn: document.getElementById('wv-content-edit'),
            mdToolbar: document.getElementById('wv-md-toolbar'),
            mdH1: document.getElementById('wv-md-h1'),
            mdBold: document.getElementById('wv-md-bold'),
            mdItalic: document.getElementById('wv-md-italic'),
            mdList: document.getElementById('wv-md-list'),
            mdQuote: document.getElementById('wv-md-quote'),
            mdCode: document.getElementById('wv-md-code'),
            linkTarget: document.getElementById('wv-link-target'),
            backlinkTarget: document.getElementById('wv-backlink-target'),
            insertLink: document.getElementById('wv-insert-link'),
            insertBacklink: document.getElementById('wv-insert-backlink'),
            uploadImage: document.getElementById('wv-upload-image'),
            imageInput: document.getElementById('wv-image-input'),
            addProp: document.getElementById('wv-add-prop'),
            props: document.getElementById('wv-props'),
            backlinks: document.getElementById('wv-backlinks'),
            save: document.getElementById('wv-save'),
            del: document.getElementById('wv-delete'),
            status: document.getElementById('wv-status'),
            searchCenter: document.getElementById('wv-search-center'),
            portalKeyword: document.getElementById('wv-portal-keyword'),
            portalCategory: document.getElementById('wv-portal-category'),
            portalTags: document.getElementById('wv-portal-tags'),
            portalSort: document.getElementById('wv-portal-sort'),
            portalRun: document.getElementById('wv-portal-run'),
            portalClear: document.getElementById('wv-portal-clear'),
            portalCount: document.getElementById('wv-portal-count'),
            portalResults: document.getElementById('wv-portal-results'),
        };

        const state = {
            entries: [],
            selectedId: null,
            activeCategory: '',
            activeTags: new Set(),
            query: '',
            draftProperties: [],
            searchCenterOpen: false,
            activeFolder: '',
            customFolders: [],
            collapsedFolders: new Set(),
            contentMode: 'view',
            previewTimer: null,
        };

        function setContentMode(mode) {
            state.contentMode = mode === 'edit' ? 'edit' : 'view';

            const isEdit = state.contentMode === 'edit';
            if (el.content) el.content.hidden = !isEdit;
            if (el.mdToolbar) el.mdToolbar.hidden = !isEdit;
            if (el.contentPreview) el.contentPreview.hidden = isEdit;

            if (el.contentEditBtn) {
                el.contentEditBtn.classList.toggle('active', isEdit);
            }
            if (el.contentViewBtn) {
                el.contentViewBtn.classList.toggle('active', !isEdit);
            }
        }

        function syncLinkTargets() {
            if (!el.linkTarget || !el.backlinkTarget) return;
            const current = selectedEntry();

            const options = ['<option value="">选择词条...</option>'];
            for (const item of state.entries) {
                if (current && item.id === current.id) continue;
                options.push('<option value="' + escapeHtml(item.name || '') + '">' + escapeHtml(item.name || '') + '</option>');
            }
            el.linkTarget.innerHTML = options.join('');

            const backlinks = ['<option value="">选择反向来源...</option>'];
            for (const link of (current?.incoming_links || [])) {
                backlinks.push('<option value="' + escapeHtml(link.name || '') + '">' + escapeHtml(link.name || '') + '</option>');
            }
            el.backlinkTarget.innerHTML = backlinks.join('');
        }

        function insertAtCursor(insertText) {
            if (!el.content || !insertText) return;
            const input = el.content;
            const start = input.selectionStart ?? input.value.length;
            const end = input.selectionEnd ?? input.value.length;
            const before = input.value.slice(0, start);
            const after = input.value.slice(end);
            input.value = before + insertText + after;
            const cursor = start + insertText.length;
            input.setSelectionRange(cursor, cursor);
            input.focus();
            schedulePreview();
        }

        function wrapSelection(prefix, suffix, placeholder) {
            if (!el.content) return;
            const input = el.content;
            const start = input.selectionStart ?? 0;
            const end = input.selectionEnd ?? 0;
            const selected = input.value.slice(start, end);
            const text = selected || (placeholder || '');
            const replacement = prefix + text + suffix;

            const before = input.value.slice(0, start);
            const after = input.value.slice(end);
            input.value = before + replacement + after;

            const selectionStart = start + prefix.length;
            const selectionEnd = selectionStart + text.length;
            input.setSelectionRange(selectionStart, selectionEnd);
            input.focus();
            schedulePreview();
        }

        function toggleLinePrefix(prefix) {
            if (!el.content) return;
            const input = el.content;
            const value = input.value;
            const start = input.selectionStart ?? 0;
            const end = input.selectionEnd ?? 0;

            const lineStart = value.lastIndexOf('\n', Math.max(0, start - 1)) + 1;
            const lineEndIndex = value.indexOf('\n', end);
            const lineEnd = lineEndIndex === -1 ? value.length : lineEndIndex;
            const block = value.slice(lineStart, lineEnd);
            const lines = block.split('\n');

            const nonEmpty = lines.filter((line) => line.trim().length > 0);
            const allPrefixed = nonEmpty.length > 0 && nonEmpty.every((line) => line.startsWith(prefix));

            const transformed = lines.map((line) => {
                if (!line.trim()) {
                    return line;
                }
                if (allPrefixed) {
                    return line.startsWith(prefix) ? line.slice(prefix.length) : line;
                }
                return line.startsWith(prefix) ? line : prefix + line;
            });

            const replacement = transformed.join('\n');
            input.value = value.slice(0, lineStart) + replacement + value.slice(lineEnd);
            input.setSelectionRange(lineStart, lineStart + replacement.length);
            input.focus();
            schedulePreview();
        }

        async function renderMarkdownPreview() {
            if (!el.contentPreview) return;
            const content = (el.content?.value || '').trim();
            if (!content) {
                el.contentPreview.innerHTML = '<div class="text-muted">暂无正文，点击“编辑正文”开始写作。</div>';
                return;
            }

            try {
                const data = await requestJson(renderPreviewApi, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken,
                    },
                    body: JSON.stringify({
                        novel: Number(workspaceId),
                        content_md: el.content.value,
                    }),
                });
                el.contentPreview.innerHTML = data.html || '<pre>' + escapeHtml(el.content.value) + '</pre>';
            } catch (_) {
                el.contentPreview.innerHTML = '<pre>' + escapeHtml(el.content.value) + '</pre>';
            }
        }

        function schedulePreview() {
            if (state.previewTimer) {
                window.clearTimeout(state.previewTimer);
            }
            state.previewTimer = window.setTimeout(() => {
                renderMarkdownPreview();
            }, 250);
        }

        const folderStorageKey = 'wv_custom_folders_' + workspaceId;
        const folderCollapseStorageKey = 'wv_collapsed_folders_' + workspaceId;

        try {
            const cache = JSON.parse(localStorage.getItem(folderStorageKey) || '[]');
            state.customFolders = Array.isArray(cache) ? cache.map(normalizeFolderPath).filter(Boolean) : [];
        } catch (_) {
            state.customFolders = [];
        }

        try {
            const cache = JSON.parse(localStorage.getItem(folderCollapseStorageKey) || '[]');
            const list = Array.isArray(cache) ? cache.map(normalizeFolderPath).filter(Boolean) : [];
            state.collapsedFolders = new Set(list);
        } catch (_) {
            state.collapsedFolders = new Set();
        }

        function persistCustomFolders() {
            localStorage.setItem(folderStorageKey, JSON.stringify(state.customFolders));
        }

        function persistCollapsedFolders() {
            localStorage.setItem(folderCollapseStorageKey, JSON.stringify(Array.from(state.collapsedFolders)));
        }

        function collectFolderPaths() {
            const set = new Set();
            for (const entry of state.entries) {
                const folder = normalizeFolderPath(entry.folder_path || '');
                if (!folder) continue;
                const parts = folder.split('/');
                for (let i = 1; i <= parts.length; i += 1) {
                    set.add(parts.slice(0, i).join('/'));
                }
            }
            for (const folder of state.customFolders) {
                const normalized = normalizeFolderPath(folder);
                if (!normalized) continue;
                const parts = normalized.split('/');
                for (let i = 1; i <= parts.length; i += 1) {
                    set.add(parts.slice(0, i).join('/'));
                }
            }
            return Array.from(set).sort((a, b) => a.localeCompare(b, 'zh-CN'));
        }

        function buildFolderTree() {
            const root = {
                path: '',
                name: '',
                children: [],
                entries: [],
            };
            const map = new Map();
            map.set('', root);

            function ensureFolder(path) {
                const normalized = normalizeFolderPath(path);
                if (map.has(normalized)) {
                    return map.get(normalized);
                }
                const parts = normalized.split('/');
                const name = parts.at(-1) || '';
                const parentPath = parts.slice(0, -1).join('/');
                const parent = ensureFolder(parentPath);
                const node = {
                    path: normalized,
                    name,
                    children: [],
                    entries: [],
                };
                parent.children.push(node);
                map.set(normalized, node);
                return node;
            }

            for (const folder of collectFolderPaths()) {
                ensureFolder(folder);
            }

            for (const entry of state.entries) {
                const folder = normalizeFolderPath(entry.folder_path || '');
                const parent = ensureFolder(folder);
                parent.entries.push(entry);
            }

            const sortNode = (node) => {
                node.children.sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'));
                node.entries.sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'zh-CN'));
                for (const child of node.children) {
                    sortNode(child);
                }
            };
            sortNode(root);
            return root;
        }

        function renderFolderTree() {
            if (!el.folderTree) return;
            const rows = [];
            const tree = buildFolderTree();

            const allActive = state.activeFolder === '' ? ' active' : '';
            rows.push(
                '<button type="button" class="worldview-v2-folder-node worldview-v2-folder-root' + allActive + '" data-folder="" data-drop-folder="">📚 全部词条</button>'
            );

            function renderGuideRails(flags) {
                if (!flags.length) {
                    return '';
                }
                return '<span class="worldview-v2-tree-rails" aria-hidden="true">' +
                    flags.map((on) => '<span class="worldview-v2-tree-rail' + (on ? ' on' : '') + '"></span>').join('') +
                    '</span>';
            }

            function renderEntryRow(entry, depth, ancestorHasNext) {
                const activeEntry = state.selectedId === entry.id ? ' active' : '';
                rows.push(
                    '<div class="worldview-v2-tree-row" data-depth="' + depth + '">' +
                    renderGuideRails(ancestorHasNext) +
                    '<button type="button" class="worldview-v2-tree-entry' + activeEntry + '" draggable="true" data-entry-id="' + entry.id + '">📄 ' + escapeHtml(entry.name || '未命名词条') + '</button>' +
                    '</div>'
                );
            }

            function renderNode(node, depth, ancestorHasNext, isLastSibling) {
                const hasChildren = node.children.length > 0 || node.entries.length > 0;
                const isCollapsed = state.collapsedFolders.has(node.path);
                const isActive = state.activeFolder === node.path ? ' active' : '';

                rows.push(
                    '<div class="worldview-v2-tree-row" data-depth="' + depth + '">' +
                    renderGuideRails(ancestorHasNext) +
                    '<div class="worldview-v2-tree-folder-row">' +
                    '<button type="button" class="worldview-v2-folder-toggle" data-toggle-folder="' + escapeHtml(node.path) + '">' +
                    (hasChildren ? (isCollapsed ? '▸' : '▾') : '•') +
                    '</button>' +
                    '<button type="button" class="worldview-v2-folder-node' + isActive + '" data-folder="' + escapeHtml(node.path) + '" data-drop-folder="' + escapeHtml(node.path) + '">📁 ' + escapeHtml(node.name) + '</button>' +
                    '</div>' +
                    '</div>'
                );

                if (isCollapsed) {
                    return;
                }

                const childAncestor = ancestorHasNext.concat(!isLastSibling);
                const children = [];
                for (const entry of node.entries) {
                    children.push({ type: 'entry', entry });
                }
                for (const child of node.children) {
                    children.push({ type: 'folder', node: child });
                }

                children.forEach((child, index) => {
                    const childIsLast = index === children.length - 1;
                    if (child.type === 'entry') {
                        renderEntryRow(child.entry, depth + 1, childAncestor);
                        return;
                    }
                    renderNode(child.node, depth + 1, childAncestor, childIsLast);
                });
            }

            const rootChildren = [];
            for (const node of tree.children) {
                rootChildren.push({ type: 'folder', node });
            }
            for (const entry of tree.entries) {
                rootChildren.push({ type: 'entry', entry });
            }

            rootChildren.forEach((child, index) => {
                const isLast = index === rootChildren.length - 1;
                if (child.type === 'entry') {
                    renderEntryRow(child.entry, 1, []);
                    return;
                }
                renderNode(child.node, 1, [], isLast);
            });

            el.folderTree.innerHTML = rows.join('');
        }

        async function moveEntryToFolder(entryId, targetFolder) {
            const entry = state.entries.find((item) => item.id === Number(entryId));
            if (!entry) return;
            const folder = normalizeFolderPath(targetFolder || '');
            const current = normalizeFolderPath(entry.folder_path || '');
            if (folder === current) return;

            setStatus('移动词条中...');
            const data = await requestJson(apiBase + entry.id + '/', {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken,
                },
                body: JSON.stringify({ folder_path: folder }),
            });

            if (data && typeof data.folder_path === 'string') {
                entry.folder_path = data.folder_path;
            } else {
                entry.folder_path = folder;
            }

            if (folder && !state.customFolders.includes(folder)) {
                state.customFolders.push(folder);
                state.customFolders.sort((a, b) => a.localeCompare(b, 'zh-CN'));
                persistCustomFolders();
            }

            renderFiltersAndList();
            renderEditor();
            setStatus('已移动到目录：' + (folder || '根目录'));
        }

        function setSearchCenterOpen(open) {
            state.searchCenterOpen = !!open;
            if (el.searchCenter) {
                el.searchCenter.hidden = !state.searchCenterOpen;
            }
            if (state.searchCenterOpen && el.portalKeyword) {
                el.portalKeyword.focus();
            }
        }

        function computeSearchScore(item, keyword) {
            const q = (keyword || '').trim().toLowerCase();
            if (!q) return 0;

            const name = String(item.name || '').toLowerCase();
            const aliases = (item.aliases || []).map((text) => String(text).toLowerCase());
            const category = String(item.category || '').toLowerCase();
            const tags = (item.tags || []).map((text) => String(text).toLowerCase());
            const content = String(item.content_md || '').toLowerCase();
            const props = Object.entries(item.properties || {})
                .map(([key, value]) => String(key) + ' ' + String(value ?? ''))
                .join(' ')
                .toLowerCase();

            let score = 0;
            if (name === q) score += 120;
            if (name.includes(q)) score += 80;

            for (const alias of aliases) {
                if (alias === q) score += 100;
                else if (alias.includes(q)) score += 60;
            }

            if (category.includes(q)) score += 20;
            for (const tag of tags) {
                if (tag === q) score += 40;
                else if (tag.includes(q)) score += 18;
            }

            if (props.includes(q)) score += 22;
            if (content.includes(q)) {
                score += 30;
                const hits = content.split(q).length - 1;
                score += Math.min(hits, 5) * 6;
            }
            return score;
        }

        function findSnippet(item, keyword) {
            const text = String(item.content_md || '').replace(/\s+/g, ' ').trim();
            if (!text) return '暂无正文摘要';
            const q = String(keyword || '').trim().toLowerCase();
            if (!q) return text.slice(0, 120);
            const i = text.toLowerCase().indexOf(q);
            if (i < 0) return text.slice(0, 120);
            const start = Math.max(0, i - 28);
            const end = Math.min(text.length, i + q.length + 44);
            const prefix = start > 0 ? '...' : '';
            const suffix = end < text.length ? '...' : '';
            return prefix + text.slice(start, end) + suffix;
        }

        function runSearchCenter() {
            const keyword = (el.portalKeyword?.value || '').trim();
            const category = (el.portalCategory?.value || '').trim();
            const requiredTags = parseCsv(el.portalTags?.value || '');
            const sortMode = el.portalSort?.value || 'score';

            let list = state.entries.filter((item) => {
                if (category && (item.category || '').trim() !== category) return false;
                if (requiredTags.length) {
                    const tags = item.tags || [];
                    for (const tag of requiredTags) {
                        if (!tags.includes(tag)) return false;
                    }
                }
                return true;
            });

            const ranked = list.map((item) => ({
                item,
                score: computeSearchScore(item, keyword),
            }));

            if (keyword) {
                list = ranked.filter((row) => row.score > 0).map((row) => row.item);
            }

            const decorated = list.map((item) => ({
                item,
                score: computeSearchScore(item, keyword),
                updatedAt: new Date(item.updated_at || 0).getTime() || 0,
            }));

            if (sortMode === 'updated') {
                decorated.sort((a, b) => b.updatedAt - a.updatedAt);
            } else if (sortMode === 'name') {
                decorated.sort((a, b) => String(a.item.name || '').localeCompare(String(b.item.name || ''), 'zh-CN'));
            } else {
                decorated.sort((a, b) => b.score - a.score || String(a.item.name || '').localeCompare(String(b.item.name || ''), 'zh-CN'));
            }

            if (el.portalCount) {
                el.portalCount.textContent = decorated.length + ' 条结果';
            }

            if (!el.portalResults) {
                return;
            }

            if (!decorated.length) {
                el.portalResults.innerHTML = '<div class="text-muted">没有匹配结果，试试放宽筛选条件。</div>';
                return;
            }

            el.portalResults.innerHTML = decorated.map((row) => {
                const item = row.item;
                const aliasText = (item.aliases || []).slice(0, 3).join(', ');
                const tagText = (item.tags || []).slice(0, 5).join(', ');
                return '<article class="wv-search-card" data-id="' + item.id + '">' +
                    '<div class="wv-search-card-head">' +
                    '<h4>' + escapeHtml(item.name || '未命名词条') + '</h4>' +
                    '<span class="wv-search-score">相关度 ' + Math.max(0, Math.round(row.score)) + '</span>' +
                    '</div>' +
                    '<div class="wv-search-meta">分类：' + escapeHtml(item.category || '未分类') +
                    (aliasText ? ' · 别名：' + escapeHtml(aliasText) : '') +
                    (tagText ? ' · 标签：' + escapeHtml(tagText) : '') +
                    '</div>' +
                    '<p class="wv-search-snippet">' + escapeHtml(findSnippet(item, keyword)) + '</p>' +
                    '<div><button type="button" class="button secondary" data-open-entry="' + item.id + '">打开词条</button></div>' +
                    '</article>';
            }).join('');
        }

        function setStatus(text, isError) {
            if (!el.status) return;
            el.status.textContent = text || '';
            el.status.style.color = isError ? '#b42318' : '';
        }

        function selectedEntry() {
            return state.entries.find((item) => item.id === state.selectedId) || null;
        }

        function filteredEntries() {
            return state.entries.filter((item) => {
                if (state.activeCategory && (item.category || '') !== state.activeCategory) return false;
                if (state.activeTags.size) {
                    const tags = item.tags || [];
                    for (const tag of state.activeTags) {
                        if (!tags.includes(tag)) return false;
                    }
                }
                if (state.activeFolder) {
                    const folder = normalizeFolderPath(item.folder_path || '');
                    if (!(folder === state.activeFolder || folder.startsWith(state.activeFolder + '/'))) return false;
                }
                if (state.query) {
                    const q = state.query.toLowerCase();
                    const haystack = [
                        item.name || '',
                        item.folder_path || '',
                        ...(item.aliases || []),
                        item.content_md || '',
                    ]
                        .join(' ')
                        .toLowerCase();
                    if (!haystack.includes(q)) return false;
                }
                return true;
            });
        }

        function computeFacets(list) {
            const categories = new Map();
            const tags = new Map();
            for (const item of list) {
                const category = (item.category || '未分类').trim() || '未分类';
                categories.set(category, (categories.get(category) || 0) + 1);
                for (const tag of item.tags || []) {
                    tags.set(tag, (tags.get(tag) || 0) + 1);
                }
            }
            return {
                categories: Array.from(categories.entries()).map(([name, count]) => ({ name, count })),
                tags: Array.from(tags.entries()).map(([name, count]) => ({ name, count })),
            };
        }

        function renderPropsRows() {
            const rows = state.draftProperties;
            if (!rows.length) {
                el.props.innerHTML = '<div class="text-muted">暂无属性，点击“添加属性”开始整理结构化数据。</div>';
                return;
            }
            el.props.innerHTML = rows
                .map((row, idx) => {
                    return '<div class="worldview-v2-prop-row" data-index="' + idx + '">' +
                        '<input type="text" class="wv-prop-key" placeholder="属性名" value="' + escapeHtml(row.key) + '">' +
                        '<input type="text" class="wv-prop-value" placeholder="属性值" value="' + escapeHtml(row.value) + '">' +
                        '<button type="button" class="button secondary wv-remove-prop">删除</button>' +
                        '</div>';
                })
                .join('');
        }

        function renderEditor() {
            const item = selectedEntry();
            if (!item) {
                el.name.value = '';
                el.category.value = '';
                el.aliases.value = '';
                el.folderPath.value = state.activeFolder || '';
                el.tagsInput.value = '';
                el.content.value = '';
                state.draftProperties = [];
                renderPropsRows();
                el.backlinks.innerHTML = '<div class="text-muted">未选中词条</div>';
                syncLinkTargets();
                renderMarkdownPreview();
                return;
            }

            el.name.value = item.name || '';
            el.category.value = item.category || '';
            el.aliases.value = (item.aliases || []).join(', ');
            el.folderPath.value = item.folder_path || '';
            el.tagsInput.value = (item.tags || []).join(', ');
            el.content.value = item.content_md || '';
            state.draftProperties = Object.entries(item.properties || {}).map(([key, value]) => ({ key, value: String(value ?? '') }));
            renderPropsRows();

            const links = item.incoming_links || [];
            if (!links.length) {
                el.backlinks.innerHTML = '<div class="text-muted">暂无反向链接</div>';
            } else {
                el.backlinks.innerHTML = links
                    .map((link) => {
                        return '<div class="worldview-v2-backlink">' +
                            '<div class="from">' + escapeHtml(link.name) + '</div>' +
                            '<div class="text-muted">' + escapeHtml(link.context || '') + '</div>' +
                            '</div>';
                    })
                    .join('');
            }

                    syncLinkTargets();
                    renderMarkdownPreview();
        }

        function renderFiltersAndList() {
            const list = filteredEntries();
            const facets = computeFacets(state.entries);

            renderFolderTree();

            el.categories.innerHTML = facets.categories
                .map((cat) => {
                    const isActive = state.activeCategory === cat.name ? ' active' : '';
                    return '<button type="button" class="worldview-v2-chip' + isActive + '" data-category="' + escapeHtml(cat.name) + '">' +
                        escapeHtml(cat.name) + ' (' + cat.count + ')' +
                        '</button>';
                })
                .join('');

            el.tags.innerHTML = facets.tags
                .map((tag) => {
                    const isActive = state.activeTags.has(tag.name) ? ' active' : '';
                    return '<button type="button" class="worldview-v2-chip' + isActive + '" data-tag="' + escapeHtml(tag.name) + '">#' +
                        escapeHtml(tag.name) + ' (' + tag.count + ')' +
                        '</button>';
                })
                .join('');

            el.count.textContent = String(list.length);
            el.results.innerHTML = list
                .map((item) => {
                    const active = item.id === state.selectedId ? ' active' : '';
                    const alias = (item.aliases || []).slice(0, 2).join(', ');
                    return '<button type="button" class="worldview-v2-item' + active + '" data-id="' + item.id + '">' +
                        '<div class="name">' + escapeHtml(item.name) + '</div>' +
                        '<div class="meta">' +
                        escapeHtml(item.category || '未分类') +
                        (item.folder_path ? ' · 📁 ' + escapeHtml(item.folder_path) : '') +
                        (alias ? ' · ' + escapeHtml(alias) : '') +
                        '</div>' +
                        '</button>';
                })
                .join('');
        }

        async function loadEntries() {
            const data = await requestJson(apiBase + '?novel=' + workspaceId);
            state.entries = Array.isArray(data) ? data : (Array.isArray(data.results) ? data.results : []);
            if (!state.entries.find((item) => item.id === state.selectedId)) {
                state.selectedId = state.entries[0]?.id || null;
            }
            renderFiltersAndList();
            renderEditor();
        }

        function collectPayload() {
            const properties = {};
            for (const row of state.draftProperties) {
                const key = (row.key || '').trim();
                if (!key) continue;
                properties[key] = (row.value || '').trim();
            }
            return {
                novel: Number(workspaceId),
                name: el.name.value.trim(),
                category: el.category.value.trim(),
                folder_path: normalizeFolderPath(el.folderPath.value),
                aliases: parseCsv(el.aliases.value),
                tags: parseCsv(el.tagsInput.value),
                properties,
                content_md: el.content.value,
            };
        }

        async function saveEntry() {
            const payload = collectPayload();
            if (!payload.name) {
                setStatus('词条名不能为空', true);
                return;
            }

            const current = selectedEntry();
            const isUpdate = !!current;
            const url = isUpdate ? apiBase + current.id + '/' : apiBase;
            const method = isUpdate ? 'PATCH' : 'POST';

            const data = await requestJson(url, {
                method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken,
                },
                body: JSON.stringify(payload),
            });
            state.selectedId = data.id;
            setStatus('已保存');
            await loadEntries();
        }

        async function deleteEntry() {
            const current = selectedEntry();
            if (!current) return;
            if (!window.confirm('确定删除词条：' + current.name + '？')) return;

            await requestJson(apiBase + current.id + '/', {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': csrftoken,
                },
            });

            state.selectedId = null;
            setStatus('已删除');
            await loadEntries();
        }

        el.search.addEventListener('input', () => {
            state.query = el.search.value.trim();
            renderFiltersAndList();
        });

        el.create.addEventListener('click', () => {
            state.selectedId = null;
            renderFiltersAndList();
            renderEditor();
            setContentMode('edit');
            setStatus('已进入新建模式');
        });

        el.categories.addEventListener('click', (event) => {
            const btn = event.target.closest('[data-category]');
            if (!btn) return;
            const category = btn.dataset.category;
            state.activeCategory = state.activeCategory === category ? '' : category;
            renderFiltersAndList();
        });

        el.tags.addEventListener('click', (event) => {
            const btn = event.target.closest('[data-tag]');
            if (!btn) return;
            const tag = btn.dataset.tag;
            if (state.activeTags.has(tag)) {
                state.activeTags.delete(tag);
            } else {
                state.activeTags.add(tag);
            }
            renderFiltersAndList();
        });

        el.results.addEventListener('click', (event) => {
            const node = event.target.closest('[data-id]');
            if (!node) return;
            state.selectedId = Number(node.dataset.id);
            renderFiltersAndList();
            renderEditor();
        });

        if (el.folderTree) {
            el.folderTree.addEventListener('click', (event) => {
                const toggle = event.target.closest('[data-toggle-folder]');
                if (toggle) {
                    const path = normalizeFolderPath(toggle.dataset.toggleFolder || '');
                    if (path) {
                        if (state.collapsedFolders.has(path)) {
                            state.collapsedFolders.delete(path);
                        } else {
                            state.collapsedFolders.add(path);
                        }
                        persistCollapsedFolders();
                        renderFolderTree();
                    }
                    return;
                }

                const entryNode = event.target.closest('[data-entry-id]');
                if (entryNode) {
                    state.selectedId = Number(entryNode.dataset.entryId);
                    renderFiltersAndList();
                    renderEditor();
                    return;
                }

                const node = event.target.closest('[data-folder]');
                if (!node) return;
                state.activeFolder = normalizeFolderPath(node.dataset.folder || '');
                renderFiltersAndList();
            });

            el.folderTree.addEventListener('dragstart', (event) => {
                const node = event.target.closest('[data-entry-id]');
                if (!node) return;
                event.dataTransfer.effectAllowed = 'move';
                event.dataTransfer.setData('text/worldview-entry-id', node.dataset.entryId || '');
                node.classList.add('dragging');
            });

            el.folderTree.addEventListener('dragend', (event) => {
                const node = event.target.closest('[data-entry-id]');
                if (!node) return;
                node.classList.remove('dragging');
                for (const item of el.folderTree.querySelectorAll('.is-drop-target')) {
                    item.classList.remove('is-drop-target');
                }
            });

            el.folderTree.addEventListener('dragover', (event) => {
                const target = event.target.closest('[data-drop-folder]');
                if (!target) return;
                event.preventDefault();
                for (const item of el.folderTree.querySelectorAll('.is-drop-target')) {
                    item.classList.remove('is-drop-target');
                }
                target.classList.add('is-drop-target');
            });

            el.folderTree.addEventListener('dragleave', (event) => {
                const target = event.target.closest('[data-drop-folder]');
                if (!target) return;
                target.classList.remove('is-drop-target');
            });

            el.folderTree.addEventListener('drop', async (event) => {
                const target = event.target.closest('[data-drop-folder]');
                if (!target) return;
                event.preventDefault();
                target.classList.remove('is-drop-target');

                const entryId = event.dataTransfer.getData('text/worldview-entry-id');
                if (!entryId) return;
                const folder = normalizeFolderPath(target.dataset.dropFolder || '');

                try {
                    await moveEntryToFolder(Number(entryId), folder);
                } catch (error) {
                    setStatus(error.message || '拖拽移动失败', true);
                }
            });
        }

        if (el.createFolder) {
            el.createFolder.addEventListener('click', () => {
                const base = state.activeFolder ? state.activeFolder + '/' : '';
                const name = window.prompt('请输入新文件夹名称', '新建文件夹');
                if (!name) return;
                const folder = normalizeFolderPath(base + name);
                if (!folder) return;
                if (!state.customFolders.includes(folder)) {
                    state.customFolders.push(folder);
                    state.customFolders.sort((a, b) => a.localeCompare(b, 'zh-CN'));
                    persistCustomFolders();
                }
                state.activeFolder = folder;
                if (el.folderPath && !el.folderPath.value.trim()) {
                    el.folderPath.value = folder;
                }
                renderFiltersAndList();
                setStatus('已创建目录：' + folder);
            });
        }

        el.addProp.addEventListener('click', () => {
            state.draftProperties.push({ key: '', value: '' });
            renderPropsRows();
        });

        el.props.addEventListener('input', (event) => {
            const rowNode = event.target.closest('.worldview-v2-prop-row');
            if (!rowNode) return;
            const idx = Number(rowNode.dataset.index);
            const keyInput = rowNode.querySelector('.wv-prop-key');
            const valueInput = rowNode.querySelector('.wv-prop-value');
            state.draftProperties[idx] = {
                key: keyInput?.value || '',
                value: valueInput?.value || '',
            };
        });

        el.props.addEventListener('click', (event) => {
            const btn = event.target.closest('.wv-remove-prop');
            if (!btn) return;
            const rowNode = btn.closest('.worldview-v2-prop-row');
            if (!rowNode) return;
            const idx = Number(rowNode.dataset.index);
            state.draftProperties.splice(idx, 1);
            renderPropsRows();
        });

        el.save.addEventListener('click', async () => {
            try {
                setStatus('保存中...');
                await saveEntry();
                await renderMarkdownPreview();
                setContentMode('view');
            } catch (error) {
                setStatus(error.message || '保存失败', true);
            }
        });

        if (el.contentViewBtn) {
            el.contentViewBtn.addEventListener('click', async () => {
                setContentMode('view');
                await renderMarkdownPreview();
            });
        }

        if (el.contentEditBtn) {
            el.contentEditBtn.addEventListener('click', () => {
                setContentMode('edit');
                el.content?.focus();
            });
        }

        if (el.content) {
            el.content.addEventListener('input', schedulePreview);
        }

        if (el.mdH1) {
            el.mdH1.addEventListener('click', () => toggleLinePrefix('# '));
        }
        if (el.mdBold) {
            el.mdBold.addEventListener('click', () => wrapSelection('**', '**', '加粗文本'));
        }
        if (el.mdItalic) {
            el.mdItalic.addEventListener('click', () => wrapSelection('*', '*', '斜体文本'));
        }
        if (el.mdList) {
            el.mdList.addEventListener('click', () => toggleLinePrefix('- '));
        }
        if (el.mdQuote) {
            el.mdQuote.addEventListener('click', () => toggleLinePrefix('> '));
        }
        if (el.mdCode) {
            el.mdCode.addEventListener('click', () => wrapSelection('```\n', '\n```', '代码片段'));
        }

        if (el.insertLink) {
            el.insertLink.addEventListener('click', () => {
                const name = (el.linkTarget?.value || '').trim();
                if (!name) return;
                insertAtCursor('[[' + name + ']]');
            });
        }

        if (el.insertBacklink) {
            el.insertBacklink.addEventListener('click', () => {
                const name = (el.backlinkTarget?.value || '').trim();
                if (!name) return;
                insertAtCursor('[[' + name + ']]');
            });
        }

        if (el.uploadImage && el.imageInput) {
            el.uploadImage.addEventListener('click', () => {
                el.imageInput.click();
            });

            el.imageInput.addEventListener('change', async () => {
                const file = el.imageInput.files?.[0];
                if (!file) return;
                try {
                    setStatus('上传图片中...');
                    const formData = new FormData();
                    formData.append('novel', String(workspaceId));
                    formData.append('image', file);
                    const data = await requestFormJson(uploadImageApi, formData, {
                        headers: {
                            'X-CSRFToken': csrftoken,
                        },
                    });
                    if (data.url) {
                        insertAtCursor('\n![' + file.name + '](' + data.url + ')\n');
                        setStatus('图片已上传');
                    } else {
                        setStatus('图片上传成功，但未返回地址', true);
                    }
                } catch (error) {
                    setStatus(error.message || '图片上传失败', true);
                } finally {
                    el.imageInput.value = '';
                }
            });
        }

        el.del.addEventListener('click', async () => {
            try {
                await deleteEntry();
            } catch (error) {
                setStatus(error.message || '删除失败', true);
            }
        });

        if (el.openSearch) {
            el.openSearch.addEventListener('click', () => {
                setSearchCenterOpen(true);
                runSearchCenter();
            });
        }

        if (el.closeSearch) {
            el.closeSearch.addEventListener('click', (event) => {
                event.preventDefault();
                setSearchCenterOpen(false);
            });
        }

        document.addEventListener('click', (event) => {
            const btn = event.target.closest('#wv-close-search');
            if (!btn) return;
            setSearchCenterOpen(false);
        });

        if (el.portalRun) {
            el.portalRun.addEventListener('click', runSearchCenter);
        }

        if (el.portalKeyword) {
            el.portalKeyword.addEventListener('keydown', (event) => {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    runSearchCenter();
                }
            });
        }

        if (el.portalClear) {
            el.portalClear.addEventListener('click', () => {
                if (el.portalKeyword) el.portalKeyword.value = '';
                if (el.portalCategory) el.portalCategory.value = '';
                if (el.portalTags) el.portalTags.value = '';
                if (el.portalSort) el.portalSort.value = 'score';
                runSearchCenter();
            });
        }

        if (el.portalResults) {
            el.portalResults.addEventListener('click', (event) => {
                const btn = event.target.closest('[data-open-entry]');
                if (!btn) return;
                state.selectedId = Number(btn.dataset.openEntry);
                renderFiltersAndList();
                renderEditor();
                setSearchCenterOpen(false);
            });
        }

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && state.searchCenterOpen) {
                setSearchCenterOpen(false);
            }
        });

        try {
            setStatus('加载中...');
            await loadEntries();
            setSearchCenterOpen(false);
            setContentMode('view');
            if (state.searchCenterOpen) {
                runSearchCenter();
            }
            renderFolderTree();
            setStatus(state.entries.length ? '已加载' : '还没有词条，先创建一个吧');
        } catch (error) {
            setStatus(error.message || '加载失败', true);
        }
    });
})();
