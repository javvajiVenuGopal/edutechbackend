from sqlalchemy import Column, Integer, String, Boolean, DateTime,ForeignKey
from datetime import datetime, timezone
from app.core.database import Base


class Notification(Base):

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    title = Column(String)

    message = Column(String)

    is_read = Column(Boolean, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))