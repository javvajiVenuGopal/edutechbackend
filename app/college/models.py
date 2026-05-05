from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime, timezone
from app.core.database import Base


class CollegeFeedback(Base):
    __tablename__ = "college_feedbacks"

    id = Column(Integer, primary_key=True)

    booking_id = Column(Integer, ForeignKey("bookings.id"))

    guide_id = Column(Integer, ForeignKey("senior_guides.id"))

    faculty_rating = Column(Integer)

    placement_rating = Column(Integer)

    infrastructure_rating = Column(Integer)

    hidden_fees = Column(String)

    strict_attendance = Column(String)

    ragging_situation = Column(String)

    comments = Column(String)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))