# Déploiement DataEcon.Ci (dimensionné pour environ 5 000 utilisateurs par jour)

## Architecture
Nginx (port 5000) -> gunicorn (4 workers x 8 threads) -> PostgreSQL 15 (réglé), sauvegarde quotidienne dans `backups/`.

## Lancer
    docker compose up --build -d
    docker compose ps          (web et db doivent être "healthy")

## Réglages (compose.yaml, section web > environment)
- WEB_CONCURRENCY : nombre de processus (4 pour 4 vCPU / 8 Go)
- WEB_THREADS : threads par processus
- ANALYSIS_SLOTS : analyses lourdes simultanées (2 conseillé pour 4 vCPU ; les autres attendent en file)
- DB_POOL_SIZE / DB_MAX_OVERFLOW : connexions PostgreSQL par processus

## Serveur conseillé
4 vCPU, 8 Go de RAM, disque SSD 50 Go.

## Test de charge (avant ouverture au public)
    python tools/loadtest.py http://localhost:5000 200 60
(200 visiteurs simultanés pendant 60 secondes ; viser 0 erreur et p95 < 2 s)

## Cloudflare
Mettre le domaine derrière Cloudflare (offre gratuite) : cache, protection anti-attaque, HTTPS.

## Sauvegardes
Un dump compressé par jour, conservé 7 jours dans `backups/`. Copiez-les régulièrement hors du serveur.
