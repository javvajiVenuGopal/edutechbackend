from ics import Calendar, Event
from datetime import datetime, timezone
import pytz


def create_calendar_invite(
    title,
    description,
    start_time,
    end_time,
    location="Online Call",
    file_path="invite.ics"
):

    calendar = Calendar()

    event = Event()
    event.name = title
    

    IST = pytz.timezone("Asia/Kolkata")

# convert IST → UTC
    start_time = IST.localize(start_time).astimezone(timezone.utc)
    end_time = IST.localize(end_time).astimezone(timezone.utc)
    event.description = description
    event.location = location

    calendar.events.add(event)

    with open(file_path, "w") as f:
        f.writelines(calendar)

    return file_path