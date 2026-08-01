web: python manage.py migrate && python manage.py seed_movies && gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
