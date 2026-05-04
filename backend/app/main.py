from fastapi import FastAPI

from app.api.routers import methodologies, methodologies_public
from app.core.config import settings

app = FastAPI(title="PsychoGraph Backend")
app.include_router(methodologies.router)
app.include_router(methodologies_public.router)


@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "ok", "nlp_service": settings.NLP_SERVICE_URL}
