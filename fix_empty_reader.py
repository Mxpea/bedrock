import re

with open(r'f:\WORKSPACE\bedrock\project\inkwell-studio\templates\novels\reader.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('<a class="nav-btn index" href="/novels/">前往作品列表</a>',
                    '<a class="nav-btn index" href="{% if chapter %}{% url \'novel-detail-page\' chapter.novel.public_id %}{% else %}/novels/{% endif %}">返回章节目录</a>')

with open(r'f:\WORKSPACE\bedrock\project\inkwell-studio\templates\novels\reader.html', 'w', encoding='utf-8') as f:
    f.write(text)
