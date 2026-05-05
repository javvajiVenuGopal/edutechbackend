from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.auth.utils import get_current_user
from app.auth.models import User
from app.senior_guide.models import SeniorGuide
from app.booking.models import Booking
from app.calls.models import CallSession
from app.wallet.models import WithdrawalRequest


router = APIRouter(
    prefix="/admin/analytics",
    tags=["Admin Analytics"]
)


# ---------------- ADMIN ACCESS CHECK ----------------

def admin_only(user):
    if user["role"] not in ["admin", "SUPERADMIN"]:
        raise HTTPException(403, "Admin access required")


# ---------------- DASHBOARD STATS ----------------

@router.get("/dashboard")
def dashboard_stats(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    total_users = db.query(User).count()

    total_guides = db.query(SeniorGuide).count()

    active_guides = db.query(SeniorGuide).filter(
        SeniorGuide.status == "ACTIVE"
    ).count()

    total_bookings = db.query(Booking).count()

    completed_calls = db.query(CallSession).filter(
        CallSession.status == "COMPLETED"
    ).count()

    pending_withdrawals = db.query(WithdrawalRequest).filter(
        WithdrawalRequest.status == "PENDING"
    ).count()

    approved_withdrawals = db.query(WithdrawalRequest).filter(
        WithdrawalRequest.status == "APPROVED"
    ).count()

    # revenue calculation (₹44 per call)
    total_revenue = completed_calls * 44
    
    return {
        "total_users": total_users,
        "total_guides": total_guides,
        "active_guides": active_guides,
        "total_bookings": total_bookings,
        "completed_calls": completed_calls,
        "total_revenue": total_revenue,
        "pending_withdrawals": pending_withdrawals,
        "approved_withdrawals": approved_withdrawals
    }