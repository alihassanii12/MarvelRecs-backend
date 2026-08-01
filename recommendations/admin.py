from django.contrib import admin
from .models import UserWatchHistory, UserRating, UserFavorite


@admin.register(UserWatchHistory)
class UserWatchHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'movie', 'watched_at', 'completed']
    list_filter = ['completed']
    search_fields = ['user__email', 'movie__title']


@admin.register(UserRating)
class UserRatingAdmin(admin.ModelAdmin):
    list_display = ['user', 'movie', 'score', 'rated_at']
    search_fields = ['user__email', 'movie__title']


@admin.register(UserFavorite)
class UserFavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'movie', 'added_at']
    search_fields = ['user__email', 'movie__title']
