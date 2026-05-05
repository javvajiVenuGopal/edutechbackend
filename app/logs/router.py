from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.auth.utils import get_current_user
from app.logs.models import ActivityLog


router = APIRouter(prefix="/logs", tags=["Activity Logs"])


# ---------------- ADMIN ACCESS CHECK ----------------

def admin_only(user):

    allowed_roles = [
        "SUPERADMIN",
        "ADMIN",
        "FINANCIAL_ADMIN",
        "SUPPORT_ADMIN",
        "CONTENT_ADMIN"
    ]

    if user["role"] not in allowed_roles:
        raise HTTPException(403, "Access denied")


# ---------------- VIEW ALL LOGS ----------------

@router.get("/all")
def view_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    logs = db.query(ActivityLog).order_by(
        ActivityLog.created_at.desc()
    ).offset(offset).limit(limit).all()

    return logs


# ---------------- VIEW SINGLE LOG ----------------

@router.get("/{log_id}")
def get_log(
    log_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    log = db.query(ActivityLog).filter(
        ActivityLog.id == log_id
    ).first()

    if not log:
        raise HTTPException(404, "Log not found")

    return log


# ---------------- FILTER LOGS ----------------

@router.get("/filter")
def filter_logs(
    user_email: str = None,
    log_type: str = None,
    start_date: datetime = None,
    end_date: datetime = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    query = db.query(ActivityLog)

    if user_email:
        query = query.filter(ActivityLog.user_email == user_email)

    if log_type:
        query = query.filter(ActivityLog.log_type == log_type)

    if start_date:
        query = query.filter(ActivityLog.created_at >= start_date)

    if end_date:
        query = query.filter(ActivityLog.created_at <= end_date)

    return query.order_by(ActivityLog.created_at.desc()).all()


# ---------------- DELETE SINGLE LOG ----------------

@router.delete("/delete/{log_id}")
def delete_log(
    log_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    log = db.query(ActivityLog).filter(
        ActivityLog.id == log_id
    ).first()

    if not log:
        raise HTTPException(404, "Log not found")

    db.delete(log)
    db.commit()

    return {"message": "Log deleted successfully"}


# ---------------- CLEAR ALL LOGS ----------------

@router.delete("/clear")
def clear_logs(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if user["role"] != "SUPERADMIN":
        raise HTTPException(403, "Only SUPERADMIN allowed")

    db.query(ActivityLog).delete()
    db.commit()

    return {"message": "All logs cleared successfully"}