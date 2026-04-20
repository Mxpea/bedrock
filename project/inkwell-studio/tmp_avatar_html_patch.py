import re

file_path = 'f:/WORKSPACE/bedrock/project/inkwell-studio/templates/author_profile.html'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

find_str = '''            <div class="author-homepage-avatar" {% if homepage_config.avatar %}style="background-image: url('{{ homepage_config.avatar.url }}'); background-size: cover; background-position: center;"{% endif %}>'''

replace_str = '''            <div class="author-homepage-avatar" {% if homepage_config.avatar %}style="background-image: url('{{ homepage_config.avatar.url }}'); background-size: cover; background-position: center; width: 96px; height: 96px; border-radius: 999px; border: 4px solid #fff; flex-shrink: 0;"{% endif %}>'''

if find_str in text:
    text = text.replace(find_str, replace_str)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print("Avatar HTML patched.")
else:
    print("Could not find the target string to replace.")
