"""
Management command to compute and cache Sentence-Transformer embeddings
for all movies in the database.

Usage:
    python manage.py build_embeddings
    python manage.py build_embeddings --force   # recompute even if already cached
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Build and cache NLP embeddings for all movies (Sentence Transformers).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recompute embeddings even if already cached.',
        )

    def handle(self, *args, **options):
        from movies.models import Movie
        from recommendations.engine.recommender import get_recommender

        total = Movie.objects.count()
        if total == 0:
            self.stderr.write(self.style.ERROR(
                "No movies in DB. Run `python manage.py seed_movies` first."
            ))
            return

        if options['force']:
            self.stdout.write("Clearing cached embeddings…")
            Movie.objects.update(embedding=None)

        self.stdout.write(f"Building embeddings for {total} movies…")
        recommender = get_recommender()
        recommender.build(force=True)
        self.stdout.write(self.style.SUCCESS("Embeddings built and cached successfully."))
