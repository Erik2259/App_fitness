import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import SexoEnum


class UsuarioBase(BaseModel):
    """Campos de perfil editables, compartidos entre creación y actualización."""

    nombre: str = Field(min_length=1, max_length=120)
    fecha_nacimiento: date | None = None
    sexo: SexoEnum | None = None
    altura_cm: float | None = Field(default=None, gt=0, lt=300)
    peso_kg: float | None = Field(default=None, gt=0, lt=500)

    # Datos fisiológicos base (referencia para el cálculo de TRIMP en Fase 2)
    fc_maxima: int | None = Field(default=None, gt=0, lt=250)
    fc_reposo: int | None = Field(default=None, gt=0, lt=200)
    ftp_running_watts: float | None = Field(default=None, gt=0)


class UsuarioCreate(UsuarioBase):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UsuarioUpdate(BaseModel):
    """Actualización parcial: todos los campos opcionales."""

    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    fecha_nacimiento: date | None = None
    sexo: SexoEnum | None = None
    altura_cm: float | None = Field(default=None, gt=0, lt=300)
    peso_kg: float | None = Field(default=None, gt=0, lt=500)
    fc_maxima: int | None = Field(default=None, gt=0, lt=250)
    fc_reposo: int | None = Field(default=None, gt=0, lt=200)
    ftp_running_watts: float | None = Field(default=None, gt=0)


class UsuarioOut(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    activo: bool
    created_at: datetime
    updated_at: datetime
