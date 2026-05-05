from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.limiter import limiter

from app.auth.utils import (
    get_current_user,
    create_token,
    hash_password,
    verify_password
)

from app.admin.schemas import AdminLoginSchema, AdminRegisterSchema
from app.admin.models import AdminRole,EligibilityQuestion
from app.admin.permission import role_required
from app.admin.export_router import admin_only

from app.logs.service import create_log
from app.notifications.service import create_notification

from app.senior_guide.models import SeniorGuide
from app.booking.models import Booking, RefundRequest
from app.wallet.models import Referral, WalletTransaction, WithdrawalRequest
from app.calls.models import CallSession
from app.auth.models import User


router = APIRouter(prefix="/admin", tags=["Admin Panel"])


# ---------------- ADMIN LOGIN ----------------

@router.post("/login")
@limiter.limit("50/minute")
def admin_login(
    request: Request,
    data: AdminLoginSchema,
    db: Session = Depends(get_db)
):

    admin = db.query(AdminRole).filter(
        AdminRole.email == data.email
    ).first()

    if not admin:
        raise HTTPException(401, "Admin not found")

    if not admin.is_active:
        raise HTTPException(403, "Admin account disabled")

    if not verify_password(data.password, admin.password):
        raise HTTPException(401, "Invalid password")

    token = create_token({
        "user_id": admin.id,
        "email": admin.email,
        "role": admin.role
    })

    return {
        "message": "Admin login successful",
        "role": admin.role,
        "access_token": token
    }


# ---------------- REGISTER ADMIN ----------------

@router.post("/register")
@limiter.limit("3/minute")
def register_admin(
    request: Request,
    data: AdminRegisterSchema,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    role_required(["SUPERADMIN"])(user)

    existing = db.query(AdminRole).filter(
        AdminRole.email == data.email
    ).first()

    if existing:
        raise HTTPException(400, "Admin already exists")

    new_admin = AdminRole(
        email=data.email,
        password=hash_password(data.password),
        role=data.role,
        is_active=data.is_active
    )

    db.add(new_admin)
    db.commit()

    create_log(
        db,
        user["email"],
        f"Created admin {data.email}",
        "ADMIN_CREATION"
    )

    return {"message": "Admin created successfully"}


# ---------------- GUIDE MANAGEMENT ----------------

from datetime import datetime, timezone

@router.get("/guides/pending")
def pending_guides(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    admin_only(user)

    guides = db.query(SeniorGuide).filter(
        SeniorGuide.status == "PENDING_VERIFICATION"
    ).all()

    return [
        {
            "id": guide.id,
            "name": guide.user.full_name,
            "college": guide.college_name,
            "branch": guide.branch,
            "year": guide.year_of_study,
            "created_at": guide.created_at,
        }
        for guide in guides
    ]

from datetime import datetime, timezone

@router.put("/guides/approve/{guide_id}")
def approve_guide(
    guide_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    admin_only(user)

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == guide_id
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    guide.status = "ELIGIBLE_TEST"
    guide.is_verified = True
    guide.verified_by = user["email"]
    guide.verified_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "message": "Documents verified successfully",
        "status": guide.status
    }

@router.put("/guides/reject/{guide_id}")
def reject_guide(guide_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):

    admin_only(user)

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == guide_id
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    guide.status = "REJECTED"
    db.commit()

    return {"message": "Guide rejected successfully"}


@router.put("/guides/suspend/{guide_id}")
def suspend_guide(guide_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):

    admin_only(user)

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == guide_id
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    guide.status = "SUSPENDED"
    db.commit()

    return {"message": "Guide suspended successfully"}

@router.put("/guides/pass-test/{guide_id}")
def pass_test(
    guide_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    role_required(["SUPERADMIN"])(user)

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == guide_id
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    guide.status = "ACTIVE"

    target_user = db.query(User).filter(
        User.id == guide.user_id
    ).first()

    if target_user:
        target_user.role = "senior_guide"

    db.commit()

    return {
        "message": "Guide activated successfully"
    }


@router.put("/guides/reset-attempts/{guide_id}")
def reset_attempts(guide_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):

    role_required(["SUPERADMIN"])(user)

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == guide_id
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    guide.attempts = 0
    guide.status = "ELIGIBLE_TEST"

    db.commit()

    return {"message": "Attempts reset successfully"}


@router.put("/guides/force-activate/{guide_id}")
def force_activate(guide_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):

    role_required(["SUPERADMIN"])(user)

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == guide_id
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    guide.status = "ACTIVE"
    db.commit()

    return {"message": "Guide activated manually"}


# ---------------- BOOKINGS & CALLS ----------------

from sqlalchemy.orm import aliased

@router.get("/bookings")
def view_bookings(user=Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)

    Seeker = aliased(User)
    Guide = aliased(User)

    bookings = (
        db.query(
            Booking.id,
            Booking.time_slot,
            Booking.status,
            Booking.payment_status,
            Booking.amount,
            Seeker.full_name.label("seeker_name"),
            Guide.full_name.label("guide_name"),
        )
        .join(Seeker, Booking.seeker_id == Seeker.id)
        .join(Guide, Booking.guide_id == Guide.id)
        .all()
    )

    return [dict(row._mapping) for row in bookings]

@router.get("/calls")
def view_calls(user=Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)

    Seeker = aliased(User)
    Guide = aliased(User)

    calls = (
        db.query(
            CallSession.id,
            CallSession.booking_id,
            CallSession.start_time,
            CallSession.end_time,
            CallSession.duration_minutes,
            CallSession.status,
            Seeker.full_name.label("seeker_name"),
            Guide.full_name.label("guide_name"),
        )
        .join(Booking, CallSession.booking_id == Booking.id)
        .join(Seeker, Booking.seeker_id == Seeker.id)
        .join(Guide, Booking.guide_id == Guide.id)
        .all()
    )

    return [dict(row._mapping) for row in calls]

import   razorpay
import os
client = razorpay.Client(
    auth=(
        os.getenv("RAZORPAY_KEY_ID"),
         os.getenv("RAZORPAY_KEY_SECRET")
    )
)
# ----
from sqlalchemy.orm import aliased

@router.get("/refund/requests")
def get_refund_requests(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    admin_only(user)

    UserAlias = aliased(User)
    BookingAlias = aliased(Booking)

    refunds = (
        db.query(
            RefundRequest.id,
            RefundRequest.booking_id,
            RefundRequest.reason,
            RefundRequest.status,
            RefundRequest.created_at,
            UserAlias.full_name.label("user_name"),
            BookingAlias.amount.label("amount"),
        )
        .join(UserAlias, RefundRequest.user_id == UserAlias.id)
        .join(BookingAlias, RefundRequest.booking_id == BookingAlias.id)
        .all()
    )

    return [dict(r._mapping) for r in refunds]

@router.put("/refund/{booking_id}")
def process_refund(
    booking_id: int,
    action: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
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

    print("Refund status:", refund.status)
    print("Booking payment_status:", booking.payment_status)
    print("Payment ID:", booking.razorpay_payment_id)
    print("Amount:", booking.amount)


    # ================= REJECT =================

    if action == "REJECTED":

        refund.status = "REJECTED"
        booking.payment_status = "PAID"

        db.commit()

        return {"message": "Refund rejected"}


    # ================= APPROVE =================

    if action == "APPROVED":

        # already refunded earlier
        if booking.payment_status == "REFUNDED":

            refund.status = "APPROVED"

            db.commit()

            return {
                "message":
                "Refund already processed earlier"
            }

        if not booking.razorpay_payment_id:
            raise HTTPException(
                400,
                "Payment ID missing"
            )

        if not booking.amount:
            raise HTTPException(
                400,
                "Booking amount missing"
            )

        try:

            refund_response = client.payment.refund(
                booking.razorpay_payment_id,
                {
                    "amount": int(booking.amount * 100)
                }
            )

            print("Refund success:", refund_response)

        except Exception as e:

            error_text = str(e)

            print("Refund error:", error_text)

            # already refunded in Razorpay
            if "already been fully refunded" in error_text:

                refund.status = "APPROVED"
                booking.payment_status = "REFUNDED"

                db.commit()

                return {
                    "message":
                    "Refund already completed earlier"
                }

            raise HTTPException(
                500,
                f"Refund failed: {error_text}"
            )

        refund.status = "APPROVED"
        booking.payment_status = "REFUNDED"

        db.commit()

        return {
            "message":
            "Refund successful via Razorpay"
        }


    raise HTTPException(
        400,
        "Invalid action. Use APPROVED or REJECTED"
    )

# ---------------- WITHDRAW MANAGEMENT ----------------

from sqlalchemy.orm import aliased

# @router.get("/withdraw/requests")
# def view_withdrawals(user=Depends(get_current_user), db: Session = Depends(get_db)):
#     admin_only(user)

#     Guide = aliased(User)

#     withdrawals = (
#         db.query(
#             WithdrawalRequest.id,
#             WithdrawalRequest.amount,
#             WithdrawalRequest.status,
#             WithdrawalRequest.created_at,
#             Guide.full_name.label("guide_name"),
#         )
#         .join(Guide, WithdrawalRequest.guide_id == Guide.id)
#         .all()
#     )

#     return [dict(row._mapping) for row in withdrawals]

@router.put("/referral/approve/{referral_id}")
def approve_referral(
    referral_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    referral = db.query(Referral).filter(
        Referral.id == referral_id
    ).first()

    if not referral:
        raise HTTPException(404, "Referral not found")


    if referral.status != "PENDING":
        raise HTTPException(400, "Already processed")


    GUIDE_REWARD = 25
    USER_REWARD = 50


    referrer = db.query(SeniorGuide).filter(
        SeniorGuide.id == referral.referrer_id
    ).first()


    new_user = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == referral.referred_user_id
    ).first()


    # credit guide
    referrer.wallet_balance += GUIDE_REWARD
    referrer.referral_bonus += GUIDE_REWARD


    # credit new user
    new_user.wallet_balance += USER_REWARD
    new_user.referred_by = referrer.id


    # transactions
    db.add(WalletTransaction(
        guide_id=referrer.id,
        amount=GUIDE_REWARD,
        type="credit",
        remark="Referral bonus earned"
    ))


    db.add(WalletTransaction(
        guide_id=new_user.id,
        amount=USER_REWARD,
        type="credit",
        remark="Referral signup bonus"
    ))


    referral.status = "APPROVED"

    db.commit()

    return {
        "message": "Referral approved & wallet credited 🎉"
    }

@router.put("/admin/referral/reject/{referral_id}")
def reject_referral(
    referral_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    referral = db.query(Referral).filter(
        Referral.id == referral_id
    ).first()

    if not referral:
        raise HTTPException(404, "Referral not found")

    referral.status = "REJECTED"

    db.commit()

    return {
        "message": "Referral rejected"
    }

@router.put("/withdraw/approve/{request_id}")
def approve_withdrawal(
    request_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    withdrawal = db.query(WithdrawalRequest).filter(
        WithdrawalRequest.id == request_id
    ).first()

    if not withdrawal:
        raise HTTPException(404, "Request not found")

    if withdrawal.status != "PENDING":
        raise HTTPException(400, "Already processed")

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == withdrawal.guide_id
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    try:

        payout = client.payout.create(
            {
                "account_number": os.getenv("YOUR_RAZORPAYX_ACCOUNT_NUMBER"),
                "fund_account": {
                    "account_type": "vpa",
                    "vpa": {
                        "address": withdrawal.upi_id
                    },
                    "contact": {
                        "name": guide.full_name,
                        "type": "employee",
                        "reference_id": str(guide.id)
                    }
                },
                "amount": int(withdrawal.amount * 100),
                "currency": "INR",
                "mode": "UPI",
                "purpose": "payout",
                "queue_if_low_balance": True,
                "reference_id": str(withdrawal.id),
                "narration": "Guide withdrawal payout"
            }
        )

        withdrawal.status = "APPROVED"
        withdrawal.payout_id = payout["id"]

        guide.pending_withdrawal -= withdrawal.amount

        db.commit()

        return {
            "message": "Withdrawal approved & paid successfully"
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Payout failed: {str(e)}"
        )

@router.put("/withdraw/reject/{request_id}")
def reject_withdrawal(request_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):

    admin_only(user)

    withdrawal = db.query(WithdrawalRequest).filter(
        WithdrawalRequest.id == request_id
    ).first()

    if not withdrawal:
        raise HTTPException(404, "Request not found")

    withdrawal.status = "REJECTED"

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == withdrawal.guide_id
    ).first()

    if guide:
        guide.wallet_balance += withdrawal.amount
        guide.pending_withdrawal -= withdrawal.amount

    db.commit()

    return {"message": "Withdrawal rejected"}


# ---------------- USER CONTROL ----------------

@router.put("/users/suspend/{user_id}")
def suspend_user(user_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):

    admin_only(user)

    target = db.query(User).filter(User.id == user_id).first()

    if not target:
        raise HTTPException(404, "User not found")

    target.is_active = False
    db.commit()

    return {"message": "User suspended"}


@router.put("/users/activate/{user_id}")
def activate_user(user_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):

    admin_only(user)

    target = db.query(User).filter(User.id == user_id).first()

    if not target:
        raise HTTPException(404, "User not found")

    target.is_active = True
    db.commit()

    return {"message": "User activated"}


# ---------------- ANALYTICS ----------------

@router.get("/analytics")
def admin_analytics(user=Depends(get_current_user), db: Session = Depends(get_db)):

    admin_only(user)

    completed_calls = db.query(CallSession).filter(
        CallSession.status == "COMPLETED"
    ).count()

    return {
        "total_users": db.query(User).count(),
        "total_guides": db.query(SeniorGuide).count(),
        "active_guides": db.query(SeniorGuide).filter(
            SeniorGuide.status == "ACTIVE"
        ).count(),
        "total_bookings": db.query(Booking).count(),
        "completed_calls": completed_calls,
        "total_revenue": completed_calls * 44,
        "pending_withdrawals": db.query(WithdrawalRequest).filter(
            WithdrawalRequest.status == "PENDING"
        ).count()
    }


# ---------------- ADMIN DASHBOARD SUMMARY ----------------

@router.get("/dashboard")
def admin_dashboard(user=Depends(get_current_user), db: Session = Depends(get_db)):

    admin_only(user)

    return {
        "users": db.query(User).count(),
        "guides": db.query(SeniorGuide).count(),
        "bookings": db.query(Booking).count(),
        "withdraws": db.query(WithdrawalRequest).filter(
            WithdrawalRequest.status == "PENDING"
        ).count()
    }


# ---------------- FINANCE SUMMARY ----------------

@router.get("/finance/revenue-summary")
def revenue_summary(user=Depends(get_current_user), db: Session = Depends(get_db)):

    role_required(["SUPERADMIN", "FINANCIAL_ADMIN"])(user)

    completed_calls = db.query(CallSession).filter(
        CallSession.status == "COMPLETED"
    ).count()

    return {
        "total_completed_calls": completed_calls,
        "platform_revenue": completed_calls * 44,
        "guide_payout": completed_calls * 55
    }




@router.get("/users")
def get_all_users(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    admin_only(user)

    users = db.query(User).all()

    return [
        {
            "id": u.id,
            "name": u.full_name,
            "email": u.email,
            "mobile_number": u.mobile_number,
            "role": u.role,
            "status": "verified" if u.is_verified else "not_verified",
            "created_at": u.created_at
        }
        for u in users
    ]

@router.get("/users/{user_id}")
def get_user_details(
    user_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    admin_only(user)

    target = db.query(User).filter(User.id == user_id).first()

    if not target:
        raise HTTPException(404, "User not found")

    return {
        "id": target.id,
        "name": target.full_name,
        "email": target.email,
        "role": target.role,
        "status": "active" if target.is_active else "suspended"
    }
    
@router.delete("/users/delete/{user_id}")
def delete_user(
    user_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    admin_only(user)

    target = db.query(User).filter(User.id == user_id).first()

    if not target:
        raise HTTPException(404, "User not found")

    db.delete(target)
    db.commit()

    return {"message": "User deleted successfully"}

@router.put("/users/change-role/{user_id}")
def change_user_role(
    user_id: int,
    role: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    admin_only(user)

    target = db.query(User).filter(User.id == user_id).first()

    if not target:
        raise HTTPException(404, "User not found")

    target.role = role
    db.commit()

    return {"message": "User role updated"}


@router.get("/users/status/{status}")
def filter_users_by_status(
    status: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    admin_only(user)

    if status == "active":
        users = db.query(User).filter(User.is_active == True).all()

    elif status == "suspended":
        users = db.query(User).filter(User.is_active == False).all()

    else:
        raise HTTPException(400, "Invalid status")

    return [     {         "id": u.id,         "name": u.full_name,         "email": u.email,         "role": u.role     }     for u in users ]


@router.get("/users/role/{role}")
def filter_users_by_role(
    role: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    admin_only(user)

    users = db.query(User).filter(User.role == role).all()

    return [     {         "id": u.id,         "name": u.full_name,         "email": u.email,         "role": u.role     }     for u in users ]

@router.get("/guides/documents/{guide_id}")
def get_guide_documents(
    guide_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    admin_only(user)

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == guide_id
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    return {
        "aadhaar": guide.aadhaar_path,
        "college_id": guide.college_id_card_path,
        "hall_ticket": guide.hall_ticket_path
    }

from fastapi.responses import FileResponse

@router.get("/documents/{file_name}")
def serve_document(file_name: str):
    path = file_name
    
    if not os.path.exists(path):
        raise HTTPException(404, "File not found")

    return FileResponse(path)

@router.get("/guides/{guide_id}")
def guide_details(
    guide_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    admin_only(user)

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == guide_id
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    return {
        "id": guide.id,
        "college": guide.college_name,
        "branch": guide.branch,
        "attempts": guide.attempts,
        "wallet": guide.wallet_balance,
        "status": guide.status,
        "aadhaar": guide.aadhaar_path,
        "college_id": guide.college_id_card_path,
        "hall_ticket": guide.hall_ticket_path,
        "verified_by": guide.verified_by,
        "verified_at": guide.verified_at
    }
@router.post("/questions/create")
def create_question(
    question: str,
    answer: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    new_q = EligibilityQuestion(
        question=question,
        correct_answer=answer
    )

    db.add(new_q)
    db.commit()

    return {"message": "Question created"}

@router.get("/questions/all")
def get_all_questions(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    return db.query(EligibilityQuestion).all()


@router.put("/questions/update/{question_id}")
def update_question(
    question_id: int,
    question: str,
    answer: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    q = db.query(EligibilityQuestion).filter(
        EligibilityQuestion.id == question_id
    ).first()

    if not q:
        raise HTTPException(404, "Question not found")

    q.question = question
    q.correct_answer = answer

    db.commit()

    return {"message": "Updated successfully"}

@router.delete("/questions/delete/{question_id}")
def delete_question(
    question_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    admin_only(user)

    q = db.query(EligibilityQuestion).filter(
        EligibilityQuestion.id == question_id
    ).first()

    if not q:
        raise HTTPException(404, "Question not found")

    db.delete(q)
    db.commit()

    return {"message": "Deleted successfully"}
