from django.urls import path
from .views import (
    SimilarMoviesView,
    QueryRecommendView,
    PersonalizedView,
    WatchHistoryView,
    UserRatingView,
    FavoritesView,
    GenreRecommendView,
    NLPStatsView,
)

urlpatterns = [
    # NLP / AI recommendation endpoints
    path('similar/<int:movie_id>/', SimilarMoviesView.as_view(), name='similar-movies'),
    path('query/', QueryRecommendView.as_view(), name='query-recommend'),
    path('genre/', GenreRecommendView.as_view(), name='genre-recommend'),
    path('for-me/', PersonalizedView.as_view(), name='personalized'),
    path('stats/', NLPStatsView.as_view(), name='nlp-stats'),

    # User interaction endpoints
    path('history/', WatchHistoryView.as_view(), name='watch-history'),
    path('ratings/', UserRatingView.as_view(), name='user-ratings'),
    path('favorites/', FavoritesView.as_view(), name='favorites'),
]
