import asyncio

from app.calls.models import CallSession
from app.auth.models import User
from fastapi import APIRouter, Depends, HTTPException, Body,BackgroundTasks
from sqlalchemy.orm import Session

from app.notifications.service import create_notification
from app.core.database import get_db
from app.wallet.models import Referral, WithdrawalRequest
from app.senior_guide.models import SeniorGuide
from app.auth.utils import get_current_user


router = APIRouter(prefix="/wallet", tags=["Wallet"])

from sqlalchemy.orm import aliased

@router.get("/admin/all-requests")
def all_requests(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if user["role"] not in ["SUPERADMIN", "FINANCIAL_ADMIN"]:
        raise HTTPException(403, "Admin access required")

    Guide = aliased(User)

    withdrawals = (
        db.query(
            WithdrawalRequest.id,
            WithdrawalRequest.amount,
            WithdrawalRequest.status,
            WithdrawalRequest.created_at,
            WithdrawalRequest.upi_id,
            Guide.full_name.label("guide_name"),
        )
        .join(Guide, WithdrawalRequest.guide_id == Guide.id)
        .all()
    )

    return [dict(row._mapping) for row in withdrawals]
#-----------------------------------------------

from app.wallet.models import WalletTransaction


@router.get("/transactions")
def transaction_history(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if user["role"] != "senior_guide":

        raise HTTPException(403, "Access denied")

    guide = db.query(SeniorGuide).filter(

        SeniorGuide.user_id == user["user_id"]

    ).first()

    credits = db.query(WalletTransaction).filter(

        WalletTransaction.guide_id == guide.id

    ).all()

    withdrawals = db.query(WithdrawalRequest).filter(

        WithdrawalRequest.guide_id == guide.id

    ).all()

    result = []

    for c in credits:

        result.append({

            "id": c.id,

            "amount": c.amount,

            "type": "credit",

            "created_at": c.created_at

        })

    for w in withdrawals:

        result.append({

            "id": w.id,

            "amount": w.amount,

            "type": "debit",

            "status": w.status,

            "created_at": w.created_at

        })

    return sorted(
        result,
        key=lambda x: x["created_at"],
        reverse=True
    )
@router.get("/balance")
def wallet_balance(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if user["role"] != "senior_guide":
        raise HTTPException(403, "Only guides allowed")

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    return {
        "available_balance": guide.wallet_balance or 0,
        "pending_withdrawal": guide.pending_withdrawal or 0
    }
    
    
# ---------------------------------------------------
# GUIDE CREATE WITHDRAW REQUEST
# ---------------------------------------------------


from datetime import datetime, timezone, timedelta

@router.post("/withdraw/request")
def create_withdraw_request(  background_tasks: BackgroundTasks,
    amount: float = Body(...),
    upi_id: str = Body(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if user["role"] != "senior_guide":
        raise HTTPException(403, "Only guides can withdraw")

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    print("====================",amount==500)
    # ✅ Minimum withdrawal check
    if amount < 500:
        raise HTTPException(400, "Minimum withdrawal ₹500")

    print("======================", guide.wallet_balance < amount)
    if guide.wallet_balance < amount:
        raise HTTPException(400, "Insufficient balance")


    # ✅ Weekly withdrawal restriction check (ADD HERE)
    last_request = db.query(WithdrawalRequest).filter(
        WithdrawalRequest.guide_id == guide.id
    ).order_by(
        WithdrawalRequest.created_at.desc()
    ).first()

    if last_request:
        diff = datetime.now(timezone.utc) - last_request.created_at
        print(diff < timedelta(days=7))
        if diff < timedelta(days=7):
            raise HTTPException(
                400,
                "Withdrawal allowed once per week only"
            )


    # withdraw create logic
    guide.wallet_balance -= amount
    guide.pending_withdrawal += amount

    withdraw = WithdrawalRequest(
    guide_id=guide.id,
    amount=amount,
    upi_id=upi_id,
    status="PENDING"
)

    db.add(withdraw)
    db.commit()
    

    background_tasks.add_task(
        create_notification,
            db,
            user["user_id"],
            "Withdrawal Requested",
            "Your withdrawal request submitted successfully"
        
    )

    return {
        "message": "Withdrawal request submitted"
    } 


import razorpay
import os
client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"),
          os.getenv("RAZORPAY_KEY_SECRET"))
)




from fastapi import Body
import hmac
import hashlib




from fastapi import Body, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.auth.utils import get_current_user
from app.senior_guide.models import SeniorGuide
from app.wallet.models import WalletTransaction



import hmac
import hashlib



# CREATE ORDER

from fastapi import Body, HTTPException
from pydantic import BaseModel
import razorpay
from app.core.config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET


class OrderRequest(BaseModel):
    amount: float


client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
)


@router.post("/add-money/order")
def create_wallet_order(data: OrderRequest = Body(...)):

    amount = data.amount

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    order = client.order.create({
        "amount": int(amount * 100),
        "currency": "INR",
        "payment_capture": 1
    })

    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"]
    }


# VERIFY PAYMENT

@router.post("/add-money/verify")
def verify_wallet_payment(  background_tasks: BackgroundTasks,
    data: dict = Body(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    generated_signature = hmac.new(

        os.getenv("RAZORPAY_KEY_SECRET").encode(),

        f"{data['razorpay_order_id']}|{data['razorpay_payment_id']}".encode(),

        hashlib.sha256

    ).hexdigest()


    if generated_signature != data["razorpay_signature"]:
        raise HTTPException(400, "Invalid signature")


    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()


    if not guide:
        raise HTTPException(404, "Guide not found")


    payment = client.payment.fetch(
        data["razorpay_payment_id"]
    )


    amount = payment["amount"] / 100


    guide.wallet_balance += amount


    tx = WalletTransaction(
    guide_id=guide.id,
    amount=amount,
    type="WALLET_TOPUP",
    remark="Wallet recharge via Razorpay"
)


    db.add(tx)
    db.commit()
    

    background_tasks.add_task(
        create_notification,
            db,
            user["user_id"],
            "Wallet Updated",
            f"₹{amount} added successfully"
        
    )


    return {
        "message": "Wallet updated successfully",
        "amount_added": amount
    }  

# GENERATE REFERRAL CODE

@router.get("/my-code")
def get_referral_code(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    return {
        "referral_code": f"REF-SG-{guide.id}"
    }

@router.post("/apply/{code}")
def apply_referral(
    code: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    try:
        guide_id = int(code.replace("REF-SG-", ""))

    except:
        raise HTTPException(400, "Invalid referral code")


    referrer = db.query(SeniorGuide).filter(
        SeniorGuide.id == guide_id
    ).first()

    if not referrer:
        raise HTTPException(404, "Guide not found")


    # prevent self referral
    if referrer.user_id == user["user_id"]:
        raise HTTPException(400, "Cannot use your own code")


    # prevent duplicate usage
    already_used = db.query(Referral).filter(
        Referral.referred_user_id == user["user_id"],
        Referral.status.in_(["PENDING", "APPROVED"])
    ).first()

    if already_used:
        raise HTTPException(400, "Referral already used")


    referral = Referral(
        referrer_id=referrer.id,
        referred_user_id=user["user_id"],
        amount=25,
        status="PENDING"
    )

    db.add(referral)
    db.commit()

    return {
        "message": "Referral applied successfully. Reward will be credited after activation ✅"
    }

@router.get("/stats")
def referral_stats(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    total = db.query(Referral).filter(
        Referral.referrer_id == guide.id
    ).count()

    earnings = total * 25

    return {

        "total_referrals": total,
        "total_earnings": earnings

    }
    


MIN_CALL_DURATION = 600   # 10 minutes (seconds)
CALL_REWARD = 55


@router.post("/credit-call-earning/{call_id}")
def credit_call_earning(  background_tasks: BackgroundTasks,
    call_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if user["role"] != "senior_guide":
        raise HTTPException(403, "Only guides eligible")

    call = db.query(CallSession).filter(
        CallSession.id == call_id
    ).first()

    if not call:
        raise HTTPException(404, "Call not found")

    duration = (call.end_time - call.start_time).seconds

    if duration < MIN_CALL_DURATION:
        return {
            "message": "Call less than 10 minutes. No reward."
        }

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    # prevent duplicate credit
    already_paid = db.query(WalletTransaction).filter(
        WalletTransaction.call_id == call_id
    ).first()

    if already_paid:
        return {"message": "Already credited"}

    guide.wallet_balance += CALL_REWARD
    db.add(WalletTransaction(
    guide_id=guide.id,
    amount=CALL_REWARD,
    type="CALL_EARNING",
    call_id=call_id,
    booking_id=call.booking_id,
    remark="Call completion reward"
))

    # --------------------------------------------------
    # UPDATE CALL COUNT
    # --------------------------------------------------
    
    if guide.total_calls is None:
        guide.total_calls = 0
    
    guide.total_calls += 1
    
    
    # --------------------------------------------------
    # REFERRAL BONUS AFTER FIRST SUCCESSFUL CALL
    # --------------------------------------------------
    
    if guide.total_calls == 1 and guide.referred_by and not guide.referral_paid:
    
        GUIDE_REWARD = 25
        USER_REWARD = 50
    
        referrer = db.query(SeniorGuide).filter(
            SeniorGuide.id == guide.referred_by
        ).first()
    
        if referrer:
    
            # credit referrer wallet
            referrer.wallet_balance += GUIDE_REWARD
            referrer.referral_bonus += GUIDE_REWARD
    
            db.add(WalletTransaction(
                guide_id=referrer.id,
                amount=GUIDE_REWARD,
                type="REFERRAL",
                remark="Referral bonus earned",
                call_id=call_id,
                 booking_id=call.booking_id
                
                
            ))
    
            # credit new guide wallet
            guide.wallet_balance += USER_REWARD
    
            db.add(WalletTransaction(
                guide_id=guide.id,
                amount=USER_REWARD,
                type="REFERRAL",
                remark="Referral signup reward",
                 booking_id=call.booking_id,
                call_id=call_id
            ))
    
            referral = db.query(Referral).filter(
                Referral.referred_user_id == guide.user_id,
                Referral.status == "PENDING"
            ).first()
    
            if referral:
                referral.status = "APPROVED"
    
            guide.referral_paid = True
    
            background_tasks.add_task(
                create_notification,
                db,
                guide.user_id,
                "Referral Bonus Received",
                "₹50 credited to your wallet"
            )
    
            background_tasks.add_task(
                create_notification,
                db,
                referrer.user_id,
                "Referral Bonus Earned",
                "₹25 credited to your wallet"
            )
    
    
    # --------------------------------------------------
    # SAVE CHANGES
    # --------------------------------------------------
    
    db.commit()
    background_tasks.add_task(
    create_notification,
        db,
        user["user_id"],
        "Reward Credited",
        "₹55 added to your wallet"
    
)

    return {
        "message": "₹55 credited successfully",
        "amount": CALL_REWARD
    }
    

@router.get("/summary")
def wallet_summary(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if user["role"] != "senior_guide":
        raise HTTPException(403, "Access denied")

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.user_id == user["user_id"]
    ).first()

    total_earned = db.query(
        WalletTransaction
    ).filter(
        WalletTransaction.guide_id == guide.id
    ).with_entities(
        WalletTransaction.amount
    ).all()

    total_earned = sum([t.amount for t in total_earned])

    return {
        "pending_earnings": guide.pending_withdrawal,
        "available_balance": guide.wallet_balance,
        "total_earned": total_earned,
        "withdraw_threshold": 500
    }
