from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from passlib.context import CryptContext

from app.core.config import SECRET_KEY, ALGORITHM


pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto"
)

security = HTTPBearer()


# HASH PASSWORD
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# VERIFY PASSWORD
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password
    )


# CREATE TOKEN
def create_token(data: dict):

    payload = data.copy()

    payload["exp"] = datetime.now(timezone.utc) + timedelta(days=7)

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    try:

        token = credentials.credentials

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("user_id")
        role = payload.get("role")

        if user_id is None or role is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token payload"
            )

        return payload

    except Exception:

        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
import os

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def validate_file(filename: str):
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Only PDF, JPG, PNG allowed")


def validate_size(file):
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    if size > MAX_FILE_SIZE:
        raise ValueError("File size must be under 5MB")
