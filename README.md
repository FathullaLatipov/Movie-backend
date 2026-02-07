# Movie REST API (Django + DRF)

REST API для поиска фильмов через Кинопоиск и получения ссылок на просмотр.

## Структура проекта

```
movie/
  manage.py
  requirements.txt
  README.md
  config/                 # Настройки Django
    settings.py
    urls.py
    wsgi.py
    asgi.py
  api/                     # Приложение API
    views.py               # DRF-вьюхи
    urls.py                # Маршруты /api/v1/...
    services.py            # Запросы к Кинопоиску
    apps.py
```

## Venv и запуск

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать (Windows)
venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt

# Переменные окружения (по желанию)
set KINOPOISK_API_KEY=ваш_ключ
set FILMS_STORAGE_BASE=https://flcksbr.top/film/

# Запуск
python manage.py runserver
```

Сервер: http://127.0.0.1:8000/

## API (v1)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/movies?q=...` | Поиск по названию (до 10) |
| GET | `/api/v1/movies?genre=...&year=...` | Поиск по жанру и году (до 20) |
| GET | `/api/v1/movies/<id>` | Детали фильма |
| GET | `/api/v1/movies/<id>/watch` | Детали + ссылка на просмотр |
| GET | `/api/v1/genres` | Список жанров |

Переменные окружения: `KINOPOISK_API_KEY`, `FILMS_STORAGE_BASE`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`.
