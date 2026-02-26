from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from django.urls import path

schema_view = get_schema_view(
    openapi.Info(
        title="FirstAPI Documentation",
        default_version="v1",
        description="API documentation for the FirstAPI project",
    ),
    public=True,
    permission_classes=[permissions.AllowAny], # IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
)

urlpatterns = [
    path("swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]