import threading
import time
from datetime import datetime
from app.database import SessionLocal
from app.models import Tournament, TournamentStanding, SystemSetting
from app.services.tournament_service import execute_tournament
from app.services.matchmaking_service import run_ladder_matchmaking

_scheduler_running = False
_last_ladder_run = 0.0
_last_scheduled_slot = ""


def check_and_run_due_tournaments():
    db = SessionLocal()
    try:
        now = datetime.now()
        due_tournaments = db.query(Tournament).filter(
            Tournament.status == "open",
            Tournament.start_time != None,
            Tournament.start_time <= now
        ).all()

        for tour in due_tournaments:
            standings_count = db.query(TournamentStanding).filter_by(tournament_id=tour.id).count()
            if standings_count >= 2:
                execute_tournament(tour.id, db)
            else:
                tour.status = "cancelled"
                db.commit()
    except Exception:
        pass
    finally:
        db.close()


def check_and_run_ladder():
    global _last_ladder_run, _last_scheduled_slot
    db = SessionLocal()
    try:
        en_row = db.query(SystemSetting).filter(SystemSetting.key == "ladder_enabled").first()
        is_enabled = en_row.value.lower() == "true" if en_row else True
        if not is_enabled:
            return

        mode_row = db.query(SystemSetting).filter(SystemSetting.key == "ladder_mode").first()
        mode = mode_row.value if mode_row else "interval"

        now = datetime.now()

        if mode == "weekly":
            day_row = db.query(SystemSetting).filter(SystemSetting.key == "ladder_weekly_day").first()
            time_row = db.query(SystemSetting).filter(SystemSetting.key == "ladder_weekly_time").first()

            target_day = day_row.value if day_row else "4"
            target_time = time_row.value if time_row else "20:00"

            current_day = str(now.weekday())
            current_time = now.strftime("%H:%M")
            slot_id = f"{now.strftime('%Y-%m-%d')}_{target_time}"

            day_match = (target_day == "all" or target_day == current_day)
            time_match = (current_time == target_time)

            if day_match and time_match and _last_scheduled_slot != slot_id:
                _last_scheduled_slot = slot_id
                _last_ladder_run = time.time()
                run_ladder_matchmaking(db)

        else:
            val_setting = db.query(SystemSetting).filter(SystemSetting.key == "ladder_interval_value").first()
            unit_setting = db.query(SystemSetting).filter(SystemSetting.key == "ladder_interval_unit").first()

            interval_val = int(val_setting.value) if val_setting else 15
            interval_unit = unit_setting.value if unit_setting else "minute"

            multiplier = 60
            if interval_unit == "hour":
                multiplier = 3600
            elif interval_unit == "day":
                multiplier = 86400

            interval_sec = max(60, interval_val * multiplier)
            now_ts = time.time()
            if now_ts - _last_ladder_run >= interval_sec:
                _last_ladder_run = now_ts
                run_ladder_matchmaking(db)
    except Exception:
        pass
    finally:
        db.close()


def _scheduler_loop():
    while _scheduler_running:
        check_and_run_due_tournaments()
        check_and_run_ladder()
        time.sleep(10)


def start_scheduler():
    global _scheduler_running
    if not _scheduler_running:
        _scheduler_running = True
        t = threading.Thread(target=_scheduler_loop, daemon=True)
        t.start()