import random
from sqlalchemy.orm import Session
from app.models import User, Bot, Match, Season
from app.services.match_runner import run_match_between_bots
from app.services.tournament_service import calculate_elo


def run_ladder_matchmaking(db: Session = None) -> list[dict]:
    own_session = False
    if db is None:
        from app.database import SessionLocal
        db = SessionLocal()
        own_session = True

    results = []
    try:
        active_season = db.query(Season).filter(Season.status == "active").order_by(Season.id.desc()).first()
        if not active_season:
            return results

        active_bots = (
            db.query(Bot)
            .join(User, Bot.user_id == User.id)
            .filter(
                User.role == "player",
                User.is_banned == False,
                Bot.is_active == True
            )
            .all()
        )

        user_bot_map = {}
        for b in active_bots:
            if b.user_id not in user_bot_map:
                user_bot_map[b.user_id] = b

        candidate_bots = list(user_bot_map.values())
        if len(candidate_bots) < 2:
            return results

        candidate_bots.sort(key=lambda b: b.owner.elo if b.owner else 0.0, reverse=True)

        paired = []
        i = 0
        while i < len(candidate_bots) - 1:
            paired.append((candidate_bots[i], candidate_bots[i + 1]))
            i += 2

        for b1, b2 in paired:
            p1 = b1.owner
            p2 = b2.owner
            old_elo1 = p1.elo if p1 else 0.0
            old_elo2 = p2.elo if p2 else 0.0

            info1 = {
                "id": b1.id,
                "name": b1.name,
                "language": b1.language,
                "code": b1.code,
                "source_path": b1.source_path,
                "binary_path": b1.binary_path
            }
            info2 = {
                "id": b2.id,
                "name": b2.name,
                "language": b2.language,
                "code": b2.code,
                "source_path": b2.source_path,
                "binary_path": b2.binary_path
            }

            if random.random() > 0.5:
                info1, info2 = info2, info1
                b1, b2 = b2, b1
                p1, p2 = p2, p1
                old_elo1, old_elo2 = old_elo2, old_elo1

            res = run_match_between_bots(info1, info2)
            winner_id = b1.id if res["winner"] == 1 else (b2.id if res["winner"] == 2 else 0)
            score_a = 1.0 if res["winner"] == 1 else (0.0 if res["winner"] == 2 else 0.5)

            if p1 and p2 and p1.id != p2.id:
                new_elo1, new_elo2 = calculate_elo(old_elo1, old_elo2, score_a)
                p1.elo = max(0.0, new_elo1)
                p2.elo = max(0.0, new_elo2)

            match_record = Match(
                tournament_id=None,
                bot1_id=b1.id,
                bot2_id=b2.id,
                winner_bot_id=winner_id,
                winner_name=res["winner_name"],
                win_reason=res["reason"],
                moves_count=res["moves"],
                duration_sec=res["duration_sec"],
                replay_data=res["replay_data"]
            )
            db.add(match_record)
            db.commit()

            results.append({
                "match_id": match_record.id,
                "p1": p1.username if p1 else "P1",
                "p2": p2.username if p2 else "P2",
                "winner": res["winner_name"],
                "elo_update": {
                    "p1": f"{old_elo1:.1f} -> {p1.elo:.1f}",
                    "p2": f"{old_elo2:.1f} -> {p2.elo:.1f}"
                }
            })

    except Exception:
        db.rollback()
    finally:
        if own_session:
            db.close()

    return results