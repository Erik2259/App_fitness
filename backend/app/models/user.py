import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, Float, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.biometric import MetricaBiometrica
    from app.models.workout import Entrenamiento


class SexoEnum(str, enum.Enum):
    MASCULINO = "masculino"
    FEMENINO = "femenino"
    OTRO = "otro"


class Usuario(Base):
    """Atleta híbrido registrado en la app: datos de perfil y fisiológicos base.

    Los valores fisiológicos (fc_maxima, ftp_running_watts, etc.) son la referencia
    contra la que el backend calcula métricas de carga como el TRIMP — el LLM nunca
    hace estos cálculos, solo los interpreta una vez ya procesados.
    """

    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)

    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    sexo: Mapped[SexoEnum | None] = mapped_column(Enum(SexoEnum, name="sexo_enum"), nullable=True)

    altura_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    peso_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Datos fisiológicos base (referencia para cálculos de carga en Fase 2) ---
    fc_maxima: Mapped[int | None] = mapped_column(nullable=True)
    fc_reposo: Mapped[int | None] = mapped_column(nullable=True)
    ftp_running_watts: Mapped[float | None] = mapped_column(Float, nullable=True)

    activo: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    entrenamientos: Mapped[list["Entrenamiento"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )
    metricas_biometricas: Mapped[list["MetricaBiometrica"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Usuario id={self.id} email={self.email!r}>"
