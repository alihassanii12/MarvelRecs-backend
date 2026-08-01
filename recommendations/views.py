from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from movies.models import Movie
from movies.serializers import MovieListSerializer
from .models import UserWatchHistory, UserRating, UserFavorite
from .serializers import (
    WatchHistorySerializer,
    UserRatingSerializer,
    UserFavoriteSerializer,
    RecommendationResultSerializer,
)
from .engine.recommender import get_recommender


def _enrich(results: list[dict]) -> list[dict]:
    """Attach Movie objects to recommender result dicts."""
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


# ------------------------------------------------------------------ #
#  Similar Movies
# ------------------------------------------------------------------ #

class SimilarMoviesView(APIView):
    """
    GET /api/recommendations/similar/<movie_id>/
    Returns movies similar to the given movie using NLP (NLTK + TF-IDF).

    Query params:
      ?top_n=10        — number of results (default 10, max 50)
      ?semantic=false  — use sentence-transformer embeddings (default false / TF-IDF)
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, movie_id):
        try:
            Movie.objects.get(pk=movie_id)
        except Movie.DoesNotExist:
            return Response({'error': 'Movie not found.'}, status=status.HTTP_404_NOT_FOUND)

        top_n = min(int(request.query_params.get('top_n', 10)), 50)
        use_semantic = request.query_params.get('semantic', 'false').lower() == 'true'

        recommender = get_recommender()
        results = recommender.similar_to_movie(movie_id, top_n=top_n, use_semantic=use_semantic)
        enriched = _enrich(results)

        serializer = RecommendationResultSerializer(enriched, many=True)
        return Response(serializer.data)


class GenreRecommendView(APIView):
    """
    GET /api/recommendations/genre/?genre=Action
    Returns top movies for a given genre using TF-IDF.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        genre = request.query_params.get('genre', '').strip()
        if not genre:
            return Response({'error': 'genre query param is required.'}, status=status.HTTP_400_BAD_REQUEST)

        top_n = min(int(request.query_params.get('top_n', 10)), 50)
        recommender = get_recommender()
        results = recommender.genre_based(genre, top_n=top_n)
        enriched = _enrich(results)

        serializer = RecommendationResultSerializer(enriched, many=True)
        return Response(serializer.data)


class NLPStatsView(APIView):
    """
    GET /api/recommendations/stats/
    Returns TF-IDF vocabulary stats — useful for debugging / admin.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        recommender = get_recommender()
        return Response(recommender.get_vocab_stats())


# ------------------------------------------------------------------ #
#  Search-Style Query Recommendations
# ------------------------------------------------------------------ #

class QueryRecommendView(APIView):
    """
    POST /api/recommendations/query/
    Body: { "query": "funny space adventure with talking animals" }
    Returns movies semantically similar to the free-text query.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        query = request.data.get('query', '').strip()
        if not query:
            return Response({'error': 'query field is required.'}, status=status.HTTP_400_BAD_REQUEST)

        top_n = min(int(request.data.get('top_n', 10)), 50)
        use_semantic = str(request.data.get('semantic', False)).lower() == 'true'

        recommender = get_recommender()
        results = recommender.similar_to_query(query, top_n=top_n, use_semantic=use_semantic)
        enriched = _enrich(results)

        serializer = RecommendationResultSerializer(enriched, many=True)
        return Response(serializer.data)


# ------------------------------------------------------------------ #
#  Personalized Recommendations
# ------------------------------------------------------------------ #

class PersonalizedView(APIView):
    """
    GET /api/recommendations/for-me/
    Returns personalized recommendations based on the authenticated
    user's watch history and ratings.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        top_n = min(int(request.query_params.get('top_n', 10)), 50)
        use_semantic = request.query_params.get('semantic', 'false').lower() == 'true'

        recommender = get_recommender()
        results = recommender.personalized_for_user(
            request.user.id, top_n=top_n, use_semantic=use_semantic
        )

        if not results:
            return Response(
                {'message': 'Watch some movies first to get personalized recommendations.'},
                status=status.HTTP_200_OK,
            )

        enriched = _enrich(results)
        serializer = RecommendationResultSerializer(enriched, many=True)
        return Response(serializer.data)


# ------------------------------------------------------------------ #
#  Watch History
# ------------------------------------------------------------------ #

class WatchHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        history = UserWatchHistory.objects.filter(user=request.user).select_related('movie')
        serializer = WatchHistorySerializer(history, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Mark a movie as watched. Body: { "movie": <id>, "completed": true }"""
        serializer = WatchHistorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            # Rebuild recommender so new watch is reflected immediately
            get_recommender().build(force=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """Remove a movie from watch history. Body: { "movie": <id> }"""
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
        serializer = UserRatingSerializer(ratings, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Add or update a rating. Body: { "movie": <id>, "score": 8.5, "review": "..." }"""
        movie_id = request.data.get('movie')
        existing = UserRating.objects.filter(user=request.user, movie_id=movie_id).first()

        if existing:
            serializer = UserRatingSerializer(existing, data=request.data, partial=True)
        else:
            serializer = UserRatingSerializer(data=request.data)

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
        serializer = UserFavoriteSerializer(favorites, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Add to favorites. Body: { "movie": <id> }"""
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
