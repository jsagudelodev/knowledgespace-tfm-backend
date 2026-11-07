from typing import Any, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    def __init__(self, db: Session):
        super().__init__(Message, db)

    def create_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        sources: Optional[Any] = None,
        token_count: Optional[int] = None,
        assistant_id: Optional[int] = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=sources,
            token_count=token_count,
            assistant_id=assistant_id,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_by_conversation(self, conversation_id: int, skip: int = 0, limit: int = 50) -> List[Message]:
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def assistant_id_of_company(self, message_id: int, company_id: int) -> Optional[int]:
        """Qué asistente respondió un mensaje, solo si es de `company_id`.

        Lo usa el feedback para atribuir la calificación al asistente que de
        verdad respondió. El filtro por empresa impide que un `message_id`
        ajeno revele qué asistente usó otra organización. None si el mensaje
        no es de la empresa o es anterior a que se guardara el asistente."""
        fila = (
            self.db.query(Message.assistant_id)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .filter(Message.id == message_id, Conversation.company_id == company_id)
            .first()
        )
        return fila[0] if fila else None

    def count_by_company(self, company_id: int) -> int:
        """`messages` no tiene `company_id`: se llega a la empresa por su
        conversación, y ese join es lo que garantiza el aislamiento."""
        return (
            self.db.query(func.count(Message.id))
            .join(Conversation, Message.conversation_id == Conversation.id)
            .filter(Conversation.company_id == company_id)
            .scalar()
            or 0
        )
