from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(title="PsychoGraph Backend")


@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "ok", "nlp_service": settings.NLP_SERVICE_URL}
