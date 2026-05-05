from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime
from datetime import datetime, timezone
from app.core.database import Base


class SeekerProfile(Base):
    __tablename__ = "seeker_profiles"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    location = Column(String)  # India / Abroad
    state = Column(String)     # NEW COLUMN
    college = Column(String)
    branch = Column(String)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class SeekerFeedback(Base):
    __tablename__ = "seeker_feedback"

    id = Column(Integer, primary_key=True)

    booking_id = Column(Integer, ForeignKey("bookings.id"))

    rating = Column(Integer)
    honest = Column(Boolean)
    recommend = Column(Boolean)
    comment = Column(String)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))