from apscheduler.schedulers.background import BackgroundScheduler
from app.core.database import SessionLocal
from app.services.reminder_service import check_and_send_reminders


scheduler = BackgroundScheduler()


def start_scheduler():

    def job():
        db = SessionLocal()
        try:
            check_and_send_reminders(db)
        finally:
            db.close()

    scheduler.add_job(job, "interval", minutes=1)

    scheduler.start()