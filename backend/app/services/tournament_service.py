from sqlalchemy.orm import Session
from app.models import Tournament, Bot, Match, TournamentStanding
from app.services.match_runner import run_match_between_bots


def calculate_elo(r_a: float, r_b: float, score_a: float, k: float = 32.0) -> tuple[float, float]:
    expected_a = 1.0 / (1.0 + 10.0 ** ((r_b - r_a) / 400.0))
    expected_b = 1.0 - expected_a
    score_b = 1.0 - score_a
    return round(r_a + k * (score_a - expected_a), 1), round(r_b + k * (score_b - expected_b), 1)


def execute_tournament(tournament_id: int, db: Session = None):
    own_session = False
    if db is None:
        from app.database import SessionLocal
        db = SessionLocal()
        own_session = True

    try:
        tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not tournament or tournament.status == "completed":
            return

        tournament.status = "running"
        db.commit()

        standings = db.query(TournamentStanding).filter_by(tournament_id=tournament.id).all()
        bot_ids = [s.bot_id for s in standings]
        bots = db.query(Bot).filter(Bot.id.in_(bot_ids)).all()

        if len(bots) < 2:
            tournament.status = "cancelled"
            db.commit()
            return

        for i in range(len(bots)):
            for j in range(len(bots)):
                if i == j:
                    continue
                b1, b2 = bots[i], bots[j]

                info1 = {"name": b1.name, "source_path": b1.source_path, "binary_path": b1.binary_path}
                info2 = {"name": b2.name, "source_path": b2.source_path, "binary_path": b2.binary_path}

                res = run_match_between_bots(info1, info2)
                winner_id = b1.id if res["winner"] == 1 else (b2.id if res["winner"] == 2 else 0)

                match_record = Match(
                    tournament_id=tournament.id,
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

                s1 = db.query(TournamentStanding).filter_by(tournament_id=tournament.id, bot_id=b1.id).first()
                s2 = db.query(TournamentStanding).filter_by(tournament_id=tournament.id, bot_id=b2.id).first()

                s1.played += 1
                s2.played += 1

                if res["winner"] == 1:
                    s1.won += 1
                    s1.points += 3
                    s2.lost += 1
                    score_a = 1.0
                elif res["winner"] == 2:
                    s2.won += 1
                    s2.points += 3
                    s1.lost += 1
                    score_a = 0.0
                else:
                    s1.drawn += 1
                    s2.drawn += 1
                    s1.points += 1
                    s2.points += 1
                    score_a = 0.5

                if b1.owner and b2.owner and b1.owner.id != b2.owner.id:
                    new_elo1, new_elo2 = calculate_elo(b1.owner.elo, b2.owner.elo, score_a)
                    b1.owner.elo = new_elo1
                    b2.owner.elo = new_elo2

                db.commit()

        tournament.status = "completed"
        db.commit()

    except Exception:
        db.rollback()
        tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if tournament:
            tournament.status = "open"
            db.commit()
        raise
    finally:
        if own_session:
            db.close()