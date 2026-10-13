#!/usr/bin/env python3
"""
BOT MẪU: BOT RUSH & ESCORT (ĐỘT KÍCH VÀ HỘ TỐNG THẦN TỐC)
Chiến thuật:
- Phân vai động (Dynamic Roles): Xác định Quân Tiên Phong (Runner) gần đích nhất.
- Chế độ Rush: Đẩy Runner tiến về đích với tốc độ cao nhất.
- Chế độ Hộ Tống (Escort): Dùng các quân khác tiêu diệt kẻ địch rình rập xung quanh Runner.
- Chế độ Phong Tỏa (Blockade): Tập trung cản trở/tiêu diệt quân tiến xa nhất của đối phương.
"""

import sys
import json
import random

BEATS = {"R": "S", "S": "P", "P": "R"}

def get_goal_coord(player):
    return (0, 8) if player == 1 else (8, 0)

def get_home_coord(player):
    return (8, 0) if player == 1 else (0, 8)

def chebyshev_dist(r1, c1, r2, c2):
    return max(abs(r1 - r2), abs(c1 - c2))

def is_in_danger(board, tr, tc, piece_type, opponent):
    """Kiểm tra xem ô (tr, tc) có bị quân địch đe dọa ăn ở lượt tới không."""
    for dr in range(-1, 2):
        for dc in range(-1, 2):
            nr, nc = tr + dr, tc + dc
            if 0 <= nr < 9 and 0 <= nc < 9:
                enemy = board[nr][nc]
                if enemy and enemy["owner"] == opponent:
                    if BEATS.get(enemy["type"]) == piece_type:
                        return True
    return False

def get_my_runner(board, player, gr, gc):
    """Tìm quân ta đang ở gần đích nhất."""
    min_dist = 999
    runner_pos = None
    for r in range(len(board)):
        for c in range(len(board[r])):
            p = board[r][c]
            if p and p["owner"] == player:
                d = chebyshev_dist(r, c, gr, gc)
                if d < min_dist:
                    min_dist = d
                    runner_pos = (r, c)
    return runner_pos, min_dist

def get_opp_runner(board, opponent, hr, hc):
    """Tìm quân địch đang ở gần ô thắng của họ (chính là ô nhà của ta) nhất."""
    min_dist = 999
    opp_runner_pos = None
    for r in range(len(board)):
        for c in range(len(board[r])):
            p = board[r][c]
            if p and p["owner"] == opponent:
                d = chebyshev_dist(r, c, hr, hc)
                if d < min_dist:
                    min_dist = d
                    opp_runner_pos = (r, c)
    return opp_runner_pos, min_dist

def main():
    last_moves = []

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except Exception:
            continue

        if data.get("type") == "move":
            legal_moves = data.get("legal_moves", [])
            board = data.get("board", [])
            player = data.get("turn", 1)
            opponent = 2 if player == 1 else 1

            gr, gc = get_goal_coord(player)
            goal_notat = "i9" if player == 1 else "a1"
            hr, hc = get_home_coord(player)

            if not legal_moves:
                print(json.dumps({}))
                sys.stdout.flush()
                continue

            my_runner_pos, my_runner_dist = get_my_runner(board, player, gr, gc)
            opp_runner_pos, opp_runner_dist = get_opp_runner(board, opponent, hr, hc)

            best_move = None
            best_score = -999999

            for m in legal_moves:
                score = 0
                to_notat = m.get("to_notation", "")

                # 1. Bắt cơ hội thắng ngay lập tức
                if to_notat == goal_notat:
                    best_move = m
                    break

                fr, fc = m["from"]["r"], m["from"]["c"]
                tr, tc = m["to"]["r"], m["to"]["c"]
                moving_piece = board[fr][fc]
                ptype = moving_piece["type"] if moving_piece else "R"

                is_runner = (my_runner_pos and (fr, fc) == my_runner_pos)

                # 2. Đẩy quân Tiên phong (Runner) tiến về đích với điểm thưởng cao
                if is_runner:
                    cur_d = chebyshev_dist(fr, fc, gr, gc)
                    new_d = chebyshev_dist(tr, tc, gr, gc)
                    score += (cur_d - new_d) * 80

                # 3. Ăn quân có định hướng (Hộ tống & Triệt hạ Runner đối thủ)
                if m.get("is_capture"):
                    score += 200
                    target = m.get("target_piece")

                    # Thưởng thêm nếu ăn quân địch đang đe dọa Runner của ta
                    if target and my_runner_pos:
                        if chebyshev_dist(tr, tc, my_runner_pos[0], my_runner_pos[1]) <= 2:
                            score += 400

                    # Thưởng lớn nếu tiêu diệt chính Runner của địch
                    if opp_runner_pos and (tr, tc) == opp_runner_pos:
                        score += 500

                # 4. Phong tỏa quân tiên phong của địch (Blockade)
                if opp_runner_dist <= 3 and not is_runner:
                    if opp_runner_pos:
                        new_dist_to_opp_runner = chebyshev_dist(tr, tc, opp_runner_pos[0], opp_runner_pos[1])
                        if new_dist_to_opp_runner <= 1:
                            score += 350

                # 5. Đánh giá rủi ro (Né bị ăn)
                if is_in_danger(board, tr, tc, ptype, opponent):
                    score -= 400 if is_runner else 200  # Trừ điểm nặng hơn nếu là Runner

                # 6. Tránh lặp nước đi vô nghĩa
                if (tr, tc, fr, fc) in last_moves:
                    score -= 150

                score += random.uniform(0, 5)

                if score > best_score:
                    best_score = score
                    best_move = m

            if best_move:
                bfr, bfc = best_move["from"]["r"], best_move["from"]["c"]
                btr, btc = best_move["to"]["r"], best_move["to"]["c"]
                last_moves.append((bfr, bfc, btr, btc))
                if len(last_moves) > 6:
                    last_moves.pop(0)

                response = {
                    "from": best_move.get("from_notation") or best_move["from"],
                    "to": best_move.get("to_notation") or best_move["to"]
                }
            else:
                response = {}

            print(json.dumps(response))
            sys.stdout.flush()

if __name__ == "__main__":
    main()