from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración central de la aplicación, cargada desde variables de entorno.

    En Docker, estas variables llegan a través de `environment:` en docker-compose.yml.
    Fuera de Docker (ej. corriendo Alembic localmente), se puede usar un archivo .env.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://fitness_user:fitness_pass@db:5432/fitness_coach"
    secret_key: str = "change-me-in-production"

    project_name: str = "AI Fitness & Performance Coach"
    api_v1_prefix: str = "/api/v1"

    # --- Autenticación (JWT) ---
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 h

    # --- Fase 4: coach LLM (Anthropic Claude) ---
    # Si anthropic_api_key está vacío, el coach devuelve el prompt construido sin llamar
    # al modelo (modo "dry-run"), útil en desarrollo y tests sin gastar tokens.
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-5"
    llm_max_tokens: int = 1024

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
