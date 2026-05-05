from sqlalchemy import Column, Integer, DateTime, ForeignKey, Boolean, String
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class CallSession(Base):
    __tablename__ = "call_sessions"

    id = Column(Integer, primary_key=True)

    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True)

    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    duration_minutes = Column(Integer, default=0)

    status = Column(String, default="CREATED")
    

    auto_ended = Column(Boolean, default=False)

    reconnect_attempts = Column(Integer, default=0)

    refund_flag = Column(Boolean, default=False)
    refund_reason = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    booking = relationship("Booking")
