from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from config.views import DashboardPageView, HomePageView, LoginPageView, NovelListPageView, RegisterPageView, EditorPageView, ReaderPageView, AuthorProfilePageView
from apps.novels.views import ChapterViewSet, NovelViewSet

router = DefaultRouter()
router.register(r"novels", NovelViewSet, basename="novel")
router.register(r"chapters", ChapterViewSet, basename="chapter")

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("login/", LoginPageView.as_view(), name="login-page"),
    path("register/", RegisterPageView.as_view(), name="register-page"),
    path("dashboard/", DashboardPageView.as_view(), name="dashboard-page"),
    path("novels/", NovelListPageView.as_view(), name="novels-page"),
    path("editor/", EditorPageView.as_view(), name="editor-page"),
    path("reader/", ReaderPageView.as_view(), name="reader-page"),
    path("reader/<int:chapter_id>/", ReaderPageView.as_view(), name="reader-chapter-page"),
    path("u/<str:username>/", AuthorProfilePageView.as_view(), name="author-profile-page"),
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/customization/", include("apps.customization.urls")),
    path("api/", include(router.urls)),
]
