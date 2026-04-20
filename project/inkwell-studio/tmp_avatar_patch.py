import re

file_path = 'f:/WORKSPACE/bedrock/project/inkwell-studio/apps/customization/views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Make sure imports are present
if 'from PIL import Image' not in text:
    text = 'from PIL import Image\nfrom io import BytesIO\nfrom django.core.files.base import ContentFile\n' + text

old_upload_avatar = '''    def upload_avatar(self, request):
        config, _ = AuthorHomepageConfig.objects.get_or_create(author=request.user)
        image_file = request.FILES.get("avatar")
        if not image_file:
            return Response({"detail": "未上传头像"}, status=status.HTTP_400_BAD_REQUEST)
        if config.avatar:
            config.avatar.delete(save=False)
        config.avatar = image_file
        config.save(update_fields=["avatar", "updated_at"])
        serializer = self.get_serializer(config)
        return Response(serializer.data, status=status.HTTP_200_OK)'''

new_upload_avatar = '''    def upload_avatar(self, request):
        config, _ = AuthorHomepageConfig.objects.get_or_create(author=request.user)
        image_file = request.FILES.get("avatar")
        if not image_file:
            return Response({"detail": "未上传头像"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            img = Image.open(image_file)
            
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            width, height = img.size
            new_size = min(width, height)
            left = (width - new_size) / 2
            top = (height - new_size) / 2
            right = (width + new_size) / 2
            bottom = (height + new_size) / 2
            
            img = img.crop((left, top, right, bottom))
            
            img = img.resize((512, 512), Image.Resampling.LANCZOS)
            
            img_io = BytesIO()
            img.save(img_io, format='JPEG', quality=90)
            img_content = ContentFile(img_io.getvalue(), name=f"{request.user.username}_avatar.jpg")
            
            if config.avatar:
                config.avatar.delete(save=False)
                
            config.avatar = img_content
            config.save(update_fields=["avatar", "updated_at"])
            
            serializer = self.get_serializer(config)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"detail": f"头像处理失败: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)'''

if old_upload_avatar in text:
    text = text.replace(old_upload_avatar, new_upload_avatar)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print("Avatar upload logic updated.")
else:
    print("Could not find the target code to replace.")