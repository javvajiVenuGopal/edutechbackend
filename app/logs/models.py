from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone
from app.core.database import Base


class ActivityLog(Base):

    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True)

    user_email = Column(String)

    action = Column(String)

    module = Column(String)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))