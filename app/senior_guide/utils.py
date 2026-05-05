import jwt
from datetime import datetime, timezone, timedelta

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"

def create_token(data: dict):
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=2)

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)