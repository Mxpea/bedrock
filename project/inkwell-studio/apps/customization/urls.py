from rest_framework.routers import DefaultRouter

from .views import (
    AdvancedStyleGrantViewSet,
    AuthorHomepageConfigViewSet,
    CSSSecurityEventViewSet,
    CustomCSSRequestViewSet,
    ThemeConfigViewSet,
    CustomFontViewSet,
)

router = DefaultRouter()
router.register(r"theme-configs", ThemeConfigViewSet, basename="theme-config")
router.register(r"fonts", CustomFontViewSet, basename="custom-font")
router.register(r"css-requests", CustomCSSRequestViewSet, basename="css-request")
router.register(r"style-grants", AdvancedStyleGrantViewSet, basename="style-grant")
router.register(r"homepage-configs", AuthorHomepageConfigViewSet, basename="homepage-config")
router.register(r"css-security-events", CSSSecurityEventViewSet, basename="css-security-event")

urlpatterns = router.urls
