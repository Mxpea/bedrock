import re

with open('f:/WORKSPACE/bedrock/project/inkwell-studio/templates/author_profile.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update JS rendering for Works
new_returns = r"""        return '<div class="homepage-work-grid">' + list.map((item) =>
            '<article class="homepage-work-card">' +
            '<div class="card-head">' +
            '<div class="card-title-group">' +
            '<img src="' + (item.cover_url || '/static/images/default-cover.png') + '" class="card-cover" alt="" onerror="this.src=\'/static/images/default-cover.png\';this.onerror=null;">' +
            '<div class="card-title-info">' +
            '<span class="card-label">WORKSPACE</span>' +
            '<h4><a href="' + item.read_url + '">' + item.title + '</a></h4>' +
            '</div>' +
            '</div>' +
            '<span class="card-badge">公开</span>' +
            '</div>' +
            '<p class="card-summary">' + (item.summary || '暂无简介') + '</p>' +
            '<p class="card-time">更新于 ' + formatDate(item.updated_at) + '</p>' +
            '<div class="card-actions">' +
            '<a class="card-btn primary" href="' + item.read_url + '">阅读</a>' +
            '<a class="card-btn secondary" href="/ws/' + item.slug + '/">进入工作区</a>' +
            '</div>' +
            '</article>'
        ).join('') + '</div>';"""

text = re.sub(
    r"""        return '<div class="homepage-work-grid">'.*?</article>'\n\s*\)\.join\(''\) \+ '</div>';""",
    new_returns,
    text,
    flags=re.DOTALL
)

# 2. Update CSS styles for the new works card
css_addition = r"""
.homepage-work-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 16px;
}

.homepage-work-card {
    border: 1px solid var(--line);
    border-radius: 20px;
    padding: 24px;
    background: #fff;
    display: flex;
    flex-direction: column;
    gap: 20px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.02);
}

.homepage-work-card .card-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
}

.homepage-work-card .card-title-group {
    display: flex;
    gap: 14px;
    align-items: center;
}

.homepage-work-card .card-cover {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    object-fit: cover;
    border: 1px solid var(--line);
    background: #f8fafc;
}

.homepage-work-card .card-title-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.homepage-work-card .card-label {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    color: var(--muted);
    text-transform: uppercase;
}

.homepage-work-card h4 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-main);
}

.homepage-work-card h4 a {
    color: inherit;
    text-decoration: none;
}

.homepage-work-card .card-badge {
    font-size: 1rem;
    color: var(--text-main);
    font-weight: 500;
}

.homepage-work-card .card-summary {
    margin: 0;
    font-size: 0.95rem;
    color: var(--text-main);
    line-height: 1.5;
    flex-grow: 1;
}

.homepage-work-card .card-time {
    margin: 0;
    font-size: 0.85rem;
    color: var(--text-light, #52525b);
}

.homepage-work-card .card-actions {
    display: flex;
    gap: 12px;
    margin-top: 4px;
}

.homepage-work-card .card-btn {
    display: inline-flex;
    justify-content: center;
    align-items: center;
    padding: 10px 24px;
    border-radius: 999px;
    font-size: 1rem;
    font-weight: 700;
    text-decoration: none;
    transition: all 0.2s ease;
    cursor: pointer;
}

.homepage-work-card .card-btn.primary {
    background: #183153;
    color: #fff;
    border: 1px solid #183153;
}

.homepage-work-card .card-btn.primary:hover {
    background: #102441;
}

.homepage-work-card .card-btn.secondary {
    background: #fff;
    color: var(--text-main);
    border: 1px solid #e2e8f0;
}

.homepage-work-card .card-btn.secondary:hover {
    background: #f8fafc;
    border-color: #cbd5e1;
}
"""

text = re.sub(r'\.homepage-work-grid {[\s\S]*?}\n\n\.homepage-work-item {[\s\S]*?}\n\n\.homepage-work-item p,', '.homepage-work-item p,', text)
text = text.replace('</style>', css_addition + '\n</style>')

with open('f:/WORKSPACE/bedrock/project/inkwell-studio/templates/author_profile.html', 'w', encoding='utf-8') as f:
    f.write(text)
