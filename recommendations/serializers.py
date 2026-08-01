from rest_framework import serializers
from movies.serializers import MovieListSerializer
from movies.models import Movie
from .models import UserWatchHistory, UserRating, UserFavorite


class WatchHistorySerializer(serializers.ModelSerializer):
    movie_detail = MovieListSerializer(source='movie', read_only=True)

    class Meta:
        model = UserWatchHistory
        fields = ['id', 'movie', 'movie_detail', 'watched_at', 'completed']
        read_only_fields = ['watched_at']


class UserRatingSerializer(serializers.ModelSerializer):
    movie_detail = MovieListSerializer(source='movie', read_only=True)

    class Meta:
        model = UserRating
        fields = ['id', 'movie', 'movie_detail', 'score', 'review', 'rated_at', 'updated_at']
        read_only_fields = ['rated_at', 'updated_at']

    def validate_score(self, value):
        if not (1.0 <= value <= 10.0):
            raise serializers.ValidationError("Score must be between 1.0 and 10.0.")
        return value


class UserFavoriteSerializer(serializers.ModelSerializer):
    movie_detail = MovieListSerializer(source='movie', read_only=True)

    class Meta:
        model = UserFavorite
        fields = ['id', 'movie', 'movie_detail', 'added_at']
        read_only_fields = ['added_at']


class RecommendationResultSerializer(serializers.Serializer):
    """Serializes a list of {movie_id, score} enriched with movie data."""
    movie = MovieListSerializer()
    score = serializers.FloatField()
