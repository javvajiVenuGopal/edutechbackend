import asyncio

from app.notifications.service import create_notification
from fastapi import APIRouter, Body, Depends, HTTPException, Request
import razorpay
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import os
from pydantic import BaseModel

from app.utils.language import get_message, language_header
from app.core.database import get_db
from app.core.payment import client
from app.auth.utils import get_current_user
from app.auth.models import User
from app.booking.models import Booking
from app.booking.schemas import CreateBookingSchema
from app.senior_guide.models import SeniorGuide
from app.core.limiter import limiter
from app.notifications.models import Notification
from app.services.calendar_service import create_calendar_invite
from app.email.email_service import send_calendar_invite
from  app.admin.analytics_router import admin_only

from fastapi import BackgroundTasks

router = APIRouter(prefix="/booking", tags=["Booking"])

from datetime import datetime, timezone
from sqlalchemy import cast, DateTime
from datetime import datetime, timezone

@router.get("/guide-history")
def guide_history(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    return db.query(Booking).filter(
        Booking.guide_id == guide.id,
        Booking.status == "COMPLETED"
    ).all()
    
    
@router.get("/guide-bookings")
def guide_bookings(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    return db.query(Booking).filter(
        Booking.guide_id == guide.id,
        Booking.status == "CONFIRMED",
        cast(Booking.time_slot, DateTime) > datetime.now(timezone.utc)
    ).all()
# SEEKER BOOKING HISTORY
@router.get("/my-bookings")
def my_bookings(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    return db.query(Booking).filter(
        Booking.seeker_id == user["user_id"]
    ).all()



# CREATE BOOKING
@router.post("/create")
@limiter.limit("10/minute")
def create_booking(
    request: Request,background_tasks: BackgroundTasks,
    data: CreateBookingSchema,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    accept_language: str = Depends(language_header)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == data.guide_id,
        SeniorGuide.status == "ACTIVE"
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not available")

    existing = db.query(Booking).filter(
        Booking.guide_id == data.guide_id,
        Booking.time_slot == data.time_slot,
        Booking.status != "CANCELLED"
    ).first()

    if existing:
        raise HTTPException(400, "Slot already booked")

    booking = Booking(
        seeker_id=user["user_id"],
        guide_id=data.guide_id,
        time_slot=data.time_slot,
        status="CREATED",
        payment_status="PENDING"
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)
    background_tasks.add_task(
    create_notification,
        
        user["user_id"],
        "Booking Created",
        "Your session booking request submitted"
    
)

    return {
        "message": get_message("booking_created", accept_language),
        "booking_id": booking.id
    }




client = razorpay.Client(auth=(
    os.getenv("RAZORPAY_KEY_ID"),
    os.getenv("RAZORPAY_KEY_SECRET")
))


@router.post("/payment/create/{booking_id}")
def create_order(
    booking_id: int,
    db: Session = Depends(get_db)
):

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    if booking.payment_status == "PAID":
        raise HTTPException(400, "Already paid")

    # Razorpay keys check
    if not os.getenv("RAZORPAY_KEY_ID") or not os.getenv("RAZORPAY_KEY_SECRET"):
        raise HTTPException(
            status_code=500,
            detail="Razorpay keys missing in .env"
        )

    # Use booking amount if exists else default ₹99
    amount = getattr(booking, "amount", 99)

    try:

        order = client.order.create({
            "amount": int(amount * 100),
            "currency": "INR",
            "payment_capture": 1
        })

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Razorpay order creation failed: {str(e)}"
        )

    booking.razorpay_order_id = order["id"]

    db.commit()

    return {
        "order_id": order["id"],
        "razorpay_key": os.getenv("RAZORPAY_KEY_ID"),
        "amount": int(amount * 100)
    }

# VERIFY PAYMENT
@router.post("/payment/verify")
def verify_payment(background_tasks: BackgroundTasks,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):

    booking = db.query(Booking).filter(
        Booking.id == data["booking_id"]
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    try:

        client.utility.verify_payment_signature({
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"]
        })

    except Exception:

        raise HTTPException(400, "Invalid payment signature")

    booking.payment_status = "PAID"
    booking.status = "CONFIRMED"
    booking.razorpay_payment_id = data["razorpay_payment_id"]
    booking.razorpay_order_id = data["razorpay_order_id"]


    

    notification = Notification(
    user_id=booking.guide_id,
    title="New Session Request",
    message=f"You have a new call request (Booking ID: {booking.id})" 
    )

    db.add(notification)

    db.commit()
    from app.services.calendar_service import create_calendar_invite
    from app.email.email_service import send_calendar_invite
    from datetime import datetime, timezone, timedelta
    import os
    
    # ensure folder exists
    os.makedirs("calendar_invites", exist_ok=True)
    
    start_time = datetime.fromisoformat(booking.time_slot)
    end_time = start_time + timedelta(minutes=15)
    
    file_path = f"calendar_invites/invite_{booking.id}.ics"
    
    create_calendar_invite(
        title="Exameets Consultation Call",
        description=f"Booking ID: {booking.id}",
        start_time=start_time,
        end_time=end_time,
        file_path=file_path
    )
    
    # fetch seeker
    seeker = db.query(User).filter(
        User.id == booking.seeker_id
    ).first()
    
    # fetch guide
    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == booking.guide_id
    ).first()
    
    guide_user = db.query(User).filter(
        User.id == guide.user_id
    ).first()
    
    # send emails
    if seeker:
        send_calendar_invite(seeker.email, file_path)
    
    if guide_user:
        send_calendar_invite(guide_user.email, file_path)
    guide = db.query(SeniorGuide).filter(
    SeniorGuide.id == booking.guide_id
).first()

    # notify guide
    background_tasks.add_task(
        create_notification,
            
            guide.user_id,
            "New Booking Confirmed",
            f"A seeker booked your session (Booking ID: {booking.id})"
        
    )

    # notify seeker
    background_tasks.add_task(
        create_notification,
            
            booking.seeker_id,
            "Payment Successful",
            "Your session booking confirmed successfully"
        
    )

    return {"message": "Payment verified successfully"}

# CANCEL BOOKING
@router.put("/cancel/{booking_id}")
def cancel_booking(background_tasks:BackgroundTasks,
    booking_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.seeker_id == user["user_id"]
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    booking.status = "CANCELLED"

    if booking.payment_status == "PAID":
        booking.payment_status = "REFUND_REQUESTED"

    db.commit()
    guide = db.query(SeniorGuide).filter(
    SeniorGuide.id == booking.guide_id
).first()

    background_tasks.add_task(
        create_notification,
            
            booking.seeker_id,
            "Booking Cancelled",
            "Your booking cancelled successfully"
        
    )

    background_tasks.add_task(
        create_notification,
            
            guide.user_id,
            "Session Cancelled",
            "A seeker cancelled the booking"
        
    )

    return {"message": "Booking cancelled successfully"}


@router.get("/guide/upcoming")
def guide_upcoming_calls(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    return db.query(Booking).filter(
        Booking.guide_id == guide.id,
        Booking.status == "CONFIRMED",
        cast(Booking.time_slot, DateTime) > datetime.now(timezone.utc)
    ).all()


# BOOKING DETAILS
@router.get("/{booking_id}")
def booking_details(
    booking_id: int,
    db: Session = Depends(get_db)
):

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    return booking




# BOOKING STATUS
@router.get("/status/{booking_id}")
def booking_status(
    booking_id: int,
    db: Session = Depends(get_db)
):

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    return {
        "status": booking.status,
        "payment_status": booking.payment_status
    }
    
    


class RefundCreate(BaseModel):
    reason: str


class RefundResponse(BaseModel):
    booking_id: int
    status: str
    reason: str

    class Config:
        from_attributes = True
        
        

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.booking.models import RefundRequest

from app.booking.models import Booking



# ✅ CREATE REFUND REQUEST (SEEKER)

from datetime import datetime, timezone, timedelta
from datetime import datetime, timezone, timedelta

@router.post("/refund/request/{booking_id}")
def create_refund_request(
    booking_id: int,
    data: RefundCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):

    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.seeker_id == user["user_id"]
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    # refund only if payment completed
    if booking.payment_status != "PAID":
        raise HTTPException(
            400,
            "Refund already requested or payment not completed"
        )

    # block duplicate refund request
    existing = db.query(RefundRequest).filter(
        RefundRequest.booking_id == booking_id
    ).first()

    if existing:
        raise HTTPException(
            400,
            "Refund already requested"
        )

    booking_time = datetime.fromisoformat(
        booking.time_slot
    )

    now = datetime.now(timezone.utc)

    refund_allowed_time = booking_time + timedelta(minutes=10)

    # allow refund only after 10 minutes
    if now < refund_allowed_time:
        raise HTTPException(
            400,
            "Refund allowed only after 10 minutes from session start"
        )

    # block completed calls (unless short call)
    if booking.status == "COMPLETED" and not booking.refund_flag:
        raise HTTPException(
            400,
            "Call completed successfully. Refund not allowed"
        )

    # allow refund if short duration call
    if booking.refund_flag:
        reason = "Call duration less than 5 minutes"
    else:
        reason = data.reason

    refund = RefundRequest(
        booking_id=booking_id,
        user_id=user["user_id"],
        reason=reason,
        status="PENDING"
    )

    db.add(refund)

    booking.payment_status = "REFUND_REQUESTED"

    db.commit()

    return {
        "message": "Refund request submitted successfully"
    }
@router.get("/refund/status/{booking_id}")
def get_refund_status(
    booking_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):

    refund = db.query(RefundRequest).filter(
        RefundRequest.booking_id == booking_id,
        RefundRequest.user_id == user["user_id"]
    ).first()

    if not refund:
        return {"status": "NOT_REQUESTED"}

    return {
        "status": refund.status,
        "reason": refund.reason
    }
        
   # ---------------- REFUND MANAGEMENT ----------------

@router.put("/refund/{booking_id}")
def process_refund(background_tasks:BackgroundTasks,
    booking_id: int,
    action: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    refund = db.query(RefundRequest).filter(
        RefundRequest.booking_id == booking_id
    ).first()

    if not refund:
        raise HTTPException(404, "Refund request not found")

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    if action == "REJECTED":

        refund.status = "REJECTED"

        db.commit()

        return {
            "message": "Refund rejected"
        }


    if action == "APPROVED":

        # Razorpay payment id stored during payment success
        if not booking.razorpay_payment_id:
            raise HTTPException(
                400,
                "Payment ID missing"
            )

        try:

            client.payment.refund(
                booking.razorpay_payment_id,
                {
                    "amount": int(
                        booking.amount * 100
                    )
                }
            )

        except Exception as e:

            raise HTTPException(
                500,
                f"Refund failed: {str(e)}"
            )

        refund.status = "APPROVED"

        booking.payment_status = "REFUNDED"

        db.commit()
        background_tasks.add_task(
        create_notification,
            
            booking.seeker_id,
            "Refund Approved",
            "Your payment refund completed successfully"
        
    )

        return {
            "message": "Refund successful via Razorpay"
        }

 

