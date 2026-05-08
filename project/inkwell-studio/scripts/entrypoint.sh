#!/bin/sh
set -e

umask 002

mkdir -p /app/staticfiles /app/media
if [ "$(id -u)" = "0" ]; then
	chown -R app:app /app/staticfiles /app/media || true
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application --bind 0.0.0.0:8000
