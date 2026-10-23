from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Season, SeasonHistory, User, Bot
from app.dependencies import get_current_admin

router = APIRouter(prefix="/api/seasons", tags=["Seasons"])


def _parse_datetime(val: datetime | str) -> datetime:
    if isinstance(val, datetime):
        return val.replace(tzinfo=None) if val.tzinfo else val
    val_str = str(val).strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(val_str, fmt)
        except ValueError:
            pass
    return datetime.fromisoformat(val_str.replace("Z", "+00:00")).replace(tzinfo=None)


class SeasonCreateRequest(BaseModel):
    name: str
    start_date: datetime | str
    end_date: datetime | str | None = None


class SeasonUpdateRequest(BaseModel):
    name: str | None = None
    start_date: datetime | str | None = None
    end_date: datetime | str | None = None


class SeasonResetRequest(BaseModel):
    new_season_name: str
    new_start_date: datetime | str | None = None
    new_end_date: datetime | str | None = None


@router.get("")
def list_seasons(db: Session = Depends(get_db)):
    seasons = db.query(Season).order_by(Season.id.desc()).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "status": s.status,
            "start_date": s.start_date.strftime("%d/%m/%Y %H:%M") if s.start_date else None,
            "end_date": s.end_date.strftime("%d/%m/%Y %H:%M") if s.end_date else None,
            "start_date_iso": s.start_date.isoformat() if s.start_date else None,
            "end_date_iso": s.end_date.isoformat() if s.end_date else None,
            "created_at": s.created_at.strftime("%d/%m/%Y")
        }
        for s in seasons
    ]


@router.get("/active")
def get_active_season(db: Session = Depends(get_db)):
    active_s = db.query(Season).filter(Season.status == "active").order_by(Season.id.desc()).first()
    if not active_s:
        active_s = db.query(Season).order_by(Season.id.desc()).first()
    if not active_s:
        return None
    return {
        "id": active_s.id,
        "name": active_s.name,
        "status": active_s.status,
        "start_date": active_s.start_date.strftime("%d/%m/%Y %H:%M") if active_s.start_date else None,
        "end_date": active_s.end_date.strftime("%d/%m/%Y %H:%M") if active_s.end_date else None
    }


@router.post("")
def create_season(
    req: SeasonCreateRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tên mùa giải không được để trống.")

    start_dt = _parse_datetime(req.start_date)
    end_dt = _parse_datetime(req.end_date) if req.end_date else None

    s = Season(name=name, status="upcoming", start_date=start_dt, end_date=end_dt)
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"message": f"Tạo lịch trình mùa giải '{name}' thành công!", "season_id": s.id}


@router.put("/{season_id}")
def update_season(
    season_id: int,
    req: SeasonUpdateRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    s = db.query(Season).filter(Season.id == season_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Không tìm thấy mùa giải.")

    if req.name and req.name.strip():
        s.name = req.name.strip()
    if req.start_date:
        s.start_date = _parse_datetime(req.start_date)
    if req.end_date:
        s.end_date = _parse_datetime(req.end_date)

    db.commit()
    return {"message": f"Cập nhật mùa giải '{s.name}' thành công!"}


@router.delete("/{season_id}")
def delete_season(
    season_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    s = db.query(Season).filter(Season.id == season_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Không tìm thấy mùa giải.")

    if s.status == "active":
        raise HTTPException(status_code=400, detail="Không thể xóa mùa giải đang hoạt động.")

    db.delete(s)
    db.commit()
    return {"message": f"Đã xóa mùa giải '{s.name}' thành công!"}


@router.post("/{season_id}/reset-and-start-new")
def reset_season_and_start_new(
    season_id: int,
    req: SeasonResetRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    current_season = db.query(Season).filter(Season.id == season_id).first()
    if not current_season:
        raise HTTPException(status_code=404, detail="Mùa giải hiện tại không tồn tại.")

    new_name = req.new_season_name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Tên mùa giải mới không được để trống.")

    now = datetime.utcnow()
    players = db.query(User).filter(User.role == "player").order_by(User.elo.desc()).all()

    db.query(SeasonHistory).filter(SeasonHistory.season_id == current_season.id).delete()

    for idx, p in enumerate(players, 1):
        db.add(SeasonHistory(
            season_id=current_season.id,
            user_id=p.id,
            elo=p.elo,
            rank=idx,
            matches_played=0,
            wins=0,
            created_at=now
        ))

    current_season.status = "completed"
    if not current_season.end_date or current_season.end_date > now:
        current_season.end_date = now

    new_start = _parse_datetime(req.new_start_date) if req.new_start_date else now
    new_end = _parse_datetime(req.new_end_date) if req.new_end_date else None

    db.query(Season).filter(Season.status == "active").update({"status": "completed"}, synchronize_session=False)

    new_season = Season(
        name=new_name,
        status="active",
        start_date=new_start,
        end_date=new_end,
        created_at=now
    )
    db.add(new_season)

    db.query(User).filter(User.role == "player").update({"elo": 0.0}, synchronize_session=False)

    db.commit()
    return {
        "message": f"Đã hoàn thành '{current_season.name}', lưu lịch sử bảng xếp hạng và khởi tạo '{new_name}' (Elo toàn bộ người chơi đã reset về 0)!",
        "new_season_id": new_season.id
    }


@router.get("/{season_id}/leaderboard")
def get_season_leaderboard(season_id: int, db: Session = Depends(get_db)):
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Không tìm thấy mùa giải.")

    if season.status == "active":
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
                "detail": f"Mùa đang đấu",
                "score_label": f"{p.elo:.1f}",
                "elo": p.elo
            })
        return results

    histories = db.query(SeasonHistory).filter(SeasonHistory.season_id == season_id).order_by(SeasonHistory.elo.desc()).all()
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
            "detail": f"Hạng chốt mùa",
            "score_label": f"{h.elo:.1f}",
            "elo": h.elo
        })
    return results