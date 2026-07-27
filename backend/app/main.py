from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401  (registra los modelos en Base.metadata)
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Solo en desarrollo: crea las tablas automáticamente si no existen.
    # En producción, el esquema se gestiona exclusivamente con migraciones de Alembic.
    if settings.environment == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title=settings.project_name,
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["sistema"])
async def health_check() -> dict:
    """Verifica que la API esté viva y qué entorno está corriendo."""
    return {"status": "ok", "environment": settings.environment}
