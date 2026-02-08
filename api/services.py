"""
Сервис для работы с API Кинопоиска.
"""
import os
from urllib.parse import quote
import requests

KINOPOISK_API_URL = "https://api.kinopoisk.dev/v1.4/movie"
FILMS_STORAGE_BASE = os.environ.get("FILMS_STORAGE_BASE", "https://flcksbr.top/film/")

def _headers():
    key = "RNGX6C9-AVH4RKV-QRB6PCH-V05VDJN"
    return {"X-API-KEY": key} if key else {}


def search_by_query(q: str):
    """Поиск по названию, до 10 результатов."""
    encoded = quote(q)
    url = f"{KINOPOISK_API_URL}/search?page=1&limit=10&query={encoded}"
    resp = requests.get(url, headers=_headers(), timeout=15)
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
    resp = requests.get(KINOPOISK_API_URL, headers=_headers(), params=params, timeout=15)
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


def get_movie_details(movie_id: int):
    """Полная информация о фильме по ID."""
    url = f"{KINOPOISK_API_URL}/{movie_id}"
    resp = requests.get(url, headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_watch_link(movie_id: int):
    """Детали фильма и ссылка на просмотр."""
    details = get_movie_details(movie_id)
    details["view_link"] = f"{FILMS_STORAGE_BASE}{movie_id}"
    return details
