from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean
from datetime import datetime, timezone
from app.core.database import Base


class AvailabilitySlot(Base):
    __tablename__ = "availability_slots"

    id = Column(Integer, primary_key=True)

    guide_id = Column(Integer, ForeignKey("senior_guides.id"))

    start_time = Column(DateTime)

    end_time = Column(DateTime)

    is_booked = Column(Boolean, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))