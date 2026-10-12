// ===== PHẦN 4: UI LOBBY & GIAO DIỆN CHÍNH =====
document.getElementById('headerPlayerName').innerText = playerName;

function promptChangePlayerName() {
    const newName = prompt('Nhập tên hiển thị của bạn:', playerName);
    if (newName && newName.trim()) {
        playerName = newName.trim().substring(0, 20);
        localStorage.setItem('ottv2_player_name', playerName);
        document.getElementById('headerPlayerName').innerText = playerName;
    }
}

function switchLobbyTab(tab) {
    const btnRooms = document.getElementById('tabActiveRoomsBtn');
    const btnHistory = document.getElementById('tabMatchHistoryBtn');
    const contentRooms = document.getElementById('tabContentRooms');
    const contentHistory = document.getElementById('tabContentHistory');

    if (tab === 'rooms') {
        btnRooms.className = 'px-4 py-2.5 rounded-xl font-extrabold text-xs md:text-sm transition-all flex items-center gap-2 bg-sky-600 text-white shadow-lg';
        btnHistory.className = 'px-4 py-2.5 rounded-xl font-extrabold text-xs md:text-sm transition-all flex items-center gap-2 bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-750';
        contentRooms.classList.remove('hidden');
        contentHistory.classList.add('hidden');
    } else {
        btnHistory.className = 'px-4 py-2.5 rounded-xl font-extrabold text-xs md:text-sm transition-all flex items-center gap-2 bg-sky-600 text-white shadow-lg';
        btnRooms.className = 'px-4 py-2.5 rounded-xl font-extrabold text-xs md:text-sm transition-all flex items-center gap-2 bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-750';
        contentHistory.classList.remove('hidden');
        contentRooms.classList.add('hidden');
    }
}

function showLobbyView() {
    document.getElementById('lobbyView').classList.remove('hidden');
    document.getElementById('gameView').classList.add('hidden');
    currentRoomCode = null;
    currentRoomData = null;
    isOfflineAI = false;
    subscribeToLobby();
}

function showGameView() {
    document.getElementById('lobbyView').classList.add('hidden');
    document.getElementById('gameView').classList.remove('hidden');
}

function subscribeToLobby() {
    if (window.gameFirebase) {
        window.gameFirebase.subscribeRoomsList(renderRoomsList);
        window.gameFirebase.subscribeHistoryList(renderHistoryList);
    }
}

function refreshRoomList() {
    if (window.gameFirebase) {
        window.gameFirebase.subscribeRoomsList(renderRoomsList);
    }
}

function renderRoomsList(rooms) {
    const activeRooms = rooms.filter(r => r.status === 'waiting' || r.status === 'playing');
    const grid = document.getElementById('roomListGrid');
    const badge = document.getElementById('roomCountBadge');
    badge.innerText = `${activeRooms.length}`;

    if (activeRooms.length === 0) {
        grid.innerHTML = `
        <div class="col-span-full py-12 text-center text-slate-500 text-xs">
            <i class="fa-solid fa-gamepad text-2xl mb-2 block text-slate-600"></i>
            Chưa có phòng nào đang mở. Hãy bấm "Tạo Phòng Mới" để bắt đầu!
        </div>`;
        return;
    }

    grid.innerHTML = activeRooms.map(room => {
        let statusBadge = '';
        let actionBtn = '';

        if (room.isLiveBotArena) {
            statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span> 🔴 LIVE BOT</span>`;
            actionBtn = `<button onclick="spectateSelectedRoom('${room.roomId}')" class="px-3 py-1.5 rounded-xl bg-gradient-to-r from-rose-600 to-purple-600 hover:from-rose-500 hover:to-purple-500 text-white text-xs font-black shadow-lg shadow-rose-600/30 flex items-center gap-1.5 transition-all">
                <i class="fa-solid fa-eye"></i> XEM LIVE
            </button>`;
        } else if (room.status === 'waiting') {
            statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">Đang chờ (1/2)</span>`;
            actionBtn = `
            <div class="flex items-center gap-1.5">
                <button onclick="joinSelectedRoom('${room.roomId}')" class="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold transition-all shadow-md">
                    <i class="fa-solid fa-right-to-bracket mr-1"></i> Tham Gia
                </button>
                <button onclick="spectateSelectedRoom('${room.roomId}')" class="px-2.5 py-1.5 rounded-lg bg-purple-900/60 hover:bg-purple-800 text-purple-200 text-xs font-bold transition-all border border-purple-500/30" title="Xem Bàn Chơi">
                    <i class="fa-solid fa-eye"></i>
                </button>
            </div>`;
        } else if (room.status === 'playing') {
            statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Đang đấu (2/2)</span>`;
            actionBtn = `<button onclick="spectateSelectedRoom('${room.roomId}')" class="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold transition-all shadow-md flex items-center gap-1">
                <i class="fa-solid fa-eye"></i> Xem Trận
            </button>`;
        }

        const borderStyle = room.isLiveBotArena ? 'border-purple-500/50 bg-purple-950/20' : 'border-slate-800';

        return `
        <div class="glass-card p-4 rounded-xl border ${borderStyle} flex flex-col justify-between gap-3 hover:border-slate-700 transition-all">
            <div class="flex items-start justify-between">
                <div>
                    <h4 class="font-bold text-sm text-slate-100 flex items-center gap-1.5">
                        ${room.isLiveBotArena ? '<span class="text-xs">🤖⚔️🤖</span>' : ''} ${room.roomName}
                    </h4>
                    <p class="text-[10px] text-slate-400 font-mono mt-0.5">Mã: ${room.roomId} • Chủ: ${room.hostName}</p>
                </div>
                ${statusBadge}
            </div>

            <div class="flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/80 pt-2">
                <span class="flex items-center gap-1"><i class="fa-solid fa-eye text-amber-400"></i> ${room.spectatorsCount || 0} khán giả</span>
                ${actionBtn}
            </div>
        </div>`;
    }).join('');
}

function renderHistoryList(history) {
    const grid = document.getElementById('matchHistoryGrid');
    const badge = document.getElementById('historyCountBadge');
    badge.innerText = `${history.length}`;

    if (!history || history.length === 0) {
        grid.innerHTML = `
        <div class="col-span-full py-12 text-center text-slate-500 text-xs italic">
            Chưa có trận đấu nào được lưu. Hãy tham gia thi đấu để lưu lịch sử!
        </div>`;
        return;
    }

    grid.innerHTML = history.map(item => {
        let reasonBadge = '';
        if (item.reasonType === 'surrender') {
            reasonBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20"><i class="fa-solid fa-flag"></i> Thắng do Bỏ cuộc</span>`;
        } else if (item.reasonType === 'extinction') {
            reasonBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"><i class="fa-solid fa-skull"></i> Diệt chủng 1 loại quân</span>`;
        } else {
            reasonBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-500/10 text-sky-400 border border-sky-500/20"><i class="fa-solid fa-bullseye"></i> Chiếm thành công Ô Đích</span>`;
        }

        const mins = Math.floor(item.durationSec / 60);
        const secs = item.durationSec % 60;
        const timeStr = mins > 0 ? `${mins} phút ${secs}s` : `${secs} giây`;

        return `
        <div class="glass-card p-4 rounded-xl border border-slate-800 flex flex-col justify-between gap-3">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-1.5 text-xs font-bold text-amber-400">
                    <i class="fa-solid fa-crown text-amber-400"></i> Thắng: ${item.winnerName}
                </div>
                ${reasonBadge}
            </div>

            <div class="text-xs text-slate-300 font-semibold bg-slate-900/80 p-2.5 rounded-lg border border-slate-800/80 flex items-center justify-between">
                <span class="text-sky-300">${item.p1Name} (P1)</span>
                <span class="text-slate-500 font-mono font-normal">VS</span>
                <span class="text-rose-300">${item.p2Name} (P2)</span>
            </div>

            <div class="text-[11px] text-slate-400 leading-tight">
                ${item.reason}
            </div>

            <div class="flex items-center justify-between text-[10px] text-slate-500 border-t border-slate-800/80 pt-2">
                <span><i class="fa-solid fa-shoe-prints mr-1"></i> ${item.totalMoves} nước • ⏱️ ${timeStr}</span>
                <span><i class="fa-regular fa-clock mr-1"></i> ${item.dateStr}</span>
            </div>

            <div class="flex items-center gap-2 pt-1 border-t border-slate-800/60">
                <button onclick="openReplayFromHistory('${item.id}')" class="flex-1 py-1.5 rounded-lg bg-purple-900/60 hover:bg-purple-800 text-purple-200 border border-purple-500/30 text-xs font-bold transition-all shadow flex items-center justify-center gap-1.5">
                    <i class="fa-solid fa-film"></i> Xem Replay
                </button>
                <button onclick="exportReplayFromHistory('${item.id}')" class="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold transition-all shadow" title="Tải File Replay JSON">
                    <i class="fa-solid fa-download"></i>
                </button>
            </div>
        </div>`;
    }).join('');
}

function openCreateRoomModal() {
    document.getElementById('createRoomModal').classList.remove('hidden');
}

function closeCreateRoomModal() {
    document.getElementById('createRoomModal').classList.add('hidden');
}

async function submitCreateRoom() {
    const nameInput = document.getElementById('inputRoomName').value.trim();
    closeCreateRoomModal();

    const initialBoard = createSymmetricalInitialBoard();
    const initialGState = {
        board: initialBoard,
        turn: 1,
        selectedSquare: null,
        validMoves: [],
        moveHistory: [],
        isGameOver: false,
        winner: null,
        winReason: '',
        startTime: Date.now(),
        totalMoves: 0
    };

    try {
        const roomCode = await window.gameFirebase.createRoom(nameInput, initialGState, playerName);
        joinSelectedRoom(roomCode);
    } catch (e) {
        showNotice('Lỗi tạo phòng: ' + e.message);
    }
}

async function quickJoinRoom() {
    if (!window.gameFirebase) return;
    const rooms = Object.values(roomsStore);
    const waiting = rooms.find(r => r.status === 'waiting');
    if (waiting) {
        joinSelectedRoom(waiting.roomId);
    } else {
        showNotice('Không tìm thấy phòng trống. Đang tự động tạo phòng mới!');
        submitCreateRoom();
    }
}

async function joinSelectedRoom(roomCode) {
    try {
        const res = await window.gameFirebase.joinRoom(roomCode, playerName);
        currentRoomCode = roomCode;
        myRole = res.role;
        isOfflineAI = false;

        showGameView();
        listenRoomUpdates(roomCode);
    } catch (e) {
        showNotice(e.message);
    }
}

async function spectateSelectedRoom(roomCode) {
    try {
        const res = await window.gameFirebase.joinRoom(roomCode, playerName);
        currentRoomCode = roomCode;
        myRole = 'spectator';
        isOfflineAI = false;

        showGameView();
        listenRoomUpdates(roomCode);
    } catch (e) {
        showNotice(e.message);
    }
}

function listenRoomUpdates(roomCode) {
    window.gameFirebase.subscribeRoom(roomCode, (roomData) => {
        if (roomData.deleted || roomData.status === 'cancelled') {
            showNotice('Chủ phòng đã rời đi, phòng đã bị hủy.');
            showLobbyView();
            return;
        }

        currentRoomData = roomData;
        gameState = roomData.gameState;

        document.getElementById('roomCodeBadge').innerText = `Phòng: ${roomData.roomId}`;
        document.getElementById('spectatorCountVal').innerText = roomData.spectatorsCount || 0;
        document.getElementById('p1Name').innerText = roomData.hostName || 'Chủ Phòng';
        document.getElementById('p2Name').innerText = roomData.guestName || 'Đang chờ P2...';

        const guestReadyBadge = document.getElementById('p2ReadyBadge');
        if (roomData.guestReady) {
            guestReadyBadge.classList.remove('hidden');
        } else {
            guestReadyBadge.classList.add('hidden');
        }

        const preBanner = document.getElementById('preGameBanner');
        const turnBanner = document.getElementById('turnBanner');
        const btnReady = document.getElementById('btnGuestReady');
        const btnStart = document.getElementById('btnHostStart');
        const specTag = document.getElementById('spectatorModeTag');

        if (myRole === 'spectator') {
            specTag.classList.remove('hidden');
            btnReady.classList.add('hidden');
            btnStart.classList.add('hidden');
        } else {
            specTag.classList.add('hidden');
        }

        if (roomData.status === 'waiting') {
            preBanner.classList.remove('hidden');
            turnBanner.classList.add('hidden');

            if (myRole === 2) {
                btnReady.classList.remove('hidden');
                btnReady.innerText = roomData.guestReady ? 'HỦY SẴN SÀNG' : 'SẴN SÀNG';
                btnReady.className = roomData.guestReady
                    ? 'px-5 py-2 rounded-xl bg-slate-700 hover:bg-slate-600 font-extrabold text-white text-xs shadow-lg transition-all'
                    : 'px-5 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 font-extrabold text-white text-xs shadow-lg transition-all';
            } else {
                btnReady.classList.add('hidden');
            }

            if (myRole === 1) {
                btnStart.classList.remove('hidden');
                btnStart.disabled = !roomData.guestReady;
            } else {
                btnStart.classList.add('hidden');
            }

            document.getElementById('preGameStatusText').innerText = roomData.guestReady
                ? 'Khách (P2) đã Sẵn sàng! Chủ phòng bấm Bắt đầu để bắt đầu ván đấu.'
                : 'Đang chờ Người Chơi 2 bấm Sẵn sàng...';
        } else {
            preBanner.classList.add('hidden');
            turnBanner.classList.remove('hidden');
        }

        if (roomData.lastEmote) {
            showEmoteToast(roomData.lastEmote);
        }

        renderAll();
    });
}

async function toggleGuestReady() {
    if (!currentRoomData || myRole !== 2) return;
    const newReadyState = !currentRoomData.guestReady;
    playReadySound();
    await window.gameFirebase.toggleGuestReady(currentRoomCode, newReadyState);
}

async function startOnlineMatch() {
    if (!currentRoomData || myRole !== 1 || !currentRoomData.guestReady) return;
    playWinSound();
    await window.gameFirebase.startMatch(currentRoomCode);
}

function startOfflineAIMode() {
    isOfflineAI = true;
    myRole = 1;
    aiRole = 2;
    currentRoomCode = null;
    aiDifficulty = document.getElementById('aiDifficultySelect').value || 'medium';

    document.getElementById('p1Name').innerText = playerName;
    document.getElementById('p2Name').innerText = `Máy AI (${aiDifficulty.toUpperCase()})`;
    document.getElementById('roomCodeBadge').innerText = 'Chế độ: Đấu với Máy';

    document.getElementById('preGameBanner').classList.add('hidden');
    document.getElementById('turnBanner').classList.remove('hidden');
    document.getElementById('spectatorModeTag').classList.add('hidden');

    const initialBoard = PureGameEngine.createSymmetricalBoard(window.OTT_RULES);
    currentReplayRecord = ReplayManager.createMatchRecord({
        mode: 'human_vs_ai',
        p1: { name: playerName, type: 'human' },
        p2: { name: `Máy AI (${aiDifficulty.toUpperCase()})`, type: 'bot', strategy: aiDifficulty },
        rules: window.OTT_RULES,
        initialBoard
    });

    gameState = {
        board: PureGameEngine.cloneBoard(initialBoard),
        turn: 1,
        selectedSquare: null,
        validMoves: [],
        moveHistory: [],
        isGameOver: false,
        winner: null,
        winReason: '',
        startTime: Date.now(),
        totalMoves: 0
    };

    showGameView();
    renderAll();
}

function requestExitRoom() {
    if (isBotVsBotMode) {
        stopBotVsBotMatch();
        return;
    }
    if (isOfflineAI || myRole === 'spectator' || gameState.isGameOver || (currentRoomData && currentRoomData.status === 'finished')) {
        leaveRoomDirectly();
        return;
    }

    if (currentRoomData && currentRoomData.status === 'waiting') {
        if (myRole === 1) {
            if (confirm('Bạn là Chủ phòng. Rời phòng sẽ HỦY BÀN CHƠI này. Bạn có chắc không?')) {
                window.gameFirebase.deleteUnstartedRoom(currentRoomCode);
                leaveRoomDirectly();
            }
        } else {
            leaveRoomDirectly();
        }
        return;
    }

    openForfeitModal();
}

function openForfeitModal() {
    document.getElementById('forfeitModal').classList.remove('hidden');
}

function closeForfeitModal() {
    document.getElementById('forfeitModal').classList.add('hidden');
}

function confirmForfeitAndExit() {
    closeForfeitModal();
    if (!gameState.isGameOver && (myRole === 1 || myRole === 2)) {
        const opponentRole = myRole === 1 ? 2 : 1;
        const forfeiterName = myRole === 1 ? (currentRoomData?.hostName || 'P1') : (currentRoomData?.guestName || 'P2');
        const reason = `Đối thủ (${forfeiterName}) đã rời trận / bỏ cuộc giữa chừng!`;

        finishMatch(opponentRole, reason, 'surrender');
        if (currentRoomCode && window.gameFirebase) {
            window.gameFirebase.updateGameState(currentRoomCode, gameState, true);
        }
    }
    leaveRoomDirectly();
}

function leaveRoomDirectly() {
    showLobbyView();
}

window.addEventListener('beforeunload', () => {
    if (currentRoomCode && window.gameFirebase) {
        if (currentRoomData && currentRoomData.status === 'waiting' && myRole === 1) {
            window.gameFirebase.deleteUnstartedRoom(currentRoomCode);
        } else if (!gameState.isGameOver && currentRoomData && currentRoomData.status === 'playing' && (myRole === 1 || myRole === 2)) {
            const opponentRole = myRole === 1 ? 2 : 1;
            const forfeiterName = myRole === 1 ? (currentRoomData?.hostName || 'P1') : (currentRoomData?.guestName || 'P2');
            const reason = `Đối thủ (${forfeiterName}) đã đóng trình duyệt / mất kết nối!`;
            finishMatch(opponentRole, reason, 'surrender');
            window.gameFirebase.updateGameState(currentRoomCode, gameState, true);
        }
    }
});

function sendQuickEmote(msg) {
    if (!isOfflineAI && currentRoomCode && window.gameFirebase) {
        const sName = myRole === 1 ? 'P1' : (myRole === 2 ? 'P2' : 'Khán giả');
        window.gameFirebase.sendEmote(currentRoomCode, sName, msg);
    } else {
        showEmoteToast({ senderName: 'Bạn', msg });
    }
}

function showEmoteToast(eData) {
    const toast = document.getElementById('chatToast');
    document.getElementById('chatToastSender').innerText = `${eData.senderName}:`;
    document.getElementById('chatToastMessage').innerText = eData.msg;

    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 3200);
}

function renderBoard() {
    const gridEl = document.getElementById('boardGrid');
    gridEl.innerHTML = '';

    for (let r = 0; r < 9; r++) {
        for (let c = 0; c < 9; c++) {
            const cell = gameState.board[r][c];
            const cellBtn = document.createElement('button');
            cellBtn.className = 'board-cell relative rounded-lg flex items-center justify-center font-bold transition-all duration-150';

            const isEven = (r + c) % 2 === 0;
            let bgStyle = isEven ? 'bg-slate-900' : 'bg-slate-850';

            if (Math.abs(r - c) <= 1) bgStyle += ' central-diagonal-cell';

            if (r === 8 && c === 0) {
                bgStyle = 'bg-rose-950/70 border-2 border-rose-500/90 shadow-lg shadow-rose-500/20';
                cellBtn.title = 'Ô Nhà P1 • Đích của P2 (Cấm P1 đi vào)';
            }
            if (r === 0 && c === 8) {
                bgStyle = 'bg-sky-950/70 border-2 border-sky-500/90 shadow-lg shadow-sky-500/20';
                cellBtn.title = 'Ô Nhà P2 • Đích của P1 (Cấm P2 đi vào)';
            }

            const isSelected = gameState.selectedSquare && gameState.selectedSquare.r === r && gameState.selectedSquare.c === c;
            if (isSelected) bgStyle += ' ring-2 ring-amber-400 bg-amber-500/20 z-10';

            cellBtn.className += ` ${bgStyle}`;

            const validMove = gameState.validMoves.find(m => (m.to ? (m.to.r === r && m.to.c === c) : (m.r === r && m.c === c)));
            if (validMove) {
                if (validMove.isCapture) {
                    cellBtn.classList.add('capture-target', 'ring-2', 'ring-rose-500', 'bg-rose-500/20', 'z-10');
                } else {
                    const dot = document.createElement('div');
                    dot.className = 'w-3 h-3 md:w-3.5 md:h-3.5 rounded-full bg-emerald-400/80 pulse-valid-move shadow-md shadow-emerald-400/50';
                    cellBtn.appendChild(dot);
                }
            }

            if (!cell) {
                if (r === 8 && c === 0 && !validMove) {
                    const goalBadge = document.createElement('span');
                    goalBadge.className = 'text-[9px] font-black text-rose-400/90 uppercase pointer-events-none';
                    goalBadge.innerText = 'ĐÍCH P2';
                    cellBtn.appendChild(goalBadge);
                }
                if (r === 0 && c === 8 && !validMove) {
                    const goalBadge = document.createElement('span');
                    goalBadge.className = 'text-[9px] font-black text-sky-400/90 uppercase pointer-events-none';
                    goalBadge.innerText = 'ĐÍCH P1';
                    cellBtn.appendChild(goalBadge);
                }
            }

            if (cell) {
                const pieceBadge = document.createElement('div');
                const isP1 = cell.owner === 1;
                const pieceColor = isP1
                    ? 'bg-gradient-to-tr from-sky-600 to-sky-400 border-2 border-sky-300 text-white shadow-md shadow-sky-500/30'
                    : 'bg-gradient-to-tr from-rose-600 to-rose-400 border-2 border-rose-300 text-white shadow-md shadow-rose-500/30';

                pieceBadge.className = `piece-badge w-[86%] h-[86%] rounded-xl flex items-center justify-center font-bold text-base md:text-xl ${pieceColor}`;
                pieceBadge.innerText = PIECE_EMOJIS[cell.type];
                cellBtn.appendChild(pieceBadge);
            }

            cellBtn.onclick = () => handleCellClick(r, c);
            gridEl.appendChild(cellBtn);
        }
    }
}

function updatePieceCounts() {
    const counts = { 1: { R: 0, P: 0, S: 0 }, 2: { R: 0, P: 0, S: 0 } };
    for (let r = 0; r < 9; r++) {
        for (let c = 0; c < 9; c++) {
            const p = gameState.board[r][c];
            if (p) counts[p.owner][p.type]++;
        }
    }
    document.getElementById('p1RockCount').innerText = counts[1].R;
    document.getElementById('p1PaperCount').innerText = counts[1].P;
    document.getElementById('p1ScissorsCount').innerText = counts[1].S;

    document.getElementById('p2RockCount').innerText = counts[2].R;
    document.getElementById('p2PaperCount').innerText = counts[2].P;
    document.getElementById('p2ScissorsCount').innerText = counts[2].S;
}

function renderTurnInfo() {
    const turnDot = document.getElementById('turnDot');
    const turnText = document.getElementById('turnText');

    if (gameState.turn === 1) {
        turnText.innerText = `Lượt đi: ${currentRoomData?.hostName || 'P1'} (Xanh)`;
        turnText.className = 'text-sky-300 font-bold';
        turnDot.className = 'w-3 h-3 rounded-full bg-sky-400 animate-ping';
    } else {
        turnText.innerText = `Lượt đi: ${currentRoomData?.guestName || (isOfflineAI ? 'Máy AI' : 'P2')} (Đỏ)`;
        turnText.className = 'text-rose-300 font-bold';
        turnDot.className = 'w-3 h-3 rounded-full bg-rose-400 animate-ping';
    }
}

function renderMoveHistory() {
    const list = document.getElementById('moveLogList');
    document.getElementById('moveCountText').innerText = `Nước ${gameState.moveHistory.length}`;

    if (gameState.moveHistory.length === 0) {
        list.innerHTML = '<div class="text-center text-slate-500 my-auto py-4 text-xs italic">Bàn cờ đã sẵn sàng!</div>';
        return;
    }

    list.innerHTML = gameState.moveHistory.map((item, idx) => {
        const color = item.turn === 1 ? 'text-sky-400' : 'text-rose-400';
        return `<div class="px-2 py-1 rounded bg-slate-900/60 border border-slate-800/80 flex items-center justify-between">
            <span class="${color} font-bold">${item.text}</span>
            <span class="text-[9px] text-slate-500">#${gameState.moveHistory.length - idx}</span>
        </div>`;
    }).join('');
}

function renderVictoryModal() {
    if (!gameState.isGameOver) return;

    const modal = document.getElementById('victoryModal');
    const title = document.getElementById('victoryTitle');
    const reason = document.getElementById('victoryReason');
    const glow = document.getElementById('victoryGlow');

    if (gameState.winner === 1) {
        const wName = currentRoomData?.hostName || playerName;
        title.innerText = `${wName} CHIẾN THẮNG! 🎉`;
        title.className = 'text-2xl font-black text-sky-400 mb-2';
        glow.className = 'absolute -top-24 left-1/2 -translate-x-1/2 w-48 h-48 bg-sky-500/30 rounded-full blur-3xl pointer-events-none';
    } else {
        const wName = currentRoomData?.guestName || (isOfflineAI ? 'MÁY AI' : 'P2');
        title.innerText = `${wName} CHIẾN THẮNG! 🎉`;
        title.className = 'text-2xl font-black text-rose-400 mb-2';
        glow.className = 'absolute -top-24 left-1/2 -translate-x-1/2 w-48 h-48 bg-rose-500/30 rounded-full blur-3xl pointer-events-none';
    }

    reason.innerText = gameState.winReason;
    modal.classList.remove('hidden');
}

function renderAll() {
    renderBoard();
    updatePieceCounts();
    renderTurnInfo();
    renderMoveHistory();
    if (gameState.isGameOver) renderVictoryModal();
}

function triggerConfetti() {
    const canvas = document.getElementById('confettiCanvas');
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const particles = [];
    const colors = ['#38bdf8', '#f43f5e', '#fbbf24', '#34d399', '#a855f7'];

    for (let i = 0; i < 120; i++) {
        particles.push({
            x: canvas.width / 2,
            y: canvas.height / 2,
            vx: (Math.random() - 0.5) * 16,
            vy: (Math.random() - 0.7) * 16,
            size: Math.random() * 8 + 4,
            color: colors[Math.floor(Math.random() * colors.length)],
            life: 100
        });
    }

    function animateConfetti() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        let alive = false;

        particles.forEach(p => {
            if (p.life > 0) {
                alive = true;
                p.x += p.vx;
                p.y += p.vy;
                p.vy += 0.22;
                p.life -= 1;

                ctx.fillStyle = p.color;
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                ctx.fill();
            }
        });

        if (alive) requestAnimationFrame(animateConfetti);
    }
    animateConfetti();
}

function showNotice(msg) {
    document.getElementById('noticeModalText').innerText = msg;
    document.getElementById('noticeModal').classList.remove('hidden');
}

function closeNoticeModal() {
    document.getElementById('noticeModal').classList.add('hidden');
}

function openRulesModal() { document.getElementById('rulesModal').classList.remove('hidden'); }
function closeRulesModal() { document.getElementById('rulesModal').classList.add('hidden'); }
function closeVictoryModal() { document.getElementById('victoryModal').classList.add('hidden'); }

showLobbyView();

// ===== HELPER FUNCTIONS FOR BOT ARENA & REPLAY VIEWER =====
let selectedInitialBotSpeed = 600;

function openBotArenaModal() {
    const modal = document.getElementById('botArenaModal');
    if (modal) modal.classList.remove('hidden');
}

function closeBotArenaModal() {
    const modal = document.getElementById('botArenaModal');
    if (modal) modal.classList.add('hidden');
}

function selectInitialBotSpeed(speedMs, btnEl) {
    selectedInitialBotSpeed = speedMs;
    document.querySelectorAll('.modal-bot-speed').forEach(btn => {
        btn.className = 'modal-bot-speed px-2 py-1.5 rounded-lg text-xs font-bold bg-slate-800 text-slate-300 hover:bg-slate-700';
    });
    if (btnEl) {
        btnEl.className = 'modal-bot-speed px-2 py-1.5 rounded-lg text-xs font-bold bg-purple-600 text-white shadow';
    }
}

function startBotArenaFromModal() {
    const b1Strategy = document.getElementById('bot1StrategySelect')?.value || 'smart';
    const b2Strategy = document.getElementById('bot2StrategySelect')?.value || 'rusher';
    closeBotArenaModal();
    startBotVsBotMatch({ b1Strategy, b2Strategy, speedMs: selectedInitialBotSpeed });
}

function openReplayFromHistory(matchId) {
    loadHistoryFromStorage();
    const match = matchHistoryStore.find(m => m.id === matchId);
    if (!match) {
        showNotice('Không tìm thấy dữ liệu ván đấu!');
        return;
    }
    if (!match.initialBoard || !match.moves || match.moves.length === 0) {
        showNotice('Ván đấu này không có dữ liệu chi tiết nước đi để xem lại!');
        return;
    }
    ReplayViewer.open(match);
}

function exportReplayFromHistory(matchId) {
    loadHistoryFromStorage();
    const match = matchHistoryStore.find(m => m.id === matchId);
    if (!match) return;
    ReplayManager.exportReplayFile(match);
}

function exportCurrentReplayFile() {
    if (ReplayViewer.activeReplay) {
        ReplayManager.exportReplayFile(ReplayViewer.activeReplay);
    }
}

function downloadCurrentMatchReplay() {
    if (currentReplayRecord) {
        ReplayManager.exportReplayFile(currentReplayRecord);
    } else {
        showNotice('Chưa có dữ liệu Replay cho trận này!');
    }
}

function watchCurrentMatchReplay() {
    closeVictoryModal();
    if (currentReplayRecord) {
        ReplayViewer.open(currentReplayRecord);
    } else {
        showNotice('Chưa có dữ liệu Replay cho trận này!');
    }
}

function triggerUploadReplay() {
    const fileInput = document.getElementById('replayFileInput');
    if (fileInput) fileInput.click();
}

function handleReplayFileSelected(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        const content = e.target.result;
        const parsed = ReplayManager.parseReplayFile(content);
        if (!parsed) {
            showNotice('File Replay không hợp lệ hoặc bị lỗi cấu trúc JSON!');
            return;
        }
        saveMatchRecord(parsed);
        ReplayViewer.open(parsed);
        showNotice(`Đã nạp thành công Replay: ${parsed.p1?.name || 'P1'} vs ${parsed.p2?.name || 'P2'}!`);
    };
    reader.readAsText(file);
    event.target.value = '';
}

// Xử lý nạp Replay từ URL hoặc tiếp tục nhánh thế cờ đã rẽ từ trang khác
window.addEventListener('load', async () => {
    // 1. Kiểm tra có nhánh rẽ ván đấu từ Replay không
    const forkDataStr = sessionStorage.getItem('ottv2_fork_state');
    if (forkDataStr) {
        sessionStorage.removeItem('ottv2_fork_state');
        try {
            const forkData = JSON.parse(forkDataStr);
            if (forkData && forkData.board && typeof startForkedMatch === 'function') {
                setTimeout(() => {
                    startForkedMatch(forkData.board, forkData.turn, forkData.title);
                }, 300);
                return;
            }
        } catch (e) {}
    }

    // 2. Kiểm tra có tham số ?replay=... trên URL không
    const params = new URLSearchParams(window.location.search);
    const replayUrl = params.get('replay');
    if (replayUrl) {
        try {
            const resp = await fetch(replayUrl);
            if (resp.ok) {
                const data = await resp.json();
                setTimeout(() => {
                    ReplayViewer.open(data);
                }, 400);
            }
        } catch (e) {
            console.warn('Lỗi nạp replay từ URL:', e);
        }
    }
});
