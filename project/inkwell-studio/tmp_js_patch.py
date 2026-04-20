import re

file_path = 'f:/WORKSPACE/bedrock/project/inkwell-studio/templates/author_profile.html'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

el_patch = '''        removeModule: document.getElementById('ah-remove-module'),
        headerInput: document.getElementById('ah-header-upload'),
        btnHeader: document.getElementById('ah-btn-upload-header'),
        avatarInput: document.getElementById('ah-avatar-upload'),
        btnAvatar: document.getElementById('ah-btn-upload-avatar'),'''

text = text.replace("removeModule: document.getElementById('ah-remove-module'),", el_patch)

js_patch = '''
        // Image Upload Logic
        if (el.btnHeader) {
            el.btnHeader.addEventListener('click', async () => {
                if (!el.headerInput.files.length) {
                    setStatus('请先选择头图文件', true);
                    return;
                }
                const formData = new FormData();
                formData.append('header_image', el.headerInput.files[0]);

                try {
                    setStatus('上传头图中...');
                    el.btnHeader.disabled = true;
                    // fetch with multipart
                    const res = await fetch('/api/customization/homepage-configs/upload_header/', {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: formData
                    });
                    if (res.ok) {
                        setStatus('头图上传成功', false);
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        throw new Error(await res.text());
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
                if (!el.avatarInput.files.length) {
                    setStatus('请先选择头像文件', true);
                    return;
                }
                const formData = new FormData();
                formData.append('avatar', el.avatarInput.files[0]);

                try {
                    setStatus('上传头像中...');
                    el.btnAvatar.disabled = true;
                    // fetch with multipart
                    const res = await fetch('/api/customization/homepage-configs/upload_avatar/', {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: formData
                    });
                    if (res.ok) {
                        setStatus('头像上传成功', false);
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        throw new Error(await res.text());
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

# append right before initBuilder();
init_idx = text.find('function initBuilder() {')
if init_idx != -1 and 'upload_header' not in text:
    text = text[:init_idx] + js_patch + text[init_idx:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print("JS logic injected.")
else:
    print("Failed to find injection point.")
