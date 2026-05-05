import asyncio

from  app.notifications.service import create_notification
from fastapi import APIRouter, Depends, HTTPException,BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from app.core.database import get_db
from app.booking.models import Booking
from app.rating.models import GuideRating
from app.college.models import CollegeFeedback
from app.reports.service import generate_report
from app.email.email_service import send_report_email
from app.auth.models import User
from app.auth.utils import get_current_user
from app.senior_guide.models import SeniorGuide


router = APIRouter(
    prefix="/report",
    tags=["Report System"]
)


# ---------------- ACCESS CHECK ----------------

def allowed_user(user, booking, db):

    if user["role"] == "SUPERADMIN":
        return True

    if booking.seeker_id == user["user_id"]:
        return True

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == booking.guide_id
    ).first()

    if guide and guide.user_id == user["user_id"]:
        return True

    return False


# ---------------- GENERATE REPORT ----------------

@router.get("/generate/{booking_id}")
def generate_pdf_report(  background_tasks: BackgroundTasks,
    booking_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    if booking.status != "COMPLETED":
        raise HTTPException(400, "Booking not completed yet")

    if not allowed_user(user, booking, db):
        raise HTTPException(403, "Access denied")

    rating = db.query(GuideRating).filter(
        GuideRating.booking_id == booking_id
    ).first()

    if not rating:
        raise HTTPException(400, "Rating not submitted yet")

    feedback = db.query(CollegeFeedback).filter(
        CollegeFeedback.booking_id == booking_id
    ).first()

    if not feedback:
        raise HTTPException(400, "College feedback not submitted yet")

    os.makedirs("reports", exist_ok=True)

    file_path = f"reports/report_{booking_id}.pdf"

    if not os.path.exists(file_path):

        generate_report(
            file_path=file_path,
            booking=booking,
            rating=rating,
            feedback=feedback
        )
        background_tasks.add_task(
        create_notification,
            
            booking.seeker_id,
            "Report Ready",
            "Your consultation report is ready to download"
        
    )
    return {
    "guide_id": booking.guide_id,
    "date": booking.time_slot.split("T")[0],
"time": booking.time_slot.split("T")[1][:5],
    "topic": "Career Guidance Session",
    "summary": f"Session completed successfully. Rating: {rating.rating}/5"
}


# ---------------- DOWNLOAD REPORT ----------------

@router.get("/download/{booking_id}")
def download_report(  background_tasks: BackgroundTasks,
    booking_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()
    print(booking.id)
    

    if not booking:
        
        raise HTTPException(404, "Booking not found")

    if not allowed_user(user, booking, db):
        print("Yes")
        raise HTTPException(403, "Access denied")

    file_path = f"reports/report_{booking_id}.pdf"

    if not os.path.exists(file_path):
        raise HTTPException(404, "Report not generated yet")
    
    background_tasks.add_task(
    create_notification,
        
        booking.seeker_id,
        "Report Downloaded",
        "You downloaded your consultation report"
    
)

    return FileResponse(
        path=file_path,
        filename=f"consultation_report_{booking_id}.pdf",
        media_type="application/pdf"
    )


# ---------------- REPORT STATUS ----------------

@router.get("/status/{booking_id}")
def report_status(
    booking_id: int,
    db: Session = Depends(get_db)
):

    file_path = f"reports/report_{booking_id}.pdf"

    return {
        "generated": os.path.exists(file_path)
    }


# ---------------- SEEKER REPORT HISTORY ----------------

@router.get("/my-reports")
def my_reports(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    bookings = db.query(Booking).filter(
        Booking.seeker_id == user["user_id"],
        Booking.status == "COMPLETED"
    ).all()

    return bookings


# ---------------- GUIDE REPORT HISTORY ----------------

@router.get("/guide-reports")
def guide_reports(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        return []

    bookings = db.query(Booking).filter(
        Booking.guide_id == guide.id,
        Booking.status == "COMPLETED"
    ).all()

    return bookings


# ---------------- RESEND REPORT EMAIL ----------------

@router.post("/resend-email/{booking_id}")
def resend_report_email(  background_tasks: BackgroundTasks,
    booking_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    if booking.seeker_id != user["user_id"]:
        raise HTTPException(403, "Only seeker allowed")

    file_path = f"reports/report_{booking_id}.pdf"

    if not os.path.exists(file_path):
        raise HTTPException(404, "Report not generated yet")

    seeker = db.query(User).filter(
        User.id == booking.seeker_id
    ).first()

    if not seeker:
        raise HTTPException(404, "User not found")

    send_report_email(seeker.email, file_path)
    background_tasks.add_task(
    create_notification,
        
        booking.seeker_id,
        "Report Email Sent",
        "Consultation report emailed successfully"
    
)

    return {"message": "Report email resent successfully"}
