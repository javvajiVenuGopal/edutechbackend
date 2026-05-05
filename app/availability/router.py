import asyncio

from  app.notifications.service import create_notification
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timezone

from pydantic import BaseModel

from app.core.database import get_db
from app.auth.utils import get_current_user
from app.availability.models import AvailabilitySlot
from app.senior_guide.models import SeniorGuide
from app.booking.models import Booking
from fastapi import BackgroundTasks

router = APIRouter(prefix="/availability", tags=["Availability"])


# ===============================
# REQUEST SCHEMA
# ===============================

class SlotCreate(BaseModel):
    start_time: datetime
    end_time: datetime


# ===============================
# CREATE SLOT (GUIDE)
# ===============================

@router.post("/create")
def create_slot(
    data: SlotCreate,background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if user["role"] != "senior_guide":
        raise HTTPException(403, "Only guides can create slots")

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide profile not found")

    
    start = data.start_time
    end = data.end_time

    # normalize timezone
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    start = start.astimezone(timezone.utc)
    end = end.astimezone(timezone.utc)

    # validation
    if start < datetime.now(timezone.utc):
        raise HTTPException(400, "Cannot create past slot")

    if end <= start:
        raise HTTPException(400, "End time must be after start time")

    duration = (data.end_time - data.start_time).total_seconds() / 60

    if duration < 15:
        raise HTTPException(400, "Minimum slot duration is 15 minutes")

    overlapping = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.guide_id == guide.id,
        AvailabilitySlot.start_time < data.end_time,
        AvailabilitySlot.end_time > data.start_time
    ).first()

    if overlapping:
        raise HTTPException(400, "Slot overlaps with existing slot")

    slot = AvailabilitySlot(
        guide_id=guide.id,
        start_time=data.start_time,
        end_time=data.end_time,
        is_booked=False
    )

    db.add(slot)
    db.commit()
    background_tasks.add_task(
    create_notification,
    
    user["user_id"],
    "Slot Created",
    "Your availability slot created successfully"
)
    return {"message": "Slot created successfully"}

# ===============================
# GET GUIDE SLOTS
# ===============================

@router.get("/guide/{guide_id}")
def get_slots(
    guide_id: int,
    db: Session = Depends(get_db)
):

    return db.query(AvailabilitySlot).filter(
        AvailabilitySlot.guide_id == guide_id,
        AvailabilitySlot.is_booked == False,
AvailabilitySlot.start_time > datetime.now(timezone.utc)
    ).all()


# ===============================
# GUIDE OWN SLOTS
# ===============================

@router.get("/my-slots")
def my_slots(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        return []

    return db.query(AvailabilitySlot).filter(
        AvailabilitySlot.guide_id == guide.id
    ).all()


# ===============================
# BOOK SLOT (SEEKER)
# ===============================

@router.put("/book/{slot_id}")
def book_slot(
    slot_id: int,background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if user["role"] != "seeker":
        raise HTTPException(403, "Only seekers can book slots")

    slot = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.id == slot_id
    ).with_for_update().first()

    if not slot:
        raise HTTPException(404, "Slot not found")

    now = datetime.now(timezone.utc)

    if slot.start_time.replace(tzinfo=None) <= now:
        raise HTTPException(400, "Slot time already expired")
    
    if slot.is_booked:
        raise HTTPException(400, "Slot already booked")
    existing_booking = db.query(Booking).filter(
    Booking.seeker_id == user["user_id"],
    Booking.time_slot == str(slot.start_time),
    Booking.status.in_(["CONFIRMED", "COMPLETED"])
    ).first()
    
    if existing_booking:
        raise HTTPException(400, "Booking already exists")

    slot.is_booked = True

    booking = Booking(
        seeker_id=user["user_id"],
        guide_id=slot.guide_id,
        time_slot = slot.start_time.replace(tzinfo=timezone.utc).isoformat(),
        status="CREATED",
        payment_status="PENDING"
    )

    db.add(booking)
    db.commit()
    guide = db.query(SeniorGuide).filter(
    SeniorGuide.id == slot.guide_id
).first()

# notify seeker
    background_tasks.add_task(
        create_notification,
            
            user["user_id"],
            "Slot Booked",
            "Your session slot booked successfully"
        
    )

    # notify guide
    background_tasks.add_task(
        create_notification,
            
            guide.user_id,
            "New Slot Booking",
            "A seeker booked your available slot"
        
    )

    return {
        "message": "Slot booked successfully",
        "booking_id": booking.id
    }


# ===============================
# CANCEL SLOT BOOKING (SEEKER)
# ===============================

@router.put("/cancel/{slot_id}")
def cancel_slot_booking(background_tasks:BackgroundTasks,
    slot_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    slot = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.id == slot_id
    ).first()

    if not slot:
        raise HTTPException(404, "Slot not found")

    booking = db.query(Booking).filter(
        Booking.guide_id == slot.guide_id,
        Booking.seeker_id == user["user_id"],
        Booking.time_slot == str(slot.start_time),
        Booking.status == "CREATED"
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    slot.is_booked = False
    booking.status = "CANCELLED"

    db.commit()
    guide = db.query(SeniorGuide).filter(
    SeniorGuide.id == slot.guide_id
).first()

# notify seeker
    background_tasks.add_task(
        create_notification,
            
            user["user_id"],
            "Slot Booking Cancelled",
            "Your booked slot cancelled successfully"
        
    )

    # notify guide
    background_tasks.add_task(
        create_notification,
            
            guide.user_id,
            "Booking Cancelled",
            "A seeker cancelled the booked slot"
        
)

    return {"message": "Slot booking cancelled successfully"}


# ===============================
# SEEKER UPCOMING BOOKINGS
# ===============================

@router.get("/seeker/upcoming")
def seeker_upcoming_slots(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    return db.query(Booking).filter(
        Booking.seeker_id == user["user_id"],
        Booking.status == "CONFIRMED"
    ).all()


# ===============================
# DELETE SLOT (GUIDE)
# ===============================

@router.delete("/delete/{slot_id}")
def delete_slot(
    slot_id: int,background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if user["role"] != "senior_guide":
        raise HTTPException(403, "Only guides can delete slots")

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    slot = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.id == slot_id
    ).first()

    if not slot:
        raise HTTPException(404, "Slot not found")

    if slot.guide_id != guide.id:
        raise HTTPException(403, "Not allowed")

    if slot.is_booked:
        raise HTTPException(400, "Cannot delete booked slot")

    db.delete(slot)
    db.commit()
    background_tasks.add_task(
    create_notification,
        
        user["user_id"],
        "Slot Deleted",
        "Your availability slot removed successfully"
    
)

    return {"message": "Slot deleted successfully"}
