from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=True)
    bot1_id = Column(Integer, ForeignKey("bots.id", ondelete="SET NULL"), nullable=True)
    bot2_id = Column(Integer, ForeignKey("bots.id", ondelete="SET NULL"), nullable=True)
    winner_bot_id = Column(Integer, nullable=True)
    winner_name = Column(String(100), default="")
    win_reason = Column(String(255), default="")
    moves_count = Column(Integer, default=0)
    duration_sec = Column(Integer, default=0)
    replay_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    tournament = relationship("Tournament", back_populates="matches")
    bot1 = relationship("Bot", foreign_keys=[bot1_id])
    bot2 = relationship("Bot", foreign_keys=[bot2_id])