"""
NLP Text Preprocessing Utilities
=================================
Centralises all NLTK-based text cleaning used by the recommendation engine.

Pipeline per document:
  1. Lowercase
  2. Remove punctuation / special chars
  3. Tokenise (NLTK word_tokenize)
  4. Remove English stopwords (NLTK)
  5. POS-tag tokens (NLTK averaged_perceptron_tagger_eng)
  6. Lemmatise with WordNetLemmatizer using the correct POS tag
  7. Filter short tokens (len < 2)
  8. Rejoin to a clean string

This produces vocabulary-reduced, semantically dense text that is fed into
the TF-IDF vectoriser and used for cosine similarity matching.
"""

import re
import logging

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
from nltk import pos_tag

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Initialise NLTK resources once at module level
# ------------------------------------------------------------------ #
_STOP_WORDS = set(stopwords.words('english'))
_LEMMATIZER = WordNetLemmatizer()


def _penn_to_wordnet(tag: str) -> str:
    """Convert Penn Treebank POS tag to WordNet POS constant."""
    if tag.startswith('J'):
        return wordnet.ADJ
    if tag.startswith('V'):
        return wordnet.VERB
    if tag.startswith('R'):
        return wordnet.ADV
    return wordnet.NOUN  # default


def preprocess(text: str) -> str:
    """
    Full NLP preprocessing pipeline.

    Input:  raw text string (plot + genre + keywords + actors …)
    Output: cleaned, lemmatised, stop-word-free token string

    Example:
        "Spider-Man fights villains in New York City" ->
        "spider man fight villain new york city"
    """
    if not text or not text.strip():
        return ''

    # 1. Lowercase
    text = text.lower()

    # 2. Keep letters, digits, spaces — remove punctuation
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    # 3. Tokenise
    tokens = word_tokenize(text)

    # 4. Remove stopwords and short tokens
    tokens = [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]

    # 5. POS tag
    tagged = pos_tag(tokens)

    # 6. Lemmatise with correct POS
    lemmatised = [
        _LEMMATIZER.lemmatize(word, pos=_penn_to_wordnet(tag))
        for word, tag in tagged
    ]

    # 7. Final filter — remove any token that became too short after lemmatisation
    lemmatised = [t for t in lemmatised if len(t) > 1]

    return ' '.join(lemmatised)


def extract_keywords(text: str, top_n: int = 20) -> list[str]:
    """
    Extract the most meaningful keywords from text using TF-IDF weighting
    on a single document (via frequency × rarity heuristic).

    Useful for the search/query endpoint to surface what a movie is about.
    """
    processed = preprocess(text)
    if not processed:
        return []

    tokens = processed.split()
    # Simple frequency count — caller can use TF-IDF for cross-doc weighting
    from collections import Counter
    freq = Counter(tokens)
    return [word for word, _ in freq.most_common(top_n)]
