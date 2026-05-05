from typing import Optional

from pydantic import BaseModel, EmailStr



class AdminLoginSchema(BaseModel):
    email: str
    password: str

class AdminRegisterSchema(BaseModel):
    email: EmailStr
    password: str
    role: str          # e.g., "SUPERADMIN", "FINANCIAL_ADMIN", etc.
    is_active: Optional[bool] = True