import sys
import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import text
from app.config import BOTS_DIR, REPLAYS_DIR
from app.database import engine, SessionLocal
from app.models import Base, User, Bot, Tournament, Match, TournamentStanding, Season, SeasonHistory
from app.core.security import hash_password
from app.core import engine as game_engine

BOT_RANDOM_CODE = """import sys
import json
import random

while True:
    line = sys.stdin.readline()
    if not line:
        break
    try:
        data = json.loads(line)
        legal_moves = data.get("legal_moves", [])
        if legal_moves:
            chosen = random.choice(legal_moves)
            resp = {"from": chosen["from_notation"], "to": chosen["to_notation"]}
            sys.stdout.write(json.dumps(resp) + "\\n")
            sys.stdout.flush()
    except Exception:
        pass
"""

BOT_RUSHER_CODE = """import sys
import json

while True:
    line = sys.stdin.readline()
    if not line:
        break
    try:
        data = json.loads(line)
        turn = data.get("turn", 1)
        legal_moves = data.get("legal_moves", [])
        if not legal_moves:
            continue

        target_r, target_c = (0, 8) if turn == 1 else (8, 0)
        def dist(m):
            to_coord = m["to"]
            return max(abs(target_r - to_coord["r"]), abs(target_c - to_coord["c"]))

        best_move = min(legal_moves, key=dist)
        resp = {"from": best_move["from_notation"], "to": best_move["to_notation"]}
        sys.stdout.write(json.dumps(resp) + "\\n")
        sys.stdout.flush()
    except Exception:
        pass
"""

BOT_GREEDY_CODE = """import sys
import json

while True:
    line = sys.stdin.readline()
    if not line:
        break
    try:
        data = json.loads(line)
        legal_moves = data.get("legal_moves", [])
        if not legal_moves:
            continue

        captures = [m for m in legal_moves if m.get("is_capture")]
        chosen = captures[0] if captures else legal_moves[0]
        resp = {"from": chosen["from_notation"], "to": chosen["to_notation"]}
        sys.stdout.write(json.dumps(resp) + "\\n")
        sys.stdout.flush()
    except Exception:
        pass
"""

BOT_DEFENSIVE_CODE = """import sys
import json

while True:
    line = sys.stdin.readline()
    if not line:
        break
    try:
        data = json.loads(line)
        turn = data.get("turn", 1)
        legal_moves = data.get("legal_moves", [])
        if not legal_moves:
            continue

        base_r, base_c = (8, 0) if turn == 1 else (0, 8)
        def danger_score(m):
            to_c = m["to"]
            dist_to_base = abs(base_r - to_c["r"]) + abs(base_c - to_c["c"])
            return (0 if m.get("is_capture") else 10) + dist_to_base

        best = min(legal_moves, key=danger_score)
        resp = {"from": best["from_notation"], "to": best["to_notation"]}
        sys.stdout.write(json.dumps(resp) + "\\n")
        sys.stdout.flush()
    except Exception:
        pass
"""

BOT_CPP_CODE = """#include <iostream>
#include <string>

int main() {
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) break;
        std::cout << "{\\"from\\": \\"A1\\", \\"to\\": \\"A2\\"}\\n" << std::flush;
    }
    return 0;
}
"""

BOT_JS_CODE = """const readline = require('readline');
const rl = readline.createInterface({ input: process.stdin, output: process.stdout, terminal: false });

rl.on('line', (line) => {
    try {
        const data = JSON.parse(line);
        const moves = data.legal_moves || [];
        if (moves.length > 0) {
            console.log(JSON.stringify({ from: moves[0].from_notation, to: moves[0].to_notation }));
        }
    } catch (e) {}
});
"""


def create_bot_files():
    BOTS_DIR.mkdir(parents=True, exist_ok=True)
    REPLAYS_DIR.mkdir(parents=True, exist_ok=True)

    files = {
        "bot_random.py": BOT_RANDOM_CODE,
        "bot_rusher.py": BOT_RUSHER_CODE,
        "bot_greedy.py": BOT_GREEDY_CODE,
        "bot_defensive.py": BOT_DEFENSIVE_CODE,
        "bot_cpp_template.cpp": BOT_CPP_CODE,
        "bot_js_template.js": BOT_JS_CODE,
    }
    paths = {}
    codes = {}
    for filename, code in files.items():
        file_path = BOTS_DIR / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
        paths[filename] = f"storage/bots/{filename}"
        codes[filename] = code

    return paths, codes


def create_sample_replay(replay_id: str, bot1_name: str, bot2_name: str, winner_name: str):
    board = game_engine.create_symmetrical_board()
    now_utc = datetime.now(timezone.utc)

    sample_moves = []
    current_board = [row[:] for row in board]
    turn = 1

    for step in range(1, 15):
        legal_moves = game_engine.get_all_legal_moves(current_board, turn)
        if not legal_moves:
            break
        chosen = legal_moves[0]
        applied = game_engine.apply_move(current_board, chosen)
        current_board = applied["new_board"]

        sample_moves.append({
            "step": step,
            "player": turn,
            "from": chosen["from"],
            "to": chosen["to"],
            "fromNotation": applied["from_notation"],
            "toNotation": applied["to_notation"],
            "pieceType": applied["moving_piece"]["type"],
            "isCapture": applied["is_capture"],
            "capturedType": applied["captured_piece"]["type"] if applied["captured_piece"] else None,
            "elapsedMs": 24.5,
            "boardSnapshot": [row[:] for row in current_board]
        })
        turn = 2 if turn == 1 else 1

    replay_data = {
        "id": replay_id,
        "timestamp": int(now_utc.timestamp() * 1000),
        "dateStr": now_utc.strftime("%d/%m/%Y %H:%M"),
        "rules": game_engine.GLOBAL_RULES,
        "p1": {"name": bot1_name, "type": "bot"},
        "p2": {"name": bot2_name, "type": "bot"},
        "initialBoard": board,
        "moves": sample_moves,
        "result": {
            "winner": 1 if winner_name == bot1_name else (2 if winner_name == bot2_name else None),
            "winnerName": winner_name,
            "reason": "Chiếm căn cứ đối phương",
            "reasonType": "base",
            "durationSec": 4,
            "totalMoves": len(sample_moves)
        }
    }

    try:
        replay_path = REPLAYS_DIR / f"{replay_id}.json"
        with open(replay_path, "w", encoding="utf-8") as f:
            json.dump(replay_data, f, ensure_ascii=False)
    except Exception:
        pass

    return replay_data


def seed_database():
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            conn.execute(text("PRAGMA foreign_keys = OFF;"))
            tables = [
                "matches",
                "tournament_standings",
                "tournaments",
                "season_histories",
                "seasons",
                "bots",
                "users",
                "system_settings"
            ]
            for t in tables:
                conn.execute(text(f"DROP TABLE IF EXISTS {t};"))
            conn.execute(text("PRAGMA foreign_keys = ON;"))
        else:
            conn.execute(text("DROP TABLE IF EXISTS matches, tournament_standings, tournaments, season_histories, seasons, bots, users, system_settings CASCADE;"))

    Base.metadata.create_all(bind=engine)

    if engine.dialect.name != "sqlite":
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE bots ADD COLUMN IF NOT EXISTS code TEXT;"))

    db = SessionLocal()
    try:
        bot_paths, bot_codes = create_bot_files()
        default_pass = hash_password("123456")
        now = datetime.now()

        season_1 = Season(
            name="Mùa 1",
            status="completed",
            start_date=now - timedelta(days=60),
            end_date=now - timedelta(days=2),
            created_at=now - timedelta(days=60)
        )
        season_2 = Season(
            name="Mùa 2",
            status="active",
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=60),
            created_at=now - timedelta(days=1)
        )
        db.add_all([season_1, season_2])
        db.commit()

        player_configs = [
            ("player1",  1180.0, 1850.0, False),
            ("player2",  1040.0, 1780.0, False),
            ("player3",  890.0,  1680.0, False),
            ("player4",  780.0,  1610.0, False),
            ("player5",  690.0,  1530.0, False),
            ("player6",  620.0,  1480.0, False),
            ("player7",  550.0,  1410.0, False),
            ("player8",  480.0,  1360.0, False),
            ("player9",  410.0,  1300.0, False),
            ("player10", 340.0,  1250.0, False),
            ("player11", 270.0,  1200.0, False),
            ("player12", 210.0,  1160.0, False),
            ("player13", 160.0,  1110.0, False),
            ("player14", 120.0,  1060.0, False),
            ("player15", 80.0,   1010.0, False),
            ("player16", 60.0,   960.0,  False),
            ("player17", 40.0,   910.0,  False),
            ("player18", 20.0,   870.0,  False),
            ("player19", 0.0,    820.0,  False),
            ("player20", 0.0,    600.0,  True),
        ]

        users = [
            User(username="admin", password_hash=default_pass, role="admin", elo=0.0, is_banned=False),
            User(username="system_trainer", password_hash=default_pass, role="system", elo=0.0, is_banned=False),
        ]
        for uname, s2_elo, _, is_ban in player_configs:
            users.append(User(username=uname, password_hash=default_pass, role="player", elo=s2_elo, is_banned=is_ban))

        db.add_all(users)
        db.commit()

        all_users = {u.username: u for u in db.query(User).all()}

        season_1_histories = []
        for rank_idx, (uname, _, s1_elo, _) in enumerate(player_configs, 1):
            matches_count = max(5, 20 - rank_idx // 2)
            wins_count = max(0, matches_count - rank_idx)
            season_1_histories.append(SeasonHistory(
                season_id=season_1.id,
                user_id=all_users[uname].id,
                elo=s1_elo,
                rank=rank_idx,
                matches_played=matches_count,
                wins=wins_count,
                created_at=season_1.end_date
            ))
        db.add_all(season_1_histories)
        db.commit()

        templates = [
            ("python", bot_paths["bot_rusher.py"], bot_codes["bot_rusher.py"]),
            ("python", bot_paths["bot_greedy.py"], bot_codes["bot_greedy.py"]),
            ("cpp", bot_paths["bot_cpp_template.cpp"], bot_codes["bot_cpp_template.cpp"]),
            ("javascript", bot_paths["bot_js_template.js"], bot_codes["bot_js_template.js"]),
            ("python", bot_paths["bot_defensive.py"], bot_codes["bot_defensive.py"]),
            ("python", bot_paths["bot_random.py"], bot_codes["bot_random.py"]),
        ]

        bot_entities = [
            Bot(user_id=all_users["system_trainer"].id, name="bot_system_random", language="python", code=bot_codes["bot_random.py"], source_path=bot_paths["bot_random.py"], is_active=True),
            Bot(user_id=all_users["system_trainer"].id, name="bot_system_rusher", language="python", code=bot_codes["bot_rusher.py"], source_path=bot_paths["bot_rusher.py"], is_active=False),
            Bot(user_id=all_users["system_trainer"].id, name="bot_system_greedy", language="python", code=bot_codes["bot_greedy.py"], source_path=bot_paths["bot_greedy.py"], is_active=False),
        ]

        for idx, (uname, _, _, _) in enumerate(player_configs, 1):
            lang, fpath, fcode = templates[(idx - 1) % len(templates)]
            bot_entities.append(Bot(
                user_id=all_users[uname].id,
                name=f"bot_{uname}",
                language=lang,
                code=fcode,
                source_path=fpath,
                binary_path=None,
                is_active=True
            ))

        for idx in [1, 2, 5]:
            uname = f"player{idx}"
            bot_entities.append(Bot(
                user_id=all_users[uname].id,
                name=f"bot_{uname}_v2",
                language="python",
                code=bot_codes["bot_random.py"],
                source_path=bot_paths["bot_random.py"],
                binary_path=None,
                is_active=False
            ))

        db.add_all(bot_entities)
        db.commit()

        all_bots = {b.name: b for b in db.query(Bot).all()}

        tour_1 = Tournament(
            name="Giải đấu 1",
            type="major",
            format="round_robin",
            status="completed",
            season_id=season_1.id,
            start_time=now - timedelta(days=20),
            created_by="admin",
            created_at=now - timedelta(days=25)
        )
        tour_2 = Tournament(
            name="Giải đấu 2",
            type="weekly",
            format="round_robin",
            status="completed",
            season_id=season_1.id,
            start_time=now - timedelta(days=10),
            created_by="admin",
            created_at=now - timedelta(days=12)
        )
        tour_3 = Tournament(
            name="Giải đấu 3",
            type="major",
            format="round_robin",
            status="completed",
            season_id=season_2.id,
            start_time=now - timedelta(hours=14),
            created_by="admin",
            created_at=now - timedelta(days=1)
        )
        tour_4 = Tournament(
            name="Giải đấu 4",
            type="weekly",
            format="round_robin",
            status="open",
            season_id=season_2.id,
            start_time=now + timedelta(days=2, hours=4),
            created_by="admin",
            created_at=now
        )
        tour_5 = Tournament(
            name="Giải đấu 5",
            type="major",
            format="round_robin",
            status="open",
            season_id=season_2.id,
            start_time=now + timedelta(days=6),
            created_by="admin",
            created_at=now
        )

        db.add_all([tour_1, tour_2, tour_3, tour_4, tour_5])
        db.commit()

        def create_tournament_fixtures(tour, bot_names_list, days_ago):
            p_bots = [all_bots[name] for name in bot_names_list if name in all_bots]
            n = len(p_bots)
            stats = {b.id: {"played": 0, "won": 0, "drawn": 0, "lost": 0, "points": 0} for b in p_bots}
            m_time = now - timedelta(days=days_ago)

            for i in range(n):
                for j in range(i + 1, n):
                    b1 = p_bots[i]
                    b2 = p_bots[j]

                    if i < j:
                        w_bot = b1
                        l_bot = b2
                        w_name = b1.name
                        stats[b1.id]["won"] += 1
                        stats[b1.id]["points"] += 3
                        stats[b2.id]["lost"] += 1
                    else:
                        w_bot = b2
                        l_bot = b1
                        w_name = b2.name
                        stats[b2.id]["won"] += 1
                        stats[b2.id]["points"] += 3
                        stats[b1.id]["lost"] += 1

                    stats[b1.id]["played"] += 1
                    stats[b2.id]["played"] += 1

                    rep_id = f"replay_{tour.id}_{b1.id}_{b2.id}_{int(m_time.timestamp())}"
                    rep_data = create_sample_replay(rep_id, b1.name, b2.name, w_name)

                    m = Match(
                        tournament_id=tour.id,
                        bot1_id=b1.id,
                        bot2_id=b2.id,
                        winner_bot_id=w_bot.id,
                        winner_name=w_name,
                        win_reason="Chiếm căn cứ đối phương",
                        moves_count=len(rep_data["moves"]),
                        duration_sec=4,
                        replay_data=rep_data,
                        created_at=m_time
                    )
                    db.add(m)

            for b in p_bots:
                st = stats[b.id]
                db.add(TournamentStanding(
                    tournament_id=tour.id,
                    bot_id=b.id,
                    played=st["played"],
                    won=st["won"],
                    drawn=st["drawn"],
                    lost=st["lost"],
                    points=st["points"]
                ))

        create_tournament_fixtures(
            tour_1,
            ["bot_player1", "bot_player2", "bot_player3", "bot_player4", "bot_player5", "bot_player6"],
            days_ago=20
        )

        create_tournament_fixtures(
            tour_2,
            ["bot_player2", "bot_player4", "bot_player6", "bot_player8"],
            days_ago=10
        )

        create_tournament_fixtures(
            tour_3,
            ["bot_player1", "bot_player3", "bot_player5", "bot_player7", "bot_player9", "bot_player11"],
            days_ago=1
        )

        tour_4_participants = [
            "bot_player1", "bot_player2", "bot_player3", "bot_player4",
            "bot_player5", "bot_player6", "bot_player7", "bot_player8"
        ]
        for b_name in tour_4_participants:
            db.add(TournamentStanding(tournament_id=tour_4.id, bot_id=all_bots[b_name].id))

        tour_5_participants = [
            "bot_player1", "bot_player2", "bot_player3", "bot_player4", "bot_player5"
        ]
        for b_name in tour_5_participants:
            db.add(TournamentStanding(tournament_id=tour_5.id, bot_id=all_bots[b_name].id))

        ladder_pairs = [
            ("bot_player1", "bot_player2"),
            ("bot_player3", "bot_player4"),
            ("bot_player5", "bot_player6"),
            ("bot_player7", "bot_player8"),
        ]
        for idx, (b1_name, b2_name) in enumerate(ladder_pairs, 1):
            b1 = all_bots[b1_name]
            b2 = all_bots[b2_name]
            rep_id = f"replay_ladder_{b1.id}_{b2.id}_{int(now.timestamp())}_{idx}"
            rep_data = create_sample_replay(rep_id, b1.name, b2.name, b1.name)
            db.add(Match(
                tournament_id=None,
                bot1_id=b1.id,
                bot2_id=b2.id,
                winner_bot_id=b1.id,
                winner_name=b1.name,
                win_reason="Chiếm căn cứ đối phương",
                moves_count=len(rep_data["moves"]),
                duration_sec=3,
                replay_data=rep_data,
                created_at=now - timedelta(hours=idx * 2)
            ))

        db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()