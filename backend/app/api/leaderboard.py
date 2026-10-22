from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Bot, TournamentStanding, Season, SeasonHistory

router = APIRouter(prefix="/api/leaderboard", tags=["Leaderboard"])


def get_rank_tier(elo: float) -> dict:
    val = float(elo or 0.0)
    if val >= 1000.0:
        return {"name": "Legend", "key": "legend", "icon": "fa-crown"}
    if val >= 600.0:
        return {"name": "Gold", "key": "gold", "icon": "fa-trophy"}
    if val >= 300.0:
        return {"name": "Silver", "key": "silver", "icon": "fa-shield"}
    if val >= 100.0:
        return {"name": "Bronze", "key": "bronze", "icon": "fa-shield-halved"}
    return {"name": "Wood", "key": "wood", "icon": "fa-tree"}


@router.get("")
def get_leaderboard(
    filter_type: str = Query("all"),
    tournament_id: int | None = Query(None),
    season_id: int | None = Query(None),
    db: Session = Depends(get_db)
):
    target_season = None
    if season_id:
        target_season = db.query(Season).filter(Season.id == season_id).first()

    if not target_season:
        target_season = db.query(Season).filter(Season.status == "active").order_by(Season.id.desc()).first()

    is_historical = target_season and target_season.status != "active"

    if is_historical and filter_type != "tournament":
        histories = db.query(SeasonHistory).filter(SeasonHistory.season_id == target_season.id).order_by(SeasonHistory.elo.desc()).all()
        results = []
        for idx, h in enumerate(histories, 1):
            p = h.user
            active_bot = db.query(Bot).filter(Bot.user_id == p.id, Bot.is_active == True).first() if p else None
            results.append({
                "rank": h.rank or idx,
                "player_name": p.username if p else "Ẩn danh",
                "user_id": p.id if p else None,
                "bot_name": active_bot.name if active_bot else "Đã lưu",
                "language": active_bot.language if active_bot else "N/A",
                "tier": get_rank_tier(h.elo),
                "score_label": f"{h.elo:.1f}",
                "elo": h.elo
            })
        return results

    if filter_type == "tournament":
        if not tournament_id:
            return []
        standings = db.query(TournamentStanding).filter(TournamentStanding.tournament_id == tournament_id).all()
        standings.sort(key=lambda s: (s.points, s.won), reverse=True)
        results = []
        for idx, s in enumerate(standings, 1):
            bot = s.bot
            owner = bot.owner if bot else None
            results.append({
                "rank": idx,
                "player_name": owner.username if owner else "Ẩn danh",
                "user_id": owner.id if owner else None,
                "bot_name": bot.name if bot else "Chưa chọn",
                "language": bot.language if bot else "N/A",
                "tier": get_rank_tier(owner.elo if owner else 0),
                "detail": f"{s.won}T - {s.drawn}H - {s.lost}B",
                "score_label": f"{s.points} điểm",
                "elo": s.points
            })
        return results

    players = db.query(User).filter(User.role == "player").order_by(User.elo.desc()).all()
    results = []
    for idx, p in enumerate(players, 1):
        active_bot = db.query(Bot).filter(Bot.user_id == p.id, Bot.is_active == True).first()
        if not active_bot:
            active_bot = db.query(Bot).filter(Bot.user_id == p.id).first()
        results.append({
            "rank": idx,
            "player_name": p.username,
            "user_id": p.id,
            "bot_name": active_bot.name if active_bot else "Chưa chọn",
            "language": active_bot.language if active_bot else "N/A",
            "tier": get_rank_tier(p.elo),
            "score_label": f"{p.elo:.1f}",
            "elo": p.elo
        })
    return results