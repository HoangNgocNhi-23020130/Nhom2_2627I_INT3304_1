"""
backend/app/models/user.py
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="player")  # "player", "admin", "system"
    elo = Column(Float, default=1200.0)          # Elo thuộc về Người chơi
    is_banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    bots = relationship("Bot", back_populates="owner", cascade="all, delete-orphan")