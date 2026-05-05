from fastapi import FastAPI
from app.admin.models import AdminRole
from app.auth.utils import hash_password
from app.core.config import ADMIN_EMAIL, ADMIN_PASSWORD
from app.core.database import Base, SessionLocal, engine
from app.admin.analytics_router import router as analytics_router
from app.auth.router import router as auth_router
from app.senior_guide.router import router as guide_router
from app.admin.router import router as admin_router
from app.seeker.router import router as seeker_router
from app.college.router import router as colleges_router
from app.booking.router import router as booking_router
from app.calls.router import router as call_router
from app.senior_guide.slots_router import router as slots_router
from app.rating.router import router as rating_router
from app.college.router import router as feedback_router
from app.reports.router import router as report_router
from app.master.router import router as master_router
from app.availability.router import router as availability_router
from app.admin.export_router import router as export_router
from app.logs.router import router as logs_router
from app.notifications.router import router as notification_router

from app.wallet.router import router as wallet_router
from app.core.limiter import limiter
from slowapi.middleware import SlowAPIMiddleware
from app.services.scheduler import start_scheduler
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from app.notifications.ws_router import notification_ws_router

app = FastAPI(title="Exameets")


from fastapi.middleware.cors import CORSMiddleware


origins = [
    "http://localhost:5173",
    "https://edutech-1-b374.onrender.com",
    "https://seniorguide.exameets.in"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_superadmin():
    db = SessionLocal()
    existing = db.query(AdminRole).filter(AdminRole.email == ADMIN_EMAIL).first()
    if not existing:
        hashed = hash_password(ADMIN_PASSWORD)
        superadmin = AdminRole(
            email=ADMIN_EMAIL,
            password=hashed,
            role="SUPERADMIN",
            is_active=True
        )
        db.add(superadmin)
        db.commit()
        print(f"Superadmin {ADMIN_EMAIL} created.")
    db.close()
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)



@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"message": "Too many requests"}
    )


app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

load_dotenv()


@app.on_event("startup")
def startup_event():
    start_scheduler()



Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(guide_router)
app.include_router(admin_router)
app.include_router(seeker_router)
app.include_router(booking_router)
app.include_router(call_router)
app.include_router(rating_router)
app.include_router(feedback_router)
app.include_router(report_router)
app.include_router(master_router)
app.include_router(availability_router)
app.include_router(export_router)
app.include_router(logs_router)
app.include_router(notification_router)

app.include_router(wallet_router)
app.include_router(analytics_router)
app.include_router(slots_router)
app.include_router(colleges_router)
app.include_router(notification_ws_router)
