from django.urls import path
from .views import MovieListView, MovieDetailView, UniverseListView, PhaseListView

urlpatterns = [
    path('', MovieListView.as_view(), name='movie-list'),
    path('<int:pk>/', MovieDetailView.as_view(), name='movie-detail'),
    path('universes/', UniverseListView.as_view(), name='universe-list'),
    path('phases/', PhaseListView.as_view(), name='phase-list'),
]
