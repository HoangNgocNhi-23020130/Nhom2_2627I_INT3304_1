#!/usr/bin/env python3
"""
BOT MẪU 2: BOT RUSHER (CHIẾN THUẬT TIẾN CÔNG VỀ ĐÍCH)
Chiến thuật:
- Nếu có nước đi chiếm đích ngay lập tức -> Chọn ngay để thắng!
- Tối ưu hóa việc rút ngắn khoảng cách Chebyshev tới ô đích của đối thủ (i9 cho P1, a1 cho P2).
- Ăn quân đối phương nếu trên đường tiến công.
"""

import sys
import json
import random

def get_goal_coord(player):
    return (0, 8) if player == 1 else (8, 0)

def chebyshev_dist(r1, c1, r2, c2):
    return max(abs(r1 - r2), abs(c1 - c2))

def main():
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
            player = data.get("turn", 1)
            gr, gc = get_goal_coord(player)
            goal_notat = "i9" if player == 1 else "a1"

            if not legal_moves:
                print(json.dumps({}))
                sys.stdout.flush()
                continue

            best_move = None
            best_score = -999999

            for m in legal_moves:
                score = 0
                to_notat = m.get("to_notation", "")

                # 1. Thắng ngay lập tức
                if to_notat == goal_notat:
                    best_move = m
                    break

                # 2. Rút ngắn khoảng cách tới đích
                fr, fc = m["from"]["r"], m["from"]["c"]
                tr, tc = m["to"]["r"], m["to"]["c"]

                cur_dist = chebyshev_dist(fr, fc, gr, gc)
                new_dist = chebyshev_dist(tr, tc, gr, gc)
                score += (cur_dist - new_dist) * 60

                # 3. Thưởng điểm ăn quân
                if m.get("is_capture"):
                    score += 120

                score += random.uniform(0, 5)

                if score > best_score:
                    best_score = score
                    best_move = m

            response = {
                "from": best_move.get("from_notation") or best_move["from"],
                "to": best_move.get("to_notation") or best_move["to"]
            }
            print(json.dumps(response))
            sys.stdout.flush()

if __name__ == "__main__":
    main()
