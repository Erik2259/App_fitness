from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración central de la aplicación, cargada desde variables de entorno.

    En Docker, estas variables llegan a través de `environment:` en docker-compose.yml.
    En Railway/producción llegan como variables del servicio.
    Fuera de contenedor (ej. Alembic local), se puede usar un archivo .env.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://fitness_user:fitness_pass@db:5432/fitness_coach"
    secret_key: str = "change-me-in-production"

    project_name: str = "AI Fitness & Performance Coach"
    api_v1_prefix: str = "/api/v1"

    # Crea las tablas al arrancar (Base.metadata.create_all). Práctico para un primer
    # despliegue sin migraciones; en un entorno serio se desactiva y se usa Alembic.
    auto_create_tables: bool = True

    # Orígenes permitidos por CORS (para que un frontend web/Flutter pueda llamar la API).
    # Se puede sobrescribir con una lista JSON en la variable CORS_ORIGINS.
    cors_origins: list[str] = ["*"]

    # --- Autenticación (JWT) ---
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 h

    # --- Fase 4: coach LLM (Anthropic Claude) ---
    # Si anthropic_api_key está vacío, el coach devuelve el prompt construido sin llamar
    # al modelo (modo "dry-run"), útil en desarrollo y tests sin gastar tokens.
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-5"
    llm_max_tokens: int = 1024

    @field_validator("database_url")
    @classmethod
    def _forzar_driver_asyncpg(cls, value: str) -> str:
        """Normaliza la URL de Postgres al driver async (asyncpg) que usa la app.

        Proveedores como Railway o Heroku entregan la URL como `postgresql://` (o el
        legado `postgres://`), que SQLAlchemy interpretaría con el driver síncrono.
        La app corre en modo async, así que forzamos `postgresql+asyncpg://`.
        """
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
