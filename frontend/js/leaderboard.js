const GLOBAL_LB_CACHE = new Map();

function formatRankBadge(tierKey, tierName) {
    switch ((tierKey || '').toLowerCase()) {
        case 'legend':
            return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider bg-rose-500/15 text-rose-300 border border-rose-500/40 shadow-sm shadow-rose-500/20"><i class="fa-solid fa-crown text-rose-400"></i> ${tierName || 'Legend'}</span>`;
        case 'gold':
            return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider bg-amber-500/15 text-amber-300 border border-amber-500/40 shadow-sm shadow-amber-500/20"><i class="fa-solid fa-trophy text-amber-400"></i> ${tierName || 'Gold'}</span>`;
        case 'silver':
            return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider bg-slate-500/15 text-slate-200 border border-slate-500/40"><i class="fa-solid fa-shield text-slate-300"></i> ${tierName || 'Silver'}</span>`;
        case 'bronze':
            return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider bg-amber-900/25 text-amber-500 border border-amber-800/40"><i class="fa-solid fa-shield-halved text-amber-600"></i> ${tierName || 'Bronze'}</span>`;
        default:
            return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider bg-yellow-950/40 text-amber-700 border border-yellow-900/50"><i class="fa-solid fa-tree text-amber-800"></i> ${tierName || 'Wood'}</span>`;
    }
}

class LeaderboardComponent {
    constructor(containerId) {
        this.containerId = typeof containerId === 'string' ? containerId : containerId.id;
        this.container = typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
        if (!this.container) return;

        this.filter = 'all';
        this.tournaments = [];
        this.seasons = [];
        this.selectedTourId = null;
        this.selectedSeasonId = null;
        this.currentUser = null;
        this.fullDataList = [];
        this.currentPage = 1;
        this.pageSize = 8;

        this.renderLayout();
        this.bindEvents();
        this.init();
    }

    async init() {
        this.currentUser = window.currentUser || null;
        if (!this.currentUser) {
            try {
                this.currentUser = await API.getMe();
                window.currentUser = this.currentUser;
                if (this.currentUser?.username) {
                    localStorage.setItem('ott_username', this.currentUser.username);
                }
            } catch (e) {
                const savedName = localStorage.getItem('ott_username');
                if (savedName) {
                    this.currentUser = { username: savedName, role: 'player' };
                }
            }
        }

        try {
            const seasonList = await API.getSeasons();
            this.seasons = seasonList || [];
            const seasonSelect = this.container.querySelector('.lb-season-select');
            if (seasonSelect && this.seasons.length > 0) {
                seasonSelect.innerHTML = this.seasons.map(s =>
                    `<option value="${s.id}" ${s.status === 'active' ? 'selected' : ''}>${s.name} ${s.status === 'active' ? '(Hiện tại)' : ''}</option>`
                ).join('');
                const activeS = this.seasons.find(s => s.status === 'active') || this.seasons[0];
                this.selectedSeasonId = activeS ? activeS.id : null;
            }
        } catch (e) {}

        await this.syncTournamentsForSeason();
        this.applySeasonRestrictions();
        await this.load();
    }

    renderLayout() {
        this.container.innerHTML = `
            <div class="glass-panel p-5 rounded-2xl border border-slate-800 shadow-xl space-y-4">
                <div class="space-y-3 pb-3 border-b border-slate-800">
                    <div>
                        <h2 class="text-base font-extrabold text-white flex items-center gap-2">
                            <i class="fa-solid fa-ranking-star text-amber-400"></i> Bảng xếp hạng
                        </h2>
                    </div>

                    <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
                        <div class="flex items-center gap-2">
                            <span class="text-slate-400 font-bold whitespace-nowrap">Mùa:</span>
                            <select class="lb-season-select bg-slate-900 border border-slate-700 hover:border-amber-500/50 rounded-lg px-3 py-1.5 text-amber-300 font-bold text-xs focus:outline-none focus:border-amber-400 cursor-pointer transition"></select>
                        </div>

                        <div class="flex flex-wrap items-center gap-2">
                            <button data-filter="all" class="lb-tab-btn px-3 py-1.5 rounded-lg font-bold bg-sky-600 text-white shadow-md shadow-sky-600/30 transition">Tất cả</button>
                            <button data-filter="week" class="lb-tab-btn px-3 py-1.5 rounded-lg font-bold bg-slate-800 text-slate-400 hover:text-white transition">Theo tuần</button>
                            <button data-filter="month" class="lb-tab-btn px-3 py-1.5 rounded-lg font-bold bg-slate-800 text-slate-400 hover:text-white transition">Theo tháng</button>
                            <button data-filter="tournament" class="lb-tab-btn px-3 py-1.5 rounded-lg font-bold bg-slate-800 text-slate-400 hover:text-white transition">Theo giải</button>
                            
                            <select class="lb-tour-select w-36 bg-slate-950/30 border border-slate-800/40 rounded-lg px-2.5 py-1 text-transparent font-bold text-xs pointer-events-none select-none cursor-default transition-all duration-150" style="color: transparent;"></select>
                        </div>
                    </div>
                </div>

                <div class="overflow-x-auto rounded-xl border border-slate-800/80 min-h-[380px] bg-slate-950/40">
                    <table class="w-full min-w-[650px] table-fixed text-left text-xs">
                        <thead class="lb-thead"></thead>
                        <tbody class="lb-tbody transition-opacity duration-150"></tbody>
                    </table>
                </div>

                <div class="lb-pagination-container flex justify-center pt-1 min-h-[32px]"></div>
                <div class="lb-user-banner hidden pt-1"></div>
            </div>
        `;
    }

    bindEvents() {
        const filterBtns = this.container.querySelectorAll('.lb-tab-btn');
        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                if (btn.disabled || btn.classList.contains('pointer-events-none')) return;
                const type = btn.getAttribute('data-filter');
                this.changeFilter(type);
            });
        });

        const seasonSelect = this.container.querySelector('.lb-season-select');
        seasonSelect.addEventListener('change', async (e) => {
            this.selectedSeasonId = parseInt(e.target.value, 10);
            this.currentPage = 1;

            await this.syncTournamentsForSeason();
            this.applySeasonRestrictions();

            const tbody = this.container.querySelector('.lb-tbody');
            if (tbody) tbody.classList.add('opacity-30');
            await new Promise(r => setTimeout(r, 120));

            await this.load();
            if (tbody) tbody.classList.remove('opacity-30');
        });

        const tourSelect = this.container.querySelector('.lb-tour-select');
        tourSelect.addEventListener('change', async (e) => {
            this.selectedTourId = e.target.value;
            this.currentPage = 1;
            const tbody = this.container.querySelector('.lb-tbody');
            if (tbody) tbody.classList.add('opacity-30');
            await new Promise(r => setTimeout(r, 120));
            await this.load();
            if (tbody) tbody.classList.remove('opacity-30');
        });
    }

    async syncTournamentsForSeason() {
        try {
            const tours = await API.getTournaments(false, this.selectedSeasonId);
            this.tournaments = tours || [];
            const tourSelect = this.container.querySelector('.lb-tour-select');
            if (tourSelect) {
                if (this.tournaments.length > 0) {
                    tourSelect.innerHTML = this.tournaments.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
                    this.selectedTourId = this.tournaments[0].id;
                } else {
                    tourSelect.innerHTML = '<option value="">Không có giải</option>';
                    this.selectedTourId = null;
                }
            }
        } catch (e) {}
    }

    applySeasonRestrictions() {
        const currentSeasonObj = this.seasons.find(s => s.id === this.selectedSeasonId);
        const isActive = currentSeasonObj ? currentSeasonObj.status === 'active' : true;

        const weekBtn = this.container.querySelector('button[data-filter="week"]');
        const monthBtn = this.container.querySelector('button[data-filter="month"]');

        if (!isActive) {
            [weekBtn, monthBtn].forEach(btn => {
                if (btn) {
                    btn.disabled = true;
                    btn.className = 'lb-tab-btn px-3 py-1.5 rounded-lg font-bold bg-slate-900/60 text-slate-600 border border-slate-800/40 opacity-40 cursor-not-allowed pointer-events-none transition';
                }
            });

            if (this.filter === 'week' || this.filter === 'month') {
                this.filter = 'all';
                this.updateTabButtonsUi('all');
            }
        } else {
            [weekBtn, monthBtn].forEach(btn => {
                if (btn) {
                    btn.disabled = false;
                    const isCurrent = btn.getAttribute('data-filter') === this.filter;
                    btn.className = isCurrent
                        ? 'lb-tab-btn px-3 py-1.5 rounded-lg font-bold bg-sky-600 text-white shadow-md shadow-sky-600/30 transition'
                        : 'lb-tab-btn px-3 py-1.5 rounded-lg font-bold bg-slate-800 text-slate-400 hover:text-white transition';
                }
            });
        }
    }

    updateTabButtonsUi(selectedType) {
        const filterBtns = this.container.querySelectorAll('.lb-tab-btn');
        filterBtns.forEach(b => {
            if (b.disabled) return;
            const isActive = b.getAttribute('data-filter') === selectedType;
            b.className = isActive
                ? 'lb-tab-btn px-3 py-1.5 rounded-lg font-bold bg-sky-600 text-white shadow-md shadow-sky-600/30 transition'
                : 'lb-tab-btn px-3 py-1.5 rounded-lg font-bold bg-slate-800 text-slate-400 hover:text-white transition';
        });

        const tourSelect = this.container.querySelector('.lb-tour-select');
        if (selectedType === 'tournament') {
            tourSelect.disabled = false;
            tourSelect.style.color = '';
            tourSelect.className = 'lb-tour-select w-36 bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1 text-white font-bold text-xs focus:outline-none focus:border-amber-400 cursor-pointer transition-all duration-150';
        } else {
            tourSelect.disabled = true;
            tourSelect.style.color = 'transparent';
            tourSelect.className = 'lb-tour-select w-36 bg-slate-950/30 border border-slate-800/40 rounded-lg px-2.5 py-1 text-transparent font-bold text-xs pointer-events-none select-none cursor-default transition-all duration-150';
        }
    }

    async changeFilter(type) {
        if (this.filter === type && type !== 'tournament') return;
        this.filter = type;
        this.currentPage = 1;

        this.updateTabButtonsUi(type);

        const tbody = this.container.querySelector('.lb-tbody');
        if (tbody) tbody.classList.add('opacity-30');
        await new Promise(r => setTimeout(r, 120));

        await this.load();
        if (tbody) tbody.classList.remove('opacity-30');
    }

    async load() {
        const tbody = this.container.querySelector('.lb-tbody');
        try {
            const tourId = this.filter === 'tournament' ? this.selectedTourId : null;
            const list = await API.getLeaderboard(this.filter, tourId, this.selectedSeasonId);
            this.renderFullData(list);
        } catch (err) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="${this.filter === 'tournament' ? 5 : 6}" class="text-center py-24 text-rose-400 font-semibold">${err.message || 'Lỗi nạp bảng xếp hạng'}</td></tr>`;
        }
    }

    renderFullData(list) {
        this.fullDataList = list || [];
        this.renderCurrentPage();
    }

    async goToPage(pageNum) {
        if (this.currentPage === pageNum) return;
        this.currentPage = pageNum;
        const tbody = this.container.querySelector('.lb-tbody');
        if (tbody) tbody.classList.add('opacity-30');
        await new Promise(r => setTimeout(r, 120));
        this.renderCurrentPage();
        if (tbody) tbody.classList.remove('opacity-30');
    }

    renderUserBanner(myRow, myPage) {
        const bannerEl = this.container.querySelector('.lb-user-banner');
        if (!bannerEl) return;

        const currentUsername = this.currentUser?.username || localStorage.getItem('ott_username');
        if (!currentUsername || this.currentUser?.role === 'admin') {
            bannerEl.classList.add('hidden');
            return;
        }

        bannerEl.classList.remove('hidden');

        if (!myRow) {
            bannerEl.innerHTML = `
                <div class="px-3.5 py-2.5 rounded-xl bg-slate-900/40 border border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
                    <div class="flex items-center gap-2">
                        <span class="w-1.5 h-1.5 rounded-full bg-slate-500"></span>
                        <span>Người chơi <strong class="text-slate-200">${currentUsername}</strong> chưa có điểm ghi nhận trong kỳ này.</span>
                    </div>
                    <span class="text-[11px] font-mono text-slate-400">Elo hiện tại: <strong class="text-slate-300 font-bold">${this.currentUser?.elo || 0}</strong></span>
                </div>
            `;
            return;
        }

        const jumpButtonHtml = (myPage && myPage !== this.currentPage)
            ? `<button onclick="Leaderboard.instances['${this.containerId}'].goToPage(${myPage})" class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-[11px] transition border border-slate-700/60 flex items-center gap-1.5 whitespace-nowrap">
                   <i class="fa-solid fa-crosshairs text-[10px] text-emerald-400"></i> Xem dòng của bạn (Trang ${myPage})
               </button>`
            : '';

        const isTournament = this.filter === 'tournament';
        const hasSpecialDetail = myRow.detail && myRow.detail !== '-' && myRow.detail !== 'Elo cá nhân';
        const detailSnippet = hasSpecialDetail ? `<span class="text-slate-400 mr-2">${myRow.detail} •</span>` : '';
        const tierBadgeHtml = (!isTournament && myRow.tier) ? `<div>${formatRankBadge(myRow.tier.key, myRow.tier.name)}</div>` : '';

        bannerEl.innerHTML = `
            <div class="px-4 py-2.5 rounded-xl bg-slate-900/60 border border-emerald-500/20 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-300">
                <div class="flex items-center gap-3">
                    <span class="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 font-mono font-bold text-xs">
                        #${myRow.rank}
                    </span>
                    ${tierBadgeHtml}
                    <div class="flex items-center gap-1.5">
                        <span class="font-bold text-slate-200">${myRow.player_name || currentUsername}</span>
                        <span class="px-1.5 py-0.2 text-[9px] font-bold bg-emerald-500/15 text-emerald-400/90 rounded border border-emerald-500/25">BẠN</span>
                    </div>
                    <span class="text-slate-600 hidden sm:inline">•</span>
                    <span class="text-slate-400 text-[11px] hidden sm:inline">Bot: <strong class="text-slate-300 font-medium">${myRow.bot_name || 'Chưa chọn'}</strong> <span class="text-slate-500">(${(myRow.language || 'N/A').toUpperCase()})</span></span>
                </div>

                <div class="flex items-center gap-4">
                    <div class="font-mono text-[11px]">
                        ${detailSnippet}
                        <span class="text-amber-400/90 font-bold">${myRow.score_label}</span>
                    </div>
                    ${jumpButtonHtml}
                </div>
            </div>
        `;
    }

    renderCurrentPage() {
        const thead = this.container.querySelector('.lb-thead');
        const tbody = this.container.querySelector('.lb-tbody');
        const paginationContainer = this.container.querySelector('.lb-pagination-container');
        if (!tbody) return;

        const isTournament = this.filter === 'tournament';

        if (thead) {
            if (isTournament) {
                thead.innerHTML = `
                    <tr class="border-b border-slate-800 text-slate-400 uppercase text-[10px] bg-slate-900/60 select-none">
                        <th class="py-2.5 px-3 w-16 text-center">Hạng</th>
                        <th class="py-2.5 px-4 w-[34%]">Người Chơi</th>
                        <th class="py-2.5 px-4 w-[34%]">Bot Thi Đấu</th>
                        <th class="py-2.5 px-3 w-20 text-center">Ngôn Ngữ</th>
                        <th class="py-2.5 px-4 w-32 text-right">Điểm Số</th>
                    </tr>
                `;
            } else {
                thead.innerHTML = `
                    <tr class="border-b border-slate-800 text-slate-400 uppercase text-[10px] bg-slate-900/60 select-none">
                        <th class="py-2.5 px-3 w-14 text-center">Hạng</th>
                        <th class="py-2.5 px-3 w-28 text-center">Bậc Rank</th>
                        <th class="py-2.5 px-4 w-[28%]">Người Chơi</th>
                        <th class="py-2.5 px-4 w-[28%]">Bot Thi Đấu</th>
                        <th class="py-2.5 px-3 w-20 text-center">Ngôn Ngữ</th>
                        <th class="py-2.5 px-4 w-28 text-right">Điểm / Elo</th>
                    </tr>
                `;
            }
        }

        const totalCols = isTournament ? 5 : 6;

        if (this.fullDataList.length === 0) {
            tbody.innerHTML = `<tr><td colspan="${totalCols}" class="text-center py-24 text-slate-500 italic">Không có dữ liệu trong mùa hoặc khoảng thời gian này.</td></tr>`;
            if (paginationContainer) paginationContainer.innerHTML = '';
            this.renderUserBanner(null, null);
            return;
        }

        const myUsername = (this.currentUser?.username || localStorage.getItem('ott_username') || '').trim().toLowerCase();
        const myUserId = this.currentUser?.id;
        const myBotNames = window.myBotNames || new Set();

        let myRow = null;
        let myRowIndex = -1;

        this.fullDataList.forEach((item, idx) => {
            const pName = (item.player_name || item.owner || item.username || item.user || '').trim().toLowerCase();
            const bName = (item.bot_name || item.name || '').trim().toLowerCase();
            const uId = item.user_id || item.owner_id;

            let matches = false;
            if (myUserId && uId && uId === myUserId) matches = true;
            if (!matches && myUsername && pName && pName === myUsername) matches = true;
            if (!matches && bName && myBotNames.has(bName)) matches = true;

            if (matches && myRowIndex === -1) {
                myRow = item;
                myRowIndex = idx;
            }
        });

        const myPage = myRowIndex >= 0 ? Math.floor(myRowIndex / this.pageSize) + 1 : null;
        this.renderUserBanner(myRow, myPage);

        const totalPages = Math.ceil(this.fullDataList.length / this.pageSize) || 1;
        if (this.currentPage > totalPages) this.currentPage = totalPages;
        if (this.currentPage < 1) this.currentPage = 1;

        const startIdx = (this.currentPage - 1) * this.pageSize;
        const pageItems = this.fullDataList.slice(startIdx, startIdx + this.pageSize);

        tbody.innerHTML = pageItems.map(item => {
            const playerName = item.player_name || item.owner || item.username || item.user || 'Ẩn danh';
            const botName = item.bot_name || item.name || '<span class="text-slate-500 italic">Chưa chọn</span>';
            const lang = (item.language || 'N/A').toUpperCase();
            const detail = item.detail || '';
            const score = item.score_label || item.elo || '0';
            const tierBadge = isTournament ? '' : `<td class="py-2.5 px-3 text-center">${formatRankBadge(item.tier?.key, item.tier?.name)}</td>`;

            const pNameLower = playerName.trim().toLowerCase();
            const bNameLower = (item.bot_name || item.name || '').trim().toLowerCase();
            const uId = item.user_id || item.owner_id;

            let isMe = false;
            if (myUserId && uId && uId === myUserId) isMe = true;
            if (!isMe && myUsername && pNameLower && pNameLower === myUsername) isMe = true;
            if (!isMe && bNameLower && myBotNames.has(bNameLower)) isMe = true;

            let rankBadge = `<span class="font-bold text-slate-400">#${item.rank}</span>`;
            if (item.rank === 1) {
                rankBadge = `<span class="font-black text-amber-300 inline-flex items-center gap-1"><i class="fa-solid fa-medal text-amber-400 text-sm"></i> #1</span>`;
            } else if (item.rank === 2) {
                rankBadge = `<span class="font-black text-slate-200 inline-flex items-center gap-1"><i class="fa-solid fa-medal text-slate-300 text-sm"></i> #2</span>`;
            } else if (item.rank === 3) {
                rankBadge = `<span class="font-black text-amber-600 inline-flex items-center gap-1"><i class="fa-solid fa-medal text-amber-600 text-sm"></i> #3</span>`;
            }

            const hasSpecialDetail = detail && detail !== '-' && detail !== 'Elo cá nhân';
            const detailSubtext = hasSpecialDetail
                ? `<div class="text-[10px] text-slate-400 font-mono mt-0.5">${detail}</div>`
                : '';

            if (isMe) {
                return `
                <tr class="border-b border-slate-800/80 border-l-2 border-l-emerald-400/80 bg-emerald-950/20 hover:bg-emerald-950/30 transition">
                    <td class="py-2.5 px-3 text-center">${rankBadge}</td>
                    ${tierBadge}
                    <td class="py-2.5 px-4 truncate">
                        <div class="flex items-center gap-1.5 truncate">
                            <span class="font-bold text-emerald-300 truncate">${playerName}</span>
                            <span class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 flex-shrink-0">BẠN</span>
                        </div>
                    </td>
                    <td class="py-2.5 px-4">
                        <div class="text-slate-200 font-medium truncate">${botName}</div>
                        ${detailSubtext}
                    </td>
                    <td class="py-2.5 px-3 text-center">
                        <span class="px-2 py-0.5 rounded text-[10px] uppercase bg-slate-800 text-emerald-400/90 font-bold border border-emerald-500/20">${lang}</span>
                    </td>
                    <td class="py-2.5 px-4 text-right font-mono font-bold text-amber-400/90 text-sm">${score}</td>
                </tr>`;
            }

            return `
            <tr class="border-b border-slate-800 hover:bg-slate-800/40 transition">
                <td class="py-2.5 px-3 text-center">${rankBadge}</td>
                ${tierBadge}
                <td class="py-2.5 px-4 truncate font-bold text-white">${playerName}</td>
                <td class="py-2.5 px-4">
                    <div class="text-slate-300 font-medium truncate">${botName}</div>
                    ${detailSubtext}
                </td>
                <td class="py-2.5 px-3 text-center">
                    <span class="px-2 py-0.5 rounded text-[10px] uppercase bg-slate-800 text-sky-300 font-bold border border-slate-700/60">${lang}</span>
                </td>
                <td class="py-2.5 px-4 text-right font-mono font-bold text-amber-300 text-sm">${score}</td>
            </tr>`;
        }).join('');

        this.renderPagination(totalPages);
    }

    renderPagination(totalPages) {
        const container = this.container.querySelector('.lb-pagination-container');
        if (!container) return;

        if (totalPages <= 1) {
            container.innerHTML = '';
            return;
        }

        let pages = [];
        if (totalPages <= 7) {
            for (let i = 1; i <= totalPages; i++) pages.push(i);
        } else {
            if (this.currentPage <= 4) {
                pages = [1, 2, 3, 4, 5, '...', totalPages];
            } else if (this.currentPage >= totalPages - 3) {
                pages = [1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
            } else {
                pages = [1, '...', this.currentPage - 1, this.currentPage, this.currentPage + 1, '...', totalPages];
            }
        }

        let html = '<div class="flex items-center gap-1.5 flex-wrap">';
        if (this.currentPage > 1) {
            html += `<button onclick="Leaderboard.instances['${this.containerId}'].goToPage(${this.currentPage - 1})" class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs transition"><i class="fa-solid fa-chevron-left"></i></button>`;
        } else {
            html += `<button disabled class="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-600 text-xs cursor-not-allowed"><i class="fa-solid fa-chevron-left"></i></button>`;
        }

        pages.forEach(p => {
            if (p === '...') {
                html += `<span class="px-2 py-1 text-slate-500 font-bold text-xs select-none">...</span>`;
            } else if (p === this.currentPage) {
                html += `<button class="px-3 py-1 rounded-lg bg-sky-600 text-white font-black text-xs shadow-md shadow-sky-600/30">${p}</button>`;
            } else {
                html += `<button onclick="Leaderboard.instances['${this.containerId}'].goToPage(${p})" class="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs transition">${p}</button>`;
            }
        });

        if (this.currentPage < totalPages) {
            html += `<button onclick="Leaderboard.instances['${this.containerId}'].goToPage(${this.currentPage + 1})" class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs transition"><i class="fa-solid fa-chevron-right"></i></button>`;
        } else {
            html += `<button disabled class="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-600 text-xs cursor-not-allowed"><i class="fa-solid fa-chevron-right"></i></button>`;
        }

        html += '</div>';
        container.innerHTML = html;
    }
}

const Leaderboard = {
    instances: {},
    mount(containerId) {
        if (!this.instances[containerId]) {
            this.instances[containerId] = new LeaderboardComponent(containerId);
        } else {
            const inst = this.instances[containerId];
            inst.currentUser = window.currentUser || inst.currentUser;
            inst.load();
        }
        return this.instances[containerId];
    }
};

window.Leaderboard = Leaderboard;
window.GLOBAL_LB_CACHE = GLOBAL_LB_CACHE;