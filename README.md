# Dip

Príjem, analýza a vizualizácia fyziologických dát z VR simulátora strachu z výšky.

## Štruktúra

- backend: FastAPI, príjem dát a API
- ml: trénovanie a vyhodnotenie modelu
- frontend: React rozhranie

## Spustenie

```
cp .env.example .env   # a zmeň heslá a kľúče
docker compose up --build
```

API beží na http://localhost:8000, kontrola na `/health`. Prvý admin sa vytvorí z `ADMIN_USER` a `ADMIN_PASSWORD`.

## Mock simulátor a testy

```
docker compose exec api python -m tools.mock_sender --seconds 30
```

Testy: `pip install -r backend/requirements-dev.txt`, potom `pytest backend/tests` z priečinka `backend`.

## Model

Model sa trénuje v `ml` (`python train.py --data <CEAP-360VR>`) a ukladá do `ml/artifacts/model.joblib`. Docker Compose ho pripojí do API. Odhad pre reláciu: `GET /sessions/{session}/risk`.

## Bezpečnosť a údaje

- Prihlásenie cez `POST /auth/login`, JWT na 8 hodín, heslá v argon2. Roly: `admin` (aj mazanie), `researcher` (čítanie).
- Simulátor sa pripája na `/ws/ingest?key=INGEST_KEY`. Kód účastníka aj id relácie sa pred uložením nahradia pseudonymom (HMAC s `PSEUDO_KEY`).
- `DELETE /participants/{kód}` zmaže účastníka a všetky jeho dáta.
- Surové vzorky sa mažú po 365 dňoch, sekundové priemery tepu sú v agregáte `samples_1s`.
- TLS rieši reverzný proxy pred API a frontendom, v tomto repozitári nie je.

## Frontend

```
cd frontend
npm install
npm run dev     # http://localhost:5173
npm test        # testy výpočtov nad časovými radmi
```

Adresu API mení premenná `VITE_API_URL` (predvolene http://localhost:8000). Po prihlásení sa vľavo zobrazia relácie, živá relácia sa obnovuje každú sekundu.

## Demo bez simulátora

```
docker compose exec -d api python -m tools.mock_sender --seconds 180 --loop
```

Mock sender posiela vymyslené dáta, slúžia len na ukážku rozhrania.
