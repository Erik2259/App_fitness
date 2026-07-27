from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (registra los modelos en Base.metadata)
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crea las tablas si no existen. En un primer despliegue (incluido Railway) esto
    # basta para arrancar; en un entorno con historial de esquema se desactiva
    # (auto_create_tables=False) y se gestiona con migraciones de Alembic.
    if settings.auto_create_tables:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title=settings.project_name,
    version="0.2.0",
    lifespan=lifespan,
)

# CORS: usamos tokens en el header Authorization (no cookies), así que no necesitamos
# allow_credentials; eso permite dejar allow_origins="*" sin infringir la spec de CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["sistema"])
async def health_check() -> dict:
    """Verifica que la API esté viva y qué entorno está corriendo."""
    return {"status": "ok", "environment": settings.environment}
