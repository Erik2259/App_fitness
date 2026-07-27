"""Utilidades de seguridad: hashing de contraseñas (bcrypt) y tokens JWT.

Se usa la librería `bcrypt` directamente (no passlib): passlib 1.7.4 es incompatible
con bcrypt >= 5 y falla al inicializarse. bcrypt solo considera los primeros 72 bytes
de la contraseña, así que se trunca a esa longitud de forma explícita.

Se mantiene sin dependencias de FastAPI ni de la base de datos para poder testearse
de forma aislada.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

# Límite intrínseco de bcrypt: solo usa los primeros 72 bytes de la contraseña.
_BCRYPT_MAX_BYTES = 72


def _to_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de una contraseña en texto plano."""
    return bcrypt.hashpw(_to_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Comprueba una contraseña en texto plano contra su hash almacenado."""
    try:
        return bcrypt.checkpw(_to_bytes(plain_password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Genera un JWT firmado cuyo `sub` es el id del usuario."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    """Devuelve el `sub` (id de usuario) del token, o None si es inválido/expiró."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    return payload.get("sub")
