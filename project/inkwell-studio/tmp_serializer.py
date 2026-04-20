import re

file_path = 'f:/WORKSPACE/bedrock/project/inkwell-studio/apps/customization/serializers.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

if '"header_image",' not in text:
    text = text.replace('"header_image_url",', '"header_image_url",\n            "header_image",')
if '"avatar",' not in text:
    text = text.replace('"avatar_url",', '"avatar_url",\n            "avatar",')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
