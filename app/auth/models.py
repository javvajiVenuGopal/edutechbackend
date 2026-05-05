from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime, timezone
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    mobile_number = Column(String, nullable=False)
    failed_attempts = Column(Integer, default=0)
    role = Column(String, default="seeker")
    otp = Column(String, nullable=True)
    otp_expiry = Column(DateTime, nullable=True)
    is_verified = Column(Boolean, default=False)
    last_seen = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True) 
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
