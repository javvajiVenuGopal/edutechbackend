from typing import Optional

from pydantic import BaseModel, EmailStr




class RegisterSchema(BaseModel):
    full_name: str
    email: EmailStr
    mobile_number: str
    role: Optional[str] = "seeker"


class OTPVerifySchema(BaseModel):
    email: EmailStr
    otp: str


class LoginSchema(BaseModel):
    email: str


class TokenResponse(BaseModel):
    message: str
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    mobile_number: str
    is_verified: bool

    class Config:
        from_attributes = True