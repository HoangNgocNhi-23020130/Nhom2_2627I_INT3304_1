#!/usr/bin/env python3
"""
BOT MẪU 3: BOT SMART (CHIẾN THUẬT ĐA MỤC TIÊU CÔNG THỦ TOÀN DIỆN)
Chiến thuật:
- Chiếm đích thắng ngay lập tức nếu có cơ hội
- Săn lùng loài quân sắp bị tuyệt chủng của đối phương (nếu đối phương còn <= 2 quân của loài đó)
- Ăn quân đối phương có tính toán
- Bảo vệ căn cứ nhà nếu đối thủ áp sát
- Đánh giá nguy cơ bị ăn sau khi đi
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

def count_pieces(board):
    counts = {1: {"R": 0, "P": 0, "S": 0}, 2: {"R": 0, "P": 0, "S": 0}}
    for r in range(len(board)):
        for c in range(len(board[r])):
            p = board[r][c]
            if p and p["owner"] in counts:
                counts[p["owner"]][p["type"]] += 1
    return counts

def is_in_danger(board, tr, tc, piece_type, opponent):
    for dr in range(-1, 2):
        for dc in range(-1, 2):
            nr, nc = tr + dr, tc + dc
            if 0 <= nr < 9 and 0 <= nc < 9:
                enemy = board[nr][nc]
                if enemy and enemy["owner"] == opponent:
                    if BEATS.get(enemy["type"]) == piece_type:
                        return True
    return False

def main():
    last_moves = []  # Lưu các nước đi gần nhất để tránh lặp nước vô nghĩa

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

            counts = count_pieces(board)

            # Kiểm tra xem có quân địch nào áp sát ô nhà (khoảng cách <= 2) không
            opp_threat_to_home = False
            for r in range(len(board)):
                for c in range(len(board[r])):
                    p = board[r][c]
                    if p and p["owner"] == opponent and chebyshev_dist(r, c, hr, hc) <= 2:
                        opp_threat_to_home = True
                        break
                if opp_threat_to_home:
                    break

            best_move = None
            best_score = -999999

            for m in legal_moves:
                score = 0
                to_notat = m.get("to_notation", "")

                # 1. Thắng ngay lập tức
                if to_notat == goal_notat:
                    best_move = m
                    break

                fr, fc = m["from"]["r"], m["from"]["c"]
                tr, tc = m["to"]["r"], m["to"]["c"]
                moving_piece = board[fr][fc]
                ptype = moving_piece["type"] if moving_piece else "R"

                # 2. Rút ngắn khoảng cách tới đích
                cur_dist = chebyshev_dist(fr, fc, gr, gc)
                new_dist = chebyshev_dist(tr, tc, gr, gc)
                score += (cur_dist - new_dist) * 35

                # 3. Ăn quân & Săn diệt chủng
                if m.get("is_capture"):
                    score += 300
                    target = m.get("target_piece")
                    if target:
                        ttype = target.get("type")
                        if counts[opponent].get(ttype, 0) <= 2:
                            score += 550  # Thưởng lớn để tiêu diệt sạch loài này!

                # 4. Canh giữ cửa nhà CHỈ KHI đối phương thực sự áp sát
                if opp_threat_to_home:
                    dist_to_home = chebyshev_dist(tr, tc, hr, hc)
                    if dist_to_home <= 1:
                        score += 90

                # 5. Né nguy hiểm
                if is_in_danger(board, tr, tc, ptype, opponent):
                    score -= 240
                    if counts[player].get(ptype, 0) <= 2:
                        score -= 300  # Bảo vệ quân quý giá

                # 6. Chống lặp nước đi qua lại vô nghĩa (anti-oscillation)
                if (tr, tc, fr, fc) in last_moves:
                    score -= 120

                score += random.uniform(0, 6)

                if score > best_score:
                    best_score = score
                    best_move = m

            if best_move:
                # Ghi nhớ nước đi gần nhất
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
