from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime
from datetime import datetime, timezone
from app.core.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    seeker_id = Column(Integer, ForeignKey("users.id"))
    guide_id = Column(Integer, ForeignKey("senior_guides.id"))

    time_slot = Column(String)

    razorpay_payment_id = Column(String, nullable=True)
    razorpay_order_id = Column(String, nullable=True)

    amount = Column(Float, default=99.0)  # ✅ REQUIRED FOR REFUND

    reminder_30_sent = Column(Boolean, default=False)
    reminder_5_sent = Column(Boolean, default=False)

    status = Column(String, default="CONFIRMED")
    payment_status = Column(String, default="PENDING")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RefundRequest(Base):
    __tablename__ = "refund_requests"

    id = Column(Integer, primary_key=True, index=True)

    booking_id = Column(
        Integer,
        ForeignKey("bookings.id"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    reason = Column(String, nullable=False)

    status = Column(
        String,
        default="PENDING"
    )  # PENDING / APPROVED / REJECTED

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )