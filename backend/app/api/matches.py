from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Bot, Match
from app.services.match_runner import run_match_between_bots

router = APIRouter(prefix="/api/matches", tags=["Matches"])

@router.post("/quick")
def run_quick_match(bot1_id: int, bot2_id: int, db: Session = Depends(get_db)):
    b1 = db.query(Bot).filter_by(id=bot1_id).first()
    b2 = db.query(Bot).filter_by(id=bot2_id).first()
    if not b1 or not b2:
        raise HTTPException(status_code=404, detail="Không tìm thấy bot chỉ định.")

    info1 = {"name": b1.name, "source_path": b1.source_path, "binary_path": b1.binary_path}
    info2 = {"name": b2.name, "source_path": b2.source_path, "binary_path": b2.binary_path}

    res = run_match_between_bots(info1, info2)

    match_record = Match(
        bot1_id=b1.id,
        bot2_id=b2.id,
        winner_bot_id=b1.id if res["winner"] == 1 else (b2.id if res["winner"] == 2 else 0),
        winner_name=res["winner_name"],
        win_reason=res["reason"],
        moves_count=res["moves"],
        duration_sec=res["duration_sec"],
        replay_data=res["replay_data"]
    )
    db.add(match_record)
    db.commit()
    db.refresh(match_record)

    return {
        "status": "completed",
        "result": res,
        "match_id": match_record.id,
        "replay_url": f"/api/matches/{match_record.id}/replay"
    }

@router.get("/{match_id}/replay")
def get_match_replay(match_id: int, db: Session = Depends(get_db)):
    match_record = db.query(Match).filter(Match.id == match_id).first()
    if not match_record:
        raise HTTPException(status_code=404, detail="Trận đấu không tồn tại.")
    if not match_record.replay_data:
        raise HTTPException(status_code=404, detail="Dữ liệu replay không tồn tại cho trận đấu này.")
    return match_record.replay_data

@router.get("/tournament/{tournament_id}")
def get_tournament_matches(
    tournament_id: int,
    q: str = Query(""),
    round_type: str = Query(""),
    order: str = Query("asc"),
    db: Session = Depends(get_db)
):
    query = db.query(Match).filter(Match.tournament_id == tournament_id)
    if order == "desc":
        query = query.order_by(Match.created_at.desc(), Match.id.desc())
    else:
        query = query.order_by(Match.created_at.asc(), Match.id.asc())

    matches = query.all()
    if not matches:
        return []

    bot_ids = set()
    for m in matches:
        if m.bot1_id:
            bot_ids.add(m.bot1_id)
        if m.bot2_id:
            bot_ids.add(m.bot2_id)

    bots = db.query(Bot).options(joinedload(Bot.owner)).filter(Bot.id.in_(bot_ids)).all()
    bot_map = {b.id: b for b in bots}

    total_matches = len(matches)
    half = total_matches // 2 if total_matches > 0 else 0
    results = []

    for idx, m in enumerate(matches):
        b1 = bot_map.get(m.bot1_id)
        b2 = bot_map.get(m.bot2_id)

        p1_name = b1.owner.username if (b1 and b1.owner) else "Ẩn danh"
        p2_name = b2.owner.username if (b2 and b2.owner) else "Ẩn danh"
        b1_name = b1.name if b1 else "Bot 1"
        b2_name = b2.name if b2 else "Bot 2"

        round_num = 1 if (half > 0 and idx < half) or (m.bot1_id < m.bot2_id) else 2

        if round_type and str(round_num) != round_type:
            continue

        if q.strip():
            term = q.strip().lower()
            haystack = f"{p1_name} {p2_name} {b1_name} {b2_name}".lower()
            if term not in haystack:
                continue

        results.append({
            "id": m.id,
            "index": idx + 1,
            "round": round_num,
            "player1": p1_name,
            "player2": p2_name,
            "bot1_name": b1_name,
            "bot2_name": b2_name,
            "winner_name": m.winner_name,
            "winner_bot_id": m.winner_bot_id,
            "win_reason": m.win_reason,
            "moves_count": m.moves_count,
            "duration_sec": m.duration_sec,
            "replay_url": f"/api/matches/{m.id}/replay" if m.replay_data else "",
            "created_at": m.created_at.strftime("%d/%m/%Y %H:%M") if m.created_at else ""
        })

    return results