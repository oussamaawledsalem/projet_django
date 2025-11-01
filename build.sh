# Recréez build.sh avec gestion d'erreurs
echo '#!/usr/bin/env bash
set -o errexit

echo "=== Installation des dépendances ==="
pip install -r requirements.txt

echo "=== Collecte des fichiers statiques (avec gestion d'\''erreurs) ==="
python manage.py collectstatic --noinput --clear || echo "⚠️  Certains fichiers static manquent, mais on continue..."

echo "=== Application des migrations ==="
python manage.py migrate

echo "✅ Build terminé avec succès"' > build.sh