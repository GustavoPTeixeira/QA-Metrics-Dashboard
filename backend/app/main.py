from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.metrics import router as metrics_router
from app.api.ingest import router as ingest_router
from app.api.webhooks import router as webhooks_router

app = FastAPI(
    title="QA Metrics Dashboard API",
    description="API de Governança de Qualidade de Engenharia",
    version="1.0.0",
)

# Configuração de CORS para permitir requisições do Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra os endpoints com prefixo /api
app.include_router(metrics_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")
app.include_router(webhooks_router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "qa-metrics-dashboard"}