from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.conversation import Conversation
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, db: Session):
        super().__init__(Conversation, db)

    def create_for_user(self, company_id: int, user_id: int, title: str) -> Conversation:
        conversation = Conversation(company_id=company_id, user_id=user_id, title=title)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_by_user(self, user_id: int, skip: int = 0, limit: int = 20) -> List[Conversation]:
        return (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_id_and_user(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        return (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .first()
        )
