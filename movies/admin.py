from django.contrib import admin
from .models import Movie, Cast


class CastInline(admin.TabularInline):
    model = Cast
    extra = 0
    fields = ['actor_name', 'character', 'cast_order', 'popularity']
    ordering = ['cast_order']


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'year', 'type', 'universe', 'mcu_phase',
        'imdb_rating', 'tmdb_rating', 'is_mcu_canon', 'is_tv_series',
    ]
    list_filter = ['universe', 'mcu_phase', 'type', 'is_mcu_canon', 'is_tv_series', 'is_animated', 'decade']
    search_fields = ['title', 'actors', 'plot', 'tmdb_keywords']
    readonly_fields = ['created_at', 'updated_at', 'embedding']
    inlines = [CastInline]

    fieldsets = (
        ('Core Info', {
            'fields': ('title', 'year', 'type', 'rated', 'runtime_min', 'plot', 'tagline', 'poster_url')
        }),
        ('People', {
            'fields': ('director', 'writer', 'actors')
        }),
        ('Genres & Keywords', {
            'fields': ('genre', 'tmdb_genres', 'tmdb_keywords', 'collection_name')
        }),
        ('Ratings', {
            'fields': ('imdb_rating', 'imdb_votes', 'rt_score', 'metacritic_score', 'tmdb_rating', 'tmdb_votes')
        }),
        ('Financials', {
            'fields': ('box_office_usd', 'budget_usd', 'revenue_usd')
        }),
        ('MCU / Universe', {
            'fields': ('mcu_phase', 'universe', 'decade', 'is_mcu_canon', 'is_animated', 'is_tv_series')
        }),
        ('IDs & External', {
            'fields': ('imdb_id', 'tmdb_id', 'language', 'country', 'production', 'production_countries',
                       'spoken_languages', 'status', 'popularity')
        }),
        ('TV Series', {
            'fields': ('episode_count', 'season_count', 'network'),
            'classes': ('collapse',),
        }),
        ('NLP', {
            'fields': ('embedding',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Cast)
class CastAdmin(admin.ModelAdmin):
    list_display = ['actor_name', 'character', 'movie', 'cast_order', 'popularity']
    search_fields = ['actor_name', 'character', 'movie__title']
    list_filter = ['movie__universe']
