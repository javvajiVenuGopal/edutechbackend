from  app.auth.models import User
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.notifications.models import Notification
from app.auth.utils import get_current_user

from fastapi import BackgroundTasks

from app.notifications.service import create_notification

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)


# ---------------- ADMIN ACCESS CHECK ----------------

def admin_only(user):

    if user["role"] not in [
        "SUPERADMIN",
        "SUPPORT_ADMIN",
        "FINANCIAL_ADMIN"
    ]:
        raise HTTPException(403, "Admin access required")


# ---------------- ADMIN: GET ALL NOTIFICATIONS ----------------

@router.get("/all")
def get_notifications(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    return db.query(Notification).order_by(
        Notification.created_at.desc()
    ).offset(offset).limit(limit).all()


# ---------------- USER: GET MY NOTIFICATIONS ----------------

@router.get("/my")
def my_notifications(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    return db.query(Notification).filter(
        Notification.user_id == user["user_id"]
    ).order_by(Notification.created_at.desc()).all()


# ---------------- SINGLE NOTIFICATION ----------------

@router.get("/unread-count")
def unread_count(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    count = db.query(Notification).filter(
        Notification.user_id == user["user_id"],
        Notification.is_read == False
    ).count()

    return {"unread": count}

@router.get("/{notification_id}")
def get_notification(
    notification_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    notification = db.query(Notification).filter(
        Notification.id == notification_id
    ).first()

    if not notification:
        raise HTTPException(404, "Notification not found")

    return notification


# ---------------- UNREAD COUNT ----------------


# ---------------- MARK AS READ ----------------

@router.put("/read/{notification_id}")
def mark_as_read(
    notification_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    notification = db.query(Notification).filter(
        Notification.id == notification_id
    ).first()

    if not notification:
        raise HTTPException(404, "Notification not found")

    notification.is_read = True

    db.commit()

    return {"message": "Notification marked as read"}


# ---------------- MARK ALL AS READ ----------------

@router.put("/read-all")
def mark_all_as_read(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    db.query(Notification).filter(
        Notification.user_id == user["user_id"],
        Notification.is_read == False
    ).update({"is_read": True})

    db.commit()

    return {"message": "All notifications marked as read"}


# ---------------- DELETE NOTIFICATION ----------------

@router.delete("/delete/{notification_id}")
def delete_notification(
    notification_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    notification = db.query(Notification).filter(
        Notification.id == notification_id
    ).first()

    if not notification:
        raise HTTPException(404, "Notification not found")

    db.delete(notification)
    db.commit()

    return {"message": "Notification deleted successfully"}



@router.post("/broadcast")
def broadcast_notification(  background_tasks: BackgroundTasks,
    data: dict,
  
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    title = data.get("title")
    message = data.get("message")

    if not title or not message:
        raise HTTPException(400, "Title and message required")

    users = db.query(User).all()

    for u in users:

        background_tasks.add_task(
            create_notification,
        
            u.id,
            title,
            message
        )

    return {"message": "Broadcast notification sent to all users"}
