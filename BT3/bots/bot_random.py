#!/usr/bin/env python3
"""
BOT MẪU 1: BOT RANDOM
Chiến thuật: Chọn ngẫu nhiên 1 nước đi hợp lệ trong danh sách legal_moves
"""

import sys
import json
import random

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
            if not legal_moves:
                # Không có nước đi
                print(json.dumps({}))
                sys.stdout.flush()
                continue

            # Chọn ngẫu nhiên 1 nước đi
            chosen = random.choice(legal_moves)
            response = {
                "from": chosen.get("from_notation") or chosen["from"],
                "to": chosen.get("to_notation") or chosen["to"]
            }
            print(json.dumps(response))
            sys.stdout.flush()

if __name__ == "__main__":
    main()
