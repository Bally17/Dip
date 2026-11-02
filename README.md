# Dip

Príjem, analýza a vizualizácia fyziologických dát z VR simulátora strachu z výšky.

## Štruktúra

- backend: FastAPI, príjem dát a API
- ml: trénovanie a vyhodnotenie modelu
- frontend: React rozhranie

## Spustenie

```
cp .env.example .env
docker compose up --build
```

API beží na http://localhost:8000, kontrola na `/health`.
