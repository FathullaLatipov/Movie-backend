"""
Сервис для работы с API The Movie Database (TMDB).
Документация: https://developer.themoviedb.org/docs
"""
import os
import time
from datetime import date
from urllib.parse import quote
import requests

# Без завершающего слэша, чтобы не было двойного слэша в путях
TMDB_BASE = (os.environ.get("TMDB_BASE") or "https://api.themoviedb.org/3").rstrip("/")
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
FILMS_STORAGE_BASE = os.environ.get("FILMS_STORAGE_BASE", "https://flcksbr.top/film/")
# Таймаут в секундах; можно задать TMDB_TIMEOUT=30 в .env при медленной сети
TMDB_TIMEOUT = int(os.environ.get("TMDB_TIMEOUT", "25"))
TMDB_RETRIES = 3  # повторов при ReadTimeout/ConnectionError

def _api_key():
    return (os.environ.get("TMDB_API_KEY") or os.environ.get("TMDB_API_KEY_V3") or "").strip()

def _ssl_verify():
    """Проверка SSL. Отключить (False) при SSLError из-за прокси/фаервола: TMDB_SSL_VERIFY=0"""
    v = os.environ.get("TMDB_SSL_VERIFY", "1").strip().lower()
    return v not in ("0", "false", "no", "off")

def _params(extra=None):
    p = {"api_key": _api_key(), "language": "ru-RU"}
    if extra:
        p.update(extra)
    return p


def _poster_url(path):
    if not path or not isinstance(path, str):
        return None
    path = path.strip()
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    prefix = path if path.startswith("/") else f"/{path}"
    return f"{TMDB_IMAGE_BASE}{prefix}"


def _movie_item(item: dict, is_tv: bool = False) -> dict | None:
    """Приводим элемент TMDB к формату для фронта (id, name, alternativeName, year, votes, poster)."""
    if not item or not isinstance(item, dict):
        return None
    if is_tv:
        name = item.get("name") or item.get("original_name")
        date_str = item.get("first_air_date") or ""
    else:
        name = item.get("title") or item.get("original_title")
        date_str = item.get("release_date") or ""
    year = None
    if date_str and len(str(date_str)) >= 4:
        try:
            year = int(str(date_str)[:4])
        except (ValueError, TypeError):
            pass
    return {
        "id": item.get("id"),
        "name": name,
        "alternativeName": item.get("original_title") or item.get("original_name"),
        "year": year,
        "votes": item.get("vote_count") or 0,
        "poster": _poster_url(item.get("poster_path")),
    }


def _results(items: list, is_tv: bool = False) -> list:
    out = []
    for x in items or []:
        row = _movie_item(x, is_tv=is_tv)
        if row is not None:
            out.append(row)
    return out


def _get(url: str, params: dict, on_404_return_empty: bool = False):
    """Запрос к TMDB с повторами при таймауте/соединении. При 404 можно вернуть {} без исключения."""
    last_error = None
    for attempt in range(TMDB_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=TMDB_TIMEOUT, verify=_ssl_verify())
            if resp.status_code == 404 and on_404_return_empty:
                return {}
            resp.raise_for_status()
            return resp.json() or {}
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            if attempt < TMDB_RETRIES - 1:
                time.sleep(1)
            continue
    raise last_error


# --- Блоки главной ---

def _empty_results(detail: str = "TMDB_API_KEY не задан"):
    """Возврат пустых results без запроса к TMDB (нет ключа или по требованию)."""
    return {"results": [], "detail": detail}


def get_popular_now(limit: int = 12):
    """Популярное сейчас — тренды за день (фильмы + сериалы)."""
    if not _api_key():
        return _empty_results()
    data = _get(f"{TMDB_BASE}/trending/all/day", _params(), on_404_return_empty=True)
    items = data.get("results") or []
    out = []
    for x in items[:limit]:
        if not x or not isinstance(x, dict):
            continue
        is_tv = x.get("media_type") == "tv"
        row = _movie_item(x, is_tv=is_tv)
        if row is not None:
            out.append(row)
    return {"results": out}


def get_popular_movies(limit: int = 4):
    """Популярные фильмы."""
    if not _api_key():
        return _empty_results()
    data = _get(f"{TMDB_BASE}/movie/popular", _params({"page": 1}), on_404_return_empty=True)
    items = data.get("results", [])[:limit]
    return {"results": _results(items, is_tv=False)}


def get_popular_series(limit: int = 4):
    """Популярные сериалы."""
    if not _api_key():
        return _empty_results()
    data = _get(f"{TMDB_BASE}/tv/popular", _params({"page": 1}), on_404_return_empty=True)
    items = data.get("results", [])[:limit]
    return {"results": _results(items, is_tv=True)}


def get_coming_soon(limit: int = 4):
    """Скоро в кино — премьеры (TMDB movie/upcoming). При 404 — fallback на discover с датой выхода."""
    if not _api_key():
        return _empty_results()
    data = _get(f"{TMDB_BASE}/movie/upcoming", _params({"page": 1}), on_404_return_empty=True)
    if not data:
        today = date.today().isoformat()
        data = _get(
            f"{TMDB_BASE}/discover/movie",
            _params({"page": 1, "sort_by": "popularity.desc", "primary_release_date.gte": today}),
            on_404_return_empty=True,
        )
    items = (data or {}).get("results", [])[:limit]
    return {"results": _results(items, is_tv=False)}


# --- Поиск по жанру (TMDB: discover + genre id) ---

# Маппинг названий жанров на id TMDB (movie) — можно расширить
TMDB_GENRE_IDS = {
    "приключения": 12,
    "боевик": 28,
    "комедия": 35,
    "фантастика": 878,
    "триллер": 53,
    "драма": 18,
    "криминал": 80,
    "мелодрама": 10749,
    "ужасы": 27,
    "документальный": 99,
    "фэнтези": 14,
}


def search_by_genre(genre_name: str, year: str | None):
    """Поиск фильмов по жанру (и опционально году). До 20 результатов."""
    name = (genre_name or "").strip().lower()
    genre_id = TMDB_GENRE_IDS.get(name)
    if not genre_id:
        return {"results_count": 0, "results": []}
    params = _params({"with_genres": genre_id, "page": 1, "sort_by": "popularity.desc"})
    if year:
        if "-" in year:
            parts = year.split("-")
            if len(parts) == 2:
                params["primary_release_date.gte"] = f"{parts[0].strip()}-01-01"
                params["primary_release_date.lte"] = f"{parts[1].strip()}-12-31"
        else:
            params["primary_release_year"] = year.strip()
    data = _get(f"{TMDB_BASE}/discover/movie", params)
    items = data.get("results", [])[:20]
    return {"results_count": len(items), "results": _results(items, is_tv=False)}


def search_by_query(q: str):
    """Поиск по названию (мульти: фильмы + сериалы), до 10 результатов."""
    if not (q or "").strip():
        return {"results": []}
    data = _get(f"{TMDB_BASE}/search/multi", _params({"query": q.strip(), "page": 1}))
    items = []
    for x in data.get("results", []):
        if x.get("media_type") not in ("movie", "tv"):
            continue
        is_tv = x.get("media_type") == "tv"
        items.append(_movie_item(x, is_tv=is_tv))
        if len(items) >= 10:
            break
    return {"results": items}


def get_movie_details(movie_id: int, is_tv: bool = False):
    """Полная информация о фильме/сериале по ID."""
    segment = "tv" if is_tv else "movie"
    data = _get(f"{TMDB_BASE}/{segment}/{movie_id}", _params())
    if data.get("poster_path"):
        data["poster_url"] = _poster_url(data["poster_path"])
    return data


def get_watch_link(movie_id: int, is_tv: bool = False):
    """Детали и ссылка на просмотр."""
    details = get_movie_details(movie_id, is_tv=is_tv)
    details["view_link"] = f"{FILMS_STORAGE_BASE}{movie_id}"
    return details
