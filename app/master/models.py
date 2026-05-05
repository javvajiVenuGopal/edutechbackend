from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Country(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True)

    name = Column(String, unique=True)

    states = relationship("State", back_populates="country")

    colleges = relationship("College", back_populates="country")

class College(Base):
    __tablename__ = "colleges"

    id = Column(Integer, primary_key=True)

    name = Column(String, unique=True)

    country_id = Column(Integer, ForeignKey("countries.id"))

    state_id = Column(Integer, ForeignKey("states.id"))

    country = relationship("Country", back_populates="colleges")

    state = relationship("State", back_populates="colleges")

    branches = relationship("Branch", back_populates="college")

class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True)

    name = Column(String)

    college_id = Column(Integer, ForeignKey("colleges.id"))

    college = relationship("College", back_populates="branches")
    
class State(Base):
    __tablename__ = "states"

    id = Column(Integer, primary_key=True)

    name = Column(String)

    country_id = Column(Integer, ForeignKey("countries.id"))

    country = relationship("Country", back_populates="states")

    colleges = relationship("College", back_populates="state")