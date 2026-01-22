from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from models.base import Base


class SearchHistory(Base):
    __tablename__ = "search_histories"

    id = Column(String(36), primary_key=True, index=True)

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

    entity_id = Column(Integer, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Relationship
    history_user = relationship("User", back_populates="search_histories",)

