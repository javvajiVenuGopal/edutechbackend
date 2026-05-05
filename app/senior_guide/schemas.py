from pydantic import BaseModel, EmailStr

class SeniorGuideCreate(BaseModel):
    full_name: str
    email: EmailStr
    mobile_number: str

    college_name: str
    branch: str
    year_of_study: str


class SlotCreateSchema(BaseModel):
    time_slot: str



class TestSubmitSchema(BaseModel):
    q1: str
    q2: str
    q3: str