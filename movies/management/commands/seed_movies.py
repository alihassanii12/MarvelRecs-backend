"""
Management command to seed the database from Marvel CSV files.

Usage:
    python manage.py seed_movies
    python manage.py seed_movies --dataset-dir /path/to/csvs
    python manage.py seed_movies --clear          # wipes existing data first
    python manage.py seed_movies --no-cast        # skip cast import
"""

import csv
import os
import logging
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_DATASET_DIR = os.path.join(settings.BASE_DIR, 'marvel_dataset')


def _clean_int(value, default=None):
    if value in (None, '', 'N/A', 'nan'):
        return default
    try:
        return int(float(str(value).replace(',', '').strip()))
    except (ValueError, TypeError):
        return default


def _clean_float(value, default=None):
    if value in (None, '', 'N/A', 'nan'):
        return default
    try:
        return float(str(value).replace(',', '').strip())
    except (ValueError, TypeError):
        return default


def _clean_bool(value, default=False):
    if value in (None, '', 'N/A'):
        return default
    return str(value).strip() in ('1', 'True', 'true', 'yes')


def _clean_str(value, default=None):
    if value in (None, 'N/A', 'nan', ''):
        return default
    return str(value).strip() or default


class Command(BaseCommand):
    help = 'Seed the database from Marvel CSV dataset files.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dataset-dir',
            type=str,
            default=DEFAULT_DATASET_DIR,
            help='Path to directory containing marvel CSV files.',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing Movie and Cast records before seeding.',
        )
        parser.add_argument(
            '--no-cast',
            action='store_true',
            help='Skip importing cast data.',
        )

    def handle(self, *args, **options):
        from movies.models import Movie, Cast

        dataset_dir = options['dataset_dir']
        master_path = os.path.join(dataset_dir, 'marvel_master.csv')
        cast_path = os.path.join(dataset_dir, 'marvel_cast.csv')

        if not os.path.exists(master_path):
            self.stderr.write(self.style.ERROR(f"File not found: {master_path}"))
            return

        if options['clear']:
            self.stdout.write("Clearing existing data…")
            Cast.objects.all().delete()
            Movie.objects.all().delete()
            self.stdout.write(self.style.WARNING("All movies and cast cleared."))

        # ---------------------------------------------------------------- #
        #  Import Movies
        # ---------------------------------------------------------------- #
        self.stdout.write("Importing movies from marvel_master.csv…")
        movies_created = 0
        movies_updated = 0

        with open(master_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                imdb_id = _clean_str(row.get('imdb_id'))

                defaults = {
                    'title':               _clean_str(row.get('title'), 'Unknown'),
                    'year':                _clean_int(row.get('year')),
                    'type':                _clean_str(row.get('type')),
                    'rated':               _clean_str(row.get('rated')),
                    'runtime_min':         _clean_int(row.get('runtime_min')),
                    'genre':               _clean_str(row.get('genre')),
                    'director':            _clean_str(row.get('director')),
                    'writer':              _clean_str(row.get('writer')),
                    'actors':              _clean_str(row.get('actors')),
                    'plot':                _clean_str(row.get('plot')),
                    'language':            _clean_str(row.get('language')),
                    'country':             _clean_str(row.get('country')),
                    'awards':              _clean_str(row.get('awards')),
                    'tagline':             _clean_str(row.get('tagline')),
                    'poster_url':          _clean_str(row.get('poster_url')),
                    'imdb_rating':         _clean_float(row.get('imdb_rating')),
                    'imdb_votes':          _clean_str(row.get('imdb_votes')),
                    'rt_score':            _clean_int(row.get('rt_score')),
                    'metacritic_score':    _clean_int(row.get('metacritic_score')),
                    'box_office_usd':      _clean_int(row.get('box_office_usd')),
                    'budget_usd':          _clean_int(row.get('budget_usd')),
                    'revenue_usd':         _clean_int(row.get('revenue_usd')),
                    'tmdb_id':             _clean_int(row.get('tmdb_id')),
                    'tmdb_rating':         _clean_float(row.get('tmdb_rating')),
                    'tmdb_votes':          _clean_int(row.get('tmdb_votes')),
                    'popularity':          _clean_float(row.get('popularity')),
                    'mcu_phase':           _clean_str(row.get('mcu_phase')),
                    'universe':            _clean_str(row.get('universe')),
                    'decade':              _clean_str(row.get('decade')),
                    'collection_name':     _clean_str(row.get('collection_name')),
                    'tmdb_genres':         _clean_str(row.get('tmdb_genres')),
                    'tmdb_keywords':       _clean_str(row.get('tmdb_keywords')),
                    'production':          _clean_str(row.get('production')),
                    'production_countries':_clean_str(row.get('production_countries')),
                    'spoken_languages':    _clean_str(row.get('spoken_languages')),
                    'is_animated':         _clean_bool(row.get('is_animated')),
                    'is_tv_series':        _clean_bool(row.get('is_tv_series')),
                    'is_mcu_canon':        _clean_bool(row.get('is_mcu_canon')),
                    'episode_count':       _clean_int(row.get('episode_count')),
                    'season_count':        _clean_int(row.get('season_count')),
                    'network':             _clean_str(row.get('network')),
                    'status':              _clean_str(row.get('status')),
                }

                if imdb_id:
                    obj, created = Movie.objects.update_or_create(
                        imdb_id=imdb_id, defaults=defaults
                    )
                else:
                    # No IMDB ID — match on title + year
                    obj, created = Movie.objects.update_or_create(
                        title=defaults['title'],
                        year=defaults.get('year'),
                        defaults=defaults,
                    )

                if created:
                    movies_created += 1
                else:
                    movies_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Movies done — created: {movies_created}, updated: {movies_updated}"
            )
        )

        # ---------------------------------------------------------------- #
        #  Import Cast
        # ---------------------------------------------------------------- #
        if options['no_cast'] or not os.path.exists(cast_path):
            if not os.path.exists(cast_path):
                self.stdout.write(self.style.WARNING("marvel_cast.csv not found — skipping cast."))
            return

        self.stdout.write("Importing cast from marvel_cast.csv…")
        cast_created = 0
        cast_skipped = 0

        # Build lookup: (title, year) -> Movie
        movie_lookup: dict[tuple, object] = {}
        for m in Movie.objects.only('id', 'title', 'year', 'tmdb_id'):
            movie_lookup[(m.title.lower(), m.year)] = m
            if m.tmdb_id:
                movie_lookup[('tmdb', m.tmdb_id)] = m

        cast_to_create = []

        with open(cast_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tmdb_id = _clean_int(row.get('tmdb_id'))
                title = _clean_str(row.get('title'), '')
                year = _clean_int(row.get('year'))

                movie = None
                if tmdb_id:
                    movie = movie_lookup.get(('tmdb', tmdb_id))
                if movie is None:
                    movie = movie_lookup.get((title.lower(), year))

                if movie is None:
                    cast_skipped += 1
                    continue

                cast_to_create.append(
                    Cast(
                        movie=movie,
                        actor_name=_clean_str(row.get('actor_name'), 'Unknown'),
                        character=_clean_str(row.get('character')),
                        cast_order=_clean_int(row.get('cast_order')),
                        actor_tmdb_id=_clean_int(row.get('actor_tmdb_id')),
                        popularity=_clean_float(row.get('popularity')),
                        profile_path=_clean_str(row.get('profile_path')),
                    )
                )

        # Bulk insert cast (ignore duplicates by clearing first if --clear was used)
        if cast_to_create:
            if options['clear']:
                Cast.objects.bulk_create(cast_to_create, batch_size=200)
            else:
                # Use ignore_conflicts to avoid duplicate errors on re-runs
                Cast.objects.bulk_create(cast_to_create, batch_size=200, ignore_conflicts=True)
            cast_created = len(cast_to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"Cast done — created: {cast_created}, skipped (no matching movie): {cast_skipped}"
            )
        )

        self.stdout.write(self.style.SUCCESS("\nAll done! Database seeded successfully."))
        self.stdout.write(
            "Next step: python manage.py build_embeddings  "
            "(builds NLP embeddings for recommendations)"
        )
