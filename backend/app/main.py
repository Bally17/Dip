from fastapi import FastAPI

app = FastAPI(title="Dip")


@app.get("/health")
def health():
    return {"status": "ok"}
