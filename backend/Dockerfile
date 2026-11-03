FROM python:3.12-slim
WORKDIR /srv
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app app
COPY backend/tools tools
COPY ml/features.py app/features.py
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
