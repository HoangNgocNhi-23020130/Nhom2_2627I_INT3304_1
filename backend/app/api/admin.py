from collections import OrderedDict
from math import ceil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_, func, distinct
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Bot, Tournament, Match, TournamentStanding, SystemSetting
from app.dependencies import get_current_admin
from app.config import BOTS_DIR
from app.services.matchmaking_service import run_ladder_matchmaking
from app.services import scheduler

router = APIRouter(prefix="/api/admin", tags=["Admin"])

_BOT_CODE_CACHE = OrderedDict()
_MAX_CACHE_SIZE = 128


class LadderConfigRequest(BaseModel):
    enabled: bool
    mode: str = "interval"
    interval_value: int = 15
    interval_unit: str = "minute"
    weekly_day: str = "4"
    weekly_time: str = "20:00"


@router.get("/stats")
def get_system_stats(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    total_players = db.query(User).filter(User.role == "player").count()
    total_bots = db.query(Bot).count()
    total_tournaments = db.query(Tournament).count()
    total_matches = db.query(Match).count()
    return {
        "total_players": total_players,
        "total_bots": total_bots,
        "total_tournaments": total_tournaments,
        "total_matches": total_matches,
    }


@router.get("/matchmaking/config")
def get_ladder_config(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    en_row = db.query(SystemSetting).filter(SystemSetting.key == "ladder_enabled").first()
    mode_row = db.query(SystemSetting).filter(SystemSetting.key == "ladder_mode").first()
    val_row = db.query(SystemSetting).filter(SystemSetting.key == "ladder_interval_value").first()
    unit_row = db.query(SystemSetting).filter(SystemSetting.key == "ladder_interval_unit").first()
    day_row = db.query(SystemSetting).filter(SystemSetting.key == "ladder_weekly_day").first()
    time_row = db.query(SystemSetting).filter(SystemSetting.key == "ladder_weekly_time").first()

    enabled = en_row.value.lower() == "true" if en_row else True
    mode = mode_row.value if mode_row else "interval"
    interval_value = int(val_row.value) if val_row else 15
    interval_unit = unit_row.value if unit_row else "minute"
    weekly_day = day_row.value if day_row else "4"
    weekly_time = time_row.value if time_row else "20:00"

    return {
        "enabled": enabled,
        "mode": mode,
        "interval_value": interval_value,
        "interval_unit": interval_unit,
        "weekly_day": weekly_day,
        "weekly_time": weekly_time,
        "last_run_timestamp": scheduler._last_ladder_run
    }


@router.put("/matchmaking/config")
def update_ladder_config(
    req: LadderConfigRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if req.interval_value < 1:
        raise HTTPException(status_code=400, detail="Giá trị chu kỳ tối thiểu là 1.")

    unit_names = {"minute": "phút", "hour": "giờ", "day": "ngày"}
    if req.interval_unit not in unit_names:
        raise HTTPException(status_code=400, detail="Đơn vị không hợp lệ.")

    def set_config_val(k: str, v: str):
        row = db.query(SystemSetting).filter(SystemSetting.key == k).first()
        if not row:
            db.add(SystemSetting(key=k, value=v))
        else:
            row.value = v

    set_config_val("ladder_enabled", str(req.enabled).lower())
    set_config_val("ladder_mode", req.mode)
    set_config_val("ladder_interval_value", str(req.interval_value))
    set_config_val("ladder_interval_unit", req.interval_unit)
    set_config_val("ladder_weekly_day", req.weekly_day)
    set_config_val("ladder_weekly_time", req.weekly_time)

    mult = 1 if req.interval_unit == "minute" else (60 if req.interval_unit == "hour" else 1440)
    set_config_val("ladder_interval_minutes", str(req.interval_value * mult))

    db.commit()

    day_labels = {
        "all": "mỗi ngày",
        "0": "Thứ 2 hàng tuần",
        "1": "Thứ 3 hàng tuần",
        "2": "Thứ 4 hàng tuần",
        "3": "Thứ 5 hàng tuần",
        "4": "Thứ 6 hàng tuần",
        "5": "Thứ 7 hàng tuần",
        "6": "Chủ Nhật hàng tuần"
    }

    if not req.enabled:
        message = "Cập nhật thành công: Đã TẮT tự động ghép trận xếp hạng."
    else:
        if req.mode == "weekly":
            desc = f"vào lúc {req.weekly_time} {day_labels.get(req.weekly_day, 'Thứ 6 hàng tuần')}"
        else:
            desc = f"mỗi {req.interval_value} {unit_names.get(req.interval_unit, 'phút')}/lần"
        message = f"Cập nhật thành công: Đã BẬT tự động ghép trận ({desc})."

    return {
        "message": message,
        "enabled": req.enabled,
        "mode": req.mode,
        "interval_value": req.interval_value,
        "interval_unit": req.interval_unit,
        "weekly_day": req.weekly_day,
        "weekly_time": req.weekly_time
    }


@router.post("/matchmaking/run")
def trigger_ladder_matchmaking(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    results = run_ladder_matchmaking(db)
    return {
        "message": f"Đã chạy xong đợt ghép trận xếp hạng! Tổng cộng {len(results)} trận.",
        "matches": results
    }


@router.get("/players")
def list_players_paginated(
    q: str = Query("", description="Tìm tên người chơi"),
    page: int = Query(1, ge=1),
    limit: int = Query(8, ge=1, le=50),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    query = db.query(User).filter(User.role == "player")
    if q.strip():
        query = query.filter(User.username.ilike(f"%{q.strip()}%"))

    total = query.count()
    total_pages = ceil(total / limit) if total > 0 else 1
    players = query.order_by(User.elo.desc()).offset((page - 1) * limit).limit(limit).all()

    items = []
    for p in players:
        bots = db.query(Bot).filter(Bot.user_id == p.id).all()
        active_bot = next((b for b in bots if b.is_active), None)

        items.append({
            "id": p.id,
            "username": p.username,
            "is_banned": p.is_banned,
            "total_bots": len(bots),
            "active_bot": {
                "id": active_bot.id,
                "name": active_bot.name,
                "language": active_bot.language,
                "elo": p.elo
            } if active_bot else None,
            "elo": p.elo,
            "max_elo": p.elo,
            "created_at": p.created_at.strftime("%d/%m/%Y")
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }


@router.post("/players/{user_id}/toggle-ban")
def toggle_ban_player(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id, User.role == "player").first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người chơi.")

    user.is_banned = not user.is_banned
    db.commit()
    status_str = "đã bị KHÓA" if user.is_banned else "đã được MỞ KHÓA"
    return {"message": f"Tài khoản '{user.username}' {status_str} thành công!", "is_banned": user.is_banned}


@router.delete("/players/{user_id}")
def delete_player(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id, User.role == "player").first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người chơi.")

    username = user.username
    db.delete(user)
    db.commit()
    return {"message": f"Đã xóa hoàn toàn người chơi '{username}' khỏi hệ thống."}


@router.get("/bots")
def list_bots_paginated(
    q: str = Query("", description="Tìm theo tên bot hoặc tác giả"),
    page: int = Query(1, ge=1),
    limit: int = Query(8, ge=1, le=50),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Bot).join(User, Bot.user_id == User.id)
    if q.strip():
        query = query.filter(
            or_(
                Bot.name.ilike(f"%{q.strip()}%"),
                User.username.ilike(f"%{q.strip()}%"),
                Bot.language.ilike(f"%{q.strip()}%")
            )
        )

    total = query.count()
    total_pages = ceil(total / limit) if total > 0 else 1
    bots = query.order_by(Bot.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    items = [
        {
            "id": b.id,
            "name": b.name,
            "owner": b.owner.username if b.owner else "System",
            "owner_elo": b.owner.elo if b.owner else 1200.0,
            "elo": b.owner.elo if b.owner else 1200.0,
            "language": b.language,
            "is_active": b.is_active,
            "has_binary": bool(b.binary_path),
            "created_at": b.created_at.strftime("%d/%m/%Y %H:%M")
        }
        for b in bots
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }


@router.get("/bots/{bot_id}/code")
def view_bot_source_code(
    bot_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if bot_id in _BOT_CODE_CACHE:
        _BOT_CODE_CACHE.move_to_end(bot_id)
        return _BOT_CODE_CACHE[bot_id]

    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Không tìm thấy bot.")

    code_content = bot.code or ""
    if not code_content and bot.source_path:
        try:
            src_path = Path(bot.source_path)
            if not src_path.is_absolute():
                src_path = BOTS_DIR / src_path.name
            if src_path.exists():
                code_content = src_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass

    owner_name = bot.owner.username if bot.owner else "System"

    result = {
        "id": bot.id,
        "name": bot.name,
        "owner": owner_name,
        "language": bot.language,
        "code": code_content
    }

    if len(_BOT_CODE_CACHE) >= _MAX_CACHE_SIZE:
        _BOT_CODE_CACHE.popitem(last=False)
    _BOT_CODE_CACHE[bot_id] = result

    return result


@router.delete("/bots/{bot_id}")
def delete_bot_by_admin(
    bot_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Không tìm thấy bot.")

    bot_name = bot.name
    if bot.source_path and Path(bot.source_path).exists():
        try:
            Path(bot.source_path).unlink()
        except Exception:
            pass

    if bot.binary_path and Path(bot.binary_path).exists():
        try:
            Path(bot.binary_path).unlink()
        except Exception:
            pass

    _BOT_CODE_CACHE.pop(bot_id, None)

    db.query(Match).filter((Match.bot1_id == bot_id) | (Match.bot2_id == bot_id)).delete()
    db.query(TournamentStanding).filter(TournamentStanding.bot_id == bot_id).delete()
    db.delete(bot)
    db.commit()
    return {"message": f"Đã xóa vĩnh viễn bot '{bot_name}'."}


@router.get("/tournaments")
def list_tournaments_paginated(
    q: str = Query("", description="Tìm theo tên giải đấu"),
    status: str = Query("", description="Lọc theo trạng thái"),
    page: int = Query(1, ge=1),
    limit: int = Query(6, ge=1, le=50),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Tournament)
    if q.strip():
        query = query.filter(Tournament.name.ilike(f"%{q.strip()}%"))
    if status.strip():
        query = query.filter(Tournament.status == status.strip())

    total = query.count()
    total_pages = ceil(total / limit) if total > 0 else 1
    tours = query.order_by(Tournament.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    items = []
    for t in tours:
        registered_count = (
            db.query(func.count(distinct(Bot.user_id)))
            .join(TournamentStanding, TournamentStanding.bot_id == Bot.id)
            .filter(TournamentStanding.tournament_id == t.id)
            .scalar()
        ) or 0

        items.append({
            "id": t.id,
            "name": t.name,
            "type": t.type,
            "status": t.status,
            "registered_count": registered_count,
            "created_by": t.created_by,
            "start_time": t.start_time.strftime("%d/%m/%Y %H:%M") if t.start_time else "Chưa đặt",
            "start_time_iso": t.start_time.strftime("%Y-%m-%dT%H:%M") if t.start_time else "",
            "created_at": t.created_at.strftime("%d/%m/%Y %H:%M")
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }