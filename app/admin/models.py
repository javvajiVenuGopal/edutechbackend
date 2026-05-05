from sqlalchemy import Boolean, Column, Integer, String
from app.core.database import Base
from sqlalchemy import Enum as SqlEnum

class AdminRole(Base):

    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)

    email = Column(String, unique=True)
    password = Column(String)

    role = Column(String, default="admin", nullable=False)
    
    is_active = Column(Boolean, default=True)




class EligibilityQuestion(Base):

    __tablename__ = "eligibility_questions"

    id = Column(Integer, primary_key=True, index=True)

    question = Column(String, nullable=False)

    correct_answer = Column(String, nullable=False)

    is_active = Column(Boolean, default=True)
