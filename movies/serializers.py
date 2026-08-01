from rest_framework import serializers
from .models import Movie, Cast


class CastSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cast
        fields = [
            'id', 'actor_name', 'character',
            'cast_order', 'actor_tmdb_id', 'popularity', 'profile_path',
        ]


class MovieListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    class Meta:
        model = Movie
        fields = [
            'id', 'title', 'year', 'type', 'genre', 'universe',
            'mcu_phase', 'imdb_rating', 'tmdb_rating', 'rt_score',
            'poster_url', 'is_mcu_canon', 'is_tv_series', 'popularity',
        ]


class MovieDetailSerializer(serializers.ModelSerializer):
    """Full serializer with cast for detail views."""
    cast_members = CastSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        exclude = ['embedding']  # don't expose raw embedding vectors
