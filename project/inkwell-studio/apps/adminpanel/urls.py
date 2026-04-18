from django.urls import path

from .views import (
    AdminDashboardView,
    AnalyticsView,
    OpsToolsView,
    ReviewQueueView,
    RoastModerationView,
    SystemSettingsView,
    UserDetailAdminView,
    UserManageView,
    WorkspaceDetailAdminView,
    WorkspaceManageView,
)

app_name = "adminpanel"

urlpatterns = [
    path("", AdminDashboardView.as_view(), name="dashboard"),
    path("workspaces/", WorkspaceManageView.as_view(), name="workspaces"),
    path("workspaces/<int:workspace_id>/", WorkspaceDetailAdminView.as_view(), name="workspace-detail"),
    path("users/", UserManageView.as_view(), name="users"),
    path("users/<int:user_id>/", UserDetailAdminView.as_view(), name="user-detail"),
    path("reviews/", ReviewQueueView.as_view(), name="reviews"),
    path("roasts/", RoastModerationView.as_view(), name="roasts"),
    path("settings/", SystemSettingsView.as_view(), name="settings"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
    path("ops/", OpsToolsView.as_view(), name="ops"),
]
