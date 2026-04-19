document.addEventListener("DOMContentLoaded", () => {
    const canvasEl = document.getElementById("outline-canvas");
    const layoutEl = document.getElementById("outline-layout");
    if (!canvasEl || !layoutEl) return;

    const workspaceCtx = document.querySelector("[data-workspace-context]");
    const workspaceId = Number(workspaceCtx?.dataset.workspaceId || 0);
    if (!workspaceId) return;

    const initialJsonNode = document.getElementById("outline-initial-data");
    const initialData = initialJsonNode ? JSON.parse(initialJsonNode.textContent || "{}") : {};

    const nodeLayer = document.getElementById("outline-node-layer");
    const edgeLayer = document.getElementById("outline-edge-layer");
    const viewportEl = document.getElementById("outline-viewport");
    const gridEl = document.getElementById("outline-grid");
    const minimapEl = document.getElementById("outline-minimap");
    const treeViewEl = document.getElementById("outline-tree-view");
    const statusEl = document.getElementById("outline-status");

    const sidepanelEl = document.getElementById("outline-sidepanel");
    const sidepanelToggleBtn = document.getElementById("outline-sidepanel-toggle");

    const timelineLayerEl = document.getElementById("outline-timeline-layer");
    const timelineRulerEl = document.getElementById("outline-timeline-ruler");
    const timelineSelectEl = document.getElementById("outline-timeline-select");
    const addTimelineBtn = document.getElementById("outline-add-timeline");
    const parallelViewBtn = document.getElementById("outline-toggle-parallel");
    const modeFreeBtn = document.getElementById("outline-mode-free");
    const modeTimelineBtn = document.getElementById("outline-mode-timeline");
    const unanchoredEl = document.getElementById("outline-unanchored");
    const unanchoredListEl = document.getElementById("outline-unanchored-list");

    const saveBtn = document.getElementById("outline-save");
    const autoLayoutBtn = document.getElementById("outline-auto-layout");
    const exportBtn = document.getElementById("outline-export-json");
    const addLegendBtn = document.getElementById("outline-add-legend");
    const viewCanvasBtn = document.getElementById("outline-view-canvas");
    const viewTreeBtn = document.getElementById("outline-view-tree");
    const createFromChapterBtn = document.getElementById("outline-create-from-chapter");
    const createFromCharacterBtn = document.getElementById("outline-create-from-character");

    const searchInput = document.getElementById("outline-search");
    const filterTypeInput = document.getElementById("outline-filter-type");

    const emptySelectionEl = document.getElementById("outline-empty-selection");
    const nodeForm = document.getElementById("outline-node-form");
    const edgeForm = document.getElementById("outline-edge-form");

    const nodeTitleInput = document.getElementById("outline-node-title");
    const nodeTypeInput = document.getElementById("outline-node-type");
    const nodeColorInput = document.getElementById("outline-node-color");
    const nodeDescriptionInput = document.getElementById("outline-node-description");
    const nodeTagsInput = document.getElementById("outline-node-tags");
    const nodeChapterInput = document.getElementById("outline-node-chapter");
    const nodeAnchorInput = document.getElementById("outline-node-anchor");
    const nodeCharacterInput = document.getElementById("outline-node-character");
    const openChapterBtn = document.getElementById("outline-open-chapter");
    const createChapterBindBtn = document.getElementById("outline-create-chapter-bind");

    const edgeColorInput = document.getElementById("outline-edge-color");
    const edgeStyleInput = document.getElementById("outline-edge-style");
    const edgeWidthInput = document.getElementById("outline-edge-width");
    const edgeArrowInput = document.getElementById("outline-edge-arrow");
    const edgeLabelInput = document.getElementById("outline-edge-label");

    const legendListEl = document.getElementById("outline-legend-list");

    const contextMenu = document.createElement("div");
    contextMenu.className = "outline-context-menu";
    contextMenu.hidden = true;
    document.body.appendChild(contextMenu);

    let chapters = [];
    let characters = [];
    let searchKeyword = "";
    let filterType = "";
    let connecting = null;
    let dragging = null;
    let panning = null;
    let anchorDragging = null;
    let autosaveTimer = null;
    let showTreeView = false;
    let spacePressed = false;
    let clipboardNode = null;
    let activeAnchorPositions = [];

    const history = [];
    const future = [];

    const state = normalizeCanvas(initialData);
    let selection = { kind: null, id: null };

    function defaultCanvas() {
        const timelineId = genId("timeline");
        return {
            nodes: [],
            edges: [],
            groups: [],
            legend: [
                { color: "#ef4444", meaning: "主线" },
                { color: "#3b82f6", meaning: "角色线" },
            ],
            viewport: { x: 120, y: 110, scale: 1 },
            mode: "free",
            active_timeline_id: timelineId,
            parallel_view: false,
            timelines: [
                {
                    id: timelineId,
                    name: "主线时间",
                    color: "#ef4444",
                    anchors: [],
                },
            ],
        };
    }

    function normalizeCanvas(raw) {
        const base = defaultCanvas();
        const next = raw && typeof raw === "object" ? raw : {};

        base.nodes = Array.isArray(next.nodes) ? next.nodes.map(normalizeNode) : [];
        base.edges = Array.isArray(next.edges) ? next.edges.map(normalizeEdge) : [];
        base.groups = Array.isArray(next.groups) ? next.groups : [];
        base.legend = Array.isArray(next.legend) ? next.legend : base.legend;
        base.mode = next.mode === "timeline" ? "timeline" : "free";
        base.parallel_view = Boolean(next.parallel_view);

        if (next.viewport && typeof next.viewport === "object") {
            const sx = Number(next.viewport.scale);
            base.viewport = {
                x: Number(next.viewport.x) || base.viewport.x,
                y: Number(next.viewport.y) || base.viewport.y,
                scale: Number.isFinite(sx) ? clamp(sx, 0.35, 2.4) : base.viewport.scale,
            };
        }

        if (Array.isArray(next.timelines) && next.timelines.length) {
            base.timelines = next.timelines.map((item, idx) => ({
                id: String(item?.id || genId("timeline")),
                name: String(item?.name || `时间轴 ${idx + 1}`),
                color: String(item?.color || "#ef4444"),
                anchors: Array.isArray(item?.anchors)
                    ? item.anchors.map((anchor, aidx) => ({
                        id: String(anchor?.id || genId("anchor")),
                        label: String(anchor?.label || `时间点 ${aidx + 1}`),
                        order: Number.isFinite(Number(anchor?.order)) ? Number(anchor.order) : aidx * 100,
                        color: String(anchor?.color || item?.color || "#ef4444"),
                    }))
                    : [],
            }));
        }

        const existing = new Set(base.timelines.map((item) => item.id));
        base.active_timeline_id = existing.has(next.active_timeline_id) ? next.active_timeline_id : base.timelines[0].id;
        return base;
    }

    function normalizeNode(raw) {
        const type = ["chapter", "plot", "character", "note"].includes(raw?.type) ? raw.type : "plot";
        return {
            id: String(raw?.id || genId("node")),
            type,
            title: String(raw?.title || nodeTypeLabel(type)),
            position: {
                x: Number(raw?.position?.x) || 0,
                y: Number(raw?.position?.y) || 0,
            },
            data: {
                chapter_id: raw?.data?.chapter_id ? Number(raw.data.chapter_id) : null,
                character_id: raw?.data?.character_id ? Number(raw.data.character_id) : null,
                timeline_id: raw?.data?.timeline_id ? String(raw.data.timeline_id) : null,
                anchor_id: raw?.data?.anchor_id ? String(raw.data.anchor_id) : null,
                color_tag: String(raw?.data?.color_tag || "#16324f"),
                collapsed: Boolean(raw?.data?.collapsed),
                description: String(raw?.data?.description || ""),
                tags: Array.isArray(raw?.data?.tags) ? raw.data.tags : [],
                missing_chapter: Boolean(raw?.data?.missing_chapter),
            },
        };
    }

    function normalizeEdge(raw) {
        return {
            id: String(raw?.id || genId("edge")),
            source: String(raw?.source || ""),
            target: String(raw?.target || ""),
            data: {
                color: String(raw?.data?.color || "#ef4444"),
                line_style: String(raw?.data?.line_style || "solid"),
                width: Number(raw?.data?.width || 2),
                arrow: String(raw?.data?.arrow || "forward"),
                label: String(raw?.data?.label || ""),
            },
        };
    }

    function genId(prefix) {
        return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
    }

    function nodeTypeLabel(type) {
        if (type === "chapter") return "章节节点";
        if (type === "character") return "人物节点";
        if (type === "note") return "注释节点";
        return "情节点";
    }

    function nodeTypeIcon(type) {
        if (type === "chapter") return "📖";
        if (type === "character") return "👤";
        if (type === "note") return "🗒️";
        return "💡";
    }

    function edgeDash(style) {
        if (style === "dashed") return "8 6";
        if (style === "dotted") return "2 6";
        return "";
    }

    function setStatus(text, error = false) {
        if (!statusEl) return;
        statusEl.textContent = text || "";
        statusEl.style.color = error ? "#b42318" : "";
    }

    function clone(value) {
        return JSON.parse(JSON.stringify(value));
    }

    function pushHistorySnapshot() {
        history.push(clone(state));
        if (history.length > 60) history.shift();
        future.length = 0;
    }

    function applySnapshot(snapshot) {
        state.nodes = snapshot.nodes;
        state.edges = snapshot.edges;
        state.groups = snapshot.groups;
        state.legend = snapshot.legend;
        state.viewport = snapshot.viewport;
        state.mode = snapshot.mode;
        state.active_timeline_id = snapshot.active_timeline_id;
        state.parallel_view = snapshot.parallel_view;
        state.timelines = snapshot.timelines;
        selection = { kind: null, id: null };
        renderAll();
    }

    function undo() {
        if (history.length <= 1) return;
        future.push(clone(state));
        history.pop();
        applySnapshot(clone(history[history.length - 1]));
        setStatus("已撤销");
    }

    function redo() {
        if (!future.length) return;
        const next = future.pop();
        history.push(clone(next));
        applySnapshot(clone(next));
        setStatus("已重做");
    }

    function mutate(mutator, opts = {}) {
        mutator();
        if (opts.pruneDanglingEdges !== false) {
            const nodeIds = new Set(state.nodes.map((item) => item.id));
            state.edges = state.edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target));
        }
        pushHistorySnapshot();
        renderAll();
        scheduleAutosave();
    }

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function filteredNodes() {
        return state.nodes.filter((node) => {
            if (filterType && node.type !== filterType) return false;
            if (!searchKeyword) return true;
            const text = [node.title, node.data.description, ...(node.data.tags || [])].join(" ").toLowerCase();
            return text.includes(searchKeyword.toLowerCase());
        });
    }

    function worldToScreen(x, y) {
        return {
            x: x * state.viewport.scale + state.viewport.x,
            y: y * state.viewport.scale + state.viewport.y,
        };
    }

    function screenToWorld(x, y) {
        return {
            x: (x - state.viewport.x) / state.viewport.scale,
            y: (y - state.viewport.y) / state.viewport.scale,
        };
    }

    function applyViewport() {
        viewportEl.style.transform = `translate(${state.viewport.x}px, ${state.viewport.y}px) scale(${state.viewport.scale})`;
        const gridBase = 28 * state.viewport.scale;
        gridEl.style.backgroundSize = `${gridBase}px ${gridBase}px`;
        gridEl.style.backgroundPosition = `${state.viewport.x}px ${state.viewport.y}px`;
    }

    function getActiveTimeline() {
        return state.timelines.find((item) => item.id === state.active_timeline_id) || state.timelines[0] || null;
    }

    function getSortedAnchors() {
        const timeline = getActiveTimeline();
        if (!timeline) return [];
        return [...timeline.anchors].sort((a, b) => a.order - b.order);
    }

    function timelineAnchorPositions() {
        const anchors = getSortedAnchors();
        const width = canvasEl.clientWidth;
        const left = 72;
        const right = Math.max(left + 40, width - 72);
        if (!anchors.length) return [];

        const orders = anchors.map((item) => item.order);
        const minOrder = Math.min(...orders);
        const maxOrder = Math.max(...orders);
        const span = maxOrder - minOrder || 1;

        return anchors.map((anchor, idx) => {
            const ratio = span === 0 ? (idx / Math.max(anchors.length - 1, 1)) : (anchor.order - minOrder) / span;
            const x = left + (right - left) * ratio;
            return { ...anchor, x };
        });
    }

    function ensureTimelineNodeAlignment(node) {
        if (state.mode !== "timeline") return;
        const timelineId = node.data.timeline_id || state.active_timeline_id;
        if (timelineId !== state.active_timeline_id) return;
        const anchorId = node.data.anchor_id;
        if (!anchorId) return;
        const anchor = activeAnchorPositions.find((item) => item.id === anchorId);
        if (!anchor) return;
        node.position.x = Math.round(anchor.x - 116);
    }

    function nodeSubtitle(node) {
        if (node.type === "chapter") {
            if (node.data.missing_chapter) return "章节已丢失";
            const chapter = chapters.find((item) => item.id === node.data.chapter_id);
            if (!chapter) return node.data.anchor_id ? "已绑定时间" : "未绑定章节";
            const status = chapter.is_published ? "🟢 已发布" : "🟡 草稿";
            const anchorLabel = activeAnchorPositions.find((item) => item.id === node.data.anchor_id)?.label;
            return `${status} · 第 ${chapter.order} 章${anchorLabel ? ` · 📅 ${anchorLabel}` : ""}`;
        }
        if (node.type === "character") {
            const character = characters.find((item) => item.id === node.data.character_id);
            const anchorLabel = activeAnchorPositions.find((item) => item.id === node.data.anchor_id)?.label;
            return `${character ? character.name : "未关联人物"}${anchorLabel ? ` · 首次:${anchorLabel}` : ""}`;
        }
        if (node.data.anchor_id) {
            const anchorLabel = activeAnchorPositions.find((item) => item.id === node.data.anchor_id)?.label;
            if (anchorLabel) return `📅 ${anchorLabel}`;
        }
        if (node.data.tags?.length) return node.data.tags.join(" · ");
        return state.mode === "timeline" ? "⚡ 未锚定" : "";
    }

    function renderTimelineLayer() {
        const timelineMode = state.mode === "timeline";
        timelineLayerEl.hidden = false;

        const laneNames = state.parallel_view
            ? state.timelines.map((item, idx) => ({ id: item.id, name: item.name, color: item.color, idx }))
            : [{ id: state.active_timeline_id, name: getActiveTimeline()?.name || "主线时间", color: getActiveTimeline()?.color || "#ef4444", idx: 0 }];

        const laneHeight = 210;
        if (state.parallel_view) {
            canvasEl.style.setProperty("--outline-lane-count", String(Math.max(1, laneNames.length)));
            canvasEl.style.setProperty("--outline-lane-height", `${laneHeight}px`);
        } else {
            canvasEl.style.setProperty("--outline-lane-count", "1");
            canvasEl.style.setProperty("--outline-lane-height", `${laneHeight}px`);
        }

        const anchorHtml = activeAnchorPositions.map((anchor) => `
            <div class="outline-anchor" data-anchor-id="${escapeHtml(anchor.id)}" style="left:${anchor.x}px;--anchor-color:${escapeHtml(anchor.color || '#ef4444')}">
                <span class="outline-anchor-dot"></span>
                <span class="outline-anchor-label">${escapeHtml(anchor.label)}</span>
            </div>
        `).join("");

        const laneHtml = laneNames.map((lane) => `
            <div class="outline-timeline-lane" data-lane-id="${escapeHtml(lane.id)}" style="--lane-color:${escapeHtml(lane.color || '#ef4444')};top:${70 + lane.idx * laneHeight}px">
                <span>${escapeHtml(lane.name)}</span>
            </div>
        `).join("");

        timelineRulerEl.innerHTML = `
            <div class="outline-ruler-line"></div>
            ${anchorHtml}
            ${laneHtml}
        `;

        const unanchoredNodes = timelineMode
            ? state.nodes.filter((node) => !node.data.anchor_id && (!node.data.timeline_id || node.data.timeline_id === state.active_timeline_id))
            : [];
        unanchoredEl.hidden = !timelineMode || !unanchoredNodes.length;
        unanchoredListEl.innerHTML = unanchoredNodes.map((node) => `<button type="button" data-unanchored-node="${escapeHtml(node.id)}">${escapeHtml(node.title)}</button>`).join("");
    }

    function nodeLaneY(node) {
        if (state.mode !== "timeline" || !state.parallel_view) return null;
        const idx = state.timelines.findIndex((item) => item.id === (node.data.timeline_id || state.active_timeline_id));
        if (idx < 0) return null;
        return 100 + idx * 210;
    }

    function renderNodes() {
        const visible = new Set(filteredNodes().map((item) => item.id));
        nodeLayer.innerHTML = "";

        state.nodes.forEach((node) => {
            ensureTimelineNodeAlignment(node);
            const laneMinY = nodeLaneY(node);
            if (laneMinY !== null) {
                node.position.y = clamp(node.position.y, laneMinY, laneMinY + 170);
            }

            const nodeEl = document.createElement("article");
            nodeEl.className = `outline-node outline-node-${node.type}`;
            if (!visible.has(node.id)) nodeEl.classList.add("is-filtered-out");
            if (selection.kind === "node" && selection.id === node.id) nodeEl.classList.add("is-selected");
            if (node.data.missing_chapter) nodeEl.classList.add("is-warning");
            if (state.mode === "timeline" && node.data.anchor_id) nodeEl.classList.add("is-anchored");

            nodeEl.dataset.nodeId = node.id;
            nodeEl.style.left = `${node.position.x}px`;
            nodeEl.style.top = `${node.position.y}px`;

            const subtitle = nodeSubtitle(node);
            const subtitleHtml = subtitle ? `<p class="outline-node-subtitle">${escapeHtml(subtitle)}</p>` : "";

            nodeEl.innerHTML = `
                <div class="outline-node-handle in" data-handle="in" title="输入"></div>
                <header class="outline-node-head" style="--node-color:${escapeHtml(node.data.color_tag)}">
                    <span class="outline-node-type">${nodeTypeIcon(node.type)} ${nodeTypeLabel(node.type)}</span>
                </header>
                <h4 class="outline-node-title">${escapeHtml(node.title)}</h4>
                ${subtitleHtml}
                <div class="outline-node-handle out" data-handle="out" title="输出"></div>
            `;
            nodeLayer.appendChild(nodeEl);
        });
    }

    function edgePath(sourceNode, targetNode) {
        const sx = sourceNode.position.x + 232;
        const sy = sourceNode.position.y + 58;
        const tx = targetNode.position.x;
        const ty = targetNode.position.y + 58;
        const c1x = sx + Math.max(70, (tx - sx) * 0.38);
        const c2x = tx - Math.max(70, (tx - sx) * 0.38);
        return {
            d: `M ${sx} ${sy} C ${c1x} ${sy}, ${c2x} ${ty}, ${tx} ${ty}`,
            midX: (sx + tx) / 2,
            midY: (sy + ty) / 2,
        };
    }

    function renderEdges() {
        const visible = new Set(filteredNodes().map((item) => item.id));
        const byId = new Map(state.nodes.map((node) => [node.id, node]));
        edgeLayer.querySelectorAll(".outline-edge, .outline-edge-label, .outline-edge-preview").forEach((el) => el.remove());

        state.edges.forEach((edge) => {
            const source = byId.get(edge.source);
            const target = byId.get(edge.target);
            if (!source || !target) return;

            const shouldDim = !visible.has(source.id) || !visible.has(target.id);
            const path = edgePath(source, target);

            const pathEl = document.createElementNS("http://www.w3.org/2000/svg", "path");
            pathEl.setAttribute("d", path.d);
            pathEl.setAttribute("fill", "none");
            pathEl.setAttribute("stroke", edge.data.color || "#ef4444");
            pathEl.setAttribute("stroke-width", String(edge.data.width || 2));
            pathEl.setAttribute("stroke-dasharray", edgeDash(edge.data.line_style));
            pathEl.setAttribute("class", "outline-edge");
            pathEl.dataset.edgeId = edge.id;
            if (shouldDim) pathEl.classList.add("is-filtered-out");
            if (selection.kind === "edge" && selection.id === edge.id) pathEl.classList.add("is-selected");

            const arrow = edge.data.arrow || "forward";
            if (arrow === "forward" || arrow === "both") pathEl.setAttribute("marker-end", "url(#outline-arrow-end)");
            if (arrow === "both") pathEl.setAttribute("marker-start", "url(#outline-arrow-end)");
            edgeLayer.appendChild(pathEl);

            if (edge.data.label) {
                const textEl = document.createElementNS("http://www.w3.org/2000/svg", "text");
                textEl.setAttribute("x", String(path.midX));
                textEl.setAttribute("y", String(path.midY - 6));
                textEl.setAttribute("class", "outline-edge-label");
                textEl.textContent = edge.data.label;
                edgeLayer.appendChild(textEl);
            }
        });

        if (connecting?.sourceId) {
            const source = byId.get(connecting.sourceId);
            if (!source) return;
            const sx = source.position.x + 232;
            const sy = source.position.y + 58;
            const tx = connecting.worldX;
            const ty = connecting.worldY;
            const c1x = sx + 80;
            const c2x = tx - 80;
            const previewPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
            previewPath.setAttribute("d", `M ${sx} ${sy} C ${c1x} ${sy}, ${c2x} ${ty}, ${tx} ${ty}`);
            previewPath.setAttribute("fill", "none");
            previewPath.setAttribute("stroke", "#9ca3af");
            previewPath.setAttribute("stroke-width", "2");
            previewPath.setAttribute("stroke-dasharray", "6 6");
            previewPath.setAttribute("class", "outline-edge-preview");
            edgeLayer.appendChild(previewPath);
        }
    }

    function renderTreeView() {
        const byId = new Map(state.nodes.map((node) => [node.id, node]));
        const children = new Map();
        const indegree = new Map();

        state.nodes.forEach((node) => {
            children.set(node.id, []);
            indegree.set(node.id, 0);
        });

        state.edges.forEach((edge) => {
            if (!children.has(edge.source) || !children.has(edge.target)) return;
            children.get(edge.source).push(edge.target);
            indegree.set(edge.target, (indegree.get(edge.target) || 0) + 1);
        });

        const roots = state.nodes.filter((node) => (indegree.get(node.id) || 0) === 0);

        function treeItem(node, depth) {
            const kids = (children.get(node.id) || []).map((id) => byId.get(id)).filter(Boolean);
            const kidHtml = kids.map((kid) => treeItem(kid, depth + 1)).join("");
            return `
                <li>
                    <button type="button" class="outline-tree-node" data-tree-node-id="${escapeHtml(node.id)}" style="--tree-depth:${depth}">
                        <span>${nodeTypeIcon(node.type)}</span>
                        <span>${escapeHtml(node.title)}</span>
                    </button>
                    ${kidHtml ? `<ul>${kidHtml}</ul>` : ""}
                </li>
            `;
        }

        treeViewEl.innerHTML = roots.length
            ? `<ul>${roots.map((root) => treeItem(root, 0)).join("")}</ul>`
            : '<p class="text-muted">暂无可展示的节点结构</p>';
    }

    function renderMinimap() {
        if (!minimapEl) return;
        if (!state.nodes.length) {
            minimapEl.innerHTML = "<span>无节点</span>";
            return;
        }

        const xs = state.nodes.map((node) => node.position.x);
        const ys = state.nodes.map((node) => node.position.y);
        const minX = Math.min(...xs);
        const minY = Math.min(...ys);
        const maxX = Math.max(...xs) + 232;
        const maxY = Math.max(...ys) + 116;
        const width = Math.max(1, maxX - minX);
        const height = Math.max(1, maxY - minY);
        const scale = Math.min(1, 150 / Math.max(width, height));

        const nodesHtml = state.nodes.map((node) => {
            const x = (node.position.x - minX) * scale;
            const y = (node.position.y - minY) * scale;
            return `<span class="outline-minimap-node" style="left:${x}px;top:${y}px;background:${escapeHtml(node.data.color_tag)}"></span>`;
        }).join("");

        const viewWidth = canvasEl.clientWidth / state.viewport.scale;
        const viewHeight = canvasEl.clientHeight / state.viewport.scale;
        const viewLeft = (-state.viewport.x / state.viewport.scale - minX) * scale;
        const viewTop = (-state.viewport.y / state.viewport.scale - minY) * scale;

        const frameWidth = Math.ceil(width * scale);
        const frameHeight = Math.ceil(height * scale);
        const rawViewportWidth = viewWidth * scale;
        const rawViewportHeight = viewHeight * scale;
        const viewportWidth = clamp(rawViewportWidth, 8, frameWidth);
        const viewportHeight = clamp(rawViewportHeight, 8, frameHeight);
        const viewportLeft = clamp(viewLeft, 0, Math.max(frameWidth - viewportWidth, 0));
        const viewportTop = clamp(viewTop, 0, Math.max(frameHeight - viewportHeight, 0));

        minimapEl.innerHTML = `
            <div class="outline-minimap-frame" style="width:${frameWidth}px;height:${frameHeight}px;">
                ${nodesHtml}
                <span class="outline-minimap-viewport" style="left:${viewportLeft}px;top:${viewportTop}px;width:${viewportWidth}px;height:${viewportHeight}px;"></span>
            </div>
        `;
    }

    function renderLegend() {
        legendListEl.innerHTML = (state.legend || []).map((item, idx) => `
            <div class="outline-legend-row" data-legend-idx="${idx}">
                <input type="color" value="${escapeHtml(item.color || '#ef4444')}" data-legend-color>
                <input type="text" value="${escapeHtml(item.meaning || '')}" maxlength="40" placeholder="这条颜色代表什么" data-legend-meaning>
                <button type="button" data-legend-remove>×</button>
            </div>
        `).join("");
    }

    function renderTimelineSelect() {
        timelineSelectEl.innerHTML = state.timelines.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join("");
        timelineSelectEl.value = state.active_timeline_id;
        parallelViewBtn.classList.toggle("active", state.parallel_view);
        modeFreeBtn.classList.toggle("active", state.mode === "free");
        modeTimelineBtn.classList.toggle("active", state.mode === "timeline");
    }

    function repopulateReferenceSelects() {
        nodeChapterInput.innerHTML = ['<option value="">未关联</option>']
            .concat(chapters.map((item) => `<option value="${item.id}">第 ${item.order} 章 · ${escapeHtml(item.title)}</option>`))
            .join("");

        nodeCharacterInput.innerHTML = ['<option value="">未关联</option>']
            .concat(characters.map((item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`))
            .join("");

        nodeAnchorInput.innerHTML = ['<option value="">未锚定</option>']
            .concat(getSortedAnchors().map((item) => `<option value="${item.id}">${escapeHtml(item.label)}</option>`))
            .join("");
    }

    function syncChapterNodeState() {
        const chapterMap = new Map(chapters.map((item) => [item.id, item]));
        state.nodes.forEach((node) => {
            if (node.type !== "chapter") return;
            if (!node.data.chapter_id) {
                node.data.missing_chapter = false;
                return;
            }
            const chapter = chapterMap.get(node.data.chapter_id);
            node.data.missing_chapter = !chapter;
            if (chapter && (!node.title || node.title === "章节节点" || node.title.includes("章节已丢失"))) {
                node.title = chapter.title;
            }
        });
    }

    function syncSelectionForms() {
        const selectedNode = selection.kind === "node" ? state.nodes.find((item) => item.id === selection.id) : null;
        const selectedEdge = selection.kind === "edge" ? state.edges.find((item) => item.id === selection.id) : null;

        emptySelectionEl.hidden = Boolean(selectedNode || selectedEdge);
        nodeForm.hidden = !selectedNode;
        edgeForm.hidden = !selectedEdge;

        if (selectedNode) {
            nodeTitleInput.value = selectedNode.title || "";
            nodeTypeInput.value = selectedNode.type || "plot";
            nodeColorInput.value = selectedNode.data.color_tag || "#16324f";
            nodeDescriptionInput.value = selectedNode.data.description || "";
            nodeTagsInput.value = (selectedNode.data.tags || []).join(", ");
            nodeChapterInput.value = selectedNode.data.chapter_id ? String(selectedNode.data.chapter_id) : "";
            nodeCharacterInput.value = selectedNode.data.character_id ? String(selectedNode.data.character_id) : "";
            nodeAnchorInput.value = selectedNode.data.anchor_id || "";
            openChapterBtn.disabled = !selectedNode.data.chapter_id;
        }

        if (selectedEdge) {
            edgeColorInput.value = selectedEdge.data.color || "#ef4444";
            edgeStyleInput.value = selectedEdge.data.line_style || "solid";
            edgeWidthInput.value = String(selectedEdge.data.width || 2);
            edgeArrowInput.value = selectedEdge.data.arrow || "forward";
            edgeLabelInput.value = selectedEdge.data.label || "";
        }
    }

    function renderAll() {
        activeAnchorPositions = timelineAnchorPositions();
        applyViewport();
        renderTimelineSelect();
        repopulateReferenceSelects();
        renderTimelineLayer();
        renderNodes();
        renderEdges();
        renderTreeView();
        renderMinimap();
        renderLegend();
        syncSelectionForms();
        layoutEl.classList.toggle("is-sidepanel-collapsed", sidepanelEl.hidden);
    }

    async function fetchJson(url, init = {}) {
        const response = typeof fetchWithAuthRetry === "function"
            ? await fetchWithAuthRetry(url, init)
            : await fetch(url, init);
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || "请求失败");
        return data;
    }

    async function loadReferences() {
        const [chapterRes, characterRes] = await Promise.all([
            fetchJson(`/api/chapters/?novel=${workspaceId}&ordering=order`),
            fetchJson(`/api/characters/?novel=${workspaceId}`),
        ]);
        chapters = Array.isArray(chapterRes) ? chapterRes : (chapterRes.results || []);
        characters = Array.isArray(characterRes) ? characterRes : (characterRes.results || []);
        syncChapterNodeState();
    }

    function scheduleAutosave() {
        if (autosaveTimer) clearTimeout(autosaveTimer);
        autosaveTimer = setTimeout(() => {
            saveCanvas(false).catch((error) => setStatus(`自动保存失败：${error.message || '未知错误'}`, true));
        }, 900);
    }

    async function saveCanvas(manual = true) {
        const payload = {
            outline_canvas: {
                nodes: state.nodes,
                edges: state.edges,
                groups: state.groups,
                legend: state.legend,
                viewport: state.viewport,
                mode: state.mode,
                active_timeline_id: state.active_timeline_id,
                parallel_view: state.parallel_view,
                timelines: state.timelines,
            },
        };
        setStatus(manual ? "保存中..." : "自动保存中...");
        await fetchJson(`/api/workspaces/${workspaceId}/`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        setStatus(manual ? "大纲已保存" : `自动保存 ${new Date().toLocaleTimeString('zh-CN', { hour12: false })}`);
    }

    function selectedNode() {
        if (selection.kind !== "node") return null;
        return state.nodes.find((item) => item.id === selection.id) || null;
    }

    function selectedEdge() {
        if (selection.kind !== "edge") return null;
        return state.edges.find((item) => item.id === selection.id) || null;
    }

    function createNode(type, x, y) {
        return {
            id: genId("node"),
            type,
            title: type === "chapter" ? "章节节点" : type === "character" ? "人物节点" : type === "note" ? "注释" : "情节点",
            position: { x, y },
            data: {
                chapter_id: null,
                character_id: null,
                timeline_id: state.mode === "timeline" ? state.active_timeline_id : null,
                anchor_id: null,
                color_tag: type === "chapter" ? "#2563eb" : type === "character" ? "#059669" : type === "note" ? "#7c3aed" : "#16324f",
                collapsed: false,
                description: "",
                tags: [],
                missing_chapter: false,
            },
        };
    }

    function selectNodeById(nodeId) {
        selection = { kind: "node", id: nodeId };
        renderAll();
    }

    function selectEdgeById(edgeId) {
        selection = { kind: "edge", id: edgeId };
        renderAll();
    }

    function clearSelection() {
        selection = { kind: null, id: null };
        renderAll();
    }

    function autoLayout() {
        if (state.mode === "timeline") {
            const byAnchor = new Map();
            state.nodes.forEach((node) => {
                const key = node.data.anchor_id || "unanchored";
                if (!byAnchor.has(key)) byAnchor.set(key, []);
                byAnchor.get(key).push(node);
            });
            [...byAnchor.values()].forEach((nodes) => {
                nodes.forEach((node, idx) => {
                    node.position.y = 120 + idx * 130;
                    ensureTimelineNodeAlignment(node);
                });
            });
            return;
        }

        const byType = { chapter: [], plot: [], character: [], note: [] };
        state.nodes.forEach((node) => (byType[node.type] || byType.plot).push(node));
        ["chapter", "plot", "character", "note"].forEach((type, col) => {
            byType[type].forEach((node, idx) => {
                node.position.x = 80 + col * 300;
                node.position.y = 80 + idx * 150;
            });
        });
    }

    function exportJson() {
        const blob = new Blob([JSON.stringify({
            nodes: state.nodes,
            edges: state.edges,
            groups: state.groups,
            legend: state.legend,
            viewport: state.viewport,
            mode: state.mode,
            active_timeline_id: state.active_timeline_id,
            parallel_view: state.parallel_view,
            timelines: state.timelines,
        }, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `storyline-${workspaceId}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    function openContextMenu(items, x, y) {
        contextMenu.innerHTML = items.map((item) => `<button type="button" data-menu-action="${item.action}">${escapeHtml(item.label)}</button>`).join("");
        contextMenu.style.left = `${x}px`;
        contextMenu.style.top = `${y}px`;
        contextMenu.hidden = false;
    }

    function closeContextMenu() {
        contextMenu.hidden = true;
    }

    function onCreateNode(type, x, y) {
        mutate(() => {
            const node = createNode(type, x, y);
            state.nodes.push(node);
            selection = { kind: "node", id: node.id };
        });
        setStatus(`已创建${nodeTypeLabel(type)}`);
    }

    function deleteSelection() {
        if (selection.kind === "node") {
            const id = selection.id;
            mutate(() => {
                state.nodes = state.nodes.filter((item) => item.id !== id);
                state.edges = state.edges.filter((item) => item.source !== id && item.target !== id);
                selection = { kind: null, id: null };
            });
            return;
        }
        if (selection.kind === "edge") {
            const id = selection.id;
            mutate(() => {
                state.edges = state.edges.filter((item) => item.id !== id);
                selection = { kind: null, id: null };
            });
        }
    }

    function beginConnect(sourceId, clientX, clientY) {
        const world = screenToWorld(clientX - canvasEl.getBoundingClientRect().left, clientY - canvasEl.getBoundingClientRect().top);
        connecting = { sourceId, worldX: world.x, worldY: world.y };
        renderEdges();
    }

    function updateConnect(clientX, clientY) {
        if (!connecting) return;
        const rect = canvasEl.getBoundingClientRect();
        const world = screenToWorld(clientX - rect.left, clientY - rect.top);
        connecting.worldX = world.x;
        connecting.worldY = world.y;
        renderEdges();
    }

    function finishConnect(targetNodeId) {
        if (!connecting?.sourceId || !targetNodeId || connecting.sourceId === targetNodeId) {
            connecting = null;
            renderEdges();
            return;
        }
        if (state.edges.some((edge) => edge.source === connecting.sourceId && edge.target === targetNodeId)) {
            connecting = null;
            renderEdges();
            return;
        }
        mutate(() => {
            state.edges.push({
                id: genId("edge"),
                source: connecting.sourceId,
                target: targetNodeId,
                data: { color: "#ef4444", line_style: "solid", width: 2, arrow: "forward", label: "" },
            });
        });
        connecting = null;
    }

    function startPan(clientX, clientY) {
        panning = { startX: clientX, startY: clientY, originX: state.viewport.x, originY: state.viewport.y };
        canvasEl.classList.add("is-panning");
    }

    function updatePan(clientX, clientY) {
        if (!panning) return;
        const dx = clientX - panning.startX;
        const dy = clientY - panning.startY;
        state.viewport.x = panning.originX + dx;
        state.viewport.y = panning.originY + dy;
        applyViewport();
        renderEdges();
        renderMinimap();
    }

    function stopPan() {
        if (!panning) return;
        panning = null;
        canvasEl.classList.remove("is-panning");
        pushHistorySnapshot();
        scheduleAutosave();
    }

    function startNodeDrag(nodeId, clientX, clientY) {
        const node = state.nodes.find((item) => item.id === nodeId);
        if (!node) return;
        const rect = canvasEl.getBoundingClientRect();
        const world = screenToWorld(clientX - rect.left, clientY - rect.top);
        dragging = {
            type: "node",
            nodeId,
            offsetX: world.x - node.position.x,
            offsetY: world.y - node.position.y,
            lockX: state.mode === "timeline" && Boolean(node.data.anchor_id),
        };
    }

    function maybeSnapNodeToAnchor(node) {
        if (state.mode !== "timeline") return;
        if (!activeAnchorPositions.length) return;

        const centerX = node.position.x + 116;
        const nearest = activeAnchorPositions
            .map((anchor) => ({ anchor, distance: Math.abs(anchor.x - centerX) }))
            .sort((a, b) => a.distance - b.distance)[0];

        if (nearest && nearest.distance <= 48) {
            node.data.timeline_id = state.active_timeline_id;
            node.data.anchor_id = nearest.anchor.id;
            node.position.x = Math.round(nearest.anchor.x - 116);
            return;
        }

        if (centerX < 96) {
            node.data.anchor_id = null;
            node.data.timeline_id = state.active_timeline_id;
            node.position.x = 16;
        }
    }

    function updateDrag(clientX, clientY) {
        if (!dragging) return;

        if (dragging.type === "node") {
            const node = state.nodes.find((item) => item.id === dragging.nodeId);
            if (!node) return;
            const rect = canvasEl.getBoundingClientRect();
            const world = screenToWorld(clientX - rect.left, clientY - rect.top);
            if (!dragging.lockX) {
                node.position.x = Math.round(world.x - dragging.offsetX);
            }
            node.position.y = Math.round(world.y - dragging.offsetY);

            const laneMinY = nodeLaneY(node);
            if (laneMinY !== null) {
                node.position.y = clamp(node.position.y, laneMinY, laneMinY + 170);
            }

            if (state.mode === "timeline" && !dragging.lockX) {
                maybeSnapNodeToAnchor(node);
            }

            renderNodes();
            renderEdges();
            renderMinimap();
            return;
        }

        if (dragging.type === "anchor") {
            const timeline = getActiveTimeline();
            const anchor = timeline?.anchors.find((item) => item.id === dragging.anchorId);
            if (!anchor) return;

            const rect = canvasEl.getBoundingClientRect();
            const localX = clientX - rect.left;
            const left = 72;
            const right = Math.max(left + 40, canvasEl.clientWidth - 72);
            const ratio = clamp((localX - left) / Math.max(right - left, 1), 0, 1);

            const anchors = getSortedAnchors();
            const orders = anchors.map((item) => item.order);
            const minOrder = Math.min(...orders, 0);
            const maxOrder = Math.max(...orders, 100 * Math.max(anchors.length, 1));
            anchor.order = Math.round(minOrder + ratio * Math.max(maxOrder - minOrder, 1));

            renderAll();
        }
    }

    function stopDrag() {
        if (!dragging) return;
        dragging = null;
        pushHistorySnapshot();
        scheduleAutosave();
    }

    function startAnchorDrag(anchorId) {
        dragging = { type: "anchor", anchorId };
    }

    function createAnchorByClick(clientX) {
        const timeline = getActiveTimeline();
        if (!timeline) return;

        const rect = canvasEl.getBoundingClientRect();
        const localX = clientX - rect.left;
        const left = 72;
        const right = Math.max(left + 40, canvasEl.clientWidth - 72);
        const ratio = clamp((localX - left) / Math.max(right - left, 1), 0, 1);

        const existingOrders = timeline.anchors.map((item) => item.order);
        const minOrder = existingOrders.length ? Math.min(...existingOrders) : 0;
        const maxOrder = existingOrders.length ? Math.max(...existingOrders) : 100;
        const order = Math.round(minOrder + ratio * Math.max(maxOrder - minOrder || 100, 100));

        const label = window.prompt("请输入时间锚点名称", `时间点 ${timeline.anchors.length + 1}`);
        if (!label) return;

        mutate(() => {
            timeline.anchors.push({
                id: genId("anchor"),
                label: label.trim(),
                order,
                color: timeline.color || "#ef4444",
            });
        }, { pruneDanglingEdges: false });
    }

    function escapeHtml(value) {
        return String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function setViewMode(isTree) {
        showTreeView = isTree;
        layoutEl.dataset.viewMode = isTree ? "tree" : "canvas";
        treeViewEl.hidden = !isTree;
        canvasEl.hidden = isTree;
        viewCanvasBtn.classList.toggle("active", !isTree);
        viewTreeBtn.classList.toggle("active", isTree);
    }

    function toggleSidepanel() {
        sidepanelEl.hidden = !sidepanelEl.hidden;
        sidepanelToggleBtn.textContent = sidepanelEl.hidden ? "展开工具栏" : "收起工具栏";
        layoutEl.classList.toggle("is-sidepanel-collapsed", sidepanelEl.hidden);
    }

    document.querySelectorAll("[data-outline-create]").forEach((btn) => {
        btn.addEventListener("click", () => {
            const type = btn.dataset.outlineCreate || "plot";
            const world = screenToWorld(canvasEl.clientWidth * 0.42, canvasEl.clientHeight * 0.35);
            onCreateNode(type, Math.round(world.x), Math.round(world.y));
        });
    });

    if (createFromChapterBtn) {
        createFromChapterBtn.addEventListener("click", () => {
            if (!chapters.length) {
                setStatus("当前工作区还没有章节", true);
                return;
            }
            const lines = chapters.map((item, idx) => `${idx + 1}. 第 ${item.order} 章 · ${item.title}`);
            const picked = window.prompt(`输入章节序号：\n${lines.join("\n")}`, "1");
            const chapter = chapters[Number(picked) - 1];
            if (!chapter) return;
            mutate(() => {
                const world = screenToWorld(canvasEl.clientWidth * 0.42, canvasEl.clientHeight * 0.3);
                const node = createNode("chapter", Math.round(world.x), Math.round(world.y));
                node.title = chapter.title;
                node.data.chapter_id = chapter.id;
                state.nodes.push(node);
                selection = { kind: "node", id: node.id };
            });
        });
    }

    if (createFromCharacterBtn) {
        createFromCharacterBtn.addEventListener("click", () => {
            if (!characters.length) {
                setStatus("当前工作区还没有人物", true);
                return;
            }
            const lines = characters.map((item, idx) => `${idx + 1}. ${item.name}`);
            const picked = window.prompt(`输入人物序号：\n${lines.join("\n")}`, "1");
            const character = characters[Number(picked) - 1];
            if (!character) return;
            mutate(() => {
                const world = screenToWorld(canvasEl.clientWidth * 0.45, canvasEl.clientHeight * 0.34);
                const node = createNode("character", Math.round(world.x), Math.round(world.y));
                node.title = character.name;
                node.data.character_id = character.id;
                state.nodes.push(node);
                selection = { kind: "node", id: node.id };
            });
        });
    }

    sidepanelToggleBtn?.addEventListener("click", toggleSidepanel);

    timelineSelectEl.addEventListener("change", () => {
        mutate(() => {
            state.active_timeline_id = timelineSelectEl.value;
        }, { pruneDanglingEdges: false });
    });

    addTimelineBtn.addEventListener("click", () => {
        const name = window.prompt("请输入新时间轴名称", `时间轴 ${state.timelines.length + 1}`);
        if (!name) return;
        mutate(() => {
            const id = genId("timeline");
            state.timelines.push({ id, name: name.trim(), color: "#ef4444", anchors: [] });
            state.active_timeline_id = id;
        }, { pruneDanglingEdges: false });
    });

    parallelViewBtn.addEventListener("click", () => {
        mutate(() => {
            state.parallel_view = !state.parallel_view;
        }, { pruneDanglingEdges: false });
    });

    modeFreeBtn.addEventListener("click", () => {
        mutate(() => { state.mode = "free"; }, { pruneDanglingEdges: false });
    });

    modeTimelineBtn.addEventListener("click", () => {
        if (state.mode !== "timeline" && state.nodes.some((node) => !node.data.anchor_id)) {
            window.alert("已切换到时间轴模式：未绑定时间的节点将保留在未锚定区。双击标尺可创建锚点。");
        }
        mutate(() => { state.mode = "timeline"; }, { pruneDanglingEdges: false });
    });

    timelineRulerEl.addEventListener("dblclick", (event) => {
        if (state.mode !== "timeline") {
            mutate(() => { state.mode = "timeline"; }, { pruneDanglingEdges: false });
        }
        createAnchorByClick(event.clientX);
    });

    timelineRulerEl.addEventListener("mousedown", (event) => {
        const anchorEl = event.target.closest(".outline-anchor");
        if (!anchorEl) return;
        event.preventDefault();
        startAnchorDrag(anchorEl.dataset.anchorId);
    });

    timelineRulerEl.addEventListener("contextmenu", (event) => {
        const anchorEl = event.target.closest(".outline-anchor");
        if (!anchorEl) return;
        event.preventDefault();
        const anchorId = anchorEl.dataset.anchorId;
        openContextMenu([
            { action: `anchor:rename:${anchorId}`, label: "重命名锚点" },
            { action: `anchor:delete:${anchorId}`, label: "删除锚点" },
        ], event.clientX, event.clientY);
    });

    unanchoredListEl.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-unanchored-node]");
        if (!btn) return;
        selectNodeById(btn.dataset.unanchoredNode);
    });

    canvasEl.addEventListener("mousedown", (event) => {
        closeContextMenu();

        const isMiddle = event.button === 1;
        const canPanBySpace = event.button === 0 && spacePressed;
        if (isMiddle || canPanBySpace) {
            event.preventDefault();
            startPan(event.clientX, event.clientY);
            return;
        }

        if (event.button !== 0) return;

        const handle = event.target.closest(".outline-node-handle");
        if (handle && handle.dataset.handle === "out") {
            const nodeEl = event.target.closest(".outline-node");
            if (nodeEl) {
                beginConnect(nodeEl.dataset.nodeId, event.clientX, event.clientY);
                event.preventDefault();
            }
            return;
        }

        const nodeEl = event.target.closest(".outline-node");
        if (nodeEl) {
            const nodeId = nodeEl.dataset.nodeId;
            selectNodeById(nodeId);
            startNodeDrag(nodeId, event.clientX, event.clientY);
            return;
        }

        const edgePathEl = event.target.closest(".outline-edge");
        if (edgePathEl) {
            selectEdgeById(edgePathEl.dataset.edgeId);
            return;
        }

        if (event.button === 0) {
            clearSelection();
            startPan(event.clientX, event.clientY);
        }
    });

    canvasEl.addEventListener("contextmenu", (event) => {
        event.preventDefault();
        if (!contextMenu.hidden && !event.target.closest(".outline-node")) {
            closeContextMenu();
            return;
        }
        const rect = canvasEl.getBoundingClientRect();
        const world = screenToWorld(event.clientX - rect.left, event.clientY - rect.top);

        const nodeEl = event.target.closest(".outline-node");
        if (nodeEl) {
            const nodeId = nodeEl.dataset.nodeId;
            selectNodeById(nodeId);
            openContextMenu([
                { action: `delete:${nodeId}`, label: "删除节点" },
                { action: `copy:${nodeId}`, label: "复制节点" },
            ], event.clientX, event.clientY);
            return;
        }

        openContextMenu([
            { action: `create:chapter:${world.x}:${world.y}`, label: "新建章节节点" },
            { action: `create:plot:${world.x}:${world.y}`, label: "新建情节点" },
            { action: `create:character:${world.x}:${world.y}`, label: "新建人物节点" },
            { action: `create:note:${world.x}:${world.y}`, label: "新建注释节点" },
        ], event.clientX, event.clientY);
    });

    contextMenu.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-menu-action]");
        if (!btn) return;
        const action = btn.dataset.menuAction || "";

        try {
            if (action.startsWith("create:")) {
                const [, type, x, y] = action.split(":");
                onCreateNode(type, Math.round(Number(x) || 0), Math.round(Number(y) || 0));
            } else if (action.startsWith("delete:")) {
                const [, nodeId] = action.split(":");
                selection = { kind: "node", id: nodeId };
                deleteSelection();
            } else if (action.startsWith("copy:")) {
                const [, nodeId] = action.split(":");
                const node = state.nodes.find((item) => item.id === nodeId);
                if (node) clipboardNode = clone(node);
            } else if (action.startsWith("anchor:rename:")) {
                const [, , , anchorId] = action.split(":");
                const timeline = getActiveTimeline();
                const anchor = timeline?.anchors.find((item) => item.id === anchorId);
                if (anchor) {
                    const next = window.prompt("锚点名称", anchor.label);
                    if (next) {
                        mutate(() => { anchor.label = next.trim(); }, { pruneDanglingEdges: false });
                    }
                }
            } else if (action.startsWith("anchor:delete:")) {
                const [, , , anchorId] = action.split(":");
                mutate(() => {
                    const timeline = getActiveTimeline();
                    if (!timeline) return;
                    timeline.anchors = timeline.anchors.filter((item) => item.id !== anchorId);
                    state.nodes.forEach((node) => {
                        if (node.data.anchor_id === anchorId) node.data.anchor_id = null;
                    });
                }, { pruneDanglingEdges: false });
            }
        } finally {
            closeContextMenu();
        }
    });

    document.addEventListener("pointerdown", (event) => {
        if (contextMenu.hidden) return;
        if (contextMenu.contains(event.target)) return;
        closeContextMenu();
    }, true);

    document.addEventListener("click", (event) => {
        if (!contextMenu.hidden && !contextMenu.contains(event.target)) closeContextMenu();
    });

    document.addEventListener("contextmenu", (event) => {
        if (!contextMenu.hidden && !event.target.closest("#outline-canvas") && !contextMenu.contains(event.target)) {
            closeContextMenu();
        }
    });

    document.addEventListener("wheel", () => {
        if (!contextMenu.hidden) closeContextMenu();
    }, { passive: true, capture: true });

    window.addEventListener("blur", closeContextMenu);

    canvasEl.addEventListener("wheel", (event) => {
        event.preventDefault();
        const rect = canvasEl.getBoundingClientRect();
        const cursorX = event.clientX - rect.left;
        const cursorY = event.clientY - rect.top;

        const worldBefore = screenToWorld(cursorX, cursorY);
        const factor = event.deltaY > 0 ? 0.92 : 1.08;
        state.viewport.scale = clamp(state.viewport.scale * factor, 0.35, 2.4);

        const after = worldToScreen(worldBefore.x, worldBefore.y);
        state.viewport.x += cursorX - after.x;
        state.viewport.y += cursorY - after.y;

        applyViewport();
        renderEdges();
        renderMinimap();
        scheduleAutosave();
    }, { passive: false });

    document.addEventListener("mousemove", (event) => {
        if (connecting) updateConnect(event.clientX, event.clientY);
        if (dragging) updateDrag(event.clientX, event.clientY);
        if (panning) updatePan(event.clientX, event.clientY);
    });

    document.addEventListener("mouseup", (event) => {
        if (connecting) {
            const targetHandle = event.target.closest(".outline-node-handle.in");
            const targetNode = targetHandle?.closest(".outline-node");
            finishConnect(targetNode?.dataset.nodeId || null);
        }
        if (dragging || panning) stopDrag();
        if (panning) stopPan();
    });

    treeViewEl.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-tree-node-id]");
        if (!btn) return;
        setViewMode(false);
        selectNodeById(btn.dataset.treeNodeId);
    });

    nodeForm.addEventListener("input", () => {
        const node = selectedNode();
        if (!node) return;
        mutate(() => {
            node.title = nodeTitleInput.value.trim() || nodeTypeLabel(node.type);
            node.type = nodeTypeInput.value;
            node.data.color_tag = nodeColorInput.value;
            node.data.description = nodeDescriptionInput.value;
            node.data.tags = nodeTagsInput.value.split(",").map((item) => item.trim()).filter(Boolean);
            node.data.chapter_id = nodeChapterInput.value ? Number(nodeChapterInput.value) : null;
            node.data.character_id = nodeCharacterInput.value ? Number(nodeCharacterInput.value) : null;
            node.data.anchor_id = nodeAnchorInput.value || null;
            if (state.mode === "timeline") {
                node.data.timeline_id = state.active_timeline_id;
                ensureTimelineNodeAlignment(node);
            }

            if (node.type === "chapter") {
                const chapter = chapters.find((item) => item.id === node.data.chapter_id);
                if (chapter && (node.title === "章节节点" || !nodeTitleInput.value.trim())) node.title = chapter.title;
            }
        }, { pruneDanglingEdges: false });
    });

    edgeForm.addEventListener("input", () => {
        const edge = selectedEdge();
        if (!edge) return;
        mutate(() => {
            edge.data.color = edgeColorInput.value;
            edge.data.line_style = edgeStyleInput.value;
            edge.data.width = Number(edgeWidthInput.value || 2);
            edge.data.arrow = edgeArrowInput.value;
            edge.data.label = edgeLabelInput.value.trim();
        }, { pruneDanglingEdges: false });
    });

    openChapterBtn.addEventListener("click", () => {
        const node = selectedNode();
        if (!node?.data.chapter_id) return;
        window.open(`/workspace/${workspaceId}/writing/?chapter_id=${node.data.chapter_id}`, "_blank");
    });

    createChapterBindBtn.addEventListener("click", async () => {
        const node = selectedNode();
        if (!node) return;
        const title = window.prompt("请输入新章节标题", node.title || "新章节");
        if (!title) return;

        try {
            const nextOrder = (chapters.length ? Math.max(...chapters.map((item) => Number(item.order) || 0)) : 0) + 1;
            const created = await fetchJson("/api/chapters/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ novel: workspaceId, title: title.trim(), content_md: "", order: nextOrder, is_published: false }),
            });

            await loadReferences();
            mutate(() => {
                node.data.chapter_id = Number(created.id);
                node.type = "chapter";
                node.title = created.title;
            }, { pruneDanglingEdges: false });
            setStatus("已创建并绑定章节");
        } catch (error) {
            setStatus(`创建章节失败：${error.message || '未知错误'}`, true);
        }
    });

    saveBtn.addEventListener("click", () => {
        saveCanvas(true).catch((error) => setStatus(`保存失败：${error.message || '未知错误'}`, true));
    });

    autoLayoutBtn.addEventListener("click", () => {
        mutate(() => {
            autoLayout();
        });
        setStatus("已整理节点布局");
    });

    exportBtn.addEventListener("click", exportJson);

    addLegendBtn.addEventListener("click", () => {
        mutate(() => {
            state.legend.push({ color: "#ef4444", meaning: "新图例" });
        }, { pruneDanglingEdges: false });
    });

    legendListEl.addEventListener("input", (event) => {
        const row = event.target.closest("[data-legend-idx]");
        if (!row) return;
        const idx = Number(row.dataset.legendIdx);
        if (!Number.isFinite(idx) || !state.legend[idx]) return;
        mutate(() => {
            const color = row.querySelector("[data-legend-color]")?.value || "#ef4444";
            const meaning = row.querySelector("[data-legend-meaning]")?.value || "";
            state.legend[idx].color = color;
            state.legend[idx].meaning = meaning;
        }, { pruneDanglingEdges: false });
    });

    legendListEl.addEventListener("click", (event) => {
        const removeBtn = event.target.closest("[data-legend-remove]");
        if (!removeBtn) return;
        const row = removeBtn.closest("[data-legend-idx]");
        const idx = Number(row?.dataset.legendIdx);
        if (!Number.isFinite(idx)) return;
        mutate(() => {
            state.legend.splice(idx, 1);
        }, { pruneDanglingEdges: false });
    });

    searchInput.addEventListener("input", () => {
        searchKeyword = searchInput.value.trim();
        renderAll();
    });

    filterTypeInput.addEventListener("change", () => {
        filterType = filterTypeInput.value;
        renderAll();
    });

    viewCanvasBtn.addEventListener("click", () => setViewMode(false));
    viewTreeBtn.addEventListener("click", () => setViewMode(true));

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !contextMenu.hidden) {
            closeContextMenu();
            return;
        }

        if (event.key === " ") {
            spacePressed = true;
            canvasEl.classList.add("is-space-pan");
        }

        if ((event.key === "Backspace" || event.key === "Delete") && selection.kind) {
            const activeTag = (document.activeElement?.tagName || "").toUpperCase();
            if (activeTag === "INPUT" || activeTag === "TEXTAREA" || activeTag === "SELECT") return;
            event.preventDefault();
            deleteSelection();
            return;
        }

        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
            event.preventDefault();
            if (event.shiftKey) redo(); else undo();
            return;
        }

        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "y") {
            event.preventDefault();
            redo();
            return;
        }

        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "c") {
            const node = selectedNode();
            if (!node) return;
            clipboardNode = clone(node);
            setStatus("节点已复制");
            return;
        }

        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "v") {
            if (!clipboardNode) return;
            event.preventDefault();
            mutate(() => {
                const pasted = clone(clipboardNode);
                pasted.id = genId("node");
                pasted.position.x += 40;
                pasted.position.y += 40;
                pasted.title = `${pasted.title} (副本)`;
                state.nodes.push(pasted);
                selection = { kind: "node", id: pasted.id };
            });
            setStatus("节点已粘贴");
        }
    });

    document.addEventListener("keyup", (event) => {
        if (event.key === " ") {
            spacePressed = false;
            canvasEl.classList.remove("is-space-pan");
        }
    });

    window.addEventListener("resize", () => {
        renderAll();
    });

    Promise.resolve()
        .then(() => loadReferences())
        .then(() => {
            pushHistorySnapshot();
            renderAll();
            setStatus("故事线工作台已就绪");
        })
        .catch((error) => {
            pushHistorySnapshot();
            renderAll();
            setStatus(`初始化失败：${error.message || '未知错误'}`, true);
        });
});
