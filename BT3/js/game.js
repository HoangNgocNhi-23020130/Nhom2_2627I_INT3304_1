// ===== PHẦN 3: BÀN CỜ, QUÂN CỜ & ĐIỀU PHỐI TRẬN ĐẤU (GAME CONTROLLER) =====
const ROCK = 'R';
const PAPER = 'P';
const SCISSORS = 'S';

const PIECE_EMOJIS = window.OTT_RULES ? window.OTT_RULES.pieceEmojis : { R: '✊', P: '✋', S: '✌️' };

let playerName = localStorage.getItem('ottv2_player_name') || `Người chơi ${Math.floor(100 + Math.random() * 899)}`;

let currentRoomData = null;
let currentRoomCode = null;
let myRole = 1; // 1 | 2 | 'spectator'
let aiRole = 2; // Vai trò của AI trong chế độ Offline (mặc định là 2)
let isOfflineAI = false;
let aiDifficulty = 'medium';

// Trạng thái cho chế độ 2 Bot đấu nhau (Khán giả xem trực tiếp)
let isBotVsBotMode = false;
let bot1Strategy = 'smart';
let bot2Strategy = 'rusher';
let botMatchTimer = null;
let botMatchSpeed = 600; // ms per move
let isBotMatchPaused = false;

// Bản ghi Replay cho ván đấu hiện tại
let currentReplayRecord = null;

let gameState = {
    board: Array(9).fill(null).map(() => Array(9).fill(null)),
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

// Cung cấp hàm bọc tương thích với code cũ
function createSymmetricalInitialBoard() {
    return PureGameEngine.createSymmetricalBoard(window.OTT_RULES);
}

function beats(type1, type2) {
    return PureGameEngine.beats(type1, type2, window.OTT_RULES);
}

function calculateValidMoves(r, c, b = gameState.board) {
    return PureGameEngine.getValidMovesForPiece(b, r, c, window.OTT_RULES);
}

function checkVictory(b = gameState.board) {
    return PureGameEngine.checkVictory(b, window.OTT_RULES, gameState.totalMoves);
}

function toNotation(r, c) {
    return PureGameEngine.toNotation(r, c);
}

function handleCellClick(r, c) {
    if (gameState.isGameOver) return;
    if (myRole === 'spectator' || isBotVsBotMode) return;

    if (currentRoomData && currentRoomData.status !== 'playing' && !isOfflineAI) return;
    if (gameState.turn !== myRole && !isOfflineAI) return;
    if (isOfflineAI && gameState.turn === aiRole) return;

    const clickedPiece = gameState.board[r][c];

    if (gameState.selectedSquare) {
        const sr = gameState.selectedSquare.r;
        const sc = gameState.selectedSquare.c;
        const validMove = gameState.validMoves.find(m => (m.to ? (m.to.r === r && m.to.c === c) : (m.r === r && m.c === c)));

        if (validMove) {
            executeMove(sr, sc, r, c, validMove.isCapture, validMove.targetPiece);
            return;
        }
    }

    if (clickedPiece && clickedPiece.owner === gameState.turn) {
        gameState.selectedSquare = { r, c };
        gameState.validMoves = calculateValidMoves(r, c);
        playSelectSound();
        renderBoard();
    } else {
        gameState.selectedSquare = null;
        gameState.validMoves = [];
        renderBoard();
    }
}

function executeMove(fromR, fromC, toR, toC, isCapture, targetPiece = null) {
    const piece = gameState.board[fromR][fromC];
    const destPiece = targetPiece || gameState.board[toR][toC];

    if (isCapture) playCaptureSound(); else playMoveSound();

    // Di chuyển quân
    gameState.board[toR][toC] = piece;
    gameState.board[fromR][fromC] = null;

    gameState.selectedSquare = null;
    gameState.validMoves = [];
    gameState.totalMoves = (gameState.totalMoves || 0) + 1;

    let pName = 'P1';
    if (isBotVsBotMode) {
        pName = piece.owner === 1 ? `Bot 1 (${bot1Strategy.toUpperCase()})` : `Bot 2 (${bot2Strategy.toUpperCase()})`;
    } else {
        pName = piece.owner === 1 ? (currentRoomData?.hostName || playerName) : (currentRoomData?.guestName || (isOfflineAI ? `Máy AI (${aiDifficulty.toUpperCase()})` : 'P2'));
    }

    const pEmoji = PIECE_EMOJIS[piece.type] || piece.type;
    const logMsg = isCapture && destPiece
        ? `${pName} (${pEmoji}) ăn ${PIECE_EMOJIS[destPiece.type] || destPiece.type} tại ${toNotation(toR, toC)}`
        : `${pName} (${pEmoji}) đi ${toNotation(fromR, fromC)} ➔ ${toNotation(toR, toC)}`;

    gameState.moveHistory.unshift({ text: logMsg, turn: gameState.turn });

    // Ghi nước đi vào hệ thống Replay
    if (currentReplayRecord) {
        ReplayManager.recordMove(currentReplayRecord, {
            step: gameState.totalMoves,
            player: piece.owner,
            from: { r: fromR, c: fromC },
            to: { r: toR, c: toC },
            piece,
            isCapture,
            capturedPiece: destPiece,
            boardAfter: gameState.board
        });
    }

    const winRes = checkVictory(gameState.board);
    if (winRes) {
        finishMatch(winRes.winner, winRes.reason, winRes.reasonType);
    } else {
        gameState.turn = gameState.turn === 1 ? 2 : 1;
    }

    renderAll();

    // Đồng bộ phòng trực tuyến nếu có
    if (!isOfflineAI && !isBotVsBotMode && currentRoomCode && window.gameFirebase) {
        window.gameFirebase.updateGameState(currentRoomCode, gameState, gameState.isGameOver);
    }

    // Nếu đang đấu với AI đơn lẻ (P1 là người, P2 là AI, hoặc ngược lại)
    if (isOfflineAI && !isBotVsBotMode && gameState.turn === aiRole && !gameState.isGameOver) {
        setTimeout(makeAIMove, 450);
    }

    // Nếu đang ở chế độ 2 Bot đấu nhau, hẹn giờ thực hiện nước đi tiếp theo
    if (isBotVsBotMode && !gameState.isGameOver && !isBotMatchPaused) {
        scheduleNextBotVsBotMove();
    }
}

function finishMatch(winner, reason, reasonType = 'base') {
    gameState.isGameOver = true;
    gameState.winner = winner;
    gameState.winReason = reason;

    // Dừng timer Bot vs Bot nếu đang chạy
    if (botMatchTimer) {
        clearTimeout(botMatchTimer);
        botMatchTimer = null;
    }

    let p1N = 'P1';
    let p2N = 'P2';

    if (isBotVsBotMode) {
        p1N = `Bot 1 (${bot1Strategy.toUpperCase()})`;
        p2N = `Bot 2 (${bot2Strategy.toUpperCase()})`;
    } else {
        p1N = currentRoomData?.hostName || playerName;
        p2N = currentRoomData?.guestName || (isOfflineAI ? `Máy AI (${aiDifficulty.toUpperCase()})` : 'P2');
    }

    const wName = winner === 1 ? p1N : (winner === 2 ? p2N : 'Hòa');
    const durationSec = Math.max(1, Math.floor((Date.now() - (gameState.startTime || Date.now())) / 1000));

    // Hoàn tất lưu trữ Replay
    if (currentReplayRecord) {
        ReplayManager.finishMatchRecord(currentReplayRecord, {
            winner,
            winnerName: wName,
            reason,
            reasonType,
            durationSec
        });
    } else {
        // Fallback lưu record cũ nếu không có replay tracker
        const now = new Date();
        const dateStr = `${now.getDate().toString().padStart(2, '0')}/${(now.getMonth() + 1).toString().padStart(2, '0')}/${now.getFullYear()} ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
        const record = {
            id: 'match_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6),
            roomCode: currentRoomCode || 'OFFLINE',
            p1Name: p1N,
            p2Name: p2N,
            winner,
            winnerName: wName,
            reason,
            reasonType,
            totalMoves: gameState.totalMoves || gameState.moveHistory.length,
            durationSec,
            dateStr,
            timestamp: Date.now()
        };
        saveMatchRecord(record);
    }

    playWinSound();
    triggerConfetti();
    renderAll();
}

// Bot AI đi quân khi đấu đơn (Người vs Máy)
function makeAIMove() {
    if (gameState.isGameOver || !isOfflineAI || gameState.turn !== aiRole || isBotVsBotMode) return;

    const move = PureGameEngine.getBotMove(gameState.board, aiRole, aiDifficulty, window.OTT_RULES);
    if (move) {
        executeMove(move.from.r, move.from.c, move.to.r, move.to.c, move.isCapture, move.targetPiece);
    } else {
        // AI không còn nước đi hợp lệ -> xử thua
        finishMatch(myRole, `Máy AI không còn nước đi hợp lệ nào!`, 'extinction');
    }
}

// ===== CHẾ ĐỘ 2 BOT ĐẤU NHAU (BOT VS BOT - KHÁN GIẢ XEM TRỰC TIẾP) =====
function startBotVsBotMatch({ b1Strategy = 'smart', b2Strategy = 'rusher', speedMs = 600 }) {
    isBotVsBotMode = true;
    isOfflineAI = false;
    currentRoomCode = null;
    myRole = 'spectator'; // Người dùng đóng vai trò Khán giả xem thi đấu!
    isBotMatchPaused = false;

    bot1Strategy = b1Strategy;
    bot2Strategy = b2Strategy;
    botMatchSpeed = speedMs;

    const b1Name = `Bot 1 (${bot1Strategy.toUpperCase()})`;
    const b2Name = `Bot 2 (${bot2Strategy.toUpperCase()})`;

    const initialBoard = PureGameEngine.createSymmetricalBoard(window.OTT_RULES);

    // Khởi tạo bản ghi Replay đầy đủ
    currentReplayRecord = ReplayManager.createMatchRecord({
        mode: 'bot_vs_bot',
        p1: { name: b1Name, type: 'bot', strategy: bot1Strategy },
        p2: { name: b2Name, type: 'bot', strategy: bot2Strategy },
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

    // Cập nhật UI
    document.getElementById('p1Name').innerText = b1Name;
    document.getElementById('p2Name').innerText = b2Name;
    document.getElementById('roomCodeBadge').innerText = 'Chế độ: 🤖 2 Bot Đấu Nhau';

    document.getElementById('preGameBanner').classList.add('hidden');
    document.getElementById('turnBanner').classList.remove('hidden');
    document.getElementById('spectatorModeTag').classList.remove('hidden');
    document.getElementById('spectatorModeTag').innerText = '👀 Khán Giả Xem 2 Bot';

    showGameView();
    renderAll();

    // Hiển thị thanh công cụ điều khiển Bot Match
    const botControlBar = document.getElementById('botMatchControlBar');
    if (botControlBar) botControlBar.classList.remove('hidden');

    // Bắt đầu nhịp đi đầu tiên
    scheduleNextBotVsBotMove(700);
}

function scheduleNextBotVsBotMove(delay = botMatchSpeed) {
    if (botMatchTimer) clearTimeout(botMatchTimer);
    botMatchTimer = setTimeout(stepBotVsBot, delay);
}

function stepBotVsBot() {
    if (gameState.isGameOver || !isBotVsBotMode || isBotMatchPaused) return;

    const currentStrat = gameState.turn === 1 ? bot1Strategy : bot2Strategy;
    const move = PureGameEngine.getBotMove(gameState.board, gameState.turn, currentStrat, window.OTT_RULES);

    if (move) {
        executeMove(move.from.r, move.from.c, move.to.r, move.to.c, move.isCapture, move.targetPiece);
    } else {
        // Nếu không còn nước đi hợp lệ -> xử thua
        const opp = gameState.turn === 1 ? 2 : 1;
        finishMatch(opp, `Người chơi ${gameState.turn} không còn nước đi hợp lệ nào!`, 'extinction');
    }
}

function togglePauseBotVsBot() {
    if (!isBotVsBotMode || gameState.isGameOver) return;
    isBotMatchPaused = !isBotMatchPaused;

    const btn = document.getElementById('btnPauseBotMatch');
    if (btn) {
        btn.innerHTML = isBotMatchPaused
            ? '<i class="fa-solid fa-play"></i> Tiếp Tục'
            : '<i class="fa-solid fa-pause"></i> Tạm Dừng';
    }

    if (!isBotMatchPaused) {
        scheduleNextBotVsBotMove(300);
    }
}

function setBotVsBotSpeed(speedMs) {
    botMatchSpeed = speedMs;
    // Cập nhật giao diện nút tốc độ
    document.querySelectorAll('.bot-speed-btn').forEach(btn => {
        if (parseInt(btn.dataset.speed, 10) === speedMs) {
            btn.className = 'bot-speed-btn px-2.5 py-1 rounded-lg text-xs font-bold bg-purple-600 text-white shadow';
        } else {
            btn.className = 'bot-speed-btn px-2.5 py-1 rounded-lg text-xs font-bold bg-slate-800 text-slate-400 hover:text-white';
        }
    });
}

function stopBotVsBotMatch() {
    if (botMatchTimer) {
        clearTimeout(botMatchTimer);
        botMatchTimer = null;
    }
    isBotVsBotMode = false;
    isBotMatchPaused = false;

    const botControlBar = document.getElementById('botMatchControlBar');
    if (botControlBar) botControlBar.classList.add('hidden');

    showLobbyView();
}

// Bắt đầu ván đấu từ một thế cờ Replay ("Thử đi khác")
function startForkedMatch(customBoard, turn, title = 'Nhánh ván mới') {
    isOfflineAI = true;
    isBotVsBotMode = false;
    currentRoomCode = null;
    myRole = turn; // Người chơi nhận vai trò của bên đang tới lượt đi
    aiRole = (turn === 1) ? 2 : 1; // AI nhận vai trò của bên đối thủ

    if (myRole === 1) {
        document.getElementById('p1Name').innerText = `${playerName} (Người chơi 1)`;
        document.getElementById('p2Name').innerText = `Máy AI (${aiDifficulty.toUpperCase()})`;
    } else {
        document.getElementById('p1Name').innerText = `Máy AI (${aiDifficulty.toUpperCase()})`;
        document.getElementById('p2Name').innerText = `${playerName} (Người chơi 2)`;
    }
    document.getElementById('roomCodeBadge').innerText = title;

    document.getElementById('preGameBanner').classList.add('hidden');
    document.getElementById('turnBanner').classList.remove('hidden');
    document.getElementById('spectatorModeTag').classList.add('hidden');

    const cloned = PureGameEngine.cloneBoard(customBoard);
    currentReplayRecord = ReplayManager.createMatchRecord({
        mode: 'forked_match',
        p1: { name: (myRole === 1 ? playerName : `Máy AI (${aiDifficulty.toUpperCase()})`), type: (myRole === 1 ? 'human' : 'bot') },
        p2: { name: (myRole === 2 ? playerName : `Máy AI (${aiDifficulty.toUpperCase()})`), type: (myRole === 2 ? 'human' : 'bot') },
        rules: window.OTT_RULES,
        initialBoard: cloned
    });

    gameState = {
        board: cloned,
        turn,
        selectedSquare: null,
        validMoves: [],
        moveHistory: [{ text: `Bắt đầu thế cờ mới từ Replay. Lượt: P${turn}`, turn }],
        isGameOver: false,
        winner: null,
        winReason: '',
        startTime: Date.now(),
        totalMoves: 0
    };

    showGameView();
    renderAll();

    if (turn === aiRole) {
        setTimeout(makeAIMove, 600);
    }
}
