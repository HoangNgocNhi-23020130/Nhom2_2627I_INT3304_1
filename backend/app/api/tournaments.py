from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Tournament, TournamentStanding, Match, Bot, User, Season
from app.dependencies import get_current_user, get_current_admin
from app.services.tournament_service import execute_tournament

router = APIRouter(prefix="/api/tournaments", tags=["Tournaments"])


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


class TournamentCreateRequest(BaseModel):
    name: str
    start_time: datetime | str
    season_id: int | None = None


class TournamentUpdateRequest(BaseModel):
    name: str | None = None
    start_time: datetime | str | None = None
    season_id: int | None = None


@router.post("/create")
def create_tournament(
    req: TournamentCreateRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tên giải đấu không được để trống.")

    start_dt = _parse_datetime(req.start_time)

    season_id = req.season_id
    if not season_id:
        active_season = db.query(Season).filter(Season.status == "active").order_by(Season.id.desc()).first()
        season_id = active_season.id if active_season else None

    tournament = Tournament(
        name=name,
        type="major",
        format="round_robin",
        status="open",
        season_id=season_id,
        start_time=start_dt,
        created_by=current_admin.username
    )
    db.add(tournament)
    db.commit()
    db.refresh(tournament)
    return {"message": f"Giải đấu '{name}' đã được tạo thành công!", "tournament_id": tournament.id}


@router.post("/{tournament_id}/start")
def start_tournament_manually(
    tournament_id: int,
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    tour = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tour:
        raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu.")

    if tour.status != "open":
        raise HTTPException(status_code=400, detail="Chỉ có thể bắt đầu giải đấu đang mở đăng ký!")

    standings = db.query(TournamentStanding).filter(TournamentStanding.tournament_id == tournament_id).all()
    if len(standings) < 2:
        raise HTTPException(status_code=400, detail="Cần tối thiểu 2 thí sinh đăng ký để có thể khởi tranh giải đấu!")

    tour.status = "running"
    db.commit()

    background_tasks.add_task(execute_tournament, tournament_id)
    return {"message": f"Giải đấu '{tour.name}' đã bắt đầu thi đấu ngầm!", "status": "running"}


@router.put("/{tournament_id}")
def update_tournament(
    tournament_id: int,
    req: TournamentUpdateRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    tour = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tour:
        raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu.")

    if tour.status != "open":
        raise HTTPException(status_code=400, detail="Không thể chỉnh sửa giải đấu đang diễn ra, đã xong hoặc đã hủy!")

    if req.name and req.name.strip():
        tour.name = req.name.strip()

    if req.start_time:
        tour.start_time = _parse_datetime(req.start_time)

    if req.season_id is not None:
        tour.season_id = req.season_id

    db.commit()
    return {"message": f"Cập nhật thông tin giải đấu '{tour.name}' thành công!"}


@router.post("/{tournament_id}/cancel")
def cancel_tournament(
    tournament_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    tour = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tour:
        raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu.")

    if tour.status != "open":
        raise HTTPException(status_code=400, detail="Chỉ có thể hủy giải đấu khi giải chưa diễn ra!")

    tour.status = "cancelled"
    db.commit()
    return {"message": f"Đã hủy giải đấu '{tour.name}'. Lịch sử giải vẫn được lưu trữ!"}


@router.delete("/{tournament_id}")
def delete_tournament(
    tournament_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    tour = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tour:
        raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu.")

    if tour.status != "cancelled":
        raise HTTPException(status_code=400, detail="Chỉ những giải đấu đã bị HỦY mới có thể xóa vĩnh viễn!")

    db.query(Match).filter(Match.tournament_id == tournament_id).delete()
    db.query(TournamentStanding).filter(TournamentStanding.tournament_id == tournament_id).delete()
    db.delete(tour)
    db.commit()
    return {"message": f"Đã xóa hoàn toàn giải đấu #{tournament_id} khỏi hệ thống."}


@router.get("/my")
def list_my_tournaments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_bots = db.query(Bot).filter(Bot.user_id == current_user.id).all()
    user_bot_map = {b.id: b for b in user_bots}
    user_bot_ids = list(user_bot_map.keys())

    if not user_bot_ids:
        return []

    standings = db.query(TournamentStanding).filter(TournamentStanding.bot_id.in_(user_bot_ids)).all()
    if not standings:
        return []

    tour_standing_map = {s.tournament_id: s for s in standings}
    tour_ids = list(tour_standing_map.keys())

    tournaments = (
        db.query(Tournament)
        .filter(Tournament.id.in_(tour_ids))
        .order_by(Tournament.start_time.desc())
        .all()
    )

    res = []
    for t in tournaments:
        standing = tour_standing_map.get(t.id)
        bot = user_bot_map.get(standing.bot_id) if standing else None

        registered_count = (
            db.query(func.count(distinct(Bot.user_id)))
            .join(TournamentStanding, TournamentStanding.bot_id == Bot.id)
            .filter(TournamentStanding.tournament_id == t.id)
            .scalar()
        ) or 0

        res.append({
            "id": t.id,
            "name": t.name,
            "type": t.type,
            "status": t.status,
            "season_id": t.season_id,
            "registered_count": registered_count,
            "created_by": t.created_by,
            "start_time": t.start_time.strftime("%d/%m/%Y %H:%M") if t.start_time else "Chưa đặt",
            "start_time_iso": t.start_time.strftime("%Y-%m-%dT%H:%M") if t.start_time else "",
            "created_at": t.created_at.strftime("%d/%m/%Y %H:%M"),
            "my_bot": {
                "id": bot.id,
                "name": bot.name,
                "language": bot.language
            } if bot else None,
            "my_standing": {
                "played": standing.played,
                "won": standing.won,
                "drawn": standing.drawn,
                "lost": standing.lost,
                "points": standing.points
            } if standing else None
        })
    return res


@router.post("/{tournament_id}/register")
def register_to_tournament(
    tournament_id: int,
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "admin":
        raise HTTPException(status_code=403, detail="Tài khoản Admin không được phép tham gia thi đấu giải.")

    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu.")
    if tournament.status != "open":
        raise HTTPException(status_code=400, detail="Giải đấu đã đóng đăng ký, đang đấu hoặc đã kết thúc.")

    bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == current_user.id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot không tồn tại hoặc không thuộc sở hữu của bạn.")

    user_bot_ids = [b.id for b in db.query(Bot.id).filter(Bot.user_id == current_user.id).all()]
    existing = db.query(TournamentStanding).filter(
        TournamentStanding.tournament_id == tournament_id,
        TournamentStanding.bot_id.in_(user_bot_ids)
    ).first()

    if existing:
        if existing.bot_id == bot_id:
            return {"message": f"Bot '{bot.name}' đã đăng ký giải này rồi."}
        existing.bot_id = bot_id
        db.commit()
        return {"message": f"Đã chuyển bot thi đấu giải sang '{bot.name}' thành công!"}

    db.add(TournamentStanding(tournament_id=tournament_id, bot_id=bot_id))
    db.commit()
    return {"message": f"Đăng ký thành công bot '{bot.name}' tham gia giải!"}


@router.get("")
def list_tournaments(
    season_id: int | None = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Tournament)
    if season_id is not None:
        query = query.filter(Tournament.season_id == season_id)
    tournaments = query.order_by(Tournament.start_time.asc()).all()
    res = []
    for t in tournaments:
        registered_count = (
            db.query(func.count(distinct(Bot.user_id)))
            .join(TournamentStanding, TournamentStanding.bot_id == Bot.id)
            .filter(TournamentStanding.tournament_id == t.id)
            .scalar()
        ) or 0

        res.append({
            "id": t.id,
            "name": t.name,
            "type": t.type,
            "status": t.status,
            "season_id": t.season_id,
            "registered_count": registered_count,
            "created_by": t.created_by,
            "start_time": t.start_time.strftime("%d/%m/%Y %H:%M") if t.start_time else "Chưa đặt",
            "start_time_iso": t.start_time.strftime("%Y-%m-%dT%H:%M") if t.start_time else "",
            "created_at": t.created_at.strftime("%d/%m/%Y %H:%M")
        })
    return res


@router.get("/{tournament_id}/standings")
def get_tournament_standings(tournament_id: int, db: Session = Depends(get_db)):
    standings = db.query(TournamentStanding).filter_by(tournament_id=tournament_id).all()
    standings.sort(key=lambda s: (s.points, s.won), reverse=True)
    return [
        {
            "bot_name": s.bot.name if s.bot else "Unknown",
            "played": s.played,
            "won": s.won,
            "drawn": s.drawn,
            "lost": s.lost,
            "points": s.points
        }
        for s in standings
    ]


@router.get("/{tournament_id}/matches")
def get_tournament_matches(
    tournament_id: int,
    q: str = Query(""),
    round: str = Query("", alias="round_type"),
    order: str = Query("asc"),
    db: Session = Depends(get_db)
):
    query = db.query(Match).filter(Match.tournament_id == tournament_id)
    if order == "desc":
        query = query.order_by(Match.id.desc())
    else:
        query = query.order_by(Match.id.asc())

    matches = query.all()
    results = []
    for idx, m in enumerate(matches, 1):
        bot1 = db.query(Bot).filter(Bot.id == m.bot1_id).first()
        bot2 = db.query(Bot).filter(Bot.id == m.bot2_id).first()

        p1_name = bot1.owner.username if bot1 and bot1.owner else "P1"
        b1_name = bot1.name if bot1 else "Bot 1"
        p2_name = bot2.owner.username if bot2 and bot2.owner else "P2"
        b2_name = bot2.name if bot2 else "Bot 2"

        match_round = getattr(m, "round", 1) or 1

        if round.strip():
            try:
                r_val = int(round.strip())
                if match_round != r_val:
                    continue
            except ValueError:
                pass

        if q.strip():
            kw = q.strip().lower()
            text_corpus = f"{p1_name} {b1_name} {p2_name} {b2_name}".lower()
            if kw not in text_corpus:
                continue

        results.append({
            "id": m.id,
            "index": idx,
            "round": match_round,
            "player1": p1_name,
            "bot1_name": b1_name,
            "player2": p2_name,
            "bot2_name": b2_name,
            "winner_name": m.winner_name or "Hòa",
            "win_reason": m.win_reason or "",
            "moves_count": m.moves_count or 0,
            "duration_sec": m.duration_sec or 0,
            "replay_url": f"/api/matches/{m.id}/replay"
        })
    return results