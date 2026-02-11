"""
Сервис для работы с API Кинопоиска.
"""
import os
from urllib.parse import quote
import requests

KINOPOISK_API_URL = "https://api.kinopoisk.dev/v1.4/movie"
FILMS_STORAGE_BASE = os.environ.get("FILMS_STORAGE_BASE", "https://flcksbr.top/film/")
KINOPOISK_TIMEOUT = 30  # Кинопоиск иногда отвечает долго

def _headers():
    key = os.environ.get("KINOPOISK_API_KEY", "")
    return {"X-API-KEY": key} if key else {}


def search_by_query(q: str):
    """Поиск по названию, до 10 результатов."""
    encoded = quote(q)
    url = f"{KINOPOISK_API_URL}/search?page=1&limit=10&query={encoded}"
    resp = requests.get(url, headers=_headers(), timeout=KINOPOISK_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def search_by_genre(genre_name: str, year: str | None):
    """Поиск по жанру и году, до 20 результатов по популярности."""
    params = {
        "genres.name": genre_name.lower(),
        "limit": 20,
        "notNullFields": ["poster.url", "name", "votes.kp", "genres.name"],
        "selectFields": ["id", "name", "alternativeName", "year", "votes", "poster", "genres"],
        "sortField": ["votes.kp"],
        "sortType": ["-1"],
    }
    if year:
        params["year"] = year
    resp = requests.get(KINOPOISK_API_URL, headers=_headers(), params=params, timeout=KINOPOISK_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    genre_lower = genre_name.lower()
    results = []
    for film in data.get("docs", []):
        genres = [g.get("name", "").lower() for g in film.get("genres", [])]
        if genre_lower in genres:
            results.append({
                "id": film["id"],
                "alternativeName": film.get("alternativeName"),
                "name": film.get("name"),
                "year": film.get("year"),
                "votes": film.get("votes", {}).get("kp", 0),
                "poster": film.get("poster", {}).get("url"),
            })
    return {"results_count": len(results), "results": results}


def _movie_list_params(limit: int, sort_by_votes: bool = True, type_filter: str | None = None, year: str | None = None):
    """Общие параметры для списка фильмов/сериалов."""
    params = {
        "limit": limit,
        "notNullFields": ["poster.url", "name", "votes.kp"],
        "selectFields": ["id", "name", "alternativeName", "year", "votes", "poster", "type"],
        "sortField": ["votes.kp"] if sort_by_votes else ["year"],
        "sortType": ["-1"],
    }
    if type_filter:
        params["type"] = type_filter  # "movie" | "tv-series" | "cartoon" и т.д.
    if year:
        params["year"] = year
    return params


def _docs_to_results(docs: list) -> list:
    """Преобразование docs из ответа API в единый формат для фронта."""
    return [
        {
            "id": f.get("id"),
            "alternativeName": f.get("alternativeName"),
            "name": f.get("name"),
            "year": f.get("year"),
            "votes": f.get("votes", {}).get("kp", 0),
            "poster": f.get("poster", {}).get("url"),
        }
        for f in docs
    ]


def get_popular_now(limit: int = 12):
    """Популярное сейчас — топ по голосам (фильмы и сериалы)."""
    params = _movie_list_params(limit=limit)
    resp = requests.get(KINOPOISK_API_URL, headers=_headers(), params=params, timeout=KINOPOISK_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return {"results": _docs_to_results(data.get("docs", []))}


def get_popular_movies(limit: int = 4):
    """Популярные фильмы — только type=movie, по голосам."""
    params = _movie_list_params(limit=limit, type_filter="movie")
    resp = requests.get(KINOPOISK_API_URL, headers=_headers(), params=params, timeout=KINOPOISK_TIMEOUT)
    resp.raise_for_status()
    docs = resp.json().get("docs", [])
    if len(docs) < limit:
        params = _movie_list_params(limit=50)
        resp = requests.get(KINOPOISK_API_URL, headers=_headers(), params=params, timeout=KINOPOISK_TIMEOUT)
        resp.raise_for_status()
        docs = [d for d in resp.json().get("docs", []) if d.get("type") == "movie"][:limit]
    return {"results": _docs_to_results(docs)}


def get_popular_series(limit: int = 4):
    """Популярные сериалы — только type=tv-series, по голосам."""
    params = _movie_list_params(limit=limit, type_filter="tv-series")
    resp = requests.get(KINOPOISK_API_URL, headers=_headers(), params=params, timeout=KINOPOISK_TIMEOUT)
    resp.raise_for_status()
    docs = resp.json().get("docs", [])
    if len(docs) < limit:
        params = _movie_list_params(limit=50)
        resp = requests.get(KINOPOISK_API_URL, headers=_headers(), params=params, timeout=KINOPOISK_TIMEOUT)
        resp.raise_for_status()
        docs = [d for d in resp.json().get("docs", []) if d.get("type") == "tv-series"][:limit]
    return {"results": _docs_to_results(docs)}


def get_coming_soon(limit: int = 4):
    """Скоро на экранах — премьеры (текущий и следующий год), по голосам."""
    from datetime import date
    current_year = str(date.today().year)
    next_year = str(date.today().year + 1)
    params = _movie_list_params(limit=limit * 2, year=f"{current_year}-{next_year}")
    resp = requests.get(KINOPOISK_API_URL, headers=_headers(), params=params, timeout=KINOPOISK_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    docs = data.get("docs", [])[:limit]
    return {"results": _docs_to_results(docs)}


def get_movie_details(movie_id: int):
    """Полная информация о фильме по ID."""
    url = f"{KINOPOISK_API_URL}/{movie_id}"
    resp = requests.get(url, headers=_headers(), timeout=KINOPOISK_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_watch_link(movie_id: int):
    """Детали фильма и ссылка на просмотр."""
    details = get_movie_details(movie_id)
    details["view_link"] = f"{FILMS_STORAGE_BASE}{movie_id}"
    return details
