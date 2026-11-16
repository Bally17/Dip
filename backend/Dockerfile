FROM python:3.12-slim
WORKDIR /srv
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app app
COPY backend/tools tools
COPY ml/features.py app/features.py
# Správa zo simulátora má stovky bajtov, väčšie rámce server odmietne.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--ws-max-size", "65536"]
