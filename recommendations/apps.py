from django.apps import AppConfig
import logging
import os

logger = logging.getLogger(__name__)


class RecommendationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "recommendations"

    def ready(self):
        """Pre-build the NLP recommender index when the server starts."""
        # Skip during management commands (migrate, seed_movies, etc.)
        import sys
        if any(cmd in sys.argv for cmd in [
            "migrate", "makemigrations", "seed_movies",
            "build_embeddings", "collectstatic", "check",
        ]):
            return

        # On Render: always build. Locally: only in main process
        is_render = bool(os.environ.get("RENDER"))
        is_main   = os.environ.get("RUN_MAIN") == "true"

        if not is_render and not is_main:
            return

        try:
            from recommendations.engine.recommender import get_recommender
            logger.info("Pre-building recommender on startup…")
            r = get_recommender()
            r.build()
            logger.info("Recommender ready.")
        except Exception as e:
            logger.warning(f"Recommender pre-build failed (will build on first request): {e}")
