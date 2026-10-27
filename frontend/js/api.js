const API_BASE = window.location.origin;

const memoryCache = new Map();

async function fetchWithCache(url, options = {}, ttlMs = 60000) {
    const key = url;
    const now = Date.now();

    if (memoryCache.has(key)) {
        const cached = memoryCache.get(key);
        if (now - cached.time < ttlMs) {
            return cached.data;
        }
    }

    const res = await fetch(url, options);
    if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Yêu cầu dữ liệu thất bại");
    }
    const data = await res.json();
    memoryCache.set(key, { data, time: now });
    return data;
}

function invalidateApiCache(prefix = "") {
    if (!prefix) {
        memoryCache.clear();
        return;
    }
    for (const key of memoryCache.keys()) {
        if (key.includes(prefix)) {
            memoryCache.delete(key);
        }
    }
}

const API = {
    getToken() {
        return localStorage.getItem("token");
    },
    setToken(token) {
        localStorage.setItem("token", token);
    },
    removeToken() {
        localStorage.removeItem("token");
        localStorage.removeItem("ott_username");
        memoryCache.clear();
        if (window.GLOBAL_LB_CACHE) window.GLOBAL_LB_CACHE.clear();
    },
    getAuthHeaders() {
        const token = this.getToken();
        return token ? { "Authorization": `Bearer ${token}` } : {};
    },

    async login(username, password) {
        const res = await fetch(`${API_BASE}/api/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Đăng nhập thất bại");
        this.setToken(data.access_token);
        if (username) localStorage.setItem("ott_username", username);
        return data;
    },

    async register(username, password) {
        const res = await fetch(`${API_BASE}/api/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Đăng ký thất bại");
        this.setToken(data.access_token);
        if (username) localStorage.setItem("ott_username", username);
        return data;
    },

    async getMe() {
        const res = await fetch(`${API_BASE}/api/auth/me`, {
            headers: this.getAuthHeaders()
        });
        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.detail || "Chưa đăng nhập hoặc phiên hết hạn");
        }
        const user = await res.json();
        if (user?.username) localStorage.setItem("ott_username", user.username);
        return user;
    },

    async getMyBots(forceRefresh = false) {
        const url = `${API_BASE}/api/bots/my`;
        if (forceRefresh) invalidateApiCache('/api/bots/my');
        return await fetchWithCache(url, { headers: this.getAuthHeaders() }, 30000);
    },

    async setActiveBot(botId) {
        const res = await fetch(`${API_BASE}/api/bots/${botId}/set-active`, {
            method: "POST",
            headers: this.getAuthHeaders()
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Không thể kích hoạt bot");
        invalidateApiCache('/api/bots');
        return data;
    },

    async updateBot(botId, name) {
        const res = await fetch(`${API_BASE}/api/bots/${botId}`, {
            method: "PUT",
            headers: { ...this.getAuthHeaders(), "Content-Type": "application/json" },
            body: JSON.stringify({ name })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Không thể cập nhật tên bot");
        invalidateApiCache('/api/bots');
        return data;
    },

    async deleteBot(botId) {
        const res = await fetch(`${API_BASE}/api/bots/${botId}`, {
            method: "DELETE",
            headers: this.getAuthHeaders()
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Không thể xóa bot");
        invalidateApiCache('/api/bots');
        return data;
    },

    async uploadBot(file) {
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch(`${API_BASE}/api/bots/upload`, {
            method: "POST",
            headers: this.getAuthHeaders(),
            body: formData
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Tải lên bot thất bại");
        invalidateApiCache('/api/bots');
        return data;
    },

    async getSystemBots() {
        return await fetchWithCache(`${API_BASE}/api/bots/system-bots`, {}, 120000);
    },

    async runQuickMatch(bot1Id, bot2Id) {
        const res = await fetch(`${API_BASE}/api/matches/quick?bot1_id=${bot1Id}&bot2_id=${bot2Id}`, {
            method: "POST",
            headers: this.getAuthHeaders()
        });
        let data;
        const contentType = res.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            data = await res.json();
        } else {
            throw new Error(await res.text());
        }
        if (!res.ok) throw new Error(data.detail || "Trận đấu thất bại");
        return data;
    },

    async getReplay(url) {
        const fullUrl = url.startsWith("http") ? url : `${API_BASE}${url.startsWith("/") ? "" : "/"}${url}`;
        return await fetchWithCache(fullUrl, { headers: this.getAuthHeaders() }, 600000);
    },

    async getTournamentMatches(tourId, q = "", roundType = "", order = "asc") {
        const url = `${API_BASE}/api/matches/tournament/${tourId}?q=${encodeURIComponent(q)}&round_type=${encodeURIComponent(roundType)}&order=${encodeURIComponent(order)}`;
        return await fetchWithCache(url, { headers: this.getAuthHeaders() }, 30000);
    },

    async getTournaments(forceRefresh = false, seasonId = null) {
        let url = `${API_BASE}/api/tournaments`;
        if (seasonId) url += `?season_id=${encodeURIComponent(seasonId)}`;
        if (forceRefresh) invalidateApiCache('/api/tournaments');
        return await fetchWithCache(url, { headers: this.getAuthHeaders() }, 60000);
    },

    async getMyTournaments(forceRefresh = false) {
        const url = `${API_BASE}/api/tournaments/my`;
        if (forceRefresh) invalidateApiCache('/api/tournaments/my');
        return await fetchWithCache(url, { headers: this.getAuthHeaders() }, 60000);
    },

    async registerTournament(tourId, botId) {
        const res = await fetch(`${API_BASE}/api/tournaments/${tourId}/register?bot_id=${botId}`, {
            method: "POST",
            headers: this.getAuthHeaders()
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Đăng ký giải thất bại");
        invalidateApiCache('/api/tournaments');
        return data;
    },

    async startTournament(tourId) {
        const res = await fetch(`${API_BASE}/api/tournaments/${tourId}/start`, {
            method: "POST",
            headers: this.getAuthHeaders()
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Khởi tranh giải đấu thất bại");
        invalidateApiCache('/api/tournaments');
        invalidateApiCache('/api/admin/tournaments');
        invalidateApiCache('/api/matches');
        invalidateApiCache('/api/leaderboard');
        if (window.GLOBAL_LB_CACHE) window.GLOBAL_LB_CACHE.clear();
        return data;
    },

    async getTournamentStandings(tourId) {
        return await fetchWithCache(`${API_BASE}/api/tournaments/${tourId}/standings`, {}, 60000);
    },

    async getLeaderboard(filterType = "all", tournamentId = null, seasonId = null) {
        let url = `${API_BASE}/api/leaderboard?filter_type=${encodeURIComponent(filterType)}`;
        if (tournamentId) url += `&tournament_id=${encodeURIComponent(tournamentId)}`;
        if (seasonId) url += `&season_id=${encodeURIComponent(seasonId)}`;
        return await fetchWithCache(url, {}, 300000);
    },

    async getSeasons(forceRefresh = false) {
        const url = `${API_BASE}/api/seasons`;
        if (forceRefresh) invalidateApiCache('/api/seasons');
        return await fetchWithCache(url, {}, 60000);
    },

    async getActiveSeason() {
        return await fetchWithCache(`${API_BASE}/api/seasons/active`, {}, 60000);
    },

    async getSeasonLeaderboard(seasonId) {
        const url = `${API_BASE}/api/seasons/${seasonId}/leaderboard`;
        return await fetchWithCache(url, {}, 60000);
    },

    async createSeason(name, startDate, endDate = null) {
        const res = await fetch(`${API_BASE}/api/seasons`, {
            method: "POST",
            headers: { ...this.getAuthHeaders(), "Content-Type": "application/json" },
            body: JSON.stringify({ name, start_date: startDate, end_date: endDate })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Lỗi tạo mùa giải");
        invalidateApiCache('/api/seasons');
        if (window.GLOBAL_LB_CACHE) window.GLOBAL_LB_CACHE.clear();
        return data;
    },

    async updateSeason(seasonId, updateData) {
        const res = await fetch(`${API_BASE}/api/seasons/${seasonId}`, {
            method: "PUT",
            headers: { ...this.getAuthHeaders(), "Content-Type": "application/json" },
            body: JSON.stringify(updateData)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Lỗi cập nhật mùa giải");
        invalidateApiCache('/api/seasons');
        if (window.GLOBAL_LB_CACHE) window.GLOBAL_LB_CACHE.clear();
        return data;
    },

    async deleteSeason(seasonId) {
        const res = await fetch(`${API_BASE}/api/seasons/${seasonId}`, {
            method: "DELETE",
            headers: this.getAuthHeaders()
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Lỗi xóa mùa giải");
        invalidateApiCache('/api/seasons');
        if (window.GLOBAL_LB_CACHE) window.GLOBAL_LB_CACHE.clear();
        return data;
    },

    async resetAndStartNewSeason(seasonId, newSeasonName, newStartDate = null, newEndDate = null) {
        const res = await fetch(`${API_BASE}/api/seasons/${seasonId}/reset-and-start-new`, {
            method: "POST",
            headers: { ...this.getAuthHeaders(), "Content-Type": "application/json" },
            body: JSON.stringify({
                new_season_name: newSeasonName,
                new_start_date: newStartDate,
                new_end_date: newEndDate
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Lỗi thiết lập lại mùa giải");
        invalidateApiCache('/api/seasons');
        invalidateApiCache('/api/leaderboard');
        invalidateApiCache('/api/admin/players');
        if (window.GLOBAL_LB_CACHE) window.GLOBAL_LB_CACHE.clear();
        return data;
    },

    async getAdminStats() {
        return await fetchWithCache(`${API_BASE}/api/admin/stats`, { headers: this.getAuthHeaders() }, 60000);
    },

    async getLadderConfig() {
        return await fetchWithCache(`${API_BASE}/api/admin/matchmaking/config`, { headers: this.getAuthHeaders() }, 5000);
    },

    async updateLadderConfig(configData) {
        const res = await fetch(`${API_BASE}/api/admin/matchmaking/config`, {
            method: "PUT",
            headers: { ...this.getAuthHeaders(), "Content-Type": "application/json" },
            body: JSON.stringify(configData)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Lỗi lưu cấu hình xếp hạng");
        invalidateApiCache('/api/admin/matchmaking');
        return data;
    },

    async triggerLadderRun() {
        const res = await fetch(`${API_BASE}/api/admin/matchmaking/run`, {
            method: "POST",
            headers: this.getAuthHeaders()
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Lỗi chạy ghép trận");
        invalidateApiCache('/api/leaderboard');
        invalidateApiCache('/api/admin/players');
        return data;
    },

    async getAdminPlayersPaginated(q = "", page = 1, limit = 8) {
        const url = `${API_BASE}/api/admin/players?q=${encodeURIComponent(q)}&page=${page}&limit=${limit}`;
        return await fetchWithCache(url, { headers: this.getAuthHeaders() }, 60000);
    },

    async toggleBanPlayer(userId) {
        const res = await fetch(`${API_BASE}/api/admin/players/${userId}/toggle-ban`, {
            method: "POST",
            headers: this.getAuthHeaders()
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Lỗi thay đổi trạng thái người chơi");
        invalidateApiCache('/api/admin/players');
        return data;
    },

    async deletePlayer(userId) {
        const res = await fetch(`${API_BASE}/api/admin/players/${userId}`, {
            method: "DELETE",
            headers: this.getAuthHeaders()
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Lỗi xóa người chơi");
        invalidateApiCache('/api/admin/players');
        return data;
    },

    async getAdminBotsPaginated(q = "", page = 1, limit = 8) {
        const url = `${API_BASE}/api/admin/bots?q=${encodeURIComponent(q)}&page=${page}&limit=${limit}`;
        return await fetchWithCache(url, { headers: this.getAuthHeaders() }, 60000);
    },

    async getAdminBotCode(botId) {
        return await fetchWithCache(`${API_BASE}/api/admin/bots/${botId}/code`, { headers: this.getAuthHeaders() }, 120000);
    },

    async deleteBotByAdmin(botId) {
        const res = await fetch(`${API_BASE}/api/admin/bots/${botId}`, {
            method: "DELETE",
            headers: this.getAuthHeaders()
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Không thể xóa bot");
        invalidateApiCache('/api/admin/bots');
        return data;
    },

    async getAdminTournamentsPaginated(q = "", status = "", page = 1, limit = 6) {
        const url = `${API_BASE}/api/admin/tournaments?q=${encodeURIComponent(q)}&status=${encodeURIComponent(status)}&page=${page}&limit=${limit}`;
        return await fetchWithCache(url, { headers: this.getAuthHeaders() }, 60000);
    },

    async createTournament(name, startTime) {
        const res = await fetch(`${API_BASE}/api/tournaments/create`, {
            method: "POST",
            headers: { ...this.getAuthHeaders(), "Content-Type": "application/json" },
            body: JSON.stringify({ name, start_time: startTime })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Lỗi tạo giải");
        invalidateApiCache('/api/tournaments');
        invalidateApiCache('/api/admin/tournaments');
        if (window.GLOBAL_LB_CACHE) window.GLOBAL_LB_CACHE.clear();
        return data;
    },

    async updateTournament(tourId, updateData) {
        const res = await fetch(`${API_BASE}/api/tournaments/${tourId}`, {
            method: "PUT",
            headers: { ...this.getAuthHeaders(), "Content-Type": "application/json" },
            body: JSON.stringify(updateData)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Lỗi cập nhật giải đấu");
        invalidateApiCache('/api/tournaments');
        invalidateApiCache('/api/admin/tournaments');
        if (window.GLOBAL_LB_CACHE) window.GLOBAL_LB_CACHE.clear();
        return data;
    },

    async cancelTournament(tourId) {
        const res = await fetch(`${API_BASE}/api/tournaments/${tourId}/cancel`, {
            method: "POST",
            headers: this.getAuthHeaders()
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Lỗi hủy giải đấu");
        invalidateApiCache('/api/tournaments');
        invalidateApiCache('/api/admin/tournaments');
        if (window.GLOBAL_LB_CACHE) window.GLOBAL_LB_CACHE.clear();
        return data;
    },

    async deleteTournament(tourId) {
        const res = await fetch(`${API_BASE}/api/tournaments/${tourId}`, {
            method: "DELETE",
            headers: this.getAuthHeaders()
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Lỗi xóa giải đấu");
        invalidateApiCache('/api/tournaments');
        invalidateApiCache('/api/admin/tournaments');
        if (window.GLOBAL_LB_CACHE) window.GLOBAL_LB_CACHE.clear();
        return data;
    }
};

window.API = API;
window.invalidateApiCache = invalidateApiCache;