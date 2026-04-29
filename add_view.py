import re

with open(r'f:\WORKSPACE\bedrock\project\inkwell-studio\config\views.py', 'r', encoding='utf-8') as f:
    text = f.read()

# See if we can add a NovelDetailPageView
view_code = """
class NovelDetailPageView(TemplateView):
    template_name = "novels/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workspace_id = kwargs.get("novel_id")
        
        # Check permissions similar to reader
        user = self.request.user
        base_qs = Novel.objects.filter(is_deleted=False)
        
        novel_filter = models.Q(public_id=workspace_id)
        if str(workspace_id).isdigit():
            novel_filter |= models.Q(id=workspace_id)
            
        novel = get_object_or_404(base_qs, novel_filter)
        
        # Ensure user can see this novel
        if not (user.is_authenticated and (user.is_staff or user.is_superuser or novel.author == user)):
            if novel.visibility not in [Novel.Visibility.PUBLIC, Novel.Visibility.LINK]:
                raise Http404("无权访问该工作区")
                
        context["novel"] = novel
        
        # Get accessible chapters
        chap_base = novel.chapters.all()
        if not (user.is_authenticated and (user.is_staff or user.is_superuser or novel.author == user)):
            chap_base = chap_base.filter(is_published=True)
            
        context["chapter_list"] = chap_base.order_by("order", "id")
        return context
"""

if "class NovelDetailPageView" not in text:
    # Just insert it at the bottom
    text += "\n" + view_code
    with open(r'f:\WORKSPACE\bedrock\project\inkwell-studio\config\views.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Added NovelDetailPageView to config/views.py")
else:
    print("Already exists")
