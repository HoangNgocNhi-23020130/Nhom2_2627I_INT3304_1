/**
 * ===== MODULE: REPLAY SYSTEM & MATCH RECORDER =====
 * Ghi lại đầy đủ toàn bộ ván đấu (chuỗi nước đi + bàn cờ khởi tạo + kết quả)
 * Hỗ trợ xuất/nhập file Replay JSON, trình chiếu từng nước đi và tính năng "Thử đi khác"
 */

const ReplayManager = {
    // Khởi tạo bản ghi Replay cho một ván đấu mới
    createMatchRecord({ mode, p1, p2, rules = window.OTT_RULES, initialBoard }) {
        const id = 'replay_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6);
        const now = new Date();
        const dateStr = `${now.getDate().toString().padStart(2, '0')}/${(now.getMonth() + 1).toString().padStart(2, '0')}/${now.getFullYear()} ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

        return {
            id,
            version: rules.version || window.OTT_RULES_VERSION,
            timestamp: Date.now(),
            dateStr,
            mode: mode || 'human_vs_ai', // 'bot_vs_bot' | 'human_vs_ai' | 'online_pvp'
            rulesName: rules.name,
            rules: JSON.parse(JSON.stringify(rules)),
            p1: {
                name: p1.name || 'Người Chơi 1',
                type: p1.type || 'human', // 'human' | 'bot'
                strategy: p1.strategy || null
            },
            p2: {
                name: p2.name || 'Người Chơi 2',
                type: p2.type || 'human',
                strategy: p2.strategy || null
            },
            initialBoard: PureGameEngine.cloneBoard(initialBoard),
            moves: [],
            result: null
        };
    },

    // Ghi lại 1 nước đi trong ván đấu
    recordMove(record, { step, player, from, to, piece, isCapture, capturedPiece, boardAfter }) {
        if (!record) return;

        record.moves.push({
            step: step || record.moves.length + 1,
            player,
            from: { ...from },
            to: { ...to },
            fromNotation: PureGameEngine.toNotation(from.r, from.c),
            toNotation: PureGameEngine.toNotation(to.r, to.c),
            pieceType: piece.type,
            isCapture: !!isCapture,
            capturedType: capturedPiece ? capturedPiece.type : null,
            capturedOwner: capturedPiece ? capturedPiece.owner : null,
            boardSnapshot: PureGameEngine.cloneBoard(boardAfter)
        });
    },

    // Hoàn tất bản ghi ván đấu khi có kết quả
    finishMatchRecord(record, { winner, winnerName, reason, reasonType, durationSec }) {
        if (!record) return;

        record.result = {
            winner, // 1 | 2 | 0 (hòa)
            winnerName: winnerName || (winner === 1 ? record.p1.name : (winner === 2 ? record.p2.name : 'Hòa')),
            reason,
            reasonType: reasonType || 'base',
            totalMoves: record.moves.length,
            durationSec: durationSec || Math.max(1, Math.floor((Date.now() - record.timestamp) / 1000))
        };

        // Lưu vào hệ thống lưu trữ lịch sử
        if (typeof saveMatchRecord === 'function') {
            saveMatchRecord(record);
        }
    },

    // Tải file Replay JSON về máy tính
    exportReplayFile(record) {
        if (!record) return;
        const jsonStr = JSON.stringify(record, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `OanTuTi_${record.id}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    },

    // Đọc và xác thực cấu trúc file Replay JSON
    parseReplayFile(jsonStr) {
        try {
            const data = JSON.parse(jsonStr);
            if (!data.initialBoard || !Array.isArray(data.moves)) {
                throw new Error('Dữ liệu Replay không đúng cấu trúc bàn cờ!');
            }
            return data;
        } catch (err) {
            console.error('Lỗi phân tích file Replay:', err);
            return null;
        }
    }
};

/**
 * BỘ TRÌNH CHIẾU REPLAY (REPLAY VIEWER CONTROLLER)
 */
const ReplayViewer = {
    activeReplay: null,
    currentStepIndex: 0,
    isPlaying: false,
    playInterval: null,
    playSpeedMs: 700,

    // Mở một bản ghi Replay để xem lại
    open(replayData) {
        if (!replayData || !replayData.initialBoard) return;
        this.activeReplay = replayData;
        this.currentStepIndex = 0;
        this.pause();

        const modal = document.getElementById('replayViewerModal');
        if (modal) modal.classList.remove('hidden');

        // Cập nhật tiêu đề & thông tin ván đấu trong Replay Modal
        const titleEl = document.getElementById('replayTitle');
        const descEl = document.getElementById('replayMeta');
        if (titleEl) {
            const wName = replayData.result?.winnerName || 'Không rõ';
            titleEl.innerHTML = `<span class="text-sky-400">${replayData.p1.name}</span> <span class="text-slate-400">vs</span> <span class="text-rose-400">${replayData.p2.name}</span>`;
        }
        if (descEl) {
            descEl.innerText = `${replayData.dateStr || ''} • Tổng: ${replayData.moves.length} nước đi • Thắng: ${replayData.result?.winnerName || ''} (${replayData.result?.reason || ''})`;
        }

        const slider = document.getElementById('replayStepSlider');
        if (slider) {
            slider.min = 0;
            slider.max = replayData.moves.length;
            slider.value = 0;
        }

        this.renderStep(0);
    },

    close() {
        this.pause();
        this.activeReplay = null;
        const modal = document.getElementById('replayViewerModal');
        if (modal) modal.classList.add('hidden');
    },

    // Lấy trạng thái bàn cờ tại bước `stepIndex` (0 = bàn ban đầu)
    getBoardAtStep(stepIndex) {
        if (!this.activeReplay) return null;
        if (stepIndex === 0) return this.activeReplay.initialBoard;

        const moveItem = this.activeReplay.moves[stepIndex - 1];
        if (moveItem && moveItem.boardSnapshot) {
            return moveItem.boardSnapshot;
        }

        // Tái tạo lại từ đầu nếu thiếu snapshot
        let b = PureGameEngine.cloneBoard(this.activeReplay.initialBoard);
        for (let i = 0; i < stepIndex; i++) {
            const m = this.activeReplay.moves[i];
            const applied = PureGameEngine.applyMove(b, { from: m.from, to: m.to }, this.activeReplay.rules);
            b = applied.newBoard;
        }
        return b;
    },

    // Hiển thị bàn cờ tại bước hiện tại
    renderStep(stepIndex) {
        if (!this.activeReplay) return;
        this.currentStepIndex = Math.max(0, Math.min(stepIndex, this.activeReplay.moves.length));

        const slider = document.getElementById('replayStepSlider');
        if (slider) slider.value = this.currentStepIndex;

        const stepBadge = document.getElementById('replayStepBadge');
        if (stepBadge) {
            stepBadge.innerText = `Nước: ${this.currentStepIndex} / ${this.activeReplay.moves.length}`;
        }

        const actionTextEl = document.getElementById('replayCurrentActionText');
        if (actionTextEl) {
            if (this.currentStepIndex === 0) {
                actionTextEl.innerText = 'Trạng thái khởi đầu trận đấu.';
                actionTextEl.className = 'text-xs text-slate-400 italic';
            } else {
                const curMove = this.activeReplay.moves[this.currentStepIndex - 1];
                const pName = curMove.player === 1 ? this.activeReplay.p1.name : this.activeReplay.p2.name;
                const pColor = curMove.player === 1 ? 'text-sky-400' : 'text-rose-400';
                const emoji = window.OTT_RULES.pieceEmojis[curMove.pieceType] || '';
                const capText = curMove.isCapture ? ` (Ăn ${window.OTT_RULES.pieceEmojis[curMove.capturedType] || ''})` : '';

                actionTextEl.innerHTML = `<span class="${pColor} font-bold">${pName}</span> (${emoji}) đi: <strong>${curMove.fromNotation} ➔ ${curMove.toNotation}</strong>${capText}`;
                actionTextEl.className = 'text-xs text-slate-200';
            }
        }

        // Render bàn cờ Replay
        const board = this.getBoardAtStep(this.currentStepIndex);
        this.renderReplayBoardGrid(board);

        // Cập nhật bộ đếm quân
        const counts = PureGameEngine.countRemainingPieces(board);
        const p1CountsEl = document.getElementById('replayP1Counts');
        const p2CountsEl = document.getElementById('replayP2Counts');
        if (p1CountsEl) p1CountsEl.innerHTML = `✊${counts[1].R} ✋${counts[1].P} ✌️${counts[1].S}`;
        if (p2CountsEl) p2CountsEl.innerHTML = `✊${counts[2].R} ✋${counts[2].P} ✌️${counts[2].S}`;
    },

    renderReplayBoardGrid(board) {
        const gridEl = document.getElementById('replayBoardGrid');
        if (!gridEl) return;
        gridEl.innerHTML = '';

        const size = board.length;
        const curMove = this.currentStepIndex > 0 ? this.activeReplay.moves[this.currentStepIndex - 1] : null;

        for (let r = 0; r < size; r++) {
            for (let c = 0; c < size; c++) {
                const cell = board[r][c];
                const cellDiv = document.createElement('div');
                cellDiv.className = 'board-cell relative rounded-lg flex items-center justify-center font-bold text-xs md:text-sm select-none';

                const isEven = (r + c) % 2 === 0;
                let bgClass = isEven ? 'bg-slate-900/90' : 'bg-slate-900/60';

                // Ô đích
                if (r === 0 && c === 8) {
                    bgClass = 'bg-sky-950/80 border-2 border-dashed border-sky-400/80';
                } else if (r === 8 && c === 0) {
                    bgClass = 'bg-rose-950/80 border-2 border-dashed border-rose-400/80';
                }

                // Đánh dấu ô vừa đi (Highlight move source and dest)
                if (curMove) {
                    if (curMove.from.r === r && curMove.from.c === c) {
                        bgClass += ' ring-2 ring-amber-400/60 bg-amber-950/40';
                    } else if (curMove.to.r === r && curMove.to.c === c) {
                        bgClass += ' ring-2 ring-emerald-400 bg-emerald-950/40';
                    }
                }

                cellDiv.className += ` ${bgClass}`;

                if (cell) {
                    const isP1 = cell.owner === 1;
                    const pieceColor = isP1
                        ? 'bg-gradient-to-tr from-sky-600 to-sky-400 border border-sky-300 text-white shadow-md'
                        : 'bg-gradient-to-tr from-rose-600 to-rose-400 border border-rose-300 text-white shadow-md';

                    const badge = document.createElement('div');
                    badge.className = `w-[84%] h-[84%] rounded-xl flex items-center justify-center font-bold text-sm md:text-lg ${pieceColor}`;
                    badge.innerText = window.OTT_RULES.pieceEmojis[cell.type] || cell.type;
                    cellDiv.appendChild(badge);
                }

                gridEl.appendChild(cellDiv);
            }
        }
    },

    next() {
        if (!this.activeReplay) return;
        if (this.currentStepIndex < this.activeReplay.moves.length) {
            this.renderStep(this.currentStepIndex + 1);
        } else {
            this.pause();
        }
    },

    prev() {
        if (!this.activeReplay) return;
        if (this.currentStepIndex > 0) {
            this.renderStep(this.currentStepIndex - 1);
        }
    },

    first() {
        this.renderStep(0);
    },

    last() {
        if (!this.activeReplay) return;
        this.renderStep(this.activeReplay.moves.length);
    },

    play() {
        if (this.isPlaying || !this.activeReplay) return;
        if (this.currentStepIndex >= this.activeReplay.moves.length) {
            this.currentStepIndex = 0;
        }

        this.isPlaying = true;
        this.updatePlayBtnState();

        this.playInterval = setInterval(() => {
            if (this.currentStepIndex < this.activeReplay.moves.length) {
                this.next();
            } else {
                this.pause();
            }
        }, this.playSpeedMs);
    },

    pause() {
        this.isPlaying = false;
        if (this.playInterval) {
            clearInterval(this.playInterval);
            this.playInterval = null;
        }
        this.updatePlayBtnState();
    },

    togglePlay() {
        if (this.isPlaying) this.pause(); else this.play();
    },

    setSpeed(speedMs) {
        this.playSpeedMs = speedMs;
        if (this.isPlaying) {
            this.pause();
            this.play();
        }
    },

    updatePlayBtnState() {
        const btn = document.getElementById('replayPlayBtn');
        if (!btn) return;
        btn.innerHTML = this.isPlaying
            ? '<i class="fa-solid fa-pause"></i> Tạm Dừng'
            : '<i class="fa-solid fa-play"></i> Tự Động Phát';
    },

    // Tính năng "Thử đi khác" (Fork ván đấu để người chơi tiếp tục chơi từ thế cờ hiện tại)
    forkMatchAtCurrentStep() {
        if (!this.activeReplay) return;
        const currentBoard = this.getBoardAtStep(this.currentStepIndex);
        const nextTurn = (this.currentStepIndex % 2 === 0) ? 1 : 2;

        this.close();

        // Chuyển sang màn hình chơi Offline AI bắt đầu từ thế cờ này
        if (typeof startForkedMatch === 'function') {
            startForkedMatch(currentBoard, nextTurn, `Nhánh từ ván ${this.activeReplay.p1.name} vs ${this.activeReplay.p2.name} (Nước ${this.currentStepIndex})`);
        } else {
            // Nếu đang ở trang khác (như leaderboard.html), lưu vào sessionStorage và chuyển sang index.html
            sessionStorage.setItem('ottv2_fork_state', JSON.stringify({
                board: currentBoard,
                turn: nextTurn,
                title: `Nhánh từ ván ${this.activeReplay.p1.name} vs ${this.activeReplay.p2.name} (Nước ${this.currentStepIndex})`
            }));
            window.location.href = 'index.html';
        }
    }
};

window.ReplayManager = ReplayManager;
window.ReplayViewer = ReplayViewer;
