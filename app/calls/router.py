import asyncio

from  app.notifications.service import create_notification
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect,BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timezone


from app.core.agora_config import AGORA_APP_ID
from app.core.database import get_db
from app.auth.utils import get_current_user
from app.booking.models import Booking
from app.senior_guide.models import SeniorGuide
from app.calls.models import CallSession
from app.services.agora_service import generate_agora_token
from app.services.referral_service import process_referral_bonus
from fastapi import BackgroundTasks
from .socket import manager


router = APIRouter(prefix="/call", tags=["Call System"])


def verify_booking_access(booking_id: int, user_id: int, db: Session):

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == booking.guide_id
    ).first()

    if not guide:
        raise HTTPException(404, "Guide not found")

    if user_id not in [booking.seeker_id, guide.user_id]:
        raise HTTPException(403, "Not allowed")

    return booking, guide


@router.post("/session/create/{booking_id}")
def create_call_session(background_tasks: BackgroundTasks,
    booking_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    booking, _ = verify_booking_access(
        booking_id,
        user["user_id"],
        db
    )

    if booking.payment_status != "PAID":
        raise HTTPException(400, "Payment incomplete")

    existing = db.query(CallSession).filter(
        CallSession.booking_id == booking_id
    ).first()

    if existing:
        return {"session_id": existing.id}

    session = CallSession(
        booking_id=booking_id,
        status="CREATED"
    )

    db.add(session)
    db.commit()
    db.refresh(session)
    background_tasks.add_task(
    create_notification,
        
        booking.seeker_id,
        "Call Session Created",
        "Your call session has been prepared"
    
)

    return {"session_id": session.id}

from datetime import datetime, timezone, timedelta
import random


@router.get("/token/{booking_id}")
def get_agora_token(
    booking_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    booking, _ = verify_booking_access(
        booking_id,
        user["user_id"],
        db
    )

    session = db.query(CallSession).filter(
        CallSession.booking_id == booking_id
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    # -----------------------------------------
    # SESSION WINDOW VALIDATION (REJOIN SUPPORT)
    # -----------------------------------------

    booking_time = datetime.fromisoformat(booking.time_slot)

    session_start_time = booking_time - timedelta(minutes=5)
    session_end_time = booking_time + timedelta(minutes=15)

    now = datetime.now(timezone.utc)

    # # block early join
    # if now < session_start_time:
    #     raise HTTPException(
    #         400,
    #         "Call session not started yet"
    #     )

    # # block late join
    # if now > session_end_time:
    #     raise HTTPException(
    #         400,
    #         "Call session expired"
    #     )

    # -----------------------------------------
    # GENERATE TOKEN
    # -----------------------------------------

    uid = random.randint(100000, 999999)

    channel = f"booking_{booking_id}"

    token = generate_agora_token(channel, uid)

    return {
        "appId": AGORA_APP_ID,
        "channel": channel,
        "token": token,
        "uid": uid
    }
    
@router.post("/start/{booking_id}")
async def start_call(background_tasks: BackgroundTasks,
    booking_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    
    call_session = db.query(CallSession).filter(
    CallSession.booking_id == booking_id
    ).first()

    if call_session:
        call_session.status = "STARTED"
        booking.call_status = "STARTED"
        call_session.start_time = datetime.now(timezone.utc)
    db.commit()

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == booking.guide_id
    ).first()

    # notify seeker
     # notify seeker
    await manager.send_to_user(
        booking.seeker_id,
        {
            "type": "incoming_call",
            "booking_id": booking.id
        }
    )

    # # notify guide
    # await manager.send_to_user(
    #     guide.user_id,
    #     {
    #         "type": "incoming_call",
    #         "booking_id": booking.id
    #     }
    # )
    background_tasks.add_task(
    create_notification,
        
        booking.seeker_id,
        "Call Started",
        "Your consultation call has started"
    
)

    background_tasks.add_task(
    create_notification,
        
        guide.user_id,
        "Call Started",
        "Consultation call started successfully"
    
)

    return {"message": "Call started"}



@router.post("/end/{booking_id}")
async def end_call(
    booking_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    booking.call_status = "COMPLETED"
    booking.status = "COMPLETED"

    call_session = db.query(CallSession).filter(
        CallSession.booking_id == booking_id
    ).first()

    if call_session:
        call_session.status = "COMPLETED"
    if call_session:
        call_session.end_time = datetime.now(timezone.utc)
    if call_session and call_session.start_time and call_session.end_time:

        duration = (
            call_session.end_time - call_session.start_time
        ).total_seconds()

        if duration < 300:
            booking.refund_flag = True
            booking.refund_reason = "Call duration < 5 minutes"

    db.commit()

    guide = db.query(SeniorGuide).filter(
        SeniorGuide.id == booking.guide_id
    ).first()

    # send notifications async-safe
    background_tasks.add_task(
        create_notification,
        
        booking.seeker_id,
        "Call Completed",
        "Your consultation session completed successfully"
    )

    if guide:
        background_tasks.add_task(
            create_notification,
            
            guide.user_id,
            "Session Completed",
            "Consultation session finished successfully"
        )

    await manager.send_to_user(
    booking.seeker_id,
    {
        "type": "call_ended",
        "booking_id": booking.id
    }
)

    await manager.send_to_user(
        guide.user_id,
        {
            "type": "call_ended",
            "booking_id": booking.id
        }
    )

    return {"message": "Call ended successfully"}

@router.post("/cancel/{booking_id}")
def cancel_call(backgroundtasks:BackgroundTasks,
    booking_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    booking, _ = verify_booking_access(
        booking_id,
        user["user_id"],
        db
    )

    session = db.query(CallSession).filter(
        CallSession.booking_id == booking_id
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    if session.status != "CREATED":
        raise HTTPException(400, "Cannot cancel after start")

    session.status = "CANCELLED"
    booking.status = "CANCELLED"

    db.commit()
    guide = db.query(SeniorGuide).filter(
    SeniorGuide.id == booking.guide_id
).first()

    backgroundtasks.add_task(
        create_notification,
            
            booking.seeker_id,
            "Call Cancelled",
            "Your consultation session has been cancelled"
        
    )

    backgroundtasks.add_task(
        create_notification,
            
            guide.user_id,
            "Session Cancelled",
            "Consultation session cancelled"
        
    )

    return {"message": "Call cancelled"}


@router.get("/status/{booking_id}")
def call_status(
    booking_id: int,
    db: Session = Depends(get_db)
):

    call = db.query(CallSession).filter(
        CallSession.booking_id == booking_id
    ).first()

    if not call:
        return {"call_status": "NOT_STARTED"}

    return {"call_status": call.status}



@router.websocket("/ws/call/{user_id}")
async def websocket_call(websocket: WebSocket, user_id: int):

    await manager.connect(user_id, websocket)

    print(f"Socket connected: {user_id}")

    try:
        while True:
            await websocket.receive_text()

    except:
        manager.disconnect(user_id)
        print(f"Socket disconnected: {user_id}")

        
