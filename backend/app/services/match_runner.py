import copy
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from app.core import engine
from app.config import (
    DEFAULT_BOT_TIMEOUT,
    DEFAULT_MAX_TURNS,
    BOTS_DIR,
    REPLAYS_DIR,
    BACKEND_DIR,
    ROOT_DIR,
)


def _ensure_bot_source(bot_info: dict) -> Path:
    BOTS_DIR.mkdir(parents=True, exist_ok=True)
    source_val = bot_info.get("source_path") or ""
    filename = Path(source_val).name if source_val else ""

    if not filename:
        lang = (bot_info.get("language") or "python").lower()
        ext = ".py" if lang == "python" else (".js" if lang == "javascript" else ".cpp")
        filename = f"{bot_info.get('name', 'bot')}{ext}"

    target_path = BOTS_DIR / filename
    code = bot_info.get("code")

    if not code:
        bot_id = bot_info.get("id") or bot_info.get("bot_id")
        name = bot_info.get("name")
        try:
            from app.database import SessionLocal
            from app.models.bot import Bot
            with SessionLocal() as db:
                b = None
                if bot_id:
                    b = db.query(Bot).filter(Bot.id == bot_id).first()
                elif name:
                    b = db.query(Bot).filter(Bot.name == name).first()
                if b and b.code:
                    code = b.code
        except Exception:
            pass

    if code:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(code)
        return target_path.resolve()

    if target_path.is_file():
        return target_path.resolve()

    for base in [BACKEND_DIR / "storage" / "bots", ROOT_DIR / "storage" / "bots"]:
        cand = base / filename
        if cand.is_file():
            return cand.resolve()

    return target_path.resolve()


class BotProcess:
    def __init__(self, bot_info: dict):
        self.bot_info = bot_info
        self.name = bot_info.get("name", "Bot")
        self.proc = None
        self.output_queue = None
        self.reader_thread = None
        self.start_error = None
        self._setup_command()

    def _setup_command(self):
        resolved_src = _ensure_bot_source(self.bot_info)

        if not resolved_src.exists():
            self.start_error = f"File mã nguồn bot không tồn tại: {resolved_src.name}"
            return

        ext = resolved_src.suffix.lower()

        if ext == ".py":
            self.exec_cmd = [sys.executable, "-u", str(resolved_src)]
            self.working_dir = str(resolved_src.parent)
        elif ext == ".js":
            self.exec_cmd = ["node", str(resolved_src)]
            self.working_dir = str(resolved_src.parent)
        elif ext == ".cpp":
            bin_suffix = ".exe" if sys.platform.startswith("win") else ""
            raw_bin = resolved_src.parent / f"{resolved_src.stem}_bin{bin_suffix}"

            need_compile = not raw_bin.exists()
            if not need_compile and resolved_src.stat().st_mtime > raw_bin.stat().st_mtime:
                need_compile = True

            if need_compile:
                compiler = shutil.which("g++") or shutil.which("clang++")
                if compiler:
                    subprocess.run(
                        [compiler, "-O2", "-std=c++17", str(resolved_src), "-o", str(raw_bin)],
                        capture_output=True,
                        text=True,
                    )

            if raw_bin.exists():
                try:
                    os.chmod(raw_bin, 0o755)
                except Exception:
                    pass
                self.exec_cmd = [str(raw_bin)]
                self.working_dir = str(raw_bin.parent)
            else:
                self.start_error = "Không thể biên dịch bot C++"
                return
        else:
            self.exec_cmd = [str(resolved_src)]
            self.working_dir = str(resolved_src.parent)

    def _enqueue_output(self):
        try:
            for line in iter(self.proc.stdout.readline, ""):
                if self.output_queue is not None:
                    self.output_queue.put(line)
        except Exception:
            pass
        finally:
            if self.output_queue is not None:
                self.output_queue.put(None)

    def start(self):
        if self.start_error:
            return

        self.output_queue = queue.Queue()
        try:
            self.proc = subprocess.Popen(
                self.exec_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=self.working_dir,
            )
            time.sleep(0.05)
            if self.proc.poll() is not None:
                err = self.proc.stderr.read().strip() if self.proc.stderr else ""
                self.start_error = f"Tiến trình dừng ngay khi khởi động: {err[:120]}"
                return

            self.reader_thread = threading.Thread(target=self._enqueue_output, daemon=True)
            self.reader_thread.start()
        except Exception as e:
            self.proc = None
            self.start_error = str(e)

    def stop(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=0.3)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None
        self.output_queue = None

    def query_move(self, payload_dict, timeout_sec=DEFAULT_BOT_TIMEOUT):
        if self.start_error:
            return None, self.start_error

        if not self.proc or self.proc.poll() is not None:
            err = self.proc.stderr.read().strip() if (self.proc and self.proc.stderr) else ""
            detail = f" ({err[:100]})" if err else ""
            return None, f"Bot đã dừng trước khi phản hồi.{detail}"

        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except queue.Empty:
                break

        json_input = json.dumps(payload_dict) + "\n"
        start_t = time.time()
        try:
            self.proc.stdin.write(json_input)
            self.proc.stdin.flush()
        except Exception as e:
            err = self.proc.stderr.read().strip() if (self.proc and self.proc.stderr) else ""
            detail = f" ({err[:100]})" if err else ""
            return None, f"Lỗi gửi dữ liệu tới bot: {e}{detail}"

        try:
            line = self.output_queue.get(timeout=timeout_sec)
        except queue.Empty:
            return None, f"Quá thời gian suy nghĩ ({timeout_sec * 1000:.0f}ms)!"

        elapsed_ms = (time.time() - start_t) * 1000

        if line is None or not line.strip():
            err = self.proc.stderr.read().strip() if (self.proc and self.proc.stderr) else ""
            detail = f" ({err[:100]})" if err else ""
            return None, f"Bot trả về stdout rỗng.{detail}"

        try:
            resp = json.loads(line.strip())
            return (resp, elapsed_ms), None
        except Exception:
            return None, f"JSON không hợp lệ: {line.strip()[:60]}"


def run_match_between_bots(
    bot1_info: dict,
    bot2_info: dict,
    timeout_sec: float = DEFAULT_BOT_TIMEOUT,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> dict:
    bot1 = BotProcess(bot1_info)
    bot2 = BotProcess(bot2_info)

    bot1.start()
    bot2.start()

    board = engine.create_symmetrical_board()
    initial_board = copy.deepcopy(board)
    turn = 1
    total_moves = 0
    replay_moves = []
    is_game_over = False
    winner = None
    win_reason = ""
    reason_type = "base"
    start_time = time.time()

    try:
        while not is_game_over and total_moves < max_turns:
            current_bot = bot1 if turn == 1 else bot2
            opponent_turn = 2 if turn == 1 else 1

            legal_moves = engine.get_all_legal_moves(board, turn)
            if not legal_moves:
                winner = opponent_turn
                win_reason = f"{current_bot.name} bị phong tỏa, không còn nước đi!"
                reason_type = "extinction"
                break

            payload = {
                "type": "move",
                "turn": turn,
                "move_count": total_moves + 1,
                "board": board,
                "legal_moves": legal_moves,
            }

            res, err = current_bot.query_move(payload, timeout_sec=timeout_sec)
            if err:
                winner = opponent_turn
                win_reason = f"{current_bot.name} bị xử thua: {err}"
                reason_type = "surrender"
                break

            move_dict, elapsed_ms = res
            chosen_move = None
            from_val = move_dict.get("from")
            to_val = move_dict.get("to")

            for lm in legal_moves:
                if isinstance(from_val, str) and isinstance(to_val, str):
                    if (
                        lm["from_notation"].lower() == from_val.lower()
                        and lm["to_notation"].lower() == to_val.lower()
                    ):
                        chosen_move = lm
                        break
                elif isinstance(from_val, dict) and isinstance(to_val, dict):
                    if (
                        lm["from"]["r"] == from_val.get("r")
                        and lm["from"]["c"] == from_val.get("c")
                        and lm["to"]["r"] == to_val.get("r")
                        and lm["to"]["c"] == to_val.get("c")
                    ):
                        chosen_move = lm
                        break

            if not chosen_move:
                winner = opponent_turn
                win_reason = f"{current_bot.name} đi nước phạm quy ({from_val} -> {to_val})!"
                reason_type = "surrender"
                break

            applied = engine.apply_move(board, chosen_move)
            board = applied["new_board"]
            total_moves += 1

            moving_p = applied["moving_piece"]
            replay_moves.append(
                {
                    "step": total_moves,
                    "player": turn,
                    "from": chosen_move["from"],
                    "to": chosen_move["to"],
                    "fromNotation": applied["from_notation"],
                    "toNotation": applied["to_notation"],
                    "pieceType": moving_p["type"],
                    "isCapture": applied["is_capture"],
                    "capturedType": applied["captured_piece"]["type"]
                    if applied["captured_piece"]
                    else None,
                    "elapsedMs": round(elapsed_ms, 1),
                    "boardSnapshot": copy.deepcopy(board),
                }
            )

            win_check = engine.check_victory(board, total_moves)
            if win_check:
                is_game_over = True
                winner = win_check["winner"]
                win_reason = win_check["reason"]
                reason_type = win_check["reason_type"]

            turn = 2 if turn == 1 else 1
    finally:
        bot1.stop()
        bot2.stop()

    duration_sec = max(1, int(time.time() - start_time))
    winner_name = bot1.name if winner == 1 else (bot2.name if winner == 2 else "Hòa")

    replay_id = f"replay_{int(time.time())}_{bot1.name}_{bot2.name}"

    replay_data = {
        "id": replay_id,
        "timestamp": int(time.time() * 1000),
        "dateStr": time.strftime("%d/%m/%Y %H:%M"),
        "rules": engine.GLOBAL_RULES,
        "p1": {"name": bot1.name, "type": "bot"},
        "p2": {"name": bot2.name, "type": "bot"},
        "initialBoard": initial_board,
        "moves": replay_moves,
        "result": {
            "winner": winner,
            "winnerName": winner_name,
            "reason": win_reason,
            "reasonType": reason_type,
            "durationSec": duration_sec,
            "totalMoves": total_moves,
        },
    }

    REPLAYS_DIR.mkdir(parents=True, exist_ok=True)
    replay_file_path = REPLAYS_DIR / f"{replay_id}.json"
    try:
        with open(replay_file_path, "w", encoding="utf-8") as f:
            json.dump(replay_data, f, ensure_ascii=False)
    except Exception:
        pass

    return {
        "winner": winner,
        "winner_name": winner_name,
        "reason": win_reason,
        "moves": total_moves,
        "duration_sec": duration_sec,
        "replay_id": replay_id,
        "replay_data": replay_data,
    }