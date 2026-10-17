"""Configuración de la aplicación, leída del entorno o del `.env`.

Dos decisiones de diseño que explican el comportamiento al arrancar:

- **Fallo temprano.** Los campos sin valor por defecto (`SECRET_KEY`,
  `DATABASE_URL`, las credenciales de AWS) son obligatorios: si falta alguno,
  la aplicación no llega a levantar. Se prefiere un error claro en el arranque
  a un `None` que reviente en la primera petición que lo necesite, cuando ya
  hay usuarios conectados.

- **`env_file=".env"` es una ruta relativa**, y pydantic-settings la resuelve
  contra el directorio de trabajo del proceso, no contra la ubicación de este
  archivo. Por eso el servidor debe lanzarse desde `api/`: hacerlo desde la
  raíz del repositorio encuentra los módulos pero no el `.env`, y la
  aplicación falla con errores de validación de campos obligatorios. Ver
  `COMO_ARRANCAR.md`.

La lista completa de variables, con descripciones, está en `.env.example`.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración de la aplicación, leída de variables de entorno o del `.env`
    (ver `.env.example` para la lista completa con descripciones).

    Los campos sin valor por defecto (`SECRET_KEY`, `DATABASE_URL`, las claves
    de OpenAI/Pinecone/AWS) son obligatorios: si falta alguno, la app falla al
    arrancar en vez de romper más tarde en la primera petición que lo use.
    """

    # ── Aplicación ────────────────────────────────────────────────────────────
    APP_NAME: str = "KnowledgeSpace"
    DEBUG: bool = False

    # ── Seguridad / JWT ───────────────────────────────────────────────────────
    SECRET_KEY: str                          # generar con: secrets.token_hex(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 horas

    # ── Base de datos ─────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── AWS S3 ────────────────────────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str

    # ── OpenAI ────────────────────────────────────────────────────────────────
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"

    # ── Pinecone ──────────────────────────────────────────────────────────────
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_INDEX_NAME: str = "knowspace"

    # ── Estrategia de recuperación ────────────────────────────────────────────
    # Qué configuración del pipeline atiende el chat. Los valores admitidos y
    # el porqué de cada uno están en `app/services/rag_factory.py`.
    #
    # El valor por defecto es "completo": descomposición de consultas con tope
    # de contexto y reparto equilibrado entre subpreguntas.
    #
    # Fue "descomposicion" hasta el 16 de octubre de 2026. Aquella resolvía la
    # cobertura de las preguntas compuestas pero ensanchaba sin recortar: una
    # pregunta doble enviaba nueve fragmentos al modelo en lugar de cinco, y
    # con tres subpreguntas habrían llegado quince. "completo" conserva el
    # reparto entre subpreguntas —3/2 en las seis parejas medidas, nunca 5/0—
    # con la mitad del contexto y el coste de la línea base.
    #
    # Queda declarado lo que la medición NO respalda: que responder con tres
    # fragmentos de una subpregunta baste donde antes había cinco. Comprobarlo
    # exigiría preguntas compuestas con respuesta de referencia, y el conjunto
    # de evaluación solo contiene una. Volver atrás es cambiar esta línea.
    RAG_CONFIGURACION: str = "descomposicion_acotada"

    # ── CORS ──────────────────────────────────────────────────────────────────
    # En producción sobreescribir con la URL real del frontend desplegado.
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:4200",
        "http://localhost:8080",
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]

    # ── Email / SMTP (opcional) ───────────────────────────────────────────────
    SMTP_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@knowspace.app"

    # ── Observabilidad / Langfuse (opcional) ──────────────────────────────────
    # Trazas del pipeline RAG: consulta, fragmentos recuperados con su
    # puntuación, contexto construido y generación.
    #
    # Está DESACTIVADO por defecto y las claves son opcionales a propósito.
    # Quien clone el repositorio debe poder levantar la aplicación sin dar de
    # alta una cuenta en un servicio de terceros; el resto de credenciales son
    # obligatorias porque sin ellas el sistema no funciona, mientras que sin
    # esta solo se pierden las trazas. El registro básico por `logger` sigue
    # estando disponible en cualquier caso.
    LANGFUSE_ENABLED: bool = False
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
