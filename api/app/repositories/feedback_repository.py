import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from app.db.models.feedback import Feedback
from app.db.models.knowledge_gap import KnowledgeGap
from app.db.models.message import Message
from app.db.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.feedback import WeekStats, ThemeCount, SignalBand
from app.services.knowledge_gap_index_service import find_candidates


def _period_dates(period: str) -> tuple[datetime, datetime, Optional[datetime]]:
    """
    Returns (period_start, prev_period_start, period_end).
    period_end is None for 'month' (open-ended: until now).
    """
    now = datetime.now(timezone.utc)

    if period == "month":
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if period_start.month == 1:
            prev_start = period_start.replace(year=period_start.year - 1, month=12)
        else:
            prev_start = period_start.replace(month=period_start.month - 1)
        return period_start, prev_start, None

    elif period == "90d":
        period_start = now - timedelta(days=90)
        prev_start   = now - timedelta(days=180)
        return period_start, prev_start, None

    else:  # 12m
        if now.month == 12:
            period_start = now.replace(year=now.year - 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            period_start = now.replace(year=now.year - 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_start = period_start.replace(year=period_start.year - 1)
        return period_start, prev_start, None


class FeedbackRepository(BaseRepository[Feedback]):
    def __init__(self, db: Session):
        super().__init__(Feedback, db)

    # ── Listado ────────────────────────────────────────────────────────────

    def get_by_company(
        self,
        company_id: int,
        assistant_id: Optional[int] = None,
        rating: Optional[int] = None,
        period: str = "month",
        skip: int = 0,
        limit: int = 50,
    ) -> List[Feedback]:
        q = (
            self.db.query(Feedback)
            .options(
                joinedload(Feedback.assistant),
                joinedload(Feedback.user),
                joinedload(Feedback.knowledge_gap),
            )
            .filter(Feedback.company_id == company_id)
        )
        if assistant_id is not None:
            q = q.filter(Feedback.assistant_id == assistant_id)
        if rating is not None:
            q = q.filter(Feedback.rating == rating)

        # El período se recibía y no se aplicaba: `?period=90d` y `?period=12m`
        # devolvían lo mismo, y la exportación CSV heredaba el fallo porque
        # delega en este método. Se usa el mismo `_period_dates` que las
        # estadísticas, de modo que la tabla y los KPI hablan del mismo tramo
        # de tiempo.
        period_start, _, _ = _period_dates(period)
        q = q.filter(Feedback.created_at >= period_start)

        feedbacks = q.order_by(Feedback.created_at.desc()).offset(skip).limit(limit).all()
        self._enrich(feedbacks)
        return feedbacks

    def get_by_user(self, user_id: int, skip: int = 0, limit: int = 50) -> List[Feedback]:
        return (
            self.db.query(Feedback)
            .filter(Feedback.user_id == user_id)
            .order_by(Feedback.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_message(self, message_id: int) -> List[Feedback]:
        return (
            self.db.query(Feedback)
            .filter(Feedback.message_id == message_id)
            .order_by(Feedback.created_at.desc())
            .all()
        )

    # ── Estadísticas ───────────────────────────────────────────────────────

    def get_stats(
        self,
        company_id: int,
        assistant_id: Optional[int] = None,
        period: str = "month",
    ) -> Dict:
        now = datetime.now(timezone.utc)
        period_start, prev_start, _ = _period_dates(period)

        base_q = self.db.query(Feedback).filter(Feedback.company_id == company_id)
        if assistant_id is not None:
            base_q = base_q.filter(Feedback.assistant_id == assistant_id)

        all_fb = base_q.all()
        period_fb = [f for f in all_fb if f.created_at >= period_start]
        prev_fb   = [f for f in all_fb if prev_start <= f.created_at < period_start]

        ratings        = [f.rating for f in period_fb]
        total          = len(ratings)
        prev_ratings   = [f.rating for f in prev_fb]

        # KPI 1 – Satisfacción
        avg_period = round(sum(ratings) / total, 2) if total else 0.0
        avg_prev   = round(sum(prev_ratings) / len(prev_ratings), 2) if prev_ratings else None
        delta      = round(avg_period - avg_prev, 2) if avg_prev is not None else None

        # KPI 2 – % mensajes calificados en el período
        #
        # El denominador es siempre el total de la empresa, también cuando se
        # filtra por asistente: ni `Message` ni `Conversation` guardan
        # `assistant_id`, así que no hay forma de saber qué asistente generó un
        # mensaje. Solo el `Feedback` lo sabe, porque lo registra al calificar.
        #
        # Antes se intentaba filtrar con un join sobre `Conversation.assistant_id`,
        # una columna que no existe: cualquier consulta con `assistant_id`
        # respondía 500. Al quitarlo, el porcentaje queda comparando el feedback
        # de un asistente contra los mensajes de toda la empresa, así que con
        # filtro activo se devuelve `None` en vez de una cifra que no significa
        # nada.
        from app.db.models.message import Message
        from app.db.models.conversation import Conversation
        messages_count = (
            self.db.query(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .filter(
                Conversation.company_id == company_id,
                Message.role == "assistant",
                Message.created_at >= period_start,
            )
            .count()
        )
        rated_count = total
        if assistant_id is not None:
            rated_pct = None
        else:
            rated_pct = round((rated_count / messages_count * 100), 1) if messages_count else 0.0

        # KPI 3 & thumbs
        thumbs_up   = sum(1 for r in ratings if r >= 4)
        thumbs_down = sum(1 for r in ratings if r <= 2)
        negatives   = thumbs_down

        # KPI 4 – En seguimiento
        with_gap = sum(1 for f in period_fb if f.knowledge_gap_id is not None)

        # Distribución
        distribution = {i: ratings.count(i) for i in range(1, 6)}

        # Semanal (retenido para compat)
        from collections import defaultdict
        week_data: Dict[str, List[float]] = defaultdict(list)
        cutoff = now - timedelta(weeks=6)
        for f in period_fb:
            if f.created_at >= cutoff:
                iso = f.created_at.isocalendar()
                key = f"S{iso[1]}"
                week_data[key].append(f.rating)
        weeks = [
            WeekStats(week=k, avg=round(sum(v) / len(v), 2))
            for k, v in sorted(week_data.items())
        ]

        # Temas (vacío hasta implementar job de clasificación)
        themes: List[ThemeCount] = []

        # Banda de señal implícita (requiere tabla message_events; retorna ceros hasta implementar)
        signal_band = SignalBand()

        return {
            "total": total,
            "average_rating": avg_period,
            "average_rating_delta": delta,
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "satisfaction_rate": round((thumbs_up / total) * 100, 1) if total else 0.0,
            "distribution": distribution,
            "negatives": negatives,
            "with_gap": with_gap,
            "rated_count": rated_count,
            "messages_count": messages_count,
            "rated_pct": rated_pct,
            "signal_band": signal_band,
            "weeks": weeks,
            "themes": themes,
        }

    # ── Convertir en pregunta sin respuesta ───────────────────────────────

    def convert_to_gap(
        self,
        feedback: Feedback,
        question: str,
        company_id: int,
        user_id: int,
    ) -> KnowledgeGap:
        sources = (feedback.message.sources or []) if feedback.message else []
        scores = [s.get("score") for s in sources if isinstance(s, dict) and s.get("score") is not None]
        sources_count = len(sources)
        rag_score = round(max(scores), 3) if scores else None

        # "hard" = ningún chunk pasó el umbral (sin fuentes); "soft" = hay fuentes
        # pero el score no alcanzó para responder.
        gap_type = "hard" if sources_count == 0 else "soft"

        try:
            candidates = find_candidates(question, company_id, feedback.assistant_id) or None
        except Exception:
            candidates = None

        gap = KnowledgeGap(
            company_id=company_id,
            user_id=user_id,
            assistant_id=feedback.assistant_id,
            widget_id=feedback.widget_id,
            conversation_id=feedback.message.conversation_id if feedback.message else None,
            question=question,
            sources_count=sources_count,
            rag_score=rag_score,
            gap_type=gap_type,
            status="open",
            channel="widget" if feedback.widget_id else "chat",
            candidates=candidates,
        )
        self.db.add(gap)
        self.db.flush()

        feedback.knowledge_gap_id = gap.id
        feedback.status = "converted"
        self.db.commit()
        self.db.refresh(feedback)
        return gap

    # ── Exportar CSV ───────────────────────────────────────────────────────

    def get_export_csv(
        self,
        company_id: int,
        assistant_id: Optional[int] = None,
        period: str = "month",
    ) -> str:
        feedbacks = self.get_by_company(
            company_id, assistant_id=assistant_id, period=period, limit=10000
        )
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "fecha", "usuario", "asistente", "calificacion",
            "comentario", "conversation_id", "estado",
        ])
        for f in feedbacks:
            writer.writerow([
                f.id,
                f.created_at.strftime("%Y-%m-%d %H:%M"),
                getattr(f, "user_full_name", "") or "",
                f.assistant_name or "",
                f.rating,
                f.comment or "",
                getattr(f, "conversation_id", "") or "",
                f.status,
            ])
        return output.getvalue()

    # ── Enriquecimiento ────────────────────────────────────────────────────

    def _enrich(self, feedbacks: List[Feedback]) -> None:
        """Adjunta assistant_name, user_full_name, question, answer, conversation_id,
        sources_count, rag_score, knowledge_gap_status."""
        message_ids = [f.message_id for f in feedbacks if f.message_id]
        messages_by_id: Dict[int, Message] = {}
        user_msgs_by_conv: Dict[int, List[Message]] = {}

        if message_ids:
            messages = self.db.query(Message).filter(Message.id.in_(message_ids)).all()
            messages_by_id = {m.id: m for m in messages}

            conversation_ids = {m.conversation_id for m in messages}
            user_messages = (
                self.db.query(Message)
                .filter(
                    Message.conversation_id.in_(conversation_ids),
                    Message.role == "user",
                )
                .order_by(Message.id.asc())
                .all()
            )
            for um in user_messages:
                user_msgs_by_conv.setdefault(um.conversation_id, []).append(um)

        for f in feedbacks:
            f.assistant_name          = f.assistant.name if f.assistant else None
            f.user_full_name          = f.user.full_name if f.user else None
            f.knowledge_gap_status    = f.knowledge_gap.status if f.knowledge_gap else None

            msg = messages_by_id.get(f.message_id) if f.message_id else None
            if msg:
                f.answer           = msg.content[:240] + "…" if len(msg.content) > 240 else msg.content
                f.conversation_id  = msg.conversation_id
                sources            = msg.sources or []
                f.sources_count    = len(sources)
                scores = [s.get("score") for s in sources if isinstance(s, dict) and s.get("score") is not None]
                f.rag_score        = round(max(scores), 2) if scores else None

                prior = [m for m in user_msgs_by_conv.get(msg.conversation_id, []) if m.id < msg.id]
                f.question = prior[-1].content if prior else None
            else:
                f.answer           = None
                f.conversation_id  = None
                f.sources_count    = None
                f.rag_score        = None
                f.question         = None
