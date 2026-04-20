import re

file_path = 'f:/WORKSPACE/bedrock/project/inkwell-studio/apps/customization/views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Find AuthorHomepageConfigViewSet
insert_index = text.find('class AuthorHomepageConfigViewSet(viewsets.ModelViewSet):')
publish_index = text.find('def publish(self, request):', insert_index)
publish_block_end = text.find('return Response(serializer.data)', publish_index)

action_code = '''
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_header(self, request):
        config, _ = AuthorHomepageConfig.objects.get_or_create(author=request.user)
        image_file = request.FILES.get("header_image")
        if not image_file:
            return Response({"detail": "未上头图"}, status=status.HTTP_400_BAD_REQUEST)
        if config.header_image:
            config.header_image.delete(save=False)
        config.header_image = image_file
        config.save(update_fields=["header_image", "updated_at"])
        serializer = self.get_serializer(config)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_avatar(self, request):
        config, _ = AuthorHomepageConfig.objects.get_or_create(author=request.user)
        image_file = request.FILES.get("avatar")
        if not image_file:
            return Response({"detail": "未上传头像"}, status=status.HTTP_400_BAD_REQUEST)
        if config.avatar:
            config.avatar.delete(save=False)
        config.avatar = image_file
        config.save(update_fields=["avatar", "updated_at"])
        serializer = self.get_serializer(config)
        return Response(serializer.data, status=status.HTTP_200_OK)
'''

# Wait, we can just append it at the end of the class.
# We'd find CSSSecurityEventViewSet which is the next class.
css_event_index = text.find('class CSSSecurityEventViewSet')
if css_event_index != -1 and 'def upload_header' not in text:
    text = text[:css_event_index] + action_code + '\n\n' + text[css_event_index:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print("Action code injected.")
else:
    print("Class not found or already injected.")
