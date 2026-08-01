#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

# NLTK data download
python -c "
import nltk
nltk.download('punkt_tab')
nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger_eng')
nltk.download('wordnet')
nltk.download('omw-1.4')
"

python manage.py collectstatic --no-input
python manage.py migrate
python manage.py seed_movies
