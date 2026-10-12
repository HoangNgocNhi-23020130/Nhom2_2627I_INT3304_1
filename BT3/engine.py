"""
===== ENGINE THUẦN LOGIC PYTHON (PURE GAME ENGINE) =====
Đồng bộ 100% với rules.js và engine.js của Web Client.
Hoàn toàn độc lập với UI, mạng và IO.
"""

import copy
import random

OTT_RULES = {
    "version": "2.0",
    "name": "OanTuTi Tactics 9x9 Standard",
    "board_size": 9,
    "max_turns": 200,
    "goals": {
        1: {"r": 0, "c": 8, "notation": "i9", "name": "Đích P1 (Phải-Trên)"},
        2: {"r": 8, "c": 0, "notation": "a1", "name": "Đích P2 (Trái-Dưới)"}
    },
    "homes": {
        1: {"r": 8, "c": 0, "notation": "a1", "name": "Nhà P1 (Trái-Dưới)"},
        2: {"r": 0, "c": 8, "notation": "i9", "name": "Nhà P2 (Phải-Trên)"}
    },
    "allow_enter_own_home": False,  # Ràng buộc: Cấm quân đi vào ô nhà mình
    "beats": {
        "R": "S",  # Rock > Scissors
        "S": "P",  # Scissors > Paper
        "P": "R"   # Paper > Rock
    },
    "same_type_rule": "block",  # 'block': chặn đường nhau, 'eliminate': cùng loại cùng bị loại
    "win_conditions": {
        "reach_goal": True,
        "extinction_any_type": True,
        "turn_limit": True
    },
    "piece_emojis": {
        "R": "✊",
        "P": "✋",
        "S": "✌️"
    }
}


def to_notation(r, c):
    """Chuyển tọa độ ma trận (0..8, 0..8) sang ký hiệu cờ (a1..i9)"""
    col_letter = chr(ord('a') + c)
    row_number = 9 - r
    return f"{col_letter}{row_number}"


def from_notation(notation):
    """Chuyển ký hiệu cờ (ví dụ 'a1') sang tọa độ ma trận (r, c)"""
    notation = notation.strip().lower()
    c = ord(notation[0]) - ord('a')
    r = 9 - int(notation[1:])
    return r, c


def is_valid_coord(r, c, size=9):
    return 0 <= r < size and 0 <= c < size


def create_empty_board(size=9):
    return [[None for _ in range(size)] for _ in range(size)]


def create_symmetrical_board(rules=None):
    """
    Tạo bàn cờ khởi đầu đối xứng chuẩn theo luật:
    - 18 quân/bên (6 Đấm, 6 Lá, 6 Kéo)
    - P1 ở nửa dưới (r - c >= 2), trừ ô nhà a1 (r=8, c=0)
    - P2 đối xứng qua đường chéo chính (c, r)
    - 3 đường chéo giữa (|r - c| <= 1) hoàn toàn trống.
    """
    if rules is None:
        rules = OTT_RULES
    size = rules["board_size"]
    board = create_empty_board(size)

    candidates = []
    for r in range(size):
        for c in range(size):
            if r - c >= 2:
                if r == size - 1 and c == 0:
                    continue  # Trừ ô nhà P1
                candidates.append((r, c))

    random.shuffle(candidates)
    chosen_p1_positions = candidates[:18]

    pieces = ["R"] * 6 + ["P"] * 6 + ["S"] * 6
    random.shuffle(pieces)

    for i in range(18):
        pr, pc = chosen_p1_positions[i]
        ptype = pieces[i]
        board[pr][pc] = {"owner": 1, "type": ptype}
        board[pc][pr] = {"owner": 2, "type": ptype}

    return board


def beats(type1, type2, rules=None):
    if rules is None:
        rules = OTT_RULES
    return rules["beats"].get(type1) == type2


def get_valid_moves_for_piece(board, r, c, rules=None):
    """Tính các nước đi hợp lệ cho quân tại ô (r, c)"""
    if rules is None:
        rules = OTT_RULES
    piece = board[r][c]
    if not piece:
        return []

    size = rules["board_size"]
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

        # CẤM ĐI VÀO Ô NHÀ CỦA CHÍNH MÌNH
        if not rules["allow_enter_own_home"] and nr == own_home["r"] and nc == own_home["c"]:
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
                # Ăn được quân đối phương
                moves.append({
                    "from": {"r": r, "c": c},
                    "to": {"r": nr, "c": nc},
                    "from_notation": from_notat,
                    "to_notation": to_notat,
                    "is_capture": True,
                    "target_piece": target
                })
            elif rules["same_type_rule"] == "eliminate" and piece["type"] == target["type"]:
                # Biến thể triệt tiêu
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
    """Lấy danh sách tất cả nước đi hợp lệ của một người chơi"""
    if rules is None:
        rules = OTT_RULES
    legal_moves = []
    size = rules["board_size"]
    for r in range(size):
        for c in range(size):
            p = board[r][c]
            if p and p["owner"] == player:
                legal_moves.extend(get_valid_moves_for_piece(board, r, c, rules))
    return legal_moves


def apply_move(board, move, rules=None):
    """Thực hiện nước đi trên bản sao bàn cờ và trả về bàn cờ mới cùng chi tiết"""
    if rules is None:
        rules = OTT_RULES
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
                counts[p["owner"]][pt] += 1
                counts[p["owner"]]["total"] += 1
    return counts


def check_victory(board, move_count=0, rules=None):
    """
    Kiểm tra điều kiện thắng/thua/hòa:
    1. Chiếm ô đích đối phương
    2. Hết sạch quân
    3. Tuyệt chủng 1 loài quân
    4. Hết giới hạn 200 lượt
    """
    if rules is None:
        rules = OTT_RULES

    p1_goal = rules["goals"][1]
    p2_goal = rules["goals"][2]

    # 1. Chiếm ô đích
    if rules["win_conditions"]["reach_goal"]:
        p1_at_goal = board[p1_goal["r"]][p1_goal["c"]]
        if p1_at_goal and p1_at_goal["owner"] == 1:
            return {"winner": 1, "reason": f"P1 đã đưa quân chiếm thành công ô đích {p1_goal['notation']}!", "reason_type": "base"}

        p2_at_goal = board[p2_goal["r"]][p2_goal["c"]]
        if p2_at_goal and p2_at_goal["owner"] == 2:
            return {"winner": 2, "reason": f"P2 đã đưa quân chiếm thành công ô đích {p2_goal['notation']}!", "reason_type": "base"}

    # 2. Hết sạch toàn bộ quân
    counts = count_remaining_pieces(board)
    if counts[1]["total"] == 0 and counts[2]["total"] == 0:
        return {"winner": 0, "reason": "Ván đấu hòa do cả 2 bên cùng hết sạch quân cờ!", "reason_type": "draw"}
    if counts[1]["total"] == 0:
        return {"winner": 2, "reason": "P2 thắng do P1 đã hết sạch toàn bộ quân cờ!", "reason_type": "extinction"}
    if counts[2]["total"] == 0:
        return {"winner": 1, "reason": "P1 thắng do P2 đã hết sạch toàn bộ quân cờ!", "reason_type": "extinction"}

    # 3. Diệt chủng 1 loài quân
    if rules["win_conditions"]["extinction_any_type"]:
        p1_extinct = "Đấm (✊)" if counts[1]["R"] == 0 else ("Lá (✋)" if counts[1]["P"] == 0 else ("Kéo (✌️)" if counts[1]["S"] == 0 else None))
        p2_extinct = "Đấm (✊)" if counts[2]["R"] == 0 else ("Lá (✋)" if counts[2]["P"] == 0 else ("Kéo (✌️)" if counts[2]["S"] == 0 else None))

        if p1_extinct and p2_extinct:
            return {"winner": 0, "reason": "Ván đấu hòa do cả 2 bên cùng bị tuyệt chủng một loại quân!", "reason_type": "draw"}
        if p2_extinct:
            return {"winner": 1, "reason": f"P1 thắng do P2 đã bị tiêu diệt sạch toàn bộ quân {p2_extinct}!", "reason_type": "extinction"}
        if p1_extinct:
            return {"winner": 2, "reason": f"P2 thắng do P1 đã bị tiêu diệt sạch toàn bộ quân {p1_extinct}!", "reason_type": "extinction"}

    # 4. Hết số lượt tối đa
    if rules["win_conditions"]["turn_limit"] and rules["max_turns"] and move_count >= rules["max_turns"]:
        if counts[1]["total"] > counts[2]["total"]:
            return {"winner": 1, "reason": f"Hết {rules['max_turns']} lượt: P1 thắng do còn nhiều quân hơn ({counts[1]['total']} vs {counts[2]['total']})!", "reason_type": "turn_limit"}
        elif counts[2]["total"] > counts[1]["total"]:
            return {"winner": 2, "reason": f"Hết {rules['max_turns']} lượt: P2 thắng do còn nhiều quân hơn ({counts[2]['total']} vs {counts[1]['total']})!", "reason_type": "turn_limit"}
        else:
            return {"winner": 0, "reason": f"Hết {rules['max_turns']} lượt: Ván đấu kết thúc hòa!", "reason_type": "turn_limit"}

    return None
