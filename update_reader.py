import re

with open(r'f:\WORKSPACE\bedrock\project\inkwell-studio\templates\novels\reader.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace <a href="/novels/" class="nav-btn index">≡ 返回作品列表</a>
text = text.replace('<a href="/novels/" class="nav-btn index">≡ 返回作品列表</a>',
                    '<a href="{% url \'novel-detail-page\' chapter.novel.public_id %}" class="nav-btn index">≡ 返回章节目录</a>')

# And in the empty state
text = text.replace('<a href="/novels/" class="button primary">返回作品列表</a>',
                    '<a href="{% if chapter %}{% url \'novel-detail-page\' chapter.novel.public_id %}{% else %}/novels/{% endif %}" class="button primary">返回章节目录</a>')

with open(r'f:\WORKSPACE\bedrock\project\inkwell-studio\templates\novels\reader.html', 'w', encoding='utf-8') as f:
    f.write(text)
    
print("Updated reader.html")
