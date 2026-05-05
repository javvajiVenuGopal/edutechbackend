import asyncio

from  app.notifications.service import create_notification
from fastapi import APIRouter, Depends, HTTPException,BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import Field

from app.core.database import get_db
from app.auth.utils import get_current_user
from app.rating.models import GuideRating
from app.rating.schemas import RatingCreateSchema
from app.booking.models import Booking
from app.calls.models import CallSession
from app.senior_guide.models import SeniorGuide


router = APIRouter(
    prefix="/rating",
    tags=["Guide Rating"]
)


# ---------------- SUBMIT RATING ----------------

@router.post("/submit/{booking_id}")
def submit_rating(  background_tasks: BackgroundTasks,
    booking_id: int,
    data: RatingCreateSchema,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    if booking.status != "COMPLETED":
        raise HTTPException(400, "Booking not completed")

    if booking.seeker_id != user["user_id"]:
        raise HTTPException(403, "Only seeker can rate guide")

    call_session = db.query(CallSession).filter(
        CallSession.booking_id == booking_id,
        CallSession.status == "COMPLETED"
    ).first()

    if not call_session:
        raise HTTPException(400, "Call not completed yet")

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == booking.guide_id
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    existing_rating = db.query(GuideRating).filter(
        GuideRating.booking_id == booking_id
    ).first()

    if existing_rating:
        raise HTTPException(400, "Rating already submitted")

    new_rating = GuideRating(
        booking_id=booking_id,
        guide_id=booking.guide_id,
        rating=data.rating,
        honesty=data.honesty,
        recommend=data.recommend,
        comments=data.comments
    )

    db.add(new_rating)

    previous_ratings = db.query(GuideRating).filter(
        GuideRating.guide_id == guide.id
    ).all()

    total_rating_sum = sum(r.rating for r in previous_ratings)

    new_average = (
        total_rating_sum + data.rating
    ) / (len(previous_ratings) + 1)

    guide.rating = round(new_average, 2)

    db.commit()
    
    background_tasks.add_task(
    create_notification,
        
        guide.user_id,
        "New Rating Received",
        f"You received a {data.rating}⭐ rating from a seeker"
    
)

    return {
        "message": "Rating submitted successfully",
        "average_rating": guide.rating
    }


# ---------------- GUIDE RATING SUMMARY ----------------
@router.get("/guide/{guide_id}")
def get_guide_rating(
    guide_id: int,
    db: Session = Depends(get_db)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == guide_id
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    ratings = db.query(GuideRating).filter(
        GuideRating.guide_id == guide_id
    ).all()

    return {
        "guide_id": guide_id,
        "guide_unique_id": guide.unique_id,
        "average_rating": guide.rating,
        "total_ratings": len(ratings)
    }


# ---------------- GUIDE RATING HISTORY ----------------

@router.get("/history/{guide_id}")
def rating_history(
    guide_id: int,
    db: Session = Depends(get_db)
):

    return db.query(GuideRating).filter(
        GuideRating.guide_id == guide_id
    ).all()


# ---------------- SEEKER MY RATINGS ----------------

@router.get("/my-ratings")
def my_ratings(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    bookings = db.query(Booking).filter(
        Booking.seeker_id == user["user_id"]
    ).all()

    booking_ids = [b.id for b in bookings]

    return db.query(GuideRating).filter(
        GuideRating.booking_id.in_(booking_ids)
    ).all()


# ---------------- GET BOOKING RATING ----------------

@router.get("/booking/{booking_id}")
def get_booking_rating(
    booking_id: int,
    db: Session = Depends(get_db)
):

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == booking.guide_id
    ).first()

    return {
        "booking_id": booking.id,
        "guide_unique_id": guide.unique_id if guide else None,
        "time_slot": booking.time_slot,
        "status": booking.status
    }


# ---------------- DELETE RATING (ADMIN) ----------------

@router.delete("/delete/{rating_id}")
def delete_rating(
    rating_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if user["role"] != "SUPERADMIN":
        raise HTTPException(403, "Only SUPERADMIN allowed")

    rating = db.query(GuideRating).filter(
        GuideRating.id == rating_id
    ).first()

    if not rating:
        raise HTTPException(404, "Rating not found")

    db.delete(rating)
    db.commit()

    return {"message": "Rating deleted successfully"}


# ---------------- ADMIN VIEW ALL RATINGS ----------------

@router.get("/admin/all")
def admin_all_ratings(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if user["role"] not in ["SUPERADMIN", "SUPPORT_ADMIN"]:
        raise HTTPException(403, "Access denied")

    return db.query(GuideRating).all()
