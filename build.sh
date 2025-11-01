#!/usr/bin/env bash
set -e

echo "=== Installation des dépendances ==="
pip install -r requirements.txt

echo "=== Collecte des fichiers statiques ==="
python manage.py collectstatic --noinput --clear || mkdir -p staticfiles

echo "=== Application des migrations ==="
python manage.py migrate

echo "✅ Build réussi"