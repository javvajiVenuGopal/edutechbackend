import asyncio

from app.notifications.service import create_notification
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta, timezone
from typing import Optional

from app.auth.utils import create_token, get_current_user
from app.core.database import get_db
from app.auth.models import User
from app.senior_guide.models import SeniorGuide
from app.core.limiter import limiter
from app.auth.schemas import LoginSchema, RegisterSchema, OTPVerifySchema
from app.core.otp import generate_otp
from app.email.email_service import send_email
from fastapi import BackgroundTasks

router = APIRouter(prefix="/auth", tags=["Authentication"])


# REGISTER
@router.post("/register")
@limiter.limit("3/minute")
def register(request: Request,background_tasks: BackgroundTasks, data: RegisterSchema, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(User.email == data.email).first()

    if existing_user:
        raise HTTPException(400, "User already exists")

    otp = generate_otp()

    new_user = User(
        full_name=data.full_name,
        email=data.email,
        mobile_number=data.mobile_number,
        role=data.role if data.role else "seeker",
        otp=otp,
        is_verified=False,
        otp_expiry=datetime.now(timezone.utc) + timedelta(minutes=5)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    send_email(data.email, otp)
    background_tasks.add_task(
    create_notification,
        
        new_user.id,
        "OTP Sent",
        "Registration OTP sent to your email"
    
)

    return {"message": "OTP sent successfully"}

def send_email_safe(email, otp):
    try:
        print("=====================Calling email sender...===================")
        send_email(email, otp)
    except Exception as e:
        print("=====================EMAIL FAILED:=======================", e)
# LOGIN
@router.post("/login")
@limiter.limit("5/minute")
def login(request: Request,background_tasks: BackgroundTasks, data: LoginSchema, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()
    print("login enter")

    if not user:
        raise HTTPException(404, "User not found")

    if not user.is_verified:
        raise HTTPException(403, "User registration not completed")

    otp = generate_otp()

    user.otp = otp
    user.otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=5)

    db.commit()

    print("backgroundtask  login otps ")
    try:
        print("sending email")
        # ✅ IMPORTANT FIX
        send_email_safe(user.email, otp)
        background_tasks.add_task(
            create_notification,
            user.id,
            "Login OTP Sent",
            "OTP sent to your email for login"
        )
     
       
    except Exception as e:
        print("Email failed:", e)

    return {"message": "OTP sent for login"}



@router.post("/verify-otp")
def verify_otp(
    data: OTPVerifySchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == data.email
    ).first()

    if not user:
        raise HTTPException(404, "User not found")

    if user.otp != data.otp:
        raise HTTPException(400, "Invalid OTP")

    if not user.otp_expiry:
        raise HTTPException(400, "OTP missing")

    # ensure timezone safe
    expiry = user.otp_expiry

    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    if expiry < datetime.now(timezone.utc):
        raise HTTPException(400, "OTP expired")


    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user.id
    ).first()


    guide_status = guide.status if guide else None
    guide_id = guide.id if guide else None


    # ✅ role update automatically
    role = user.role

    if guide:

        if guide.status == "ACTIVE":
            role = "senior_guide"

        elif guide.status == "ELIGIBLE_TEST":
            role = "senior_guide"

        elif guide.status == "PENDING_VERIFICATION":
            role = "seeker"


    user.is_verified = True
    user.last_seen = datetime.now(timezone.utc)
    user.otp = None
    user.otp_expiry = None

    db.commit()
    background_tasks.add_task(
    create_notification,
        
        user.id,
        "Login Successful",
        "You logged in successfully"
    
)


    token = create_token({
        "user_id": user.id,
        "email": user.email,
        "role": role
    })


    return {
        "message": "successful",
        "access_token": token,
        "token_type": "bearer",
        "role": role,
        "guide_status": guide_status,
        "guide_id": guide_id,
        "user_id": user.id
    }

# RESEND OTP
@router.post("/resend-otp")
def resend_otp(background_tasks: BackgroundTasks,email: str = Body(...), db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(404, "User not found")

    if user.otp_expiry and user.otp_expiry > datetime.now(timezone.utc):
        raise HTTPException(400, "OTP already sent. Try later")

    otp = generate_otp()

    user.otp = otp
    user.otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=5)

    db.commit()
    
    background_tasks.add_task(
    create_notification,
        
        user.id,
        "OTP Resent",
        "A new OTP has been sent to your email"
    
)
    
    send_email(email, otp)

    return {"message": "OTP resent successfully"}

@router.get("/me")
def get_profile(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # current_user is dict → use ["key"]

    user = db.query(User).filter(
        User.id == current_user["user_id"]
    ).first()

    if not user:
        raise HTTPException(404, "User not found")

    # ================= SEEKER PROFILE =================
    if user.role == "seeker":

        return {
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role
        }

    # ================= SENIOR GUIDE PROFILE =================
    if user.role == "senior_guide":

        guide_profile = db.query(SeniorGuide).filter(
            SeniorGuide.user_id == user.id
        ).first()

        if not guide_profile:
            raise HTTPException(404, "Guide profile not found")

        return {
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,

            "sg_unique_id": guide_profile.unique_id,
            "college": guide_profile.college_name,
            "branch": guide_profile.branch,
            "year": guide_profile.year_of_study,
            "rating": guide_profile.rating,
            "calls_completed": guide_profile.total_calls
        }

    # fallback
    return {
        "user_id": user.id,
        "role": user.role
    }




@router.post("/ping")
def update_last_seen(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    user = db.query(User).filter(
        User.id == current_user["user_id"]
    ).first()

    if user:
        user.last_seen = datetime.now(timezone.utc)
        db.commit()

    return {"message": "updated"}

from datetime import timedelta

@router.get("/status/{user_id}")
def user_status(user_id: int, db: Session = Depends(get_db)):

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(404)

    online = False

    if user.last_seen:
        online = user.last_seen > datetime.now(timezone.utc) - timedelta(minutes=2)

    return {"online": online}
