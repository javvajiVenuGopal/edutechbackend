from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime, timezone
from app.core.database import Base


class GuideRating(Base):
    __tablename__ = "guide_ratings"

    id = Column(Integer, primary_key=True)

    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True)

    guide_id = Column(Integer, ForeignKey("senior_guides.id"))

    rating = Column(Integer, default=0)
    total_calls = Column(Integer, default=0)
    wallet_balance = Column(Integer, default=0)
    total_earned = Column(Integer, default=0)

    honesty = Column(String, nullable=False)

    recommend = Column(String, nullable=False)

    comments = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))