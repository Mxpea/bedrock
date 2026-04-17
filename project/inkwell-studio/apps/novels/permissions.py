from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Novel


class IsAuthorOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        author = getattr(obj, "author", None)
        if author is None and hasattr(obj, "novel"):
            author = obj.novel.author
        return author == request.user


class CanReadNovel(BasePermission):
    def has_object_permission(self, request, view, obj: Novel):
        if obj.author == request.user:
            return True
        return obj.visibility in [Novel.Visibility.PUBLIC, Novel.Visibility.LINK]
