from django.urls import path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from api import views as api_views

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
    # Оба варианта пути — с префиксом /api и без (для разного деплоя/прокси)
    path("search_by_genre", api_views.search_by_genre),
    path("api/search_by_genre", api_views.search_by_genre),
    path("poster", api_views.poster_proxy),
    path("api/poster", api_views.poster_proxy),
    path("api/v1/", include("api.urls")),
]
