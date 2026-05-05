from app.notifications.models import Notification
from app.notifications.ws_manager import manager
from app.core.database import SessionLocal



def create_notification(user_id, title, message):

    db = SessionLocal()

    try:
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message
        )

        db.add(notification)
        db.commit()

        manager.send_to_user_sync(
            user_id,
            {
                "title": title,
                "message": message
            }
        )

    finally:
        db.close()
