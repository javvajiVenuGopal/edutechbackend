import asyncio
from typing import Optional
from app.wallet.models import Referral, WalletTransaction
from app.booking.models import Booking
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form,BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.auth.models import User
from app.core.database import get_db
from app.senior_guide.models import GuideSlot, SeniorGuide
from app.auth.utils import get_current_user,validate_file,validate_size
from app.senior_guide.schemas import TestSubmitSchema
from app.services.file_upload import save_file
from app.notifications.service import create_notification
from app.admin.models import EligibilityQuestion

router = APIRouter(prefix="/guides", tags=["Senior Guides"])


# ---------------------------------------------------
# APPLY AS SENIOR GUIDE
# ---------------------------------------------------
@router.post("/apply")
def apply_guide(
    background_tasks: BackgroundTasks,
    college_name: str = Form(...),
    branch: str = Form(...),
    year_of_study: str = Form(...),
    aadhaar_number: str = Form(...),
    referral_code: Optional[str] = Form(None),

    aadhaar: UploadFile = File(...),
    college_id: UploadFile = File(...),
    hall_ticket: UploadFile = File(...),

    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if user["role"] != "seeker":
        raise HTTPException(403, "Only seekers can apply")

    if not aadhaar_number.isdigit() or len(aadhaar_number) != 12:
        raise HTTPException(400, "Invalid Aadhaar number")


    # ================= CHECK EXISTING GUIDE =================

    existing = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()


    # ================= REFERRAL VALIDATION =================

    referrer = None

    if referral_code:

        referrer = db.query(SeniorGuide).filter(
            SeniorGuide.referral_code == referral_code
        ).first()

        if not referrer:
            raise HTTPException(400, "Invalid referral code")

        if referrer.user_id == user["user_id"]:
            raise HTTPException(400, "Cannot use your own referral code")

        already_used = db.query(Referral).filter(
            Referral.referred_user_id == user["user_id"],
            Referral.status == "APPROVED"
        ).first()

        if already_used:
            raise HTTPException(400, "Referral already applied")


    # ================= SAVE FILES =================

    validate_file(aadhaar.filename)
    validate_file(college_id.filename)
    validate_file(hall_ticket.filename)
    validate_size(aadhaar)
    validate_size(college_id)
    validate_size(hall_ticket)
    
    aadhaar_path = save_file(aadhaar, "aadhaar")
    college_path = save_file(college_id, "college_id")
    hall_path = save_file(hall_ticket, "hall_ticket")
    aadhaar_exists = db.query(SeniorGuide).filter(
    SeniorGuide.aadhaar_number == aadhaar_number
).first()
    
    if aadhaar_exists and aadhaar_exists.user_id != user["user_id"]:
        raise HTTPException(400, "Aadhaar already registered")


    # ================= UPDATE EXISTING RECORD =================

    if existing:

        existing.college_name = college_name
        existing.branch = branch
        existing.year_of_study = year_of_study
        existing.aadhaar_number = aadhaar_number
        existing.aadhaar_path = aadhaar_path
        existing.college_id_card_path = college_path
        existing.hall_ticket_path = hall_path
        existing.referred_by = referrer.id if referrer else None
        existing.status = "PENDING_VERIFICATION"
        existing.attempts = 0
        existing.created_at = datetime.now(timezone.utc)

        guide = existing

    else:

        guide = SeniorGuide(
            user_id=user["user_id"],
            college_name=college_name,
            branch=branch,
            year_of_study=year_of_study,
            aadhaar_number=aadhaar_number,
            aadhaar_path=aadhaar_path,
            college_id_card_path=college_path,
            hall_ticket_path=hall_path,
            referred_by=referrer.id if referrer else None,
            referral_paid=False,
            status="PENDING_VERIFICATION",
            attempts=0,
            created_at=datetime.now(timezone.utc)
        )

        db.add(guide)


    # ================= CREATE / UPDATE REFERRAL =================

    if referrer:

        referral = db.query(Referral).filter(
            Referral.referred_user_id == user["user_id"]
        ).first()

        if referral:
            referral.referrer_id = referrer.id
            referral.status = "PENDING"
        else:
            referral = Referral(
                referrer_id=referrer.id,
                referred_user_id=user["user_id"],
                amount=25,
                status="PENDING"
            )
            db.add(referral)


    # ================= SAVE =================

    db.commit()
    db.refresh(guide)


    background_tasks.add_task(
        create_notification,
        
        user["user_id"],
        "Application Submitted",
        "Your guide application submitted successfully"
    )


    return {
        "message": "Application submitted successfully",
        "status": guide.status
    }


@router.get("/test/questions")
def get_questions(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    if guide.status != "ELIGIBLE_TEST":
        raise HTTPException(400, "Not eligible")

    questions = db.query(EligibilityQuestion).filter(
        EligibilityQuestion.is_active == True
    ).all()

    return [
        {"id": q.id, "question": q.question}
        for q in questions
    ]

@router.post("/test/submit")
def submit_test(
    background_tasks: BackgroundTasks,
    data: TestSubmitSchema,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    if guide.status == "ACTIVE":
        raise HTTPException(400, "Already passed")

    if guide.status == "REJECTED":
        raise HTTPException(400, "Attempts exhausted")

    if guide.status != "ELIGIBLE_TEST":
        raise HTTPException(400, "Not eligible")

    # fetch questions from DB
    questions = db.query(EligibilityQuestion).filter(
        EligibilityQuestion.is_active == True
    ).all()

    if not questions:
        raise HTTPException(400, "No questions available")

    guide.attempts += 1

    # map answers dynamically
    submitted_answers = {
        "1": data.q1,
        "2": data.q2,
        "3": data.q3
    }

    score = sum(
        1 for q in questions
        if submitted_answers.get(str(q.id), "").strip().lower()
        == q.correct_answer.lower()
    )

    percentage = (score / len(questions)) * 100
    guide.test_score = percentage

    # PASS CONDITION
    if percentage >= 60:

        guide.status = "ACTIVE"

        if not guide.unique_id:
            guide.unique_id = f"SG-{1000 + guide.id}"

        if not guide.referral_code:
            guide.referral_code = f"REF-SG-{guide.id}"

        if guide.wallet_balance is None:
            guide.wallet_balance = 0

        if guide.total_earned is None:
            guide.total_earned = 0

        user_obj = db.query(User).filter(
            User.id == user["user_id"]
        ).first()

        if user_obj:
            user_obj.role = "senior_guide"

        # activation notification ONLY when passed
        background_tasks.add_task(
            create_notification,
            
            user["user_id"],
            "Guide Activated",
            "Congratulations! You are now an active senior guide"
        )

    # FAIL 3 TIMES → AUTO REJECT
    elif guide.attempts >= 3:
        guide.status = "REJECTED"

    db.commit()

    return {
        "score": percentage,
        "status": guide.status,
        "attempts": guide.attempts
    }

# ---------------------------------------------------
# GUIDE PROFILE
# ---------------------------------------------------
@router.get("/profile")
def get_profile(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    # if guide not applied yet
    if not guide:
        return {
            "status": "NOT_APPLIED"
        }

    return {
        "unique_id": guide.unique_id,
        "college_name": guide.college_name,
        "branch": guide.branch,
        "year_of_study": guide.year_of_study,
        "rating": guide.rating,
        "total_calls": guide.total_calls,
        "status": guide.status
    }


# ---------------------------------------------------
# UPDATE GUIDE PROFILE
# ---------------------------------------------------
@router.put("/profile/update")
def update_profile(  background_tasks: BackgroundTasks,
    branch: str = Form(...),
    year_of_study: str = Form(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    guide.branch = branch
    guide.year_of_study = year_of_study

    db.commit()
    background_tasks.add_task(
    create_notification,
        
        user["user_id"],
        "Profile Updated",
        "Your guide profile updated successfully"
    
)

    return {"message": "Profile updated successfully"}


# ---------------------------------------------------
# DASHBOARD SUMMARY
# ---------------------------------------------------
@router.get("/dashboard")
def dashboard(user=Depends(get_current_user), db: Session = Depends(get_db)):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    return {
        "unique_id": guide.unique_id,
        "status": guide.status,
        "wallet_balance": guide.wallet_balance,
        "rating": guide.rating,
        "total_calls": guide.total_calls,
        "referral_code": guide.referral_code
    }


# ---------------------------------------------------
# EARNINGS SUMMARY
# ---------------------------------------------------
@router.get("/earnings")
def earnings(user=Depends(get_current_user), db: Session = Depends(get_db)):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    return {
        "wallet_balance": guide.wallet_balance,
        "total_earned": guide.total_earned,
        "referral_bonus": guide.referral_bonus
    }


# ---------------------------------------------------
# GUIDE STATS
# ---------------------------------------------------


# ---------------------------------------------------
# REFERRAL STATS
# ---------------------------------------------------
@router.get("/referrals")
def referrals(user=Depends(get_current_user), db: Session = Depends(get_db)):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    referrals = db.query(SeniorGuide).filter(
        SeniorGuide.referred_by == str(guide.id)
    ).all()

    return {
    "total_calls": guide.total_calls or 0,
    "rating": guide.rating or 0,
    "students": guide.total_calls or 0,
    "status": guide.status
}


# ---------------------------------------------------
# REFERRAL LIST
# ---------------------------------------------------
@router.get("/referrals/list")
def referral_list(user=Depends(get_current_user), db: Session = Depends(get_db)):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    return db.query(SeniorGuide).filter(
        SeniorGuide.referred_by == str(guide.id)
    ).all()

# FIRST this route
@router.get("/my-status")
def my_status(user=Depends(get_current_user), db: Session = Depends(get_db)):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    return {
        "status": guide.status,
        "test_score": guide.test_score
    }
@router.get("/stats")
def guide_stats(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    total_students = db.query(Booking).filter(
        Booking.guide_id == guide.id
    ).count()

    return {
        "total_calls": guide.total_calls or 0,
        "students": total_students,
        "rating": guide.rating or 0
    }
# AFTER that this route
@router.get("/{guide_id}")
def get_guide_profile(
    guide_id: int,
    db: Session = Depends(get_db)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == guide_id
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    return guide


@router.get("/slots/booked")
def get_booked_slots(date: str, db: Session = Depends(get_db)):

    slots = db.query(GuideSlot).filter(
        GuideSlot.status == "BOOKED"
    ).all()

    return [s.time_slot for s in slots]

