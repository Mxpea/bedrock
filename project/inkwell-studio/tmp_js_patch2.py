import re

file_path = 'f:/WORKSPACE/bedrock/project/inkwell-studio/templates/author_profile.html'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Make sure we add the el selectors
el_patch = '''
        headerInput: document.getElementById('ah-header-upload'),
        btnHeader: document.getElementById('ah-btn-upload-header'),
        avatarInput: document.getElementById('ah-avatar-upload'),
        btnAvatar: document.getElementById('ah-btn-upload-avatar'),
        removeModule: document.getElementById('ah-remove-module'),'''

text = text.replace("removeModule: document.getElementById('ah-remove-module'),", el_patch)

js_patch = '''
        // Image Upload Logic added here
        if (el.btnHeader) {
            el.btnHeader.addEventListener('click', async () => {
                if (!el.headerInput || !el.headerInput.files.length) {
                    setStatus('请先选择头图文件', true);
                    return;
                }
                const formData = new FormData();
                formData.append('header_image', el.headerInput.files[0]);

                try {
                    setStatus('上传头图中...');
                    el.btnHeader.disabled = true;
                    // API path mapped from viewset
                    const res = await fetch('/api/customization/homepage-configs/upload_header/', {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': csrftoken
                        },
                        body: formData
                    });
                    if (res.ok) {
                        setStatus('头图上传成功', false);
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        const errText = await res.text();
                        throw new Error(errText);
                    }
                } catch (err) {
                    console.error(err);
                    setStatus('上传失败: ' + err.message, true);
                } finally {
                    el.btnHeader.disabled = false;
                }
            });
        }

        if (el.btnAvatar) {
            el.btnAvatar.addEventListener('click', async () => {
                if (!el.avatarInput || !el.avatarInput.files.length) {
                    setStatus('请先选择头像文件', true);
                    return;
                }
                const formData = new FormData();
                formData.append('avatar', el.avatarInput.files[0]);

                try {
                    setStatus('上传头像中...');
                    el.btnAvatar.disabled = true;
                    const res = await fetch('/api/customization/homepage-configs/upload_avatar/', {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': csrftoken
                        },
                        body: formData
                    });
                    if (res.ok) {
                        setStatus('头像上传成功', false);
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        const errText = await res.text();
                        throw new Error(errText);
                    }
                } catch (err) {
                    console.error(err);
                    setStatus('上传失败: ' + err.message, true);
                } finally {
                    el.btnAvatar.disabled = false;
                }
            });
        }
'''

# insert js_patch right before "renderCanvas();"
find_str = '    renderCanvas();\n    syncSettings();'
if find_str in text and 'upload_header' not in text:
    text = text.replace(find_str, js_patch + '\n' + find_str)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print("JS Logic injected.")
else:
    print("Could not find the target string for JS logic.")
