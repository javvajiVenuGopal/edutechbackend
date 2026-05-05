import asyncio

from app.notifications.service import create_notification
from fastapi import APIRouter, Depends, Form, HTTPException,BackgroundTasks
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.utils import get_current_user
from app.core.database import get_db
from app.seeker.models import SeekerProfile
from app.senior_guide.models import SeniorGuide

router = APIRouter(prefix="/seeker", tags=["Seeker"])


@router.get("/profile")
def get_profile(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    profile = db.query(SeekerProfile).filter(
        SeekerProfile.user_id == user["user_id"]
    ).first()

    if not profile:
        raise HTTPException(404, "Profile not found")

    return profile


# ===============================
# CREATE PROFILE
# ===============================
@router.post("/collegeform")
def college_form(  background_tasks: BackgroundTasks,
    college: str = Form(...),
    branch: str = Form(...),
    location: str = Form(...),
    state: str = Form(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if user["role"] != "seeker":
        raise HTTPException(403, "Only seekers allowed")

    existing_profile = db.query(SeekerProfile).filter(
        SeekerProfile.user_id == user["user_id"]
    ).first()

    if existing_profile:
        raise HTTPException(400, "Profile already exists")

    profile = SeekerProfile(
        user_id=user["user_id"],
        college=college,
        branch=branch,
        location=location,
        state=state
    )

    db.add(profile)
    db.commit()
    background_tasks.add_task(
    create_notification,
        
        user["user_id"],
        "Profile Created",
        "Your seeker profile created successfully"
    
)

    return {"message": "Profile created successfully"}


# --------------------------------------
# CREATE / UPDATE SEEKER COLLEGE FORM
# --------------------------------------
from fastapi import Form, Depends, HTTPException
from sqlalchemy.orm import Session

@router.put("/collegeform")
def update_profile(background_tasks: BackgroundTasks,
    location: str = Form(...),
    state: str = Form(...),
    college: str = Form(...),
    branch: str = Form(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    profile = db.query(SeekerProfile).filter(
        SeekerProfile.user_id == user["user_id"]
    ).first()

    if not profile:
        raise HTTPException(404, "Profile not found")

    profile.location = location
    profile.state = state
    profile.college = college
    profile.branch = branch

    db.commit()
    background_tasks.add_task(
    create_notification,
        
        user["user_id"],
        "Profile Updated",
        "Your seeker profile updated successfully"
    
)

    return {"message": "Profile updated successfully"}


from sqlalchemy import func

from sqlalchemy import func
from fastapi import Depends, Query
from app.auth.utils import get_current_user
from datetime import datetime, timezone, timedelta, timezone

def is_online(last_seen):
    if not last_seen:
        return False
    return last_seen >  datetime.now(timezone.utc) - timedelta(minutes=2)


@router.get("/guides/search")
def search_guides(
    branch: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    seeker_profile = db.query(SeekerProfile).filter(
        SeekerProfile.user_id == current_user["user_id"]
    ).first()

    if not seeker_profile or not seeker_profile.college:
        return []

    # same college guides (case-insensitive + spelling tolerant)
    query = db.query(SeniorGuide).filter(
        func.lower(SeniorGuide.college_name).ilike(
            f"%{seeker_profile.college.lower()}%"
        ),
        SeniorGuide.status == "ACTIVE"
    )

    # optional branch filter
    if branch:
        query = query.filter(
            func.lower(SeniorGuide.branch).ilike(f"%{branch.lower()}%")
        )

    guides = query.all()

    return [
        {
            "id": g.id,
            "guide_unique_id": g.unique_id,
            "college_name": g.college_name,
            "branch": g.branch,
            "rating": g.rating,
            "total_calls": g.total_calls,
            "online": is_online(g.user.last_seen) if g.user else False
        }
        for g in guides
    ]
