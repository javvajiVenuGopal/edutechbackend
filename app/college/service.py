from sqlalchemy.orm import Session
from app.auth import models
from app.auth.models import User
from app.auth.utils import hash_password, verify_password, create_token


# REGISTER
def register_user(db: Session, user):
    db_user = models.User(
        name=user.name,
        email=user.email,
        mobile=user.mobile,
        role=user.role,
        password=hash_password(user.password)
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# LOGIN
def login_user(db: Session, email: str, password: str):
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        return None

    if not verify_password(password, user.password):
        return None

    token = create_token({"user_id": user.id, "email": user.email})

    return {
        "access_token": token,
        "token_type": "bearer"
    }