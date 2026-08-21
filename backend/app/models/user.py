from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class User(Base):
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)

    instagram_accounts = relationship("InstagramAccount", back_populates="user", cascade="all, delete-orphan")
    facebook_accounts = relationship("FacebookAccount", back_populates="user", cascade="all, delete-orphan")
