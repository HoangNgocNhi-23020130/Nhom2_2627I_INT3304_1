#!/usr/bin/env python3
"""
===== TOURNAMENT RUNNER: TỔ CHỨC GIẢI ĐẤU VÒNG TRÒN TỰ ĐỘNG CHO BOT =====
- Quét các bot trong thư mục bots/
- Tổ chức đấu vòng tròn (Round-Robin) 2 lượt (đổi bên cầm quân)
- Tính điểm: Thắng = 3 điểm, Hòa = 1 điểm, Thua = 0 điểm
- Tùy chọn --live để phát sóng trực tiếp từng trận lên Web
- Xuất Bảng xếp hạng đẹp mắt ra file HTML (leaderboard.html)
"""

import sys
import os
import time
import json
import argparse
from pathlib import Path
from run_match import MatchRunner


def find_bots(bots_dir="bots"):
    p = Path(bots_dir)
    if not p.exists():
        return []
    bot_files = []
    for f in p.iterdir():
        if f.is_file():
            if f.suffix in [".py", ".cpp"] and not f.name.endswith("_bin"):
                bot_files.append(str(f))
    return sorted(bot_files)


def generate_leaderboard_html(standings, match_results, output_path="leaderboard.html"):
    rows_html = ""
    for rank, s in enumerate(standings, 1):
        win_rate = (s["won"] / s["played"] * 100) if s["played"] > 0 else 0
        medal = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else f"#{rank}"))
        rows_html += f"""
        <tr class="border-b border-slate-800 hover:bg-slate-800/40 transition">
            <td class="py-3 px-4 font-black text-amber-400">{medal}</td>
            <td class="py-3 px-4 font-bold text-white flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-purple-400"></span> {s['name']}
            </td>
            <td class="py-3 px-4 text-center font-bold text-slate-300">{s['played']}</td>
            <td class="py-3 px-4 text-center text-emerald-400 font-bold">{s['won']}</td>
            <td class="py-3 px-4 text-center text-slate-400">{s['drawn']}</td>
            <td class="py-3 px-4 text-center text-rose-400">{s['lost']}</td>
            <td class="py-3 px-4 text-center font-black text-base text-amber-300 bg-amber-500/10">{s['points']}</td>
            <td class="py-3 px-4 text-right font-mono text-slate-300">{win_rate:.1f}%</td>
        </tr>
        """

    matches_html = ""
    for idx, m in enumerate(match_results, 1):
        winner_badge = f"<span class='text-emerald-400 font-bold'>🏆 {m['winner_name']}</span>" if m['winner'] != 0 else "<span class='text-slate-400'>🤝 Hòa</span>"
        matches_html += f"""
        <div class="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between text-xs hover:border-slate-700 transition">
            <div class="flex items-center gap-2">
                <span class="text-slate-500 font-mono">#{idx}</span>
                <span class="text-sky-300 font-bold">{m['p1']}</span>
                <span class="text-slate-500 font-mono">VS</span>
                <span class="text-rose-300 font-bold">{m['p2']}</span>
            </div>
            <div class="flex items-center gap-2">
                {winner_badge}
                <span class="text-[11px] text-slate-500 font-mono">{m['moves']} nước</span>
                <button onclick="viewReplayDirectly('{m['replay_file']}')" class="px-3 py-1.5 rounded-lg bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-bold text-xs shadow-md transition flex items-center gap-1.5 cursor-pointer">
                    <i class="fa-solid fa-play"></i> Xem Replay
                </button>
                <a href="{m['replay_file']}" download title="Tải file JSON về máy" class="px-2 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white text-xs transition">
                    <i class="fa-solid fa-download"></i>
                </a>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Bảng Xếp Hạng Giải Đấu OanTuTi Arena</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        .board-cell {{ aspect-ratio: 1 / 1; }}
        .glass-panel {{ background: rgba(15, 23, 42, 0.95); backdrop-filter: blur(16px); }}
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-4 md:p-8">
    <div class="max-w-5xl mx-auto space-y-6">
        <header class="text-center space-y-2">
            <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-300 text-xs font-bold">
                🏆 OanTuTi Tactics AI Championship
            </div>
            <h1 class="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">
                BẢNG XẾP HẠNG GIẢI ĐẤU BOT
            </h1>
            <p class="text-xs text-slate-400">Cập nhật lúc: {time.strftime("%d/%m/%Y %H:%M:%S")} • Đấu vòng tròn 2 lượt</p>
        </header>

        <!-- BẢNG ĐIỂM -->
        <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-2xl backdrop-blur-md">
            <h2 class="text-base font-bold text-slate-200 mb-4 flex items-center gap-2">
                <i class="fa-solid fa-ranking-star text-amber-400"></i> Bảng Điểm Tổng Sắp
            </h2>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-xs">
                    <thead>
                        <tr class="border-b border-slate-800 text-slate-400 uppercase text-[10px] tracking-wider">
                            <th class="py-3 px-4">Hạng</th>
                            <th class="py-3 px-4">Tên Bot</th>
                            <th class="py-3 px-4 text-center">Trận</th>
                            <th class="py-3 px-4 text-center text-emerald-400">Thắng</th>
                            <th class="py-3 px-4 text-center">Hòa</th>
                            <th class="py-3 px-4 text-center text-rose-400">Thua</th>
                            <th class="py-3 px-4 text-center text-amber-400">Điểm</th>
                            <th class="py-3 px-4 text-right">Tỉ Lệ Thắng</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- DANH SÁCH CÁC TRẬN ĐẤU -->
        <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-2xl space-y-3">
            <h2 class="text-base font-bold text-slate-200 flex items-center gap-2">
                <i class="fa-solid fa-gamepad text-purple-400"></i> Lịch Sử Chi Tiết Các Trận Đấu
            </h2>
            <div class="space-y-2 max-h-96 overflow-y-auto pr-1">
                {matches_html}
            </div>
        </div>

        <div class="text-center pt-4 flex items-center justify-center gap-3">
            <a href="index.html" class="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 font-bold text-white text-xs shadow-lg transition">
                <i class="fa-solid fa-arrow-left"></i> Quay Lại Sảnh Đấu Web Client
            </a>
        </div>
    </div>

    <!-- MODAL: REPLAY VIEWER TRỰC TIẾP TRÊN TRANG (XEM KHÔNG CẦN TẢI FILE) -->
    <div id="replayViewerModal" class="fixed inset-0 bg-slate-950/90 backdrop-blur-md z-50 flex items-center justify-center p-3 md:p-6 hidden">
        <div class="glass-panel max-w-4xl w-full max-h-[95vh] rounded-2xl p-4 md:p-6 border border-slate-700 shadow-2xl flex flex-col gap-3 overflow-hidden">
            <!-- Header -->
            <div class="flex items-center justify-between pb-2 border-b border-slate-800">
                <div>
                    <h3 id="replayTitle" class="font-extrabold text-base md:text-lg text-white">Xem Lại Ván Đấu</h3>
                    <p id="replayMeta" class="text-xs text-slate-400 mt-0.5 font-medium">Thời gian • Kết quả</p>
                </div>
                <div class="flex items-center gap-2">
                    <button onclick="exportCurrentReplayFile()" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold transition shadow flex items-center gap-1.5">
                        <i class="fa-solid fa-download"></i> Tải JSON
                    </button>
                    <button onclick="ReplayViewer.close()" class="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center justify-center text-sm">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
            </div>

            <!-- Content: Board & Details -->
            <div class="flex-1 flex flex-col md:flex-row items-center justify-center gap-5 overflow-y-auto py-2">
                <!-- Replay Board -->
                <div class="w-full max-w-sm md:max-w-md aspect-square bg-slate-950 p-2 rounded-2xl border border-slate-800 shadow-2xl flex flex-col">
                    <div id="replayBoardGrid" class="grid grid-cols-9 gap-1 flex-1"></div>
                </div>

                <!-- Replay Info Sidebar -->
                <div class="w-full md:w-64 flex flex-col gap-3">
                    <div class="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
                        <div class="flex items-center justify-between mb-1.5">
                            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Diễn biến</span>
                            <span id="replayStepBadge" class="px-2 py-0.5 rounded bg-slate-800 text-sky-300 font-mono text-xs font-bold">Nước: 0 / 0</span>
                        </div>
                        <div id="replayCurrentActionText" class="text-xs text-slate-200 min-h-[36px] flex items-center">
                            Trạng thái ban đầu
                        </div>
                    </div>

                    <div class="grid grid-cols-2 gap-2 text-center text-xs">
                        <div class="p-2.5 rounded-xl bg-sky-950/40 border border-sky-500/30">
                            <span class="text-[10px] text-sky-400 font-bold block mb-1">Quân P1</span>
                            <span id="replayP1Counts" class="font-mono text-white text-xs font-bold">✊6 ✋6 ✌️6</span>
                        </div>
                        <div class="p-2.5 rounded-xl bg-rose-950/40 border border-rose-500/30">
                            <span class="text-[10px] text-rose-400 font-bold block mb-1">Quân P2</span>
                            <span id="replayP2Counts" class="font-mono text-white text-xs font-bold">✊6 ✋6 ✌️6</span>
                        </div>
                    </div>

                    <!-- Fork Button -->
                    <button onclick="ReplayViewer.forkMatchAtCurrentStep()" class="w-full py-2.5 rounded-xl bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 font-bold text-white text-xs shadow-lg transition flex items-center justify-center gap-1.5">
                        <i class="fa-solid fa-code-branch"></i> 🎯 Thử Đi Khác (Vào Web)
                    </button>
                </div>
            </div>

            <!-- Playback Controls -->
            <div class="p-3 bg-slate-900/90 rounded-xl border border-slate-800 flex flex-col gap-2">
                <div class="flex items-center gap-3">
                    <input type="range" id="replayStepSlider" min="0" max="100" value="0" oninput="ReplayViewer.renderStep(parseInt(this.value, 10))" class="flex-1 accent-sky-500 cursor-pointer">
                </div>
                <div class="flex flex-wrap items-center justify-between gap-2 pt-1">
                    <div class="flex items-center gap-1.5">
                        <button onclick="ReplayViewer.first()" class="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold" title="Về đầu"><i class="fa-solid fa-backward-step"></i></button>
                        <button onclick="ReplayViewer.prev()" class="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold" title="Lùi 1 nước"><i class="fa-solid fa-chevron-left"></i></button>
                        <button id="replayPlayBtn" onclick="ReplayViewer.togglePlay()" class="px-4 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold shadow flex items-center gap-1.5"><i class="fa-solid fa-play"></i> Tự Động Phát</button>
                        <button onclick="ReplayViewer.next()" class="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold" title="Tiến 1 nước"><i class="fa-solid fa-chevron-right"></i></button>
                        <button onclick="ReplayViewer.last()" class="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold" title="Đến cuối"><i class="fa-solid fa-forward-step"></i></button>
                    </div>
                    <div class="flex items-center gap-1">
                        <button onclick="ReplayViewer.setSpeed(1200)" class="px-2 py-1 rounded-lg text-xs bg-slate-800 text-slate-300 font-bold hover:bg-slate-700">0.5x</button>
                        <button onclick="ReplayViewer.setSpeed(600)" class="px-2 py-1 rounded-lg text-xs bg-sky-600 text-white font-bold shadow">1x</button>
                        <button onclick="ReplayViewer.setSpeed(300)" class="px-2 py-1 rounded-lg text-xs bg-slate-800 text-slate-300 font-bold hover:bg-slate-700">2x</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="js/rules.js"></script>
    <script src="js/engine.js"></script>
    <script src="js/replay.js"></script>
    <script>
    async function viewReplayDirectly(url) {{
        try {{
            const resp = await fetch(url);
            if (!resp.ok) throw new Error('Không thể tải file replay!');
            const data = await resp.json();
            ReplayViewer.open(data);
        }} catch (e) {{
            alert('Không thể mở replay: ' + e.message);
        }}
    }}
    function exportCurrentReplayFile() {{
        if (ReplayViewer && ReplayViewer.activeReplay) {{
            ReplayManager.exportReplayFile(ReplayViewer.activeReplay);
        }}
    }}
    </script>
</body>
</html>
    """

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"📄 Đã xuất Bảng xếp hạng HTML đẹp mắt: {output_path}")


def run_tournament(bots=None, live=False, delay=0.1, timeout=0.2):
    if not bots:
        bots = find_bots()

    if len(bots) < 2:
        print("❌ Cần ít nhất 2 bot trong thư mục bots/ để tổ chức giải đấu!")
        return

    print("=" * 65)
    print(f"🏁 KHỞI ĐỘNG GIẢI ĐẤU OANTUTI VỚI {len(bots)} BOT:")
    for b in bots:
        print(f"  • {Path(b).stem} ({b})")
    print("=" * 65)

    stats = {Path(b).stem: {"name": Path(b).stem, "played": 0, "won": 0, "drawn": 0, "lost": 0, "points": 0} for b in bots}
    match_results = []

    total_pairs = len(bots) * (len(bots) - 1)
    current_match = 0

    # Đấu vòng tròn 2 lượt (Lượt đi và lượt về đổi bên)
    for i in range(len(bots)):
        for j in range(len(bots)):
            if i == j:
                continue

            b1_path = bots[i]
            b2_path = bots[j]
            b1_name = Path(b1_path).stem
            b2_name = Path(b2_path).stem

            current_match += 1
            room_code = f"TOUR_{current_match}_{b1_name[:3]}_{b2_name[:3]}"
            print(f"\n[Trận {current_match}/{total_pairs}] ⚔️ {b1_name} (P1) vs {b2_name} (P2)...")

            runner = MatchRunner(
                b1_path,
                b2_path,
                room_code=room_code,
                live=live,
                delay=delay if live else 0.0,
                timeout=timeout
            )
            res = runner.run()

            winner = res["winner"]
            stats[b1_name]["played"] += 1
            stats[b2_name]["played"] += 1

            if winner == 1:
                stats[b1_name]["won"] += 1
                stats[b1_name]["points"] += 3
                stats[b2_name]["lost"] += 1
            elif winner == 2:
                stats[b2_name]["won"] += 1
                stats[b2_name]["points"] += 3
                stats[b1_name]["lost"] += 1
            else:
                stats[b1_name]["drawn"] += 1
                stats[b2_name]["drawn"] += 1
                stats[b1_name]["points"] += 1
                stats[b2_name]["points"] += 1

            match_results.append({
                "p1": b1_name,
                "p2": b2_name,
                "winner": winner,
                "winner_name": res["winner_name"],
                "reason": res["reason"],
                "moves": res["moves"],
                "replay_file": res["replay_file"]
            })

    # Xếp hạng theo điểm, sau đó số trận thắng
    standings = sorted(stats.values(), key=lambda s: (s["points"], s["won"]), reverse=True)

    print("\n" + "=" * 65)
    print("🏆 BẢNG XẾP HẠNG CHUNG CUỘC GIẢI ĐẤU:")
    print(f"{'Hạng':<5} {'Tên Bot':<20} {'Trận':<6} {'Thắng':<7} {'Hòa':<6} {'Thua':<6} {'Điểm':<6}")
    print("-" * 65)
    for r, s in enumerate(standings, 1):
        print(f"{r:<5} {s['name']:<20} {s['played']:<6} {s['won']:<7} {s['drawn']:<6} {s['lost']:<6} {s['points']:<6}")
    print("=" * 65)

    generate_leaderboard_html(standings, match_results, output_path="leaderboard.html")


def main():
    parser = argparse.ArgumentParser(description="Chạy giải đấu OanTuTi vòng tròn tự động")
    parser.add_argument("--live", action="store_true", default=False, help="Phát sóng trực tiếp từng trận lên Web qua MQTT")
    parser.add_argument("--delay", type=float, default=0.2, help="Độ trễ mỗi nước khi xem LIVE")
    parser.add_argument("--timeout", type=float, default=0.2, help="Giới hạn thời gian mỗi nước")

    args = parser.parse_args()
    run_tournament(live=args.live, delay=args.delay, timeout=args.timeout)


if __name__ == "__main__":
    main()
