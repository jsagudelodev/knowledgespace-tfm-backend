"""Registro del costo de inferencia (tokens y USD) de cada llamada a OpenAI.
Instrumentado en `chat.py` (respuestas del LLM) y `documents.py` (embeddings al
subir un documento). Alimenta los endpoints de `/api/v1/cost-tracking`."""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.cost_tracking import CostTracking

logger = logging.getLogger("uvicorn.error")

# USD por cada 1.000 tokens. Fuente: precios públicos de OpenAI.
# Modelo desconocido → se usa gpt-4o-mini como aproximación conservadora
# antes que fallar el registro del costo.
PRICING = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "text-embedding-3-small": {"input": 0.00002, "output": 0.0},
    "text-embedding-3-large": {"input": 0.00013, "output": 0.0},
}

# Modelos de chat que un asistente puede usar: solo los que tienen precio.
# El fallback de arriba evita que falle el registro, pero registra un modelo
# desconocido con el precio de gpt-4o-mini sin avisar; validar el modelo al
# crear o editar el asistente impide llegar a ese caso.
MODELOS_CHAT = frozenset(m for m in PRICING if not m.startswith("text-embedding"))


class CostTrackingService:
    """Registra el costo de cada llamada a OpenAI (chat o embeddings).

    Efecto secundario contable — un fallo aquí no debe interrumpir la
    respuesta al usuario ni el procesamiento de documentos, porque el costo
    ya se incurrió en OpenAI aunque no se logre persistir el registro.
    """

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def calculate_cost(model: str, input_tokens: int, output_tokens: int = 0) -> float:
        pricing = PRICING.get(model, PRICING["gpt-4o-mini"])
        input_cost = (input_tokens / 1_000) * pricing.get("input", 0)
        output_cost = (output_tokens / 1_000) * pricing.get("output", 0)
        return round(input_cost + output_cost, 6)

    def record(
        self,
        company_id: int,
        model: str,
        operation: str,
        input_tokens: int,
        output_tokens: int = 0,
        user_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        assistant_id: Optional[int] = None,
        document_id: Optional[int] = None,
        duration_ms: Optional[int] = None,
    ) -> Optional[float]:
        """Devuelve el costo calculado (USD) para mostrarlo de inmediato al
        caller — p. ej. junto a la respuesta del chat — o None si falló el
        registro (el costo ya se incurrió en OpenAI de todos modos).

        `duration_ms` es opcional porque no todas las llamadas se miden: la
        operación 'chat' siempre la trae (el total de `generate_response`), y
        desde el 2026-10-24 también las auxiliares (descomposición,
        reordenado), cronometradas alrededor de su propia llamada al
        proveedor. La de 'embedding' sigue sin medirse por separado —es una
        llamada rápida y ya corre dentro del total de 'chat'—, así que ahí
        queda en `None`."""
        try:
            cost = self.calculate_cost(model, input_tokens, output_tokens)
            self.db.add(CostTracking(
                company_id=company_id,
                user_id=user_id,
                conversation_id=conversation_id,
                assistant_id=assistant_id,
                document_id=document_id,
                model=model,
                operation=operation,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_cost=cost,
                duration_ms=duration_ms,
            ))
            self.db.commit()
            return cost
        except Exception:
            logger.warning("[CostTracking] No se pudo registrar el costo", exc_info=True)
            try:
                self.db.rollback()
            except Exception:
                pass
            return None
