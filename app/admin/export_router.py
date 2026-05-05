from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
import pandas as pd
import os

from app.core.database import SessionLocal
from app.auth.utils import get_current_user
from app.booking.models import Booking
from app.auth.models import User
from app.wallet.models import WithdrawalRequest


router = APIRouter(
    prefix="/admin/export",
    tags=["Admin Export"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def admin_only(user):

    allowed_roles = [
        "SUPERADMIN",
        "ADMIN",
        "SUPPORT_ADMIN",
        "FINANCIAL_ADMIN",
        "CONTENT_ADMIN"
    ]

    if user.get("role") not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )


@router.get("/bookings")
def export_bookings(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    bookings = db.query(Booking).all()

    data = [
        {
            "Booking ID": b.id,
            "Seeker ID": b.seeker_id,
            "Guide ID": b.guide_id,
            "Status": b.status,
            "Payment": b.payment_status
        }
        for b in bookings
    ]

    os.makedirs("reports", exist_ok=True)

    file_path = "reports/bookings.xlsx"

    pd.DataFrame(data).to_excel(file_path, index=False)

    return FileResponse(file_path)


@router.get("/users")
def export_users(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    users = db.query(User).all()

    data = [
        {
            "User ID": u.id,
            "Email": u.email,
            "Role": u.role
        }
        for u in users
    ]

    file_path = "reports/users.xlsx"

    pd.DataFrame(data).to_excel(file_path, index=False)

    return FileResponse(file_path)


@router.get("/withdrawals")
def export_withdrawals(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    withdrawals = db.query(WithdrawalRequest).all()

    data = [
        {
            "Request ID": w.id,
            "Guide ID": w.guide_id,
            "Amount": w.amount,
            "Status": w.status
        }
        for w in withdrawals
    ]

    file_path = "reports/withdrawals.xlsx"

    pd.DataFrame(data).to_excel(file_path, index=False)

    return FileResponse(file_path)