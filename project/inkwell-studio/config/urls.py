from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.novels.views import ChapterViewSet, NovelViewSet

router = DefaultRouter()
router.register(r"novels", NovelViewSet, basename="novel")
router.register(r"chapters", ChapterViewSet, basename="chapter")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include(router.urls)),
]
