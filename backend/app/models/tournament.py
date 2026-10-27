from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), default="major")
    format = Column(String(20), default="round_robin")
    status = Column(String(20), default="open")
    season_id = Column(Integer, ForeignKey("seasons.id", ondelete="SET NULL"), nullable=True)
    start_time = Column(DateTime, nullable=True)
    created_by = Column(String(50), default="admin")
    created_at = Column(DateTime, default=datetime.utcnow)

    season = relationship("Season")
    standings = relationship("TournamentStanding", back_populates="tournament", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="tournament", cascade="all, delete-orphan")