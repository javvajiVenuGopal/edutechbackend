from app.logs.models import ActivityLog


def create_log(db, user_email, action, module):

    log = ActivityLog(
        user_email=user_email,
        action=action,
        module=module
    )

    db.add(log)
    db.commit()