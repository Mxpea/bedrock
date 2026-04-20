import re

file_path = 'f:/WORKSPACE/bedrock/project/inkwell-studio/templates/author_profile.html'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

find_header = '''    <section class="author-homepage-hero">
        <div class="author-homepage-cover"></div>'''

replace_header = '''    <section class="author-homepage-hero">
        <div class="author-homepage-cover" {% if homepage_config.header_image %}style="background-image: url('{{ homepage_config.header_image.url }}'); background-size: cover; background-position: center;"{% endif %}></div>'''

if find_header in text:
    text = text.replace(find_header, replace_header)
    print("Header replaced")

find_avatar = '''            <div class="author-homepage-avatar">
                <div class="author-homepage-avatar-fallback">{{ profile_user.username|make_list|first|upper }}</div>
            </div>'''

replace_avatar = '''            <div class="author-homepage-avatar" {% if homepage_config.avatar %}style="background-image: url('{{ homepage_config.avatar.url }}'); background-size: cover; background-position: center;"{% endif %}>
                {% if not homepage_config.avatar %}
                <div class="author-homepage-avatar-fallback">{{ profile_user.username|make_list|first|upper }}</div>
                {% endif %}
            </div>'''

if find_avatar in text:
    text = text.replace(find_avatar, replace_avatar)
    print("Avatar replaced")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
