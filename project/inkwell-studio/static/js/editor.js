
document.addEventListener('DOMContentLoaded', () => {
    const editor = document.getElementById('main-editor-area');
    const titleInput = document.getElementById('chapter-title-input');
    if (!editor) {
        return;
    }
    
    // Auto-resize textarea
    const resizeEditor = () => {
        editor.style.height = 'auto';
        editor.style.height = editor.scrollHeight + 'px';
    };
    editor.addEventListener('input', resizeEditor);
    // Initial resize map slightly later to ensure rendering is complete
    setTimeout(resizeEditor, 10);

    const historyStack = [];
    let historyIndex = -1;
    let isApplyingHistory = false;
    let historyDebounceTimer = null;

    const snapshotState = () => ({
        title: titleInput ? titleInput.value : '',
        content: editor.value,
        start: editor.selectionStart,
        end: editor.selectionEnd,
    });

    const applySnapshot = (state) => {
        if (!state) return;
        isApplyingHistory = true;
        if (titleInput) titleInput.value = state.title;
        editor.value = state.content;
        editor.selectionStart = state.start;
        editor.selectionEnd = state.end;
        resizeEditor();
        updateWordCount();
        isApplyingHistory = false;
    };

    const recordHistory = (force = false) => {
        if (isApplyingHistory) return;
        const nextState = snapshotState();
        const prevState = historyStack[historyIndex];
        const unchanged = prevState
            && prevState.title === nextState.title
            && prevState.content === nextState.content
            && prevState.start === nextState.start
            && prevState.end === nextState.end;

        if (unchanged && !force) return;

        if (historyIndex < historyStack.length - 1) {
            historyStack.splice(historyIndex + 1);
        }

        historyStack.push(nextState);
        historyIndex = historyStack.length - 1;

        if (historyStack.length > 200) {
            historyStack.shift();
            historyIndex -= 1;
        }
    };

    const scheduleHistoryRecord = () => {
        if (historyDebounceTimer) {
            clearTimeout(historyDebounceTimer);
        }
        historyDebounceTimer = setTimeout(() => recordHistory(false), 180);
    };

    const undoHistory = () => {
        if (historyIndex <= 0) return;
        historyIndex -= 1;
        applySnapshot(historyStack[historyIndex]);
    };

    const redoHistory = () => {
        if (historyIndex >= historyStack.length - 1) return;
        historyIndex += 1;
        applySnapshot(historyStack[historyIndex]);
    };

    // Generic formatting wrapping logic for Markdown tags
    const insertTag = (startTag, endTag) => {
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        const text = editor.value;
        const selectedText = text.substring(start, end);
        const replacement = startTag + selectedText + endTag;
        
        editor.value = text.substring(0, start) + replacement + text.substring(end);
        
        // Adjust cursor intelligently
        if (start === end) {
            editor.selectionStart = editor.selectionEnd = start + startTag.length;
        } else {
            editor.selectionStart = editor.selectionEnd = start + replacement.length;
        }
        editor.focus();
        resizeEditor();
        recordHistory(true);
        scheduleLivePreview();
    };

    // Generic logic specifically for block prefixes like H1 (# ), Lists (- )
    const insertPrefix = (prefix) => {
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        const text = editor.value;
        
        // Find the absolute start of the current active line
        let lineStart = text.lastIndexOf('\n', start - 1);
        lineStart = (lineStart === -1) ? 0 : lineStart + 1;
        
        editor.value = text.substring(0, lineStart) + prefix + text.substring(lineStart);
        
        // Preserve user selection cursor movement
        editor.selectionStart = start + prefix.length;
        editor.selectionEnd = end + prefix.length;
        editor.focus();
        resizeEditor();
        recordHistory(true);
        scheduleLivePreview();
    };

    const insertTemplate = (template, cursorOffset) => {
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        const text = editor.value;
        editor.value = text.substring(0, start) + template + text.substring(end);

        const offset = Number.isFinite(cursorOffset) ? cursorOffset : template.length;
        const nextPos = start + Math.max(0, Math.min(offset, template.length));
        editor.selectionStart = nextPos;
        editor.selectionEnd = nextPos;
        editor.focus();
        resizeEditor();
        recordHistory(true);
        scheduleLivePreview();
    };

    const insertLinkTemplate = () => {
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        const text = editor.value;
        const selected = text.substring(start, end);
        const label = selected || '链接文字';
        const template = `[${label}](https://example.com)`;

        editor.value = text.substring(0, start) + template + text.substring(end);

        const urlStart = start + `[${label}](`.length;
        const urlEnd = urlStart + 'https://example.com'.length;
        editor.selectionStart = urlStart;
        editor.selectionEnd = urlEnd;
        editor.focus();
        resizeEditor();
        recordHistory(true);
        scheduleLivePreview(); // Schedule live preview after link insertion
    };

    const imageUploadInput = document.getElementById('inline-image-input');

    const uploadImageFile = async (file) => {
        if (!file) {
            throw new Error('未选择图片');
        }

        if (!currentNovelId) {
            throw new Error('请先指定工作区');
        }

        const token = checkAuth();
        if (!token) {
            window.location.href = `/login/?next=${encodeURIComponent(window.location.pathname + window.location.search)}`;
            throw new Error('未登录');
        }

        const formData = new FormData();
        formData.append('image', file);
        formData.append('novel', String(currentNovelId));

        const requestInit = {
            method: 'POST',
            body: formData,
        };

        let response;
        if (typeof fetchWithAuthRetry === 'function') {
            response = await fetchWithAuthRetry('/api/chapters/upload_image/', requestInit);
        } else {
            response = await fetch('/api/chapters/upload_image/', {
                ...requestInit,
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });
        }

        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.detail || '图片上传失败');
        }

        if (!data.url) {
            throw new Error('图片URL生成失败');
        }

        return data.url;
    };

    const insertImageMarkdown = async (file) => {
        const imageUrl = await uploadImageFile(file);
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        const text = editor.value;
        const alt = file.name.replace(/\.[^.]+$/, '') || '图片';
        const markdownImage = `![${alt}](${imageUrl})`;

        editor.value = text.substring(0, start) + markdownImage + text.substring(end);
        const nextPos = start + markdownImage.length;
        editor.selectionStart = nextPos;
        editor.selectionEnd = nextPos;
        editor.focus();
        resizeEditor();
        recordHistory(true);
        scheduleLivePreview();
    };

    if (imageUploadInput) {
        imageUploadInput.addEventListener('change', async (event) => {
            const file = event.target.files && event.target.files[0];
            if (file) {
                try {
                    if (saveStatus) {
                        saveStatus.textContent = '图片上传中...';
                    }
                    await insertImageMarkdown(file);
                    if (saveStatus) {
                        saveStatus.textContent = '图片已插入';
                    }
                } catch (error) {
                    if (saveStatus) {
                        saveStatus.textContent = error.message || '图片上传失败';
                    }
                }
            }
            imageUploadInput.value = '';
        });
    }

    const insertRubyTemplate = () => {
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        const text = editor.value;
        const selectedText = text.substring(start, end);

        const baseText = (selectedText || '文字').replaceAll('|', '｜');
        const rubyTemplate = `{注音|${baseText}|}`;

        editor.value = text.substring(0, start) + rubyTemplate + text.substring(end);

        // Place caret in the ruby reading segment after the second pipe.
        const rubyInputPos = start + `{注音|${baseText}|`.length;
        editor.selectionStart = rubyInputPos;
        editor.selectionEnd = rubyInputPos;
        editor.focus();
        resizeEditor();
        recordHistory(true);
        scheduleLivePreview();
    };

    // Auto script binder for ALL toolbar buttons driven by pure data attributes!
    document.querySelectorAll('.tool-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const { start, end, prefix, template, cursorOffset, ruby, action } = btn.dataset;
            if (start !== undefined && end !== undefined) {
                insertTag(start, end);
            } else if (prefix !== undefined) {
                insertPrefix(prefix);
            } else if (template !== undefined) {
                insertTemplate(template, parseInt(cursorOffset || `${template.length}`, 10));
            } else if (ruby !== undefined) {
                insertRubyTemplate();
            } else if (action === 'insert-link') {
                insertLinkTemplate();
            } else if (action === 'upload-image') {
                if (imageUploadInput) imageUploadInput.click();
            }
        });
    });

    // Capture Ctrl+B, Ctrl+I for shortcuts
    editor.addEventListener('keydown', (e) => {
        if (e.ctrlKey || e.metaKey) {
            if (e.key === 'b' || e.key === 'B') {
                e.preventDefault();
                insertTag('**', '**');
                return;
            }
            if (e.key === 'i' || e.key === 'I') {
                e.preventDefault();
                insertTag('*', '*');
                return;
            }
            if ((e.key === 'z' || e.key === 'Z') && !e.shiftKey) {
                e.preventDefault();
                undoHistory();
                return;
            }
            if (e.key === 'y' || e.key === 'Y' || ((e.key === 'z' || e.key === 'Z') && e.shiftKey)) {
                e.preventDefault();
                redoHistory();
            }
        }
    });

    // Capture Tab for indentation in textarea
    editor.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            e.preventDefault();
            insertTag('    ', '');
        }
    });

    editor.addEventListener('input', scheduleHistoryRecord);
    editor.addEventListener('input', scheduleLivePreview);
    if (titleInput) {
        titleInput.addEventListener('input', scheduleHistoryRecord);
        titleInput.addEventListener('input', scheduleLivePreview);
    }

    // Custom Font Logic
    const fontSelector = document.getElementById('font-selector');
    const uploadFontBtn = document.getElementById('upload-font-btn');
    const fontModal = document.getElementById('font-upload-modal');
    const fontForm = document.getElementById('font-upload-form');
    const fontUploadMsg = document.getElementById('font-upload-msg');

    // Editor data implementation
    const wordCount = document.getElementById('word-count');
    const saveStatus = document.getElementById('save-status');
    const btnSave = document.getElementById('btn-save');
    const btnPreview = document.getElementById('btn-preview');
    const workspaceLabel = document.getElementById('editor-workspace-label');
    const btnToggleChapters = document.getElementById('btn-toggle-chapters');
    const btnToggleLivePreview = document.getElementById('btn-toggle-live-preview');
    const breadcrumb = document.getElementById('editor-breadcrumb');
    const btnBackWorkspace = document.getElementById('btn-back-workspace');
    const btnToggleWorkspaceNav = document.getElementById('btn-toggle-workspace-nav');
    const btnToggleSide = document.getElementById('btn-toggle-side');
    const editorRightPanel = document.getElementById('editor-right-panel');
    const chapterStatus = document.getElementById('chapter-status');
    const workspaceShell = document.getElementById('workspace-shell');
    const workspaceSidebar = document.getElementById('workspace-sidebar');
    const editorWorkspace = document.querySelector('.editor-workspace');
    const editorCanvas = document.getElementById('editor-canvas');
    const livePreviewPane = document.getElementById('editor-live-preview');
    const livePreviewBody = document.getElementById('editor-live-preview-body');

    const resolveWorkspaceContext = () => {
        const params = new URLSearchParams(window.location.search);
        const contextNode = document.querySelector('[data-workspace-context]');
        const fromData = contextNode ? contextNode.dataset.workspaceId : null;
        const fromWindow = window.BEDROCK_WORKSPACE && window.BEDROCK_WORKSPACE.id ? String(window.BEDROCK_WORKSPACE.id) : null;
        const fromQuery = params.get('workspace_id') || params.get('novel_id');
        const pathMatch = window.location.pathname.match(/^\/workspace\/(\d+)\//);
        const fromPath = pathMatch ? pathMatch[1] : null;

        return {
            id: fromWindow || fromData || fromQuery || fromPath,
            title: (window.BEDROCK_WORKSPACE && window.BEDROCK_WORKSPACE.title)
                || (contextNode && contextNode.dataset.workspaceTitle)
                || '当前工作区',
        };
    };
    
    let currentChapterId = new URLSearchParams(window.location.search).get('chapter_id');
    const workspaceContext = resolveWorkspaceContext();
    let currentNovelId = workspaceContext.id;
    let isSaving = false;
    let mentionCharacters = [];
    let mentionOpen = false;
    let mentionStart = -1;

    const mentionPanel = document.createElement('div');
    mentionPanel.className = 'editor-mention-panel';
    mentionPanel.hidden = true;
    document.body.appendChild(mentionPanel);

    const closeMentionPanel = () => {
        mentionOpen = false;
        mentionStart = -1;
        mentionPanel.hidden = true;
        mentionPanel.innerHTML = '';
    };

    const loadMentionCharacters = async () => {
        if (!currentNovelId) {
            mentionCharacters = [];
            return;
        }
        try {
            const token = checkAuth();
            if (!token) {
                mentionCharacters = [];
                return;
            }
            const response = await fetch(`/api/characters/?novel=${currentNovelId}`, {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });
            if (!response.ok) {
                mentionCharacters = [];
                return;
            }
            const payload = await response.json();
            mentionCharacters = Array.isArray(payload) ? payload : (payload.results || []);
        } catch {
            mentionCharacters = [];
        }
    };

    const insertMentionToken = (name, cursorEnd) => {
        if (mentionStart < 0) return;
        const text = editor.value;
        const token = `{@人物:${name}}`;
        editor.value = text.slice(0, mentionStart) + token + text.slice(cursorEnd);
        const nextPos = mentionStart + token.length;
        editor.selectionStart = nextPos;
        editor.selectionEnd = nextPos;
        resizeEditor();
        recordHistory(true);
        scheduleLivePreview();
        closeMentionPanel();
        editor.focus();
    };

    const openMentionPanel = (query, cursorEnd) => {
        const lowered = (query || '').toLowerCase();
        const matched = mentionCharacters.filter((item) => {
            const byName = String(item.name || '').toLowerCase().includes(lowered);
            const byAlias = (item.aliases || []).some((alias) => String(alias).toLowerCase().includes(lowered));
            return byName || byAlias;
        }).slice(0, 8);

        if (!matched.length) {
            closeMentionPanel();
            return;
        }

        mentionPanel.innerHTML = matched.map((item, index) => `
            <button type="button" class="editor-mention-item ${index === 0 ? 'active' : ''}" data-char-name="${item.name}">
                <strong>${item.name}</strong>
                <span>${item.role_title || item.summary || ''}</span>
            </button>
        `).join('');

        const rect = editor.getBoundingClientRect();
        mentionPanel.style.left = `${rect.left + 14}px`;
        mentionPanel.style.top = `${Math.min(window.innerHeight - 220, rect.top + 56)}px`;
        mentionPanel.hidden = false;
        mentionOpen = true;

        mentionPanel.querySelectorAll('.editor-mention-item').forEach((btn) => {
            btn.addEventListener('click', () => {
                insertMentionToken(btn.dataset.charName || '', cursorEnd);
            });
        });
    };

    const handleMentionInput = () => {
        const cursor = editor.selectionStart;
        const textBefore = editor.value.slice(0, cursor);
        const match = textBefore.match(/(^|\s)@([\u4e00-\u9fa5A-Za-z0-9_\-]{0,40})$/);
        if (!match) {
            closeMentionPanel();
            return;
        }

        mentionStart = cursor - match[2].length - 1;
        openMentionPanel(match[2], cursor);
    };

    recordHistory(true);

    if (workspaceLabel) {
        workspaceLabel.textContent = `${workspaceContext.title} #${currentNovelId || '?'}`;
    }

    // Tabs toggle logic
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(p => p.style.display = 'none');
            const targetId = btn.getAttribute('data-target');
            btn.classList.add('active');
            let pane = document.getElementById(targetId);
            if (pane) pane.style.display = 'block';
        });
    });

    // Right Sidebar toggle logic
    if (btnToggleSide && editorRightPanel) {
        btnToggleSide.addEventListener('click', () => {
            editorRightPanel.classList.toggle('collapsed');
            const collapsed = editorRightPanel.classList.contains('collapsed');
            btnToggleSide.title = collapsed ? '展开辅助面板' : '收起辅助面板';
            btnToggleSide.textContent = collapsed ? '◀' : '▶';
        });
    }

    if (btnToggleChapters && editorWorkspace) {
        btnToggleChapters.addEventListener('click', () => {
            editorWorkspace.classList.toggle('is-chapters-collapsed');
            const collapsed = editorWorkspace.classList.contains('is-chapters-collapsed');
            btnToggleChapters.title = collapsed ? '展开章节栏' : '折叠章节栏';
            btnToggleChapters.textContent = collapsed ? '▶' : '◀';
        });
    }

    if (btnToggleWorkspaceNav && workspaceShell && workspaceSidebar) {
        btnToggleWorkspaceNav.addEventListener('click', () => {
            workspaceShell.classList.toggle('is-workspace-sidebar-collapsed');
            const collapsed = workspaceShell.classList.contains('is-workspace-sidebar-collapsed');
            btnToggleWorkspaceNav.title = collapsed ? '展开工作区导航' : '折叠工作区导航';
            btnToggleWorkspaceNav.textContent = collapsed ? '▶' : '◀';
        });
    }

    if (btnToggleLivePreview && editorCanvas && livePreviewPane) {
        btnToggleLivePreview.addEventListener('click', () => {
            editorCanvas.classList.toggle('preview-hidden');
            const hidden = editorCanvas.classList.contains('preview-hidden');
            btnToggleLivePreview.title = hidden ? '显示实时预览' : '隐藏实时预览';
            btnToggleLivePreview.textContent = hidden ? '◀' : '▶';
        });
    }

    if (currentNovelId && btnBackWorkspace) {
        btnBackWorkspace.href = `/workspace/${currentNovelId}/writing/`;
    }

    // Word count update
    const updateWordCount = () => {
        const text = editor.value || "";
        wordCount.textContent = `字数：${text.replace(/\s/g, '').length}`;
    };
    editor.addEventListener('input', updateWordCount);
    editor.addEventListener('input', handleMentionInput);

    editor.addEventListener('keydown', (event) => {
        if (!mentionOpen) return;
        if (event.key === 'Escape') {
            closeMentionPanel();
            return;
        }

        if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp' && event.key !== 'Enter') {
            return;
        }

        event.preventDefault();
        const items = Array.from(mentionPanel.querySelectorAll('.editor-mention-item'));
        if (!items.length) return;
        const currentIndex = items.findIndex((item) => item.classList.contains('active'));

        if (event.key === 'Enter') {
            const active = items[currentIndex >= 0 ? currentIndex : 0];
            if (active) {
                insertMentionToken(active.dataset.charName || '', editor.selectionStart);
            }
            return;
        }

        items.forEach((item) => item.classList.remove('active'));
        const delta = event.key === 'ArrowDown' ? 1 : -1;
        const next = (currentIndex + delta + items.length) % items.length;
        items[next].classList.add('active');
    });

    document.addEventListener('click', (event) => {
        if (!mentionOpen) return;
        if (event.target === editor || mentionPanel.contains(event.target)) return;
        closeMentionPanel();
    });

    const checkAuth = () => localStorage.getItem("bedrock_access");

    let previewDebounceTimer = null;

    const renderLivePreview = async () => {
        if (!livePreviewBody) {
            return;
        }

        const token = checkAuth();
        if (!token) {
            livePreviewBody.innerHTML = '<p class="text-muted">请先登录后使用实时预览。</p>';
            return;
        }

        const payload = {
            content_md: editor.value || '',
            novel: currentNovelId || null,
        };

        try {
            const response = await fetch('/api/chapters/render_preview/', {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                livePreviewBody.innerHTML = '<p class="text-muted">预览渲染失败，请稍后重试。</p>';
                return;
            }

            const data = await response.json();
            livePreviewBody.innerHTML = data.html || '<p class="text-muted">暂无内容</p>';

            livePreviewBody.querySelectorAll('.mk-custom-font[data-font]').forEach((el) => {
                const fontName = (el.getAttribute('data-font') || '').trim();
                if (fontName) {
                    el.style.fontFamily = `"${fontName}", sans-serif`;
                }
            });
        } catch (error) {
            livePreviewBody.innerHTML = '<p class="text-muted">预览服务不可用。</p>';
        }
    };

    function scheduleLivePreview() {
        if (previewDebounceTimer) {
            clearTimeout(previewDebounceTimer);
        }
        previewDebounceTimer = setTimeout(() => {
            renderLivePreview();
        }, 160);
    }

    const loadChapterList = async (novelId) => {
        const token = checkAuth();
        const container = document.getElementById('chapter-list-container');
        if (!container) return;

        if (!novelId) {
            container.innerHTML = '<p class="text-muted" style="text-align:center; font-size: 0.85rem;">未指定工作区</p>';
            return;
        }

        if (!token) {
            container.innerHTML = '<p class="text-muted" style="text-align:center; font-size: 0.85rem;">请先登录后加载章节</p>';
            return;
        }

        container.innerHTML = '<p class="text-muted" style="text-align:center; font-size: 0.85rem;">加载中...</p>';
        try {
            const res = await fetch(`/api/chapters/?novel=${novelId}`, { headers: { 'Authorization': `Bearer ${token}` } });
            if (res.ok) {
                const data = await res.json();
                const chapters = data.results || data;
                if (!chapters.length) {
                    container.innerHTML = '<p class="text-muted" style="text-align:center; font-size: 0.85rem;">暂无章节</p>';
                } else {
                    container.innerHTML = chapters.map(ch => {
                        const title = ch.title || '未命名';
                        return `
                        <button type="button" class="chapter-item ${String(ch.id) === String(currentChapterId) ? 'active' : ''}" data-chapter-id="${ch.id}">
                            <i class="ph ph-file-text" style="margin-right: 4px; opacity: 0.6; font-size: 0.9em;"></i>${title}
                        </button>`;
                    }).join('');

                    container.querySelectorAll('[data-chapter-id]').forEach((item) => {
                        item.addEventListener('click', () => {
                            const chapterId = item.getAttribute('data-chapter-id');
                            window.location.href = `/workspace/${currentNovelId}/writing/?chapter_id=${chapterId}`;
                        });
                    });
                }
            } else {
                container.innerHTML = '<p class="text-danger" style="text-align:center; font-size: 0.85rem;">章节加载失败</p>';
            }
        } catch (e) {
            container.innerHTML = '<p class="text-danger">加载失败</p>';
        }
    };

    const getNextChapterOrder = async (novelId, token) => {
        if (!novelId || !token) return 1;
        try {
            const response = await fetch(`/api/chapters/?novel=${novelId}&ordering=order`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!response.ok) return 1;
            const payload = await response.json();
            const chapters = Array.isArray(payload) ? payload : (payload.results || []);
            const maxOrder = chapters.reduce((max, item) => Math.max(max, Number(item.order) || 0), 0);
            return maxOrder + 1;
        } catch {
            return 1;
        }
    };

    document.getElementById('btn-new-chapter')?.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (!currentNovelId) return alert('请先指定工作区');
        window.location.href = `/workspace/${currentNovelId}/writing/`;
    });

    const loadChapter = async () => {
        const token = checkAuth();
        if (!token) {
            if (breadcrumb) breadcrumb.textContent = '请先登录';
            if (chapterStatus) chapterStatus.textContent = '状态：请先登录';
            loadChapterList(currentNovelId);
            return;
        }
        
        try {
            if (currentChapterId) {
                const res = await fetch(`/api/chapters/${currentChapterId}/`, { headers: { 'Authorization': `Bearer ${token}` } });
                if (res.ok) {
                    const data = await res.json();
                    titleInput.value = data.title;
                    editor.value = data.content_md;
                    currentNovelId = data.novel;
                    if (breadcrumb) breadcrumb.textContent = `工作区 ${data.workspace_name || '#' + data.novel} / ${data.title}`;
                    if (chapterStatus) chapterStatus.textContent = `状态：${data.is_published ? '已发布' : '草稿'}`;
                    resizeEditor();
                    updateWordCount();
                    recordHistory(true);
                    scheduleLivePreview();
                    loadChapterList(currentNovelId);
                } else {
                    if (breadcrumb) breadcrumb.textContent = '章节加载失败';
                    if (chapterStatus) chapterStatus.textContent = '状态：加载失败';
                }
            } else if (currentNovelId) {
                // If no chapter_id is provided, still load workspace chapter list.
                if (breadcrumb) breadcrumb.textContent = `工作区 #${currentNovelId} / 新章节`;
                if (chapterStatus) chapterStatus.textContent = '状态：草稿';
                loadChapterList(currentNovelId);
                recordHistory(true);
                scheduleLivePreview();
            } else {
                if (breadcrumb) breadcrumb.textContent = `未指定工作区`;
                if (chapterStatus) chapterStatus.textContent = '状态：未指定工作区';
                const container = document.getElementById('chapter-list-container');
                if (container) {
                    container.innerHTML = '<p class="text-muted" style="text-align:center; font-size: 0.85rem;">未指定工作区</p>';
                }
                recordHistory(true);
                scheduleLivePreview();
            }
        } catch (err) {
            console.error(err);
            if (chapterStatus) chapterStatus.textContent = '状态：加载失败';
            if (breadcrumb) breadcrumb.textContent = '加载失败';
            loadChapterList(currentNovelId);
        } finally {
            loadMentionCharacters();
        }
    };

    const saveChapter = async () => {
        const token = checkAuth();
        if (!token) {
            if (saveStatus) saveStatus.textContent = '请先登录';
            window.location.href = `/login/?next=${encodeURIComponent(window.location.pathname + window.location.search)}`;
            return;
        }
        if (isSaving || !currentNovelId) {
            if (saveStatus && !currentNovelId) saveStatus.textContent = '未指定工作区';
            return;
        }

        isSaving = true;
        saveStatus.textContent = '保存中...';
        btnSave.disabled = true;

        const payload = {
            title: titleInput.value || '未命名章节',
            content_md: editor.value,
            novel: currentNovelId
        };

        try {
            const url = currentChapterId ? `/api/chapters/${currentChapterId}/` : '/api/chapters/';
            const method = currentChapterId ? 'PUT' : 'POST';
            if (!currentChapterId) {
                payload.order = await getNextChapterOrder(currentNovelId, token);
            }
            
            const res = await fetch(url, {
                method,
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            if (res.ok) {
                const data = await res.json();
                if (!currentChapterId) {
                    currentChapterId = data.id;
                    window.history.replaceState({}, '', `/workspace/${currentNovelId}/writing/?chapter_id=${data.id}`);
                }
                const now = new Date();
                saveStatus.textContent = `已自动保存 ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
                if (breadcrumb) breadcrumb.textContent = `工作区 ${data.workspace_name || '#' + data.novel} / ${data.title}`;
                await loadChapterList(currentNovelId);
            } else {
                saveStatus.textContent = '保存失败';
            }
        } catch (err) {
            saveStatus.textContent = '网络错误';
        }

        isSaving = false;
        btnSave.disabled = false;
    };

    if (btnSave) {
        btnSave.addEventListener('click', saveChapter);
    }
    
    // Auto-save every 30 seconds
    setInterval(() => {
        if (titleInput.value.trim() !== '' || editor.value.trim() !== '') {
            saveChapter();
        }
    }, 30000);

    // Ctrl+S / Cmd+S
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            saveChapter();
        }
    });

    if (btnPreview) {
        btnPreview.addEventListener('click', () => {
        if (currentChapterId) {
            const workspaceParam = currentNovelId ? `&workspace_id=${currentNovelId}` : '';
            window.location.href = `/reader/?chapter_id=${currentChapterId}${workspaceParam}`;
            return;
        }
        window.alert('请先保存章节后再预览。');
        });
    }

    // Load initial data
    loadChapter();

    // Load available fonts into the select dropdown
    const renderFontSelector = () => {
        if (!window.bedrockCustomFonts) return;
        
        fontSelector.innerHTML = '<option value="">应用字体...</option>';
        window.bedrockCustomFonts.forEach(font => {
            const option = document.createElement('option');
            option.value = font.name;
            option.textContent = font.name;
            option.style.fontFamily = `"${font.name}", sans-serif`;
            fontSelector.appendChild(option);
        });
    };

    window.addEventListener('bedrockFontsLoaded', renderFontSelector);
    if (window.bedrockCustomFonts) renderFontSelector();

    fontSelector.addEventListener('change', (e) => {
        const fontName = e.target.value;
        if (!fontName) return;
        // Inject Custom Font Markdown Syntax
        insertTag(`{字体:${fontName}|`, `}`);
        e.target.value = ''; // Reset selection
    });

    if (uploadFontBtn && fontModal && fontForm && fontUploadMsg) {
        uploadFontBtn.addEventListener('click', () => {
        fontModal.showModal();
        fontForm.reset();
        fontUploadMsg.textContent = '';
    });

        const cancelBtn = fontModal.querySelector('.btn-cancel');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => fontModal.close());
        }

        fontForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const token = localStorage.getItem("bedrock_access");
        if (!token) {
            fontUploadMsg.textContent = '未登录，无法上传字体。';
            return;
        }

        const formData = new FormData(fontForm);
        fontUploadMsg.textContent = '上传中，请稍候...';

        try {
            const response = await fetch('/api/customization/fonts/', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });

            if (!response.ok) {
                fontUploadMsg.textContent = '上传失败：' + response.statusText;
                return;
            }

            fontUploadMsg.textContent = '上传成功！';
            // Trigger global reload of fonts in site.js
            if (window.loadCustomFonts) await window.loadCustomFonts(true);
            fontModal.close();
        } catch (error) {
            fontUploadMsg.textContent = '网络错误。';
        }
    });
    }

});
