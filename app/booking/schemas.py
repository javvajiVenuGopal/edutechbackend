from pydantic import BaseModel


class CreateBookingSchema(BaseModel):
    guide_id: int
    time_slot: str