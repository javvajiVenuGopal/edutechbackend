from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class SeniorGuide(Base):

    __tablename__ = "senior_guides"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    college_name = Column(String, nullable=False)
    branch = Column(String, nullable=False)
    year_of_study = Column(String)

    aadhaar_number = Column(String)
    aadhaar_path = Column(String)
    college_id_card_path = Column(String)
    hall_ticket_path = Column(String)

    status = Column(String, default="PENDING_VERIFICATION")
    is_verified = Column(Boolean, default=False)

    verified_by = Column(String, nullable=True)
    verified_at = Column(DateTime, nullable=True)

    test_score = Column(Integer, default=0)
    attempts = Column(Integer, default=0)

    unique_id = Column(String, nullable=True)

    rating = Column(Float, default=0)

    total_calls = Column(Integer, default=0)

    wallet_balance = Column(Integer, default=0)
    total_earned = Column(Integer, default=0)
    pending_withdrawal = Column(Integer, default=0)

    referral_code = Column(String, unique=True, nullable=True)
    referred_by = Column(Integer, nullable=True)

    referral_bonus = Column(Integer, default=0)
    referral_paid = Column(Boolean, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="senior_profile")


class GuideSlot(Base):

    __tablename__ = "guide_slots"

    id = Column(Integer, primary_key=True, index=True)

    guide_id = Column(
        Integer,
        ForeignKey("senior_guides.id"),
        nullable=False
    )

    time_slot = Column(String, nullable=False)

    status = Column(String, default="AVAILABLE")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
