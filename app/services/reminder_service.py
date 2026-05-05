from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.booking.models import Booking
from app.auth.models import User
from app.email.email_service import send_calendar_invite


def check_and_send_reminders(db: Session):

    now = datetime.now(timezone.utc)

    upcoming_bookings = db.query(Booking).filter(
        Booking.payment_status == "PAID",
        Booking.status == "CONFIRMED"
    ).all()

    for booking in upcoming_bookings:

        start_time = datetime.fromisoformat(booking.time_slot)

        # ensure timezone aware
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        else:
            start_time = start_time.astimezone(timezone.utc)

        diff_minutes = (start_time - now).total_seconds() / 60

        if 29 <= diff_minutes <= 31:
            send_reminder(db, booking, "30 minutes")

        if 4 <= diff_minutes <= 6:
            send_reminder(db, booking, "5 minutes")


def send_reminder(db, booking, label):

    seeker = db.query(User).filter(
        User.id == booking.seeker_id
    ).first()

    guide = db.query(User).filter(
        User.id == booking.guide_id
    ).first()

    file_path = f"calendar_invites/invite_{booking.id}.ics"

    if seeker:
        send_calendar_invite(seeker.email, file_path)

    if guide:
        send_calendar_invite(guide.email, file_path)

    print(f"Reminder sent ({label}) for booking {booking.id}")