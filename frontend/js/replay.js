/**
 * frontend/js/replay.js
 * Quản lý Trình diễn bàn cờ 9x9 và Phát lại ván đấu (Replay Player)
 */
const PIECE_EMOJIS = { R: '✊', P: '✋', S: '✌️' };

const ReplayViewer = {
    activeData: null,
    currentStep: 0,
    timer: null,
    speedMs: 600,

    open(data) {
        this.activeData = data;
        this.currentStep = 0;
        this.pause();

        document.getElementById('replayTitle').innerHTML = 
            `<span class="text-sky-400">${data.p1.name}</span> <span class="text-slate-400">vs</span> <span class="text-rose-400">${data.p2.name}</span>`;
        document.getElementById('replayMeta').innerText = 
            `${data.dateStr || ''} • Tổng: ${data.moves.length} nước đi • Thắng: ${data.result?.winnerName || ''} (${data.result?.reason || ''})`;

        const slider = document.getElementById('replayStepSlider');
        slider.min = 0;
        slider.max = data.moves.length;
        slider.value = 0;

        document.getElementById('replayViewerModal').classList.remove('hidden');
        this.renderStep(0);
    },

    close() {
        this.pause();
        document.getElementById('replayViewerModal').classList.add('hidden');
    },

    renderStep(stepIndex) {
        if (!this.activeData) return;
        this.currentStep = Math.max(0, Math.min(stepIndex, this.activeData.moves.length));
        document.getElementById('replayStepSlider').value = this.currentStep;
        document.getElementById('replayStepBadge').innerText = `Nước: ${this.currentStep} / ${this.activeData.moves.length}`;

        const actionTextEl = document.getElementById('replayCurrentActionText');
        if (this.currentStep === 0) {
            actionTextEl.innerText = 'Trạng thái khởi đầu ván đấu.';
            actionTextEl.className = 'text-xs text-slate-400 italic';
        } else {
            const curMove = this.activeData.moves[this.currentStep - 1];
            const pColor = curMove.player === 1 ? 'text-sky-400' : 'text-rose-400';
            const pName = curMove.player === 1 ? this.activeData.p1.name : this.activeData.p2.name;
            const emoji = PIECE_EMOJIS[curMove.pieceType] || '';
            const cap = curMove.isCapture ? ` (Ăn ${PIECE_EMOJIS[curMove.capturedType] || ''})` : '';
            actionTextEl.innerHTML = `<span class="${pColor} font-bold">${pName}</span> (${emoji}) đi: <strong>${curMove.fromNotation} ➔ ${curMove.toNotation}</strong>${cap}`;
            actionTextEl.className = 'text-xs text-slate-200';
        }

        const board = this.currentStep === 0 ? this.activeData.initialBoard : this.activeData.moves[this.currentStep - 1].boardSnapshot;
        this._renderGrid(board, this.currentStep > 0 ? this.activeData.moves[this.currentStep - 1] : null);
        this._updateCounts(board);
    },

    _renderGrid(board, curMove) {
        const grid = document.getElementById('replayBoardGrid');
        grid.innerHTML = '';

        for (let r = 0; r < 9; r++) {
            for (let c = 0; c < 9; c++) {
                const cell = board[r][c];
                const cellDiv = document.createElement('div');
                cellDiv.className = 'board-cell relative rounded-lg flex items-center justify-center font-bold text-xs md:text-sm select-none';

                let bgClass = (r + c) % 2 === 0 ? 'bg-slate-900/90' : 'bg-slate-900/60';
                if (Math.abs(r - c) <= 1) bgClass += ' central-diagonal-cell';

                // Đích
                if (r === 0 && c === 8) bgClass = 'bg-sky-950/80 border-2 border-dashed border-sky-400/80';
                if (r === 8 && c === 0) bgClass = 'bg-rose-950/80 border-2 border-dashed border-rose-400/80';

                // Highlight nước vừa đi
                if (curMove) {
                    if (curMove.from.r === r && curMove.from.c === c) bgClass += ' ring-2 ring-amber-400/60 bg-amber-950/40';
                    if (curMove.to.r === r && curMove.to.c === c) bgClass += ' ring-2 ring-emerald-400 bg-emerald-950/40';
                }

                cellDiv.className += ` ${bgClass}`;

                if (cell) {
                    const pieceColor = cell.owner === 1
                        ? 'bg-gradient-to-tr from-sky-600 to-sky-400 border border-sky-300 text-white shadow-md'
                        : 'bg-gradient-to-tr from-rose-600 to-rose-400 border border-rose-300 text-white shadow-md';
                    cellDiv.innerHTML = `<div class="w-[84%] h-[84%] rounded-xl flex items-center justify-center font-bold text-sm md:text-base ${pieceColor}">${PIECE_EMOJIS[cell.type] || cell.type}</div>`;
                }
                grid.appendChild(cellDiv);
            }
        }
    },

    _updateCounts(board) {
        const counts = { 1: { R: 0, P: 0, S: 0 }, 2: { R: 0, P: 0, S: 0 } };
        for (let r = 0; r < 9; r++) {
            for (let c = 0; c < 9; c++) {
                const p = board[r][c];
                if (p && counts[p.owner]) counts[p.owner][p.type]++;
            }
        }
        document.getElementById('replayP1Counts').innerText = `✊${counts[1].R} ✋${counts[1].P} ✌️${counts[1].S}`;
        document.getElementById('replayP2Counts').innerText = `✊${counts[2].R} ✋${counts[2].P} ✌️${counts[2].S}`;
    },

    next() {
        if (this.activeData && this.currentStep < this.activeData.moves.length) {
            this.renderStep(this.currentStep + 1);
        } else {
            this.pause();
        }
    },
    prev() {
        if (this.activeData && this.currentStep > 0) this.renderStep(this.currentStep - 1);
    },
    first() { this.renderStep(0); },
    last() { if (this.activeData) this.renderStep(this.activeData.moves.length); },

    togglePlay() {
        if (this.timer) this.pause(); else this.play();
    },

    play() {
        if (!this.activeData) return;
        if (this.currentStep >= this.activeData.moves.length) this.currentStep = 0;
        document.getElementById('replayPlayBtn').innerHTML = '<i class="fa-solid fa-pause"></i> Tạm Dừng';
        this.timer = setInterval(() => this.next(), this.speedMs);
    },

    pause() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
        const btn = document.getElementById('replayPlayBtn');
        if (btn) btn.innerHTML = '<i class="fa-solid fa-play"></i> Tự Động Phát';
    },

    setSpeed(ms) {
        this.speedMs = ms;

        document.querySelectorAll('.speed-btn').forEach(btn => {
            btn.className = 'speed-btn px-2 py-1 rounded-lg text-xs bg-slate-800 text-slate-300 hover:bg-slate-700 font-bold transition';
        });

        const activeBtn = document.getElementById(`speedBtn-${ms}`);
        if (activeBtn) {
            activeBtn.className = 'speed-btn px-2 py-1 rounded-lg text-xs bg-sky-600 text-white font-bold shadow transition';
        }

        if (this.timer) {
            this.pause();
            this.play();
        }
    },

    downloadJSON() {
        if (!this.activeData) return;
        const blob = new Blob([JSON.stringify(this.activeData, null, 2)], { type: 'application/json' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `${this.activeData.id}.json`;
        a.click();
    }
};