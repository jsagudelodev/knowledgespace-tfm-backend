"""Primitivas de autenticación: hashing de contraseñas y firma de JWT.

Este módulo solo emite y valida tokens. Quién puede acceder a qué se decide en
`app/routers/v1/security.py`, que es donde se resuelve el usuario y de donde
sale el `company_id` que aísla cada inquilino.

Decisiones que conviene conocer antes de tocar nada:

- **HS256, clave simétrica.** El mismo `SECRET_KEY` firma y verifica. Sirve
  porque emisor y verificador son el mismo servicio; si algún día un tercero
  tuviera que validar tokens sin poder emitirlos, habría que pasar a RS256.

- **El JWT va firmado, no cifrado.** Cualquiera puede leer el payload
  decodificando base64; nadie puede alterarlo sin la clave. Por eso el token
  no transporta nada sensible: solo el email en `sub`.

- **24 horas de expiración y sin refresh token.** Al caducar se vuelve a hacer
  login. Un sistema de refresh añade revocación y rotación, complejidad que
  queda fuera del alcance de este trabajo.

- **Sin lista de revocación.** Un token robado es válido hasta que expira. Es
  la contrapartida de no mantener estado de sesión en el servidor.

- **bcrypt con `sha256_crypt` deprecado.** Ver el comentario de
  `pwd_context`: permite migrar los hashes antiguos sin pedir a nadie que
  cambie su contraseña.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# bcrypt es el esquema principal; sha256_crypt queda como deprecated para que
# las contraseñas antiguas sigan verificando y se re-hasheen con bcrypt en el
# próximo login (passlib lo hace automáticamente con needs_update).
pwd_context = CryptContext(schemes=["bcrypt", "sha256_crypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
