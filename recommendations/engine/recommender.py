"""
NLP Recommendation Engine  (scikit-learn + NLTK)
=================================================

Cache strategy
--------------
On build(), after computing TF-IDF + embeddings the engine saves:

    cache/tfidf_vectorizer.pkl   — fitted TfidfVectorizer
    cache/tfidf_matrix.pkl       — sparse matrix (n_movies × vocab)
    cache/movie_ids.pkl          — list[int] matching matrix rows
    cache/embeddings.npy         — float32 ST embeddings (if available)

On next startup, build() loads these files instead of recomputing.
Cache is invalidated automatically when the movie count in the DB
differs from what was cached (i.e. after seed_movies is run).

Force rebuild:
    recommender.build(force=True)
    # or via management command:
    python manage.py build_embeddings --force
"""

import os
import pickle
import logging
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

logger = logging.getLogger(__name__)

# ── Cache directory lives next to this file ──────────────────────────
CACHE_DIR = Path(__file__).resolve().parent / "cache"

# ── File paths ────────────────────────────────────────────────────────
_F_VECTORIZER  = CACHE_DIR / "tfidf_vectorizer.pkl"
_F_MATRIX      = CACHE_DIR / "tfidf_matrix.pkl"
_F_IDS         = CACHE_DIR / "movie_ids.pkl"
_F_META        = CACHE_DIR / "meta.pkl"          # stores movie count for invalidation
_F_EMBEDDINGS  = CACHE_DIR / "embeddings.npy"

# ── Sentence Transformers (optional) ─────────────────────────────────
try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    logger.info(
        "sentence-transformers not installed — "
        "semantic mode falls back to TF-IDF. "
        "Install: pip install sentence-transformers"
    )


class MovieRecommender:
    """
    Lazy singleton recommender with .pkl cache.
    Call build() once; subsequent startups load from cache in ~1 second.
    """

    def __init__(self):
        self._movie_ids: list[int]       = []
        self._raw_texts: list[str]       = []
        self._processed_texts: list[str] = []

        self._vectorizer: TfidfVectorizer | None = None
        self._tfidf_matrix   = None
        self._tfidf_norm     = None

        self._st_model: "SentenceTransformer | None" = None
        self._embeddings: np.ndarray | None          = None

        self._built = False

    # ---------------------------------------------------------------- #
    #  Cache helpers
    # ---------------------------------------------------------------- #

    def _cache_valid(self, current_count: int) -> bool:
        """Return True if all cache files exist and movie count matches."""
        required = [_F_VECTORIZER, _F_MATRIX, _F_IDS, _F_META]
        if not all(f.exists() for f in required):
            return False
        try:
            meta = pickle.loads(_F_META.read_bytes())
            return meta.get("movie_count") == current_count
        except Exception:
            return False

    def _save_cache(self, movie_count: int) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            _F_IDS.write_bytes(pickle.dumps(self._movie_ids))
            _F_VECTORIZER.write_bytes(pickle.dumps(self._vectorizer))
            _F_MATRIX.write_bytes(pickle.dumps(self._tfidf_matrix))
            _F_META.write_bytes(pickle.dumps({"movie_count": movie_count}))

            if self._embeddings is not None:
                np.save(str(_F_EMBEDDINGS), self._embeddings)

            logger.info(f"Cache saved → {CACHE_DIR}")
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    def _load_cache(self) -> bool:
        """Load from .pkl files. Returns True on success."""
        try:
            self._movie_ids     = pickle.loads(_F_IDS.read_bytes())
            self._vectorizer    = pickle.loads(_F_VECTORIZER.read_bytes())
            self._tfidf_matrix  = pickle.loads(_F_MATRIX.read_bytes())
            self._tfidf_norm    = normalize(self._tfidf_matrix, norm="l2", copy=True)

            if _F_EMBEDDINGS.exists():
                self._embeddings = np.load(str(_F_EMBEDDINGS))
                logger.info(f"ST embeddings loaded from cache  shape={self._embeddings.shape}")

            logger.info(
                f"TF-IDF cache loaded — "
                f"{len(self._movie_ids)} movies, "
                f"vocab={len(self._vectorizer.vocabulary_)}"
            )
            return True
        except Exception as e:
            logger.warning(f"Cache load failed ({e}) — will rebuild.")
            return False

    def _clear_cache(self) -> None:
        for f in [_F_VECTORIZER, _F_MATRIX, _F_IDS, _F_META, _F_EMBEDDINGS]:
            try:
                f.unlink(missing_ok=True)
            except Exception:
                pass

    # ---------------------------------------------------------------- #
    #  Build
    # ---------------------------------------------------------------- #

    def build(self, force: bool = False) -> None:
        """
        Build the recommender index.

        1. If force=False and a valid cache exists → load from .pkl (fast).
        2. Otherwise → recompute from DB and save cache.
        """
        if self._built and not force:
            return

        from movies.models import Movie
        from .nlp_utils import preprocess

        current_count = Movie.objects.count()
        if current_count == 0:
            logger.warning("No movies in DB. Run seed_movies first.")
            return

        # ── Try loading cache ───────────────────────────────────────
        if not force and self._cache_valid(current_count):
            logger.info("Loading recommender from cache…")
            if self._load_cache():
                self._built = True
                return
        else:
            if force:
                logger.info("Force rebuild — clearing old cache…")
                self._clear_cache()
            else:
                logger.info("Cache missing or stale — rebuilding…")

        # ── Full rebuild ────────────────────────────────────────────
        movies = list(
            Movie.objects.only(
                "id", "title", "plot", "genre",
                "tmdb_keywords", "actors", "tagline",
                "universe", "mcu_phase", "embedding",
            )
        )

        self._movie_ids      = [m.id for m in movies]
        self._raw_texts      = [m.combined_text for m in movies]

        logger.info(f"NLTK preprocessing {len(movies)} texts…")
        self._processed_texts = [preprocess(t) for t in self._raw_texts]

        # ── TF-IDF ──────────────────────────────────────────────────
        self._vectorizer = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            sublinear_tf=True,
            max_features=15_000,
            min_df=1,
            max_df=0.95,
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(self._processed_texts)
        self._tfidf_norm   = normalize(self._tfidf_matrix, norm="l2", copy=True)
        logger.info(
            f"TF-IDF built — shape={self._tfidf_matrix.shape}  "
            f"vocab={len(self._vectorizer.vocabulary_)}"
        )

        # ── Sentence Transformer embeddings ─────────────────────────
        if ST_AVAILABLE:
            self._embeddings = self._load_or_compute_embeddings(movies)

        # ── Save cache ───────────────────────────────────────────────
        self._save_cache(current_count)

        self._built = True
        logger.info("Recommender ready.")

    # ---------------------------------------------------------------- #
    #  Sentence Transformer helper
    # ---------------------------------------------------------------- #

    def _load_or_compute_embeddings(self, movies) -> np.ndarray:
        cached = [m.embedding for m in movies]
        if all(e is not None for e in cached):
            logger.info("ST embeddings loaded from DB JSONField cache.")
            return np.array(cached, dtype=np.float32)

        logger.info("Computing ST embeddings (all-MiniLM-L6-v2)…")
        if self._st_model is None:
            self._st_model = SentenceTransformer("all-MiniLM-L6-v2")

        embeddings = self._st_model.encode(
            self._raw_texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

        from movies.models import Movie
        to_update = []
        for movie, emb in zip(movies, embeddings):
            movie.embedding = emb.tolist()
            to_update.append(movie)
        Movie.objects.bulk_update(to_update, ["embedding"], batch_size=100)
        logger.info("ST embeddings computed and cached in DB.")

        return embeddings.astype(np.float32)

    # ---------------------------------------------------------------- #
    #  Internal helpers
    # ---------------------------------------------------------------- #

    def _ensure_built(self) -> None:
        if not self._built:
            try:
                self.build()
            except Exception as e:
                logger.warning(f"Recommender build failed: {e}")
                self._built = False

    def _idx_of(self, movie_id: int) -> int | None:
        try:
            return self._movie_ids.index(movie_id)
        except ValueError:
            return None

    def _tfidf_scores(self, query_vec) -> np.ndarray:
        return cosine_similarity(query_vec, self._tfidf_matrix)[0]

    def _st_scores(self, query_vec: np.ndarray) -> np.ndarray:
        return cosine_similarity(query_vec.reshape(1, -1), self._embeddings)[0]

    def _top_results(
        self,
        scores: np.ndarray,
        exclude_ids: set[int],
        top_n: int,
    ) -> list[dict]:
        for mid in exclude_ids:
            idx = self._idx_of(mid)
            if idx is not None:
                scores[idx] = -1.0
        top_indices = np.argsort(scores)[::-1][:top_n]
        return [
            {"movie_id": self._movie_ids[i], "score": round(float(scores[i]), 4)}
            for i in top_indices
            if scores[i] > 0
        ]

    # ---------------------------------------------------------------- #
    #  Public API
    # ---------------------------------------------------------------- #

    def similar_to_movie(self, movie_id, top_n=10, use_semantic=False):
        try:
            self._ensure_built()
            if not self._built:
                return []
            idx = self._idx_of(movie_id)
            if idx is None:
                return []
            if use_semantic and self._embeddings is not None:
                scores = self._st_scores(self._embeddings[idx])
            else:
                scores = self._tfidf_scores(self._tfidf_matrix[idx])
            return self._top_results(scores, exclude_ids={movie_id}, top_n=top_n)
        except Exception as e:
            logger.warning(f"similar_to_movie error: {e}")
            return []

    def similar_to_query(self, query, top_n=10, use_semantic=False):
        try:
            self._ensure_built()
            if not self._built:
                return []
            from .nlp_utils import preprocess
            if use_semantic and self._embeddings is not None:
                if self._st_model is None:
                    self._st_model = SentenceTransformer("all-MiniLM-L6-v2")
                query_vec = self._st_model.encode([query], convert_to_numpy=True)[0]
                scores = self._st_scores(query_vec)
            else:
                cleaned = preprocess(query)
                if not cleaned:
                    return []
                query_vec = self._vectorizer.transform([cleaned])
                scores = self._tfidf_scores(query_vec)
            return self._top_results(scores, exclude_ids=set(), top_n=top_n)
        except Exception as e:
            logger.warning(f"similar_to_query error: {e}")
            return []

    def personalized_for_user(self, user_id, top_n=10, use_semantic=False):
        try:
            self._ensure_built()
            if not self._built:
                return []
            from recommendations.models import UserWatchHistory, UserRating
            watched_ids = set(
                UserWatchHistory.objects.filter(user_id=user_id)
                .values_list("movie_id", flat=True)
            )
            if not watched_ids:
                return []
            ratings = {
                r.movie_id: r.score
                for r in UserRating.objects.filter(user_id=user_id)
            }
            if use_semantic and self._embeddings is not None:
                dim     = self._embeddings.shape[1]
                profile = np.zeros(dim, dtype=np.float32)
                total_w = 0.0
                for mid in watched_ids:
                    idx = self._idx_of(mid)
                    if idx is None:
                        continue
                    w        = ratings.get(mid, 5.0)
                    profile += self._embeddings[idx] * w
                    total_w += w
                if total_w == 0:
                    return []
                profile /= total_w
                scores = self._st_scores(profile)
            else:
                dim     = self._tfidf_matrix.shape[1]
                profile = np.zeros(dim, dtype=np.float32)
                total_w = 0.0
                for mid in watched_ids:
                    idx = self._idx_of(mid)
                    if idx is None:
                        continue
                    w        = ratings.get(mid, 5.0)
                    profile += self._tfidf_matrix[idx].toarray()[0] * w
                    total_w += w
                if total_w == 0:
                    return []
                profile /= total_w
                from scipy.sparse import csr_matrix
                scores = cosine_similarity(
                    csr_matrix(profile.reshape(1, -1)), self._tfidf_matrix
                )[0]
            return self._top_results(scores, exclude_ids=watched_ids, top_n=top_n)
        except Exception as e:
            logger.warning(f"personalized_for_user error: {e}")
            return []

    def genre_based(self, genre: str, top_n: int = 10) -> list[dict]:
        return self.similar_to_query(genre, top_n=top_n, use_semantic=False)

    def get_vocab_stats(self) -> dict:
        self._ensure_built()
        return {
            "n_movies":          len(self._movie_ids),
            "vocab_size":        len(self._vectorizer.vocabulary_) if self._vectorizer else 0,
            "tfidf_shape":       list(self._tfidf_matrix.shape) if self._tfidf_matrix is not None else [],
            "semantic_available": self._embeddings is not None,
            "cache_dir":         str(CACHE_DIR),
            "cache_files":       [f.name for f in CACHE_DIR.iterdir()] if CACHE_DIR.exists() else [],
        }


# ------------------------------------------------------------------ #
#  Singleton
# ------------------------------------------------------------------ #
_recommender: MovieRecommender | None = None


def get_recommender() -> MovieRecommender:
    global _recommender
    if _recommender is None:
        _recommender = MovieRecommender()
    return _recommender
