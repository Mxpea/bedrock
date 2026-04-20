import re

file_path = 'f:/WORKSPACE/bedrock/project/inkwell-studio/templates/author_profile.html'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

page_settings_html = '''
        <div class="ah-builder-section">
            <h4>页面设置</h4>
            <div class="ah-module-library">
                <div style="margin-bottom: 12px;">
                    <label class="label-text" style="display:block;margin-bottom:4px;">自定义背景图/头图</label>
                    <input type="file" id="ah-header-upload" accept="image/*" style="font-size:0.85rem;width:100%" />
                    <button type="button" id="ah-btn-upload-header" class="button neutral btn-sm" style="margin-top:6px;width:100%"><i class="ph ph-upload-simple"></i> 上传头图</button>
                </div>
                <div>
                    <label class="label-text" style="display:block;margin-bottom:4px;">自定义头像</label>
                    <input type="file" id="ah-avatar-upload" accept="image/*" style="font-size:0.85rem;width:100%" />
                    <button type="button" id="ah-btn-upload-avatar" class="button neutral btn-sm" style="margin-top:6px;width:100%"><i class="ph ph-upload-simple"></i> 上传头像</button>
                </div>
            </div>
        </div>
'''

find_str = '''        <div class="ah-builder-section">
            <h4>添加组件</h4>'''

if find_str in text and 'ah-header-upload' not in text:
    text = text.replace(find_str, page_settings_html + '\n' + find_str)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print("Page settings injected.")
else:
    print("Failed to inject.")
