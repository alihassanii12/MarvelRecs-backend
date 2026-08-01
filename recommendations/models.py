from django.db import models
from django.conf import settings
from movies.models import Movie


class UserWatchHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='watch_history',
    )
    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE,
        related_name='watched_by',
    )
    watched_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=True)  # false = partial watch

    class Meta:
        unique_together = ('user', 'movie')
        ordering = ['-watched_at']

    def __str__(self):
        return f"{self.user.email} watched {self.movie.title}"


class UserRating(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ratings',
    )
    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE,
        related_name='user_ratings',
    )
    score = models.FloatField()          # 1.0 – 10.0
    review = models.TextField(null=True, blank=True)
    rated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'movie')
        ordering = ['-rated_at']

    def __str__(self):
        return f"{self.user.email} rated {self.movie.title}: {self.score}"


class UserFavorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorites',
    )
    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE,
        related_name='favorited_by',
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.email} favorited {self.movie.title}"
