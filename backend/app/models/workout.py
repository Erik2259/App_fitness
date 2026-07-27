import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import Usuario


class TipoEntrenamientoEnum(str, enum.Enum):
    RUNNING = "running"
    INTERVALOS = "intervalos"
    FUERZA = "fuerza"
    CALISTENIA = "calistenia"
    OTRO = "otro"


class Entrenamiento(Base):
    """Una sesión de entrenamiento individual, recolectada desde Apple HealthKit.

    Incluye tanto métricas de esfuerzo cardiovascular (para calcular TRIMP) como
    biomecánicas de running (para el análisis de técnica del coach) y de fuerza
    (tonelaje), ya que un mismo atleta híbrido genera ambos tipos de sesión.
    """

    __tablename__ = "entrenamientos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )

    tipo: Mapped[TipoEntrenamientoEnum] = mapped_column(
        Enum(TipoEntrenamientoEnum, name="tipo_entrenamiento_enum"), nullable=False
    )
    fuente: Mapped[str] = mapped_column(String(50), default="healthkit")

    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duracion_segundos: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- Esfuerzo cardiovascular ---
    fc_promedio: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fc_maxima_sesion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calorias_activas: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Calculado en Python/Pandas en la Fase 2 a partir de fc_promedio, duración y fc_maxima
    # del usuario. El LLM solo recibe este valor ya calculado, nunca lo estima.
    trimp: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Biomecánica de running ---
    distancia_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    ritmo_promedio_seg_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    potencia_watts_promedio: Mapped[float | None] = mapped_column(Float, nullable=True)
    potencia_watts_pico: Mapped[float | None] = mapped_column(Float, nullable=True)
    cadencia_spm: Mapped[float | None] = mapped_column(Float, nullable=True)
    oscilacion_vertical_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    tiempo_contacto_suelo_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Fuerza / calistenia ---
    tonelaje_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    series_totales: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repeticiones_totales: Mapped[int | None] = mapped_column(Integer, nullable=True)
    peso_extra_kg: Mapped[float | None] = mapped_column(Float, nullable=True)  # chaleco/lastre

    # Payload crudo tal como llega desde HealthKit (JSON), para trazabilidad y recálculos futuros
    datos_crudos: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="entrenamientos")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Entrenamiento id={self.id} tipo={self.tipo} fecha_inicio={self.fecha_inicio}>"
