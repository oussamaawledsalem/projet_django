# gunicorn.conf.py
import multiprocessing

# Nombre de workers
workers = 1
worker_class = "sync"

# Timeout augmenté pour le chargement des modèles IA
timeout = 120  # 2 minutes au lieu de 30s
graceful_timeout = 30
keepalive = 5

# Pour le plan gratuit Render
bind = "0.0.0.0:10000"