from django.db import models


class Movie(models.Model):
    # --- Identifiers ---
    imdb_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    tmdb_id = models.IntegerField(null=True, blank=True)

    # --- Core Info ---
    title = models.CharField(max_length=255)
    year = models.IntegerField(null=True, blank=True)
    type = models.CharField(max_length=50, null=True, blank=True)   # movie / series
    rated = models.CharField(max_length=20, null=True, blank=True)
    runtime_min = models.IntegerField(null=True, blank=True)
    genre = models.CharField(max_length=255, null=True, blank=True)
    director = models.TextField(null=True, blank=True)
    writer = models.TextField(null=True, blank=True)
    actors = models.TextField(null=True, blank=True)
    plot = models.TextField(null=True, blank=True)
    language = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    awards = models.TextField(null=True, blank=True)
    tagline = models.TextField(null=True, blank=True)
    poster_url = models.URLField(max_length=500, null=True, blank=True)

    # --- Ratings ---
    imdb_rating = models.FloatField(null=True, blank=True)
    imdb_votes = models.CharField(max_length=50, null=True, blank=True)
    rt_score = models.IntegerField(null=True, blank=True)
    metacritic_score = models.IntegerField(null=True, blank=True)
    tmdb_rating = models.FloatField(null=True, blank=True)
    tmdb_votes = models.IntegerField(null=True, blank=True)

    # --- Financials ---
    box_office_usd = models.BigIntegerField(null=True, blank=True)
    budget_usd = models.BigIntegerField(null=True, blank=True)
    revenue_usd = models.BigIntegerField(null=True, blank=True)

    # --- MCU / Universe ---
    mcu_phase = models.CharField(max_length=50, null=True, blank=True)
    universe = models.CharField(max_length=100, null=True, blank=True)
    decade = models.CharField(max_length=20, null=True, blank=True)
    collection_name = models.CharField(max_length=255, null=True, blank=True)
    tmdb_genres = models.CharField(max_length=255, null=True, blank=True)
    tmdb_keywords = models.TextField(null=True, blank=True)
    production = models.CharField(max_length=255, null=True, blank=True)
    production_countries = models.CharField(max_length=255, null=True, blank=True)
    spoken_languages = models.CharField(max_length=255, null=True, blank=True)

    # --- Flags ---
    is_animated = models.BooleanField(default=False)
    is_tv_series = models.BooleanField(default=False)
    is_mcu_canon = models.BooleanField(default=False)

    # --- TV-specific ---
    episode_count = models.IntegerField(null=True, blank=True)
    season_count = models.IntegerField(null=True, blank=True)
    network = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)

    # --- Popularity ---
    popularity = models.FloatField(null=True, blank=True)

    # --- NLP embedding cache (stored as JSON list of floats) ---
    embedding = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['year', 'title']

    def __str__(self):
        return f"{self.title} ({self.year})"

    @property
    def combined_text(self):
        """Text blob used for NLP similarity — plot + genre + keywords + actors."""
        parts = [
            self.title or '',
            self.plot or '',
            self.genre or '',
            self.tmdb_keywords or '',
            self.actors or '',
            self.tagline or '',
        ]
        return ' '.join(p for p in parts if p)


class Cast(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='cast_members')
    actor_name = models.CharField(max_length=255)
    character = models.CharField(max_length=255, null=True, blank=True)
    cast_order = models.IntegerField(null=True, blank=True)
    actor_tmdb_id = models.IntegerField(null=True, blank=True)
    popularity = models.FloatField(null=True, blank=True)
    profile_path = models.URLField(max_length=500, null=True, blank=True)

    class Meta:
        ordering = ['cast_order']

    def __str__(self):
        return f"{self.actor_name} as {self.character} in {self.movie.title}"
