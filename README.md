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

- Prihlásenie cez `POST /auth/login`, JWT na 8 hodín, heslá v argon2. Po 5 nesprávnych heslách je meno na 15 minút zamknuté (odpoveď 429). Roly: `admin` (aj mazanie), `researcher` (čítanie).
- Simulátor sa pripája na `/ws/ingest?key=INGEST_KEY`. Kód účastníka aj id relácie sa pred uložením nahradia pseudonymom (HMAC s `PSEUDO_KEY`).
- `DELETE /participants/{kód}` zmaže účastníka a všetky jeho dáta.
- Stránky `/docs` a `/redoc` sú vypnuté. Opis rozhrania vráti `GET /openapi.json` len s platným tokenom.
- Surové vzorky sa mažú po 365 dňoch, sekundové priemery tepu sú v agregáte `samples_1s`.
- TLS ukončuje Caddy pred API a frontendom, pozri časť HTTPS.

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

## HTTPS

```
docker compose --profile tls up -d --build
```

Služba `web` (Caddy) zostaví frontend, podáva ho na https://localhost a požiadavky na `/api/*` posiela na API. Simulátor sa potom pripája na `wss://<adresa>/api/ws/ingest?key=INGEST_KEY`. Pre localhost si Caddy vystaví vlastný certifikát, prehliadač ho preto označí ako nedôveryhodný. Pri verejnej doméne nastav `SITE_ADDRESS=moja.domena.sk` v `.env` a certifikát sa získa z Let's Encrypt. Porty 8000 a 5432 pri verejnom nasadení nezverejňuj. Caddy odpovedá len na adresu zo `SITE_ADDRESS`. Ak sa má Quest pripojiť cez miestnu sieť, nastav ju na meno alebo IP servera a certifikát Caddy musí zariadenie prijať, inak použi verejnú doménu.

## Meranie príjmu a záťaže

```
docker compose run --rm --no-deps api python -m tools.bench --sessions 1 5 10 25 50 --seconds 60
```

Nástroj otvorí zadaný počet relácií, v každej posiela 25 vzoriek za sekundu a meria čas od odoslania po potvrdenie. Po každej úrovni porovná odoslané časové značky s uloženými (stratené, zdvojené) a testovacie dáta zmaže. Počas merania jeden klient číta vzorky a odhad raz za sekundu ako frontend. Voľba `--out súbor.json` uloží celé výsledky.
