/**
 * frontend/js/app.js
 * Điều phối sự kiện người dùng và cập nhật DOM
 */
let cachedBots = [];
let lastReplayUrl = null;

// Chuyển đổi giữa các Tab
function switchTab(tabId) {
    const tabs = ['bots', 'quickMatch', 'tournaments', 'leaderboard'];
    tabs.forEach(t => {
        const view = document.getElementById(`view${t.charAt(0).toUpperCase() + t.slice(1)}`);
        const btn = document.getElementById(`tabBtn${t.charAt(0).toUpperCase() + t.slice(1)}`);
        if (t === tabId) {
            view.classList.remove('hidden');
            btn.className = 'tab-btn px-4 py-2.5 rounded-xl font-bold text-xs md:text-sm transition-all flex items-center gap-2 bg-sky-600 text-white shadow-lg';
        } else {
            view.classList.add('hidden');
            btn.className = 'tab-btn px-4 py-2.5 rounded-xl font-bold text-xs md:text-sm transition-all flex items-center gap-2 bg-slate-800 text-slate-400 hover:text-white';
        }
    });

    if (tabId === 'bots') renderBotsView();
    if (tabId === 'quickMatch') renderQuickMatchView();
    if (tabId === 'tournaments') renderTournamentsView();
    if (tabId === 'leaderboard') renderLeaderboardView();
}

// 1. Phân hệ Bot
async function renderBotsView() {
    const grid = document.getElementById('botsGrid');
    try {
        cachedBots = await API.getBots();
        if (cachedBots.length === 0) {
            grid.innerHTML = '<div class="col-span-full py-8 text-center text-slate-500 text-xs italic">Chưa có bot nào trong cơ sở dữ liệu. Hãy nộp bot đầu tiên!</div>';
            return;
        }

        grid.innerHTML = cachedBots.map(b => `
            <div class="glass-card p-3.5 rounded-xl border border-slate-800 flex flex-col justify-between gap-2.5">
                <div class="flex items-start justify-between">
                    <div>
                        <h4 class="font-bold text-sm text-white flex items-center gap-1.5">
                            <span class="w-2 h-2 rounded-full bg-purple-400"></span> ${b.name}
                        </h4>
                        <p class="text-[10px] text-slate-400 mt-0.5">Tác giả: <strong class="text-slate-300">${b.owner}</strong></p>
                    </div>
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-800 text-sky-300 border border-slate-700">${b.language}</span>
                </div>
                <div class="flex items-center justify-between text-xs pt-2 border-t border-slate-800/80">
                    <span class="text-amber-400 font-extrabold font-mono"><i class="fa-solid fa-fire text-[10px]"></i> Elo: ${b.elo}</span>
                    <button onclick="directMatchWithBot(${b.id})" class="px-2.5 py-1 rounded-lg bg-sky-600/80 hover:bg-sky-500 text-white text-[11px] font-bold transition">
                        Đấu Ngay
                    </button>
                </div>
            </div>
        `).join('');
    } catch (err) {
        grid.innerHTML = `<div class="col-span-full text-center text-rose-400 text-xs py-4">Lỗi: ${err.message}</div>`;
    }
}

async function onUploadBotClick() {
    const fileInput = document.getElementById('uploadFile');
    const usernameInput = document.getElementById('uploadUsername');
    const statusText = document.getElementById('uploadStatusText');

    if (!fileInput.files || fileInput.files.length === 0) {
        alert('Vui lòng chọn một file bot (.py, .cpp, .js)!');
        return;
    }

    statusText.innerText = 'Đang tải lên & biên dịch...';
    statusText.className = 'text-xs font-bold text-sky-400';

    try {
        const data = await API.uploadBot(fileInput.files[0], usernameInput.value.trim());
        statusText.innerText = `✅ ${data.message}`;
        statusText.className = 'text-xs font-bold text-emerald-400';
        fileInput.value = '';
        renderBotsView();
    } catch (err) {
        statusText.innerText = `❌ ${err.message}`;
        statusText.className = 'text-xs font-bold text-rose-400';
    }
}

function directMatchWithBot(botId) {
    switchTab('quickMatch');
    setTimeout(() => {
        document.getElementById('selectBot1').value = botId;
    }, 100);
}

// 2. Phân hệ Đấu Giao Hữu 1v1
async function renderQuickMatchView() {
    if (cachedBots.length === 0) cachedBots = await API.getBots();
    const sel1 = document.getElementById('selectBot1');
    const sel2 = document.getElementById('selectBot2');

    const options = cachedBots.map(b => `<option value="${b.id}">${b.name} (${b.language.toUpperCase()} • Elo: ${b.elo})</option>`).join('');
    sel1.innerHTML = options;
    sel2.innerHTML = options;

    if (cachedBots.length >= 2) sel2.selectedIndex = 1;
}

async function onRunQuickMatchClick() {
    const b1 = document.getElementById('selectBot1').value;
    const b2 = document.getElementById('selectBot2').value;
    const btn = document.getElementById('btnRunQuickMatch');
    const resBox = document.getElementById('quickMatchResultBox');

    if (!b1 || !b2) {
        alert('Vui lòng chọn đủ 2 bot!');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang Đấu...';
    resBox.classList.add('hidden');

    try {
        const data = await API.runQuickMatch(b1, b2);
        lastReplayUrl = data.replay_url;

        document.getElementById('matchWinnerText').innerText = `🏆 Chiến Thắng: ${data.result.winner_name}`;
        document.getElementById('matchReasonText').innerText = data.result.reason;
        document.getElementById('matchMovesBadge').innerText = `${data.result.moves} nước • ⏱️ ${data.result.duration_sec}s`;

        resBox.classList.remove('hidden');
    } catch (err) {
        alert(err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🚀 BẮT ĐẦU TRẬN ĐẤU';
    }
}

async function onOpenQuickMatchReplay() {
    if (!lastReplayUrl) return;
    try {
        const replayData = await API.getReplay(lastReplayUrl);
        ReplayViewer.open(replayData);
    } catch (err) {
        alert(err.message);
    }
}

// 3. Phân hệ Giải Đấu
async function renderTournamentsView() {
    const listEl = document.getElementById('tournamentsList');
    try {
        const tours = await API.getTournaments();
        if (tours.length === 0) {
            listEl.innerHTML = '<div class="text-center text-slate-500 text-xs py-8 italic">Chưa có giải đấu nào được tổ chức.</div>';
            return;
        }

        listEl.innerHTML = tours.map(t => {
            const isDone = t.status === 'completed';
            const statusBadge = isDone
                ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Đã Hoàn Thành</span>'
                : '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">Đang Thi Đấu</span>';

            return `
            <div class="glass-card p-4 rounded-xl border border-slate-800 flex items-center justify-between text-xs hover:border-slate-700 transition">
                <div>
                    <h4 class="font-extrabold text-white text-sm flex items-center gap-2">
                        <i class="fa-solid fa-trophy text-amber-400"></i> ${t.name}
                    </h4>
                    <p class="text-[10px] text-slate-400 mt-0.5">Người tạo: ${t.created_by} • ${t.created_at}</p>
                </div>
                <div class="flex items-center gap-3">
                    ${statusBadge}
                    <button onclick="onViewStandingsClick(${t.id}, '${t.name}')" class="px-3 py-1.5 rounded-lg bg-purple-600/80 hover:bg-purple-500 text-white font-bold text-xs transition">
                        <i class="fa-solid fa-ranking-star mr-1"></i> Bảng Điểm
                    </button>
                </div>
            </div>`;
        }).join('');
    } catch (err) {
        listEl.innerHTML = `<div class="text-center text-rose-400 text-xs py-4">${err.message}</div>`;
    }
}

async function onCreateTournamentClick() {
    const input = document.getElementById('inputTourName');
    const name = input.value.trim();
    if (!name) {
        alert('Vui lòng nhập tên giải đấu!');
        return;
    }
    try {
        const res = await API.createTournament(name);
        alert(res.message);
        input.value = '';
        renderTournamentsView();
    } catch (err) {
        alert(err.message);
    }
}

async function onViewStandingsClick(tourId, tourName) {
    const modal = document.getElementById('standingsModal');
    document.getElementById('standingsModalTitle').innerHTML = `<i class="fa-solid fa-trophy text-amber-400"></i> Bảng Điểm: ${tourName}`;
    const tbody = document.getElementById('standingsTbody');
    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-slate-500 py-6 italic">Đang tải bảng điểm...</td></tr>';
    modal.classList.remove('hidden');

    try {
        const standings = await API.getTournamentStandings(tourId);
        tbody.innerHTML = standings.map((s, idx) => {
            const medal = idx === 0 ? '🥇' : (idx === 1 ? '🥈' : (idx === 2 ? '🥉' : `#${idx + 1}`));
            return `
            <tr class="border-b border-slate-800 hover:bg-slate-800/40 transition">
                <td class="py-2.5 px-3 font-bold text-amber-400">${medal}</td>
                <td class="py-2.5 px-3 font-bold text-white">${s.bot_name}</td>
                <td class="py-2.5 px-3 text-center text-slate-300 font-bold">${s.played}</td>
                <td class="py-2.5 px-3 text-center text-emerald-400 font-bold">${s.won}</td>
                <td class="py-2.5 px-3 text-center text-slate-400">${s.drawn}</td>
                <td class="py-2.5 px-3 text-center text-rose-400">${s.lost}</td>
                <td class="py-2.5 px-3 text-right font-black text-amber-300">${s.points}</td>
            </tr>`;
        }).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-rose-400 py-6">${err.message}</td></tr>`;
    }
}

function closeStandingsModal() {
    document.getElementById('standingsModal').classList.add('hidden');
}

// 4. Phân hệ Bảng Xếp Hạng Elo
async function renderLeaderboardView() {
    const tbody = document.getElementById('leaderboardTbody');
    try {
        const list = await API.getLeaderboard();
        if (list.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-slate-500 py-8 italic">Chưa có dữ liệu xếp hạng.</td></tr>';
            return;
        }

        tbody.innerHTML = list.map(item => {
            const medal = item.rank === 1 ? '🥇' : (item.rank === 2 ? '🥈' : (item.rank === 3 ? '🥉' : `#${item.rank}`));
            return `
            <tr class="border-b border-slate-800 hover:bg-slate-800/40 transition">
                <td class="py-3 px-4 font-black text-amber-400 text-sm">${medal}</td>
                <td class="py-3 px-4 font-bold text-white flex items-center gap-2">
                    <span class="w-2.5 h-2.5 rounded-full bg-purple-400"></span> ${item.bot_name}
                </td>
                <td class="py-3 px-4 text-slate-300">${item.owner}</td>
                <td class="py-3 px-4"><span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-800 text-sky-300">${item.language}</span></td>
                <td class="py-3 px-4 text-right font-mono font-black text-amber-300 text-sm">${item.elo}</td>
            </tr>`;
        }).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-rose-400 py-6">${err.message}</td></tr>`;
    }
}

// Khởi chạy ứng dụng
window.addEventListener('DOMContentLoaded', () => {
    renderBotsView();
});