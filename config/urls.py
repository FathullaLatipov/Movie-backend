from django.urls import path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

schema_view = get_schema_view(
    openapi.Info(
        title="Movie REST API",
        default_version="v1",
        description="API для поиска фильмов (Кинопоиск) и получения ссылок на просмотр.",
    ),
    public=True,
)

urlpatterns = [
    path("", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("api/v1/", include("api.urls")),
]
