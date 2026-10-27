"""
backend/app/core/engine.py
Lõi game engine thuần logic, đồng bộ với shared/rules.json.
"""

import copy
import json
import random
from pathlib import Path
from app.config import RULES_FILE

# Cấu hình dự phòng nếu chưa tìm thấy shared/rules.json
DEFAULT_FALLBACK_RULES = {
    "version": "2.0",
    "name": "OanTuTi Tactics 9x9 Standard",
    "boardSize": 9,
    "maxTurns": 200,
    "goals": {
        1: {"r": 0, "c": 8, "notation": "i9", "name": "Đích P1 (Phải-Trên)"},
        2: {"r": 8, "c": 0, "notation": "a1", "name": "Đích P2 (Trái-Dưới)"}
    },
    "homes": {
        1: {"r": 8, "c": 0, "notation": "a1", "name": "Nhà P1 (Trái-Dưới)"},
        2: {"r": 0, "c": 8, "notation": "i9", "name": "Nhà P2 (Phải-Trên)"}
    },
    "allowEnterOwnHome": False,
    "beats": {"R": "S", "S": "P", "P": "R"},
    "sameTypeRule": "block",
    "winConditions": {
        "reachGoal": True,
        "extinctionAnyType": True,
        "turnLimit": True,
        "forfeit": True
    },
    "pieceTypes": ["R", "P", "S"],
    "pieceEmojis": {"R": "✊", "P": "✋", "S": "✌️"},
    "pieceCountsPerPlayer": {"R": 6, "P": 6, "S": 6}
}


def load_rules(config_path=RULES_FILE):
    if config_path and Path(config_path).exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["goals"] = {int(k): v for k, v in data["goals"].items()}
            data["homes"] = {int(k): v for k, v in data["homes"].items()}
            return data
        except Exception:
            pass
    return DEFAULT_FALLBACK_RULES


GLOBAL_RULES = load_rules()


def to_notation(r, c):
    col_letter = chr(ord('a') + c)
    row_number = 9 - r
    return f"{col_letter}{row_number}"


def from_notation(notation):
    notation = notation.strip().lower()
    c = ord(notation[0]) - ord('a')
    r = 9 - int(notation[1:])
    return r, c


def is_valid_coord(r, c, size=9):
    return 0 <= r < size and 0 <= c < size


def create_empty_board(size=9):
    return [[None for _ in range(size)] for _ in range(size)]


def create_symmetrical_board(rules=None):
    if rules is None:
        rules = GLOBAL_RULES
    size = rules["boardSize"]
    board = create_empty_board(size)

    candidates = []
    for r in range(size):
        for c in range(size):
            if r - c >= 2:
                if r == rules["homes"][1]["r"] and c == rules["homes"][1]["c"]:
                    continue
                candidates.append((r, c))

    random.shuffle(candidates)

    piece_counts = rules["pieceCountsPerPlayer"]
    total_pieces = sum(piece_counts.values())
    chosen_p1_positions = candidates[:total_pieces]

    pieces = []
    for p_type, count in piece_counts.items():
        pieces.extend([p_type] * count)
    random.shuffle(pieces)

    for i in range(total_pieces):
        pr, pc = chosen_p1_positions[i]
        ptype = pieces[i]
        board[pr][pc] = {"owner": 1, "type": ptype}
        board[pc][pr] = {"owner": 2, "type": ptype}

    return board


def beats(type1, type2, rules=None):
    if rules is None:
        rules = GLOBAL_RULES
    return rules["beats"].get(type1) == type2


def get_valid_moves_for_piece(board, r, c, rules=None):
    if rules is None:
        rules = GLOBAL_RULES
    piece = board[r][c]
    if not piece:
        return []

    size = rules["boardSize"]
    moves = []
    directions = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1)
    ]

    own_home = rules["homes"][piece["owner"]]

    for dr, dc in directions:
        nr, nc = r + dr, c + dc
        if not is_valid_coord(nr, nc, size):
            continue

        if not rules["allowEnterOwnHome"] and nr == own_home["r"] and nc == own_home["c"]:
            continue

        target = board[nr][nc]
        from_notat = to_notation(r, c)
        to_notat = to_notation(nr, nc)

        if target is None:
            moves.append({
                "from": {"r": r, "c": c},
                "to": {"r": nr, "c": nc},
                "from_notation": from_notat,
                "to_notation": to_notat,
                "is_capture": False,
                "target_piece": None
            })
        elif target["owner"] != piece["owner"]:
            if beats(piece["type"], target["type"], rules):
                moves.append({
                    "from": {"r": r, "c": c},
                    "to": {"r": nr, "c": nc},
                    "from_notation": from_notat,
                    "to_notation": to_notat,
                    "is_capture": True,
                    "target_piece": target
                })
            elif rules["sameTypeRule"] == "eliminate" and piece["type"] == target["type"]:
                moves.append({
                    "from": {"r": r, "c": c},
                    "to": {"r": nr, "c": nc},
                    "from_notation": from_notat,
                    "to_notation": to_notat,
                    "is_capture": True,
                    "is_mutual_elimination": True,
                    "target_piece": target
                })

    return moves


def get_all_legal_moves(board, player, rules=None):
    if rules is None:
        rules = GLOBAL_RULES
    legal_moves = []
    size = rules["boardSize"]
    for r in range(size):
        for c in range(size):
            p = board[r][c]
            if p and p["owner"] == player:
                legal_moves.extend(get_valid_moves_for_piece(board, r, c, rules))
    return legal_moves


def apply_move(board, move, rules=None):
    if rules is None:
        rules = GLOBAL_RULES
    new_board = copy.deepcopy(board)
    fr, fc = move["from"]["r"], move["from"]["c"]
    tr, tc = move["to"]["r"], move["to"]["c"]

    moving_piece = new_board[fr][fc]
    dest_piece = new_board[tr][tc]

    is_capture = dest_piece is not None
    is_mutual = move.get("is_mutual_elimination", False)

    if is_mutual:
        new_board[fr][fc] = None
        new_board[tr][tc] = None
    else:
        new_board[tr][tc] = moving_piece
        new_board[fr][fc] = None

    return {
        "new_board": new_board,
        "moving_piece": moving_piece,
        "is_capture": is_capture,
        "captured_piece": dest_piece,
        "from_notation": to_notation(fr, fc),
        "to_notation": to_notation(tr, tc)
    }


def count_remaining_pieces(board):
    counts = {
        1: {"R": 0, "P": 0, "S": 0, "total": 0},
        2: {"R": 0, "P": 0, "S": 0, "total": 0}
    }
    for r in range(len(board)):
        for c in range(len(board[r])):
            p = board[r][c]
            if p and p["owner"] in counts:
                pt = p["type"]
                counts[p["owner"]][pt] = counts[p["owner"]].get(pt, 0) + 1
                counts[p["owner"]]["total"] += 1
    return counts


def check_victory(board, move_count=0, rules=None):
    if rules is None:
        rules = GLOBAL_RULES

    p1_goal = rules["goals"][1]
    p2_goal = rules["goals"][2]

    if rules["winConditions"]["reachGoal"]:
        p1_at_goal = board[p1_goal["r"]][p1_goal["c"]]
        if p1_at_goal and p1_at_goal["owner"] == 1:
            return {"winner": 1, "reason": f"P1 chiếm thành công ô đích {p1_goal['notation']}!", "reason_type": "base"}

        p2_at_goal = board[p2_goal["r"]][p2_goal["c"]]
        if p2_at_goal and p2_at_goal["owner"] == 2:
            return {"winner": 2, "reason": f"P2 chiếm thành công ô đích {p2_goal['notation']}!", "reason_type": "base"}

    counts = count_remaining_pieces(board)
    if counts[1]["total"] == 0 and counts[2]["total"] == 0:
        return {"winner": 0, "reason": "Hòa do cả 2 bên cùng hết quân cờ!", "reason_type": "draw"}
    if counts[1]["total"] == 0:
        return {"winner": 2, "reason": "P2 thắng do P1 đã hết sạch toàn bộ quân cờ!", "reason_type": "extinction"}
    if counts[2]["total"] == 0:
        return {"winner": 1, "reason": "P1 thắng do P2 đã hết sạch toàn bộ quân cờ!", "reason_type": "extinction"}

    if rules["winConditions"]["extinctionAnyType"]:
        p1_extinct = any(counts[1][t] == 0 for t in rules["pieceTypes"])
        p2_extinct = any(counts[2][t] == 0 for t in rules["pieceTypes"])

        if p1_extinct and p2_extinct:
            return {"winner": 0, "reason": "Hòa do cả 2 bên cùng bị diệt chủng 1 loại quân!", "reason_type": "draw"}
        if p2_extinct:
            return {"winner": 1, "reason": "P1 thắng do đối phương bị diệt chủng 1 loại quân!", "reason_type": "extinction"}
        if p1_extinct:
            return {"winner": 2, "reason": "P2 thắng do đối phương bị diệt chủng 1 loại quân!", "reason_type": "extinction"}

    if rules["winConditions"]["turnLimit"] and rules["maxTurns"] and move_count >= rules["maxTurns"]:
        if counts[1]["total"] > counts[2]["total"]:
            return {"winner": 1, "reason": f"Hết {rules['maxTurns']} lượt: P1 thắng do nhiều quân hơn!", "reason_type": "turn_limit"}
        elif counts[2]["total"] > counts[1]["total"]:
            return {"winner": 2, "reason": f"Hết {rules['maxTurns']} lượt: P2 thắng do nhiều quân hơn!", "reason_type": "turn_limit"}
        else:
            return {"winner": 0, "reason": f"Hết {rules['maxTurns']} lượt: Kết thúc hòa!", "reason_type": "turn_limit"}

    return None