#!/usr/bin/env python3
"""
===== MATCH RUNNER: TRỌNG TÀI ĐIỀU PHỐI TRẬN ĐẤU GIỮA 2 BOT =====
Hỗ trợ:
- Chạy 2 bot độc lập (Python, C++, Binary) qua stdin/stdout.
- Kiểm soát timeout (mặc định 200ms) và tính hợp lệ của nước đi.
- Phát sóng TRỰC TIẾP (LIVE STREAM) lên Web Client qua MQTT (broker.emqx.io).
- Tự động xuất file Replay JSON đầy đủ khi kết thúc trận đấu.
"""

import sys
import os
import time
import json
import subprocess
import argparse
import select
import copy
import random
from pathlib import Path

# Nạp module Pure Game Engine
import engine

try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False


class BotProcess:
    def __init__(self, path, name=None):
        self.raw_path = path
        self.name = name or Path(path).stem
        self.proc = None
        self.exec_cmd = []
        self._prepare_executable()

    def _prepare_executable(self):
        ext = os.path.splitext(self.raw_path)[1].lower()
        if ext == ".py":
            self.exec_cmd = [sys.executable, "-u", self.raw_path]
        elif ext == ".cpp":
            # Tự động biên dịch file C++
            binary_path = os.path.splitext(self.raw_path)[0] + "_bin"
            compiler = "clang++" if subprocess.run(["which", "clang++"], capture_output=True).returncode == 0 else "g++"
            print(f"🔨 Đang biên dịch {self.raw_path} bằng {compiler}...")
            res = subprocess.run([compiler, "-O2", self.raw_path, "-o", binary_path], capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"Biên dịch thất bại {self.raw_path}:\n{res.stderr}")
            self.exec_cmd = [binary_path]
        elif ext in [".js"]:
            self.exec_cmd = ["node", self.raw_path]
        else:
            # File thực thi trực tiếp
            os.chmod(self.raw_path, 0o755)
            self.exec_cmd = [self.raw_path]

    def start(self):
        self.proc = subprocess.Popen(
            self.exec_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

    def stop(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=0.5)
            except Exception:
                self.proc.kill()
            self.proc = None

    def query_move(self, payload_dict, timeout_sec=0.2):
        """Gửi thế cờ qua stdin và nhận nước đi từ stdout trong khoảng timeout"""
        if not self.proc or self.proc.poll() is not None:
            return None, "Bot đã crash hoặc thoát trước khi gửi nước đi!"

        json_input = json.dumps(payload_dict) + "\n"
        start_t = time.time()
        try:
            self.proc.stdin.write(json_input)
            self.proc.stdin.flush()
        except Exception as e:
            return None, f"Lỗi ghi stdin: {str(e)}"

        # Chờ stdout có dữ liệu trong timeout
        rlist, _, _ = select.select([self.proc.stdout], [], [], timeout_sec)
        elapsed_ms = (time.time() - start_t) * 1000

        if not rlist:
            return None, f"Quá thời gian suy nghĩ ({timeout_sec*1000:.0f}ms)!"

        line = self.proc.stdout.readline()
        if not line:
            return None, "Bot trả về stdout rỗng!"

        try:
            resp = json.loads(line.strip())
            return (resp, elapsed_ms), None
        except Exception as e:
            return None, f"Dữ liệu JSON trả về không hợp lệ: {line.strip()[:80]}"


class MatchRunner:
    def __init__(self, bot1_path, bot2_path, room_code=None, live=False, delay=0.3, timeout=0.2, max_turns=200):
        self.bot1 = BotProcess(bot1_path, f"Bot 1 ({Path(bot1_path).stem})")
        self.bot2 = BotProcess(bot2_path, f"Bot 2 ({Path(bot2_path).stem})")
        self.room_code = room_code or f"ARENA_{random.randint(1000, 9999)}"
        self.live = live
        self.delay = delay
        self.timeout = timeout
        self.max_turns = max_turns

        self.mqtt_client = None
        if self.live and HAS_MQTT:
            self._init_mqtt()

    def _init_mqtt(self):
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            self.mqtt_client.connect("broker.emqx.io", 1883, 60)
            self.mqtt_client.loop_start()
            print(f"📡 Đã kết nối MQTT Broker (broker.emqx.io)! Phát sóng trực tiếp tại phòng: {self.room_code}")
        except Exception as e:
            print(f"⚠️ Không thể kết nối MQTT: {e}. Vẫn tiếp tục chạy chế độ console.")
            self.mqtt_client = None

    def broadcast_state(self, game_state, is_finished=False, winner_info=None):
        if not self.mqtt_client:
            return

        room_data = {
            "roomId": self.room_code,
            "roomName": f"🔴 LIVE BOT ARENA: {self.bot1.name} vs {self.bot2.name}",
            "hostUid": "runner_bot1",
            "hostName": self.bot1.name,
            "guestUid": "runner_bot2",
            "guestName": self.bot2.name,
            "guestReady": True,
            "spectatorsCount": 1,
            "status": "finished" if is_finished else "playing",
            "isLiveBotArena": True,
            "gameState": game_state,
            "winnerInfo": winner_info,
            "updatedAt": int(time.time() * 1000)
        }

        payload_str = json.dumps({"type": "ROOM_UPDATE", "data": room_data, "sender": "runner"})
        try:
            self.mqtt_client.publish("ottv2/v2/room_list", payload_str)
            self.mqtt_client.publish(f"ottv2/v2/room/{self.room_code}", payload_str)
        except Exception as e:
            pass

    def run(self):
        print("=" * 65)
        print(f"🏆 BẮT ĐẦU TRẬN ĐẤU OANTUTI ARENA")
        print(f"🔵 Người chơi 1: {self.bot1.name}")
        print(f"🔴 Người chơi 2: {self.bot2.name}")
        print(f"🏷️ Mã phòng LIVE: {self.room_code}")
        print("=" * 65)

        self.bot1.start()
        self.bot2.start()

        board = engine.create_symmetrical_board()
        initial_board = copy.deepcopy(board)
        turn = 1
        total_moves = 0
        move_history = []
        replay_moves = []
        is_game_over = False
        winner = None
        win_reason = ""
        reason_type = "base"
        start_time = int(time.time() * 1000)

        # Phát sóng trạng thái khởi đầu
        init_state = {
            "board": board,
            "turn": 1,
            "moveHistory": [{"text": "Bắt đầu trận đấu 2 Bot!", "turn": 1}],
            "isGameOver": False,
            "winner": None,
            "startTime": start_time,
            "totalMoves": 0
        }
        self.broadcast_state(init_state)
        time.sleep(1.0)  # Chờ 1s để khán giả kịp vào phòng

        while not is_game_over and total_moves < self.max_turns:
            current_bot = self.bot1 if turn == 1 else self.bot2
            opponent_turn = 2 if turn == 1 else 1

            # Lấy danh sách nước đi hợp lệ
            legal_moves = engine.get_all_legal_moves(board, turn)
            if not legal_moves:
                winner = opponent_turn
                win_reason = f"{current_bot.name} không còn nước đi hợp lệ nào!"
                reason_type = "extinction"
                is_game_over = True
                break

            # Gửi payload cho Bot
            payload = {
                "type": "move",
                "turn": turn,
                "move_count": total_moves + 1,
                "board": board,
                "legal_moves": legal_moves
            }

            res, err = current_bot.query_move(payload, timeout_sec=self.timeout)
            if err:
                # Bot vi phạm hoặc crash -> xử thua ngay lập tức!
                winner = opponent_turn
                win_reason = f"{current_bot.name} bị xử thua: {err}"
                reason_type = "surrender"
                is_game_over = True
                print(f"❌ {win_reason}")
                break

            move_dict, elapsed_ms = res
            # Xác thực nước đi trả về
            chosen_move = None
            from_str = move_dict.get("from")
            to_str = move_dict.get("to")

            for lm in legal_moves:
                # Khớp theo ký hiệu hoặc tọa độ
                if isinstance(from_str, str) and isinstance(to_str, str):
                    if lm["from_notation"].lower() == from_str.lower() and lm["to_notation"].lower() == to_str.lower():
                        chosen_move = lm
                        break
                elif isinstance(from_str, dict) and isinstance(to_str, dict):
                    if lm["from"]["r"] == from_str.get("r") and lm["from"]["c"] == from_str.get("c") and \
                       lm["to"]["r"] == to_str.get("r") and lm["to"]["c"] == to_str.get("c"):
                        chosen_move = lm
                        break

            if not chosen_move:
                # Nước đi phạm quy -> xử thua!
                winner = opponent_turn
                win_reason = f"{current_bot.name} đi nước phạm quy ({from_str} ➔ {to_str})!"
                reason_type = "surrender"
                is_game_over = True
                print(f"❌ {win_reason}")
                break

            # Áp dụng nước đi
            applied = engine.apply_move(board, chosen_move)
            board = applied["new_board"]
            total_moves += 1

            moving_p = applied["moving_piece"]
            p_emoji = engine.OTT_RULES["piece_emojis"].get(moving_p["type"], moving_p["type"])
            cap_text = f" (Ăn {engine.OTT_RULES['piece_emojis'].get(applied['captured_piece']['type'], '')})" if applied["is_capture"] else ""
            log_line = f"[{total_moves}] {current_bot.name} ({p_emoji}): {applied['from_notation']} ➔ {applied['to_notation']}{cap_text} [{elapsed_ms:.1f}ms]"
            print(log_line)

            move_history.insert(0, {"text": log_line, "turn": turn})

            # Ghi vào replay
            replay_moves.append({
                "step": total_moves,
                "player": turn,
                "from": chosen_move["from"],
                "to": chosen_move["to"],
                "fromNotation": applied["from_notation"],
                "toNotation": applied["to_notation"],
                "pieceType": moving_p["type"],
                "isCapture": applied["is_capture"],
                "capturedType": applied["captured_piece"]["type"] if applied["captured_piece"] else None,
                "elapsedMs": round(elapsed_ms, 1),
                "boardSnapshot": copy.deepcopy(board)
            })

            # Kiểm tra thắng cuộc
            win_check = engine.check_victory(board, total_moves)
            if win_check:
                is_game_over = True
                winner = win_check["winner"]
                win_reason = win_check["reason"]
                reason_type = win_check["reason_type"]

            # Cập nhật state & phát sóng trực tiếp
            turn = 2 if turn == 1 else 1
            curr_state = {
                "board": board,
                "turn": turn,
                "moveHistory": move_history[:15],
                "isGameOver": is_game_over,
                "winner": winner,
                "winReason": win_reason,
                "startTime": start_time,
                "totalMoves": total_moves
            }
            self.broadcast_state(curr_state, is_finished=is_game_over, winner_info={"winner": winner, "reason": win_reason})

            if self.delay > 0:
                time.sleep(self.delay)

        self.bot1.stop()
        self.bot2.stop()

        # Tổng kết trận đấu
        duration_sec = max(1, int(time.time() - start_time / 1000))
        w_name = self.bot1.name if winner == 1 else (self.bot2.name if winner == 2 else "Hòa")

        print("=" * 65)
        print(f"🏁 KẾT THÚC TRẬN ĐẤU sau {total_moves} nước đi!")
        print(f"🎉 CHIẾN THẮNG: {w_name}")
        print(f"💬 Lý do: {win_reason}")
        print("=" * 65)

        # Lưu Replay JSON
        replay_id = f"replay_{int(time.time())}_{self.room_code}"
        replays_dir = Path(__file__).resolve().parent / "replays"
        replays_dir.mkdir(parents=True, exist_ok=True)
        replay_file = replays_dir / f"{replay_id}.json"
        replay_path = f"replays/{replay_id}.json"

        replay_data = {
            "id": replay_id,
            "version": engine.OTT_RULES["version"],
            "dateStr": time.strftime("%d/%m/%Y %H:%M"),
            "timestamp": int(time.time() * 1000),
            "mode": "bot_vs_bot_live",
            "p1": {"name": self.bot1.name, "type": "bot"},
            "p2": {"name": self.bot2.name, "type": "bot"},
            "rules": engine.OTT_RULES,
            "initialBoard": initial_board,
            "moves": replay_moves,
            "result": {
                "winner": winner,
                "winnerName": w_name,
                "reason": win_reason,
                "reasonType": reason_type,
                "durationSec": duration_sec
            }
        }

        with open(replay_file, "w", encoding="utf-8") as f:
            json.dump(replay_data, f, ensure_ascii=False, indent=2)
        print(f"💾 Đã lưu file Replay trận đấu: {replay_path}")

        # Đồng bộ lịch sử lên MQTT
        if self.mqtt_client:
            history_record = {
                "id": replay_id,
                "roomCode": self.room_code,
                "p1Name": self.bot1.name,
                "p2Name": self.bot2.name,
                "winner": winner,
                "winnerName": w_name,
                "reason": win_reason,
                "reasonType": reason_type,
                "totalMoves": total_moves,
                "durationSec": duration_sec,
                "dateStr": time.strftime("%d/%m/%Y %H:%M"),
                "timestamp": int(time.time() * 1000),
                "replayPath": replay_path
            }
            try:
                self.mqtt_client.publish("ottv2/v2/history", json.dumps(history_record))
                time.sleep(0.5)
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except Exception:
                pass

        return {
            "winner": winner,
            "winner_name": w_name,
            "reason": win_reason,
            "moves": total_moves,
            "replay_file": replay_path
        }


def main():
    parser = argparse.ArgumentParser(description="Chạy trận đấu OanTuTi giữa 2 Bot và phát sóng LIVE lên Web")
    parser.add_argument("bot1", help="Đường dẫn file Bot 1 (vd: bots/bot_smart.py)")
    parser.add_argument("bot2", help="Đường dẫn file Bot 2 (vd: bots/bot_rusher.py)")
    parser.add_argument("--room", default=None, help="Mã phòng trực tiếp (mặc định ngẫu nhiên ARENA_XXXX)")
    parser.add_argument("--live", action="store_true", default=True, help="Phát sóng trực tiếp lên MQTT cho khán giả xem Web")
    parser.add_argument("--delay", type=float, default=0.3, help="Độ trễ giữa các nước đi (giây), vd 0.3s")
    parser.add_argument("--timeout", type=float, default=0.2, help="Giới hạn thời gian suy nghĩ mỗi nước (giây)")
    parser.add_argument("--max-turns", type=int, default=200, help="Số nước đi tối đa của ván đấu")

    args = parser.parse_args()
    runner = MatchRunner(
        args.bot1,
        args.bot2,
        room_code=args.room,
        live=args.live,
        delay=args.delay,
        timeout=args.timeout,
        max_turns=args.max_turns
    )
    runner.run()


if __name__ == "__main__":
    import random
    import copy
    main()
