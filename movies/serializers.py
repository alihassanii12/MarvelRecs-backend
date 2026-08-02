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
    """Full serializer with cast for detail views — deduped by actor+character."""
    cast_members = serializers.SerializerMethodField()

    def get_cast_members(self, obj):
        seen = set()
        result = []
        for c in obj.cast_members.all():
            key = (c.actor_name, c.character, c.cast_order)
            if key not in seen:
                seen.add(key)
                result.append(CastSerializer(c).data)
        return result

    class Meta:
        model = Movie
        exclude = ['embedding']
