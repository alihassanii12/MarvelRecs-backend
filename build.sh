#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

# NLTK data — save to home dir so it's found at runtime
python -c "
import nltk
import os
nltk_dir = os.path.expanduser('~/nltk_data')
os.makedirs(nltk_dir, exist_ok=True)
nltk.download('punkt_tab',                  download_dir=nltk_dir)
nltk.download('stopwords',                  download_dir=nltk_dir)
nltk.download('averaged_perceptron_tagger_eng', download_dir=nltk_dir)
nltk.download('wordnet',                    download_dir=nltk_dir)
nltk.download('omw-1.4',                    download_dir=nltk_dir)
print('NLTK data downloaded to', nltk_dir)
"

python manage.py collectstatic --no-input
python manage.py migrate
python manage.py seed_movies

# Pre-build NLP cache so first request is fast
python manage.py build_embeddings
