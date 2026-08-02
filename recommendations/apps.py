from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class RecommendationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "recommendations"

    def ready(self):
        """Pre-build the NLP recommender index when the server starts."""
        import os
        # Only run in the main process (not during migrate/management commands)
        if os.environ.get("RUN_MAIN") != "true" and not os.environ.get("RENDER"):
            return
        try:
            from recommendations.engine.recommender import get_recommender
            logger.info("Pre-building recommender index on startup…")
            get_recommender().build()
        except Exception as e:
            logger.warning(f"Recommender pre-build skipped: {e}")
