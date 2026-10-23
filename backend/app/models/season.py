from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.models.base import Base


class Season(Base):
    __tablename__ = "seasons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    status = Column(String(20), default="active")
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    histories = relationship("SeasonHistory", back_populates="season", cascade="all, delete-orphan")


class SeasonHistory(Base):
    __tablename__ = "season_histories"

    id = Column(Integer, primary_key=True, index=True)
    season_id = Column(Integer, ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    elo = Column(Float, default=0.0)
    rank = Column(Integer, nullable=True)
    matches_played = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    season = relationship("Season", back_populates="histories")
    user = relationship("User")