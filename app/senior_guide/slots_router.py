from  app.notifications.service import create_notification
from fastapi import APIRouter, Depends, HTTPException,BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pydantic import BaseModel

from app.core.database import get_db
from app.auth.utils import get_current_user
from app.senior_guide.models import SeniorGuide
from app.availability.models import AvailabilitySlot
import asyncio

router = APIRouter(prefix="/slots", tags=["Guide Slots"])


# ===============================
# SCHEMA
# ===============================

class SlotCreate(BaseModel):
    start_time: datetime
    end_time: datetime


# ===============================
# ADD SLOT
# ===============================

@router.post("/add")
def add_slot(  background_tasks: BackgroundTasks,
    data: SlotCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if user["role"] != "senior_guide":
        raise HTTPException(403, "Only guides can add slots")

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    if data.start_time >= data.end_time:
        raise HTTPException(400, "Invalid time range")

    overlapping = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.guide_id == guide.id,
        AvailabilitySlot.start_time < data.end_time,
        AvailabilitySlot.end_time > data.start_time
    ).first()

    if overlapping:
        raise HTTPException(400, "Slot overlaps existing slot")

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
        "Your availability slot added successfully"
    
)

    return {"message": "Slot created successfully"}


# ===============================
# GUIDE OWN SLOTS
# ===============================

@router.get("/my")
def my_slots(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    slots = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.guide_id == guide.id
    ).all()

    return slots


# ===============================
# PUBLIC GUIDE SLOTS
# ===============================

@router.get("/{guide_id}")
def get_slots(
    guide_id: int,
    db: Session = Depends(get_db)
):

    slots = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.guide_id == guide_id,
        AvailabilitySlot.is_booked == False
    ).all()

    return slots


# ===============================
# UPDATE SLOT
# ===============================

@router.put("/update/{slot_id}")
def update_slot(  background_tasks: BackgroundTasks,
    slot_id: int,
    data: SlotCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    slot = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.id == slot_id
    ).first()

    if not slot:
        raise HTTPException(404, "Slot not found")

    if slot.guide_id != guide.id:
        raise HTTPException(403, "Not allowed")

    if slot.is_booked:
        raise HTTPException(400, "Booked slot cannot be edited")

    slot.start_time = data.start_time
    slot.end_time = data.end_time

    db.commit()
    background_tasks.add_task(
    create_notification,
        
        user["user_id"],
        "Slot Updated",
        "Your slot updated successfully"
    
)

    return {"message": "Slot updated successfully"}


# ===============================
# DELETE SLOT
# ===============================

@router.delete("/{slot_id}")
def delete_slot(  background_tasks: BackgroundTasks,
    slot_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

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
        "Your slot removed successfully"
    
)

    return {"message": "Slot deleted successfully"}
