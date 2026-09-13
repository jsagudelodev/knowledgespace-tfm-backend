from typing import Any, List, Optional

from sqlalchemy.orm import Session

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
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=sources,
            token_count=token_count,
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
