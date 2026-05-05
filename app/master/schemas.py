from pydantic import BaseModel


class CountrySchema(BaseModel):
    name: str


class CollegeSchema(BaseModel):
    name: str
    country_id: int
    state_id: int


class BranchSchema(BaseModel):
    name: str
    college_id: int
    
    
class StateSchema(BaseModel):
    name: str
    country_id: int