from django.urls import path
from . import views

app_name = "api"

urlpatterns = [
    path("movies", views.movie_list),
    path("movies/<int:movie_id>", views.movie_detail),
    path("movies/<int:movie_id>/watch", views.movie_watch),
    path("genres", views.genre_list),
    path("search_by_genre", views.search_by_genre),
]
