from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from config.views import (
    AuthorProfilePageView,
    DashboardPageView,
    HomePageView,
    LoginPageView,
    NovelListPageView,
    ReaderPageView,
    RegisterPageView,
    WorkspacePageView,
)
from apps.novels.views import ChapterViewSet, NovelViewSet, CharacterViewSet, WorldviewEntryViewSet

router = DefaultRouter()
router.register(r"novels", NovelViewSet, basename="novel")
router.register(r"chapters", ChapterViewSet, basename="chapter")
router.register(r"characters", CharacterViewSet, basename="character")
router.register(r"worldview-entries", WorldviewEntryViewSet, basename="worldview-entry")

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("login/", LoginPageView.as_view(), name="login-page"),
    path("register/", RegisterPageView.as_view(), name="register-page"),
    path("dashboard/", DashboardPageView.as_view(), name="dashboard-page"),
    path("workspace/<int:workspace_id>/", WorkspacePageView.as_view(), name="workspace-page"),
    path("workspace/<int:workspace_id>/<str:module>/", WorkspacePageView.as_view(), name="workspace-module-page"),
    path("novels/", NovelListPageView.as_view(), name="novels-page"),
    path("reader/", ReaderPageView.as_view(), name="reader-page"),
    path("reader/<int:chapter_id>/", ReaderPageView.as_view(), name="reader-chapter-page"),
    path("u/<str:username>/", AuthorProfilePageView.as_view(), name="author-profile-page"),
    path("admin/", include("apps.adminpanel.urls")),
    path("django-admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/customization/", include("apps.customization.urls")),
    path("api/", include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
