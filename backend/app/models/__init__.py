"""
backend/app/models/__init__.py
Gom tất cả model vào Base.metadata để SQLAlchemy nhận diện bảng.
"""
from app.models.base import Base
from app.models.user import User
from app.models.bot import Bot
from app.models.tournament import Tournament
from app.models.match import Match
from app.models.standing import TournamentStanding
from app.models.season import Season, SeasonHistory
from app.models.setting import SystemSetting

__all__ = ["Base", "User", "Bot", "Tournament", "Match", "TournamentStanding",
           "Season", "SeasonHistory", "SystemSetting"]