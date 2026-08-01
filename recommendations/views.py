import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from movies.models import Movie
from .models import UserWatchHistory, UserRating, UserFavorite
from .serializers import (
    WatchHistorySerializer,
    UserRatingSerializer,
    UserFavoriteSerializer,
    RecommendationResultSerializer,
)
from .engine.recommender import get_recommender

logger = logging.getLogger(__name__)


def _enrich(results: list[dict]) -> list[dict]:
    if not results:
        return []
    ids = [r['movie_id'] for r in results]
    movies = {m.id: m for m in Movie.objects.filter(id__in=ids)}
    enriched = []
    for r in results:
        movie = movies.get(r['movie_id'])
        if movie:
            enriched.append({'movie': movie, 'score': r['score']})
    return enriched


def _safe_recommend(fn, *args, **kwargs) -> list[dict]:
    """Call a recommender method safely — return [] on any error."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Recommender error: {e}")
        return []


# ------------------------------------------------------------------ #
#  Similar Movies
# ------------------------------------------------------------------ #
class SimilarMoviesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, movie_id):
        try:
            Movie.objects.get(pk=movie_id)
        except Movie.DoesNotExist:
            return Response({'error': 'Movie not found.'}, status=status.HTTP_404_NOT_FOUND)

        top_n = min(int(request.query_params.get('top_n', 10)), 50)
        use_semantic = request.query_params.get('semantic', 'false').lower() == 'true'

        results = _safe_recommend(
            get_recommender().similar_to_movie, movie_id, top_n=top_n, use_semantic=use_semantic
        )
        return Response(RecommendationResultSerializer(_enrich(results), many=True).data)


# ------------------------------------------------------------------ #
#  Genre Recommendations
# ------------------------------------------------------------------ #
class GenreRecommendView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        genre = request.query_params.get('genre', '').strip()
        if not genre:
            return Response({'error': 'genre param required.'}, status=status.HTTP_400_BAD_REQUEST)
        top_n = min(int(request.query_params.get('top_n', 10)), 50)
        results = _safe_recommend(get_recommender().genre_based, genre, top_n=top_n)
        return Response(RecommendationResultSerializer(_enrich(results), many=True).data)


# ------------------------------------------------------------------ #
#  NLP Stats
# ------------------------------------------------------------------ #
class NLPStatsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        try:
            return Response(get_recommender().get_vocab_stats())
        except Exception as e:
            return Response({'error': str(e)}, status=500)


# ------------------------------------------------------------------ #
#  Query Recommendations
# ------------------------------------------------------------------ #
class QueryRecommendView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        query = request.data.get('query', '').strip()
        if not query:
            return Response({'error': 'query field is required.'}, status=status.HTTP_400_BAD_REQUEST)

        top_n = min(int(request.data.get('top_n', 10)), 50)
        use_semantic = str(request.data.get('semantic', False)).lower() == 'true'

        results = _safe_recommend(
            get_recommender().similar_to_query, query, top_n=top_n, use_semantic=use_semantic
        )
        return Response(RecommendationResultSerializer(_enrich(results), many=True).data)


# ------------------------------------------------------------------ #
#  Personalized Recommendations
# ------------------------------------------------------------------ #
class PersonalizedView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        top_n = min(int(request.query_params.get('top_n', 10)), 50)
        use_semantic = request.query_params.get('semantic', 'false').lower() == 'true'

        results = _safe_recommend(
            get_recommender().personalized_for_user,
            request.user.id, top_n=top_n, use_semantic=use_semantic
        )

        if not results:
            return Response(
                {'message': 'Watch some movies first to get personalized recommendations.'},
                status=status.HTTP_200_OK,
            )

        return Response(RecommendationResultSerializer(_enrich(results), many=True).data)


# ------------------------------------------------------------------ #
#  Watch History
# ------------------------------------------------------------------ #
class WatchHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        history = UserWatchHistory.objects.filter(user=request.user).select_related('movie')
        return Response(WatchHistorySerializer(history, many=True).data)

    def post(self, request):
        serializer = WatchHistorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            try:
                get_recommender().build(force=True)
            except Exception as e:
                logger.warning(f"Recommender rebuild failed: {e}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        movie_id = request.data.get('movie')
        deleted, _ = UserWatchHistory.objects.filter(
            user=request.user, movie_id=movie_id
        ).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'error': 'Entry not found.'}, status=status.HTTP_404_NOT_FOUND)


# ------------------------------------------------------------------ #
#  User Ratings
# ------------------------------------------------------------------ #
class UserRatingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ratings = UserRating.objects.filter(user=request.user).select_related('movie')
        return Response(UserRatingSerializer(ratings, many=True).data)

    def post(self, request):
        movie_id = request.data.get('movie')
        existing = UserRating.objects.filter(user=request.user, movie_id=movie_id).first()
        serializer = UserRatingSerializer(
            existing, data=request.data, partial=True
        ) if existing else UserRatingSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        movie_id = request.data.get('movie')
        deleted, _ = UserRating.objects.filter(
            user=request.user, movie_id=movie_id
        ).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'error': 'Rating not found.'}, status=status.HTTP_404_NOT_FOUND)


# ------------------------------------------------------------------ #
#  Favorites
# ------------------------------------------------------------------ #
class FavoritesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        favorites = UserFavorite.objects.filter(user=request.user).select_related('movie')
        return Response(UserFavoriteSerializer(favorites, many=True).data)

    def post(self, request):
        movie_id = request.data.get('movie')
        if UserFavorite.objects.filter(user=request.user, movie_id=movie_id).exists():
            return Response({'message': 'Already in favorites.'}, status=status.HTTP_200_OK)
        serializer = UserFavoriteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        movie_id = request.data.get('movie')
        deleted, _ = UserFavorite.objects.filter(
            user=request.user, movie_id=movie_id
        ).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'error': 'Favorite not found.'}, status=status.HTTP_404_NOT_FOUND)
