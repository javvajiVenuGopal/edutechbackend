from pydantic import BaseModel, Field
from typing import Optional


class RatingCreateSchema(BaseModel):

    rating: int = Field(..., ge=1, le=5)

    honesty: int = Field(..., ge=1, le=5)

    recommend: int = Field(..., ge=1, le=5)

    comments: Optional[str] = Field(default="")