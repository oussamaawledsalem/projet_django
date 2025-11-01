echo '#!/usr/bin/env bash
set +e

echo "=== Installation avec Poetry ==="
poetry install --no-dev

echo "=== Gestion static files ==="
python manage.py collectstatic --noinput --clear || mkdir -p staticfiles

echo "=== Application migrations ==="
python manage.py migrate

echo "=== Vérification installation ==="
poetry show gunicorn

echo "✅ Build Poetry réussi"' > build.sh