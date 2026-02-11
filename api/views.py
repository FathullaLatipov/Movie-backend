from urllib.parse import urlparse

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import requests

from . import services

# Домен, с которого разрешено проксировать постеры (избегаем ERR_BLOCKED_BY_CLIENT в браузере)
ALLOWED_POSTER_HOSTS = ("avatars.mds.yandex.net", "st.kp.yandex.net", "www.kinopoisk.ru")

GENRE_NAMES = [
    "Боевик", "Комедия", "Фэнтези", "Драма", "Криминал",
    "Мелодрама", "Триллер", "Ужасы", "Фантастика", "Документальный", "Приключения",
]


@swagger_auto_schema(
    method="get",
    operation_summary="Поиск фильмов",
    operation_description="Поиск по названию (q) или по жанру и году (genre, year). Укажите либо q, либо genre.",
    manual_parameters=[
        openapi.Parameter("q", openapi.IN_QUERY, description="Поиск по названию (мин. 2 символа)", type=openapi.TYPE_STRING),
        openapi.Parameter("genre", openapi.IN_QUERY, description="Жанр (напр. комедия, драма)", type=openapi.TYPE_STRING),
        openapi.Parameter("year", openapi.IN_QUERY, description="Год: 2020 или 2015-2021", type=openapi.TYPE_STRING),
    ],
)
@api_view(["GET"])
def movie_list(request: Request):
    """
    Список/поиск фильмов.
    - q — поиск по названию (минимум 2 символа).
    - genre — поиск по жанру.
    - year — год или диапазон (например 2020 или 2015-2021).
    """
    q = request.query_params.get("q", "").strip()
    genre = request.query_params.get("genre", "").strip()
    year = request.query_params.get("year", "").strip() or None

    if q:
        if len(q) < 2:
            return Response(
                {"detail": "Параметр q должен быть не короче 2 символов."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            return Response(services.search_by_query(q))
        except requests.HTTPError as e:
            return Response(
                {"detail": f"Ошибка API Кинопоиска: {e.response.status_code}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

    if genre:
        if year:
            if "-" in year:
                parts = year.split("-")
                if len(parts) != 2:
                    return Response(
                        {"detail": "Год: один год (2020) или диапазон (2016-2020)."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                try:
                    start, end = int(parts[0]), int(parts[1])
                    if start > end:
                        raise ValueError
                except ValueError:
                    return Response(
                        {"detail": "Некорректный диапазон года."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            elif not year.isdigit():
                return Response(
                    {"detail": "Год должен быть числом или диапазоном."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        try:
            return Response(services.search_by_genre(genre, year))
        except requests.HTTPError as e:
            return Response(
                {"detail": f"Ошибка API Кинопоиска: {e.response.status_code}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

    return Response(
        {"detail": "Укажите q (поиск по названию) или genre (поиск по жанру)."},
        status=status.HTTP_400_BAD_REQUEST,
    )


@swagger_auto_schema(
    method="get",
    operation_summary="Детали фильма",
    operation_description="Полная информация о фильме по ID с Кинопоиска.",
)
@api_view(["GET"])
def movie_detail(request: Request, movie_id: int):
    """Детали фильма по ID."""
    try:
        data = services.get_movie_details(movie_id)
        return Response(data)
    except requests.HTTPError as e:
        return Response(
            {"detail": "Фильм не найден или ошибка API."},
            status=status.HTTP_404_NOT_FOUND if e.response.status_code == 404 else status.HTTP_502_BAD_GATEWAY,
        )


@swagger_auto_schema(
    method="get",
    operation_summary="Ссылка на просмотр",
    operation_description="Детали фильма и ссылка на просмотр (view_link).",
)
@api_view(["GET"])
def movie_watch(request: Request, movie_id: int):
    """Детали фильма и ссылка на просмотр."""
    try:
        data = services.get_watch_link(movie_id)
        return Response(data)
    except requests.HTTPError as e:
        return Response(
            {"detail": "Фильм не найден или ошибка API."},
            status=status.HTTP_404_NOT_FOUND if e.response.status_code == 404 else status.HTTP_502_BAD_GATEWAY,
        )


@swagger_auto_schema(
    method="get",
    operation_summary="Список жанров",
    operation_description="Доступные жанры для фильтрации в поиске.",
)
@api_view(["GET"])
def genre_list(request: Request):
    """Список доступных жанров."""
    return Response({"genres": GENRE_NAMES})


@swagger_auto_schema(
    method="get",
    operation_summary="Поиск по жанру",
    operation_description="Эндпоинт для фронтенда: api/search_by_genre?genre_name=триллер",
    manual_parameters=[
        openapi.Parameter("genre_name", openapi.IN_QUERY, description="Название жанра (напр. триллер, комедия)", type=openapi.TYPE_STRING, required=True),
        openapi.Parameter("year", openapi.IN_QUERY, description="Год или диапазон (напр. 2020 или 2015-2021)", type=openapi.TYPE_STRING),
    ],
)
@api_view(["GET"])
def search_by_genre(request: Request):
    """
    Поиск фильмов по жанру.
    Запрос: GET api/search_by_genre?genre_name=триллер&year=2020 (year необязателен).
    """
    genre_name = request.query_params.get("genre_name", "").strip()
    if not genre_name:
        return Response(
            {"detail": "Укажите параметр genre_name (напр. триллер, комедия)."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    year = request.query_params.get("year", "").strip() or None
    if year and "-" in year:
        parts = year.split("-")
        if len(parts) != 2:
            return Response(
                {"detail": "Год: один год (2020) или диапазон (2016-2020)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            start, end = int(parts[0]), int(parts[1])
            if start > end:
                raise ValueError
        except ValueError:
            return Response(
                {"detail": "Некорректный диапазон года."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    elif year and not year.isdigit():
        return Response(
            {"detail": "Год должен быть числом или диапазоном."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        return Response(services.search_by_genre(genre_name, year))
    except requests.HTTPError as e:
        return Response(
            {"detail": f"Ошибка API Кинопоиска: {e.response.status_code}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )


@api_view(["GET"])
def popular_now(request: Request):
    """Популярное сейчас — топ по голосам."""
    try:
        return Response(services.get_popular_now(limit=12))
    except requests.HTTPError as e:
        return Response(
            {"detail": f"Ошибка API Кинопоиска: {e.response.status_code}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )


@api_view(["GET"])
def popular_movies(request: Request):
    """Популярные фильмы (только фильмы)."""
    try:
        return Response(services.get_popular_movies(limit=4))
    except requests.HTTPError as e:
        return Response(
            {"detail": f"Ошибка API Кинопоиска: {e.response.status_code}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )


@api_view(["GET"])
def popular_series(request: Request):
    """Популярные сериалы (только сериалы)."""
    try:
        return Response(services.get_popular_series(limit=4))
    except requests.HTTPError as e:
        return Response(
            {"detail": f"Ошибка API Кинопоиска: {e.response.status_code}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )


@api_view(["GET"])
def coming_soon(request: Request):
    """Скоро на экранах — премьеры."""
    try:
        return Response(services.get_coming_soon(limit=4))
    except requests.HTTPError as e:
        return Response(
            {"detail": f"Ошибка API Кинопоиска: {e.response.status_code}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )


def poster_proxy(request):
    """
    Прокси постеров с Yandex/Kinopoisk, чтобы обойти блокировку в браузере (ERR_BLOCKED_BY_CLIENT).
    GET ?url=<encoded_image_url>
    """
    url = request.GET.get("url", "").strip()
    if not url:
        return HttpResponse("Missing url", status=400)
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or parsed.netloc not in ALLOWED_POSTER_HOSTS:
            return HttpResponse("Forbidden", status=403)
    except Exception:
        return HttpResponse("Invalid url", status=400)
    try:
        resp = requests.get(url, timeout=15, stream=True)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "image/jpeg")
        content = resp.content
    except requests.RequestException:
        return HttpResponse("Upstream error", status=502)
    response = HttpResponse(content, content_type=content_type)
    response["Cache-Control"] = "public, max-age=86400"
    return response
