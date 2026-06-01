import uuid

from sqlalchemy import Column, String, ForeignKey, DateTime, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from models.base import Base


class SearchHistory(Base):
    __tablename__ = "search_histories"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))

    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    query = Column(String(255), nullable=False)

    entity = Column(
        String(50),
        nullable=False
        # user | salon | service | hashtag | post | query
    )

    entity_id = Column(String(64), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Relationship
    history_user = relationship("User", back_populates="search_histories",)

    __table_args__ = (
        Index("ix_search_histories_user_created", "user_id", "created_at"),
        Index("ix_search_histories_user_query", "user_id", "query"),
        Index("ix_search_histories_entity_entity_id", "entity", "entity_id"),
    )
