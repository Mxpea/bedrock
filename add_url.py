import re

with open(r'f:\WORKSPACE\bedrock\project\inkwell-studio\config\urls.py', 'r', encoding='utf-8') as f:
    text = f.read()

if "NovelDetailPageView" not in text:
    text = text.replace("NovelListPageView,", "NovelListPageView,\n    NovelDetailPageView,")
    
if 'path("novel/<str:novel_id>/", NovelDetailPageView.as_view(), name="novel-detail-page"),' not in text:
    text = text.replace('path("novels/", NovelListPageView.as_view(), name="novels-page"),', 
        'path("novels/", NovelListPageView.as_view(), name="novels-page"),\n    path("novel/<str:novel_id>/", NovelDetailPageView.as_view(), name="novel-detail-page"),')
        
with open(r'f:\WORKSPACE\bedrock\project\inkwell-studio\config\urls.py', 'w', encoding='utf-8') as f:
    f.write(text)
    
print("Added URL pattern")
