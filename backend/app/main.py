import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import models  # noqa: F401  (registra los modelos en Base.metadata)
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine

settings = get_settings()
logger = logging.getLogger("uvicorn.error")

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _db_host() -> str:
    """Host de la BD (sin credenciales) para poder mostrarlo en los logs."""
    try:
        return urlparse(settings.database_url).hostname or "?"
    except Exception:
        return "?"


async def _crear_tablas_con_reintentos(intentos: int = 8, espera: float = 2.5) -> None:
    """Crea las tablas reintentando: la BD puede tardar unos segundos en estar lista
    tras un despliegue (p. ej. la red privada de Railway al arrancar)."""
    ultimo_error: Exception | None = None
    for intento in range(1, intentos + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("BD lista (host=%s) tras %d intento(s).", _db_host(), intento)
            return
        except Exception as exc:  # noqa: BLE001
            ultimo_error = exc
            logger.warning(
                "No se pudo conectar a la BD (host=%s), intento %d/%d: %s",
                _db_host(), intento, intentos, exc.__class__.__name__,
            )
            await asyncio.sleep(espera)
    logger.error(
        "Fallo al conectar a la BD host=%s. Revisa DATABASE_URL en el servicio "
        "(en Railway debe referenciar el Postgres: ${{Postgres.DATABASE_URL}}).",
        _db_host(),
    )
    raise ultimo_error  # type: ignore[misc]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crea las tablas si no existen. En un primer despliegue (incluido Railway) esto
    # basta para arrancar; en un entorno con historial de esquema se desactiva
    # (auto_create_tables=False) y se gestiona con migraciones de Alembic.
    if settings.auto_create_tables:
        await _crear_tablas_con_reintentos()
    yield


app = FastAPI(
    title=settings.project_name,
    version="0.3.0",
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


@app.get("/", include_in_schema=False)
async def dashboard() -> FileResponse:
    """Sirve el dashboard web (SPA de una sola página) para abrir en el móvil."""
    return FileResponse(STATIC_DIR / "index.html")
