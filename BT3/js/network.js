/**
 * ===== PHẦN 1: MẠNG & LOBBY (Server / room / history) =====
 * Robust Zero-Key Multi-Transport Networking Architecture & Match History Sync:
 * 1. BroadcastChannel ('ottv2_local_bus'): Zero-latency tab-to-tab state sync.
 * 2. MQTT over Public WebSockets (broker.emqx.io): Public online broker.
 * 3. LocalStorage Room & Match History Cache.
 */

const myUserId = 'user_' + Math.random().toString(36).substring(2, 9);
const broadcastBus = window.BroadcastChannel ? new BroadcastChannel('ottv2_local_bus') : null;
let mqttClient = null;
let isMqttConnected = false;

const ROOM_STORAGE_KEY = 'ottv2_public_rooms_v2';
const HISTORY_STORAGE_KEY = 'ottv2_match_history_v2';
let roomsStore = {};
let matchHistoryStore = [];

function loadRoomsFromStorage() {
    try {
        const stored = localStorage.getItem(ROOM_STORAGE_KEY);
        if (stored) roomsStore = JSON.parse(stored);
    } catch (e) { roomsStore = {}; }
}

function saveRoomsToStorage() {
    try {
        localStorage.setItem(ROOM_STORAGE_KEY, JSON.stringify(roomsStore));
    } catch (e) {}
}

function loadHistoryFromStorage() {
    try {
        const stored = localStorage.getItem(HISTORY_STORAGE_KEY);
        if (stored) matchHistoryStore = JSON.parse(stored);
    } catch (e) { matchHistoryStore = []; }
}

function saveHistoryToStorage() {
    try {
        localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(matchHistoryStore));
    } catch (e) {}
}

loadRoomsFromStorage();
loadHistoryFromStorage();

function saveMatchRecord(record) {
    loadHistoryFromStorage();
    if (!matchHistoryStore.some(m => m.id === record.id)) {
        matchHistoryStore.unshift(record);
        saveHistoryToStorage();

        const payload = JSON.stringify({ type: 'MATCH_HISTORY_UPDATE', data: record, sender: myUserId });
        if (broadcastBus) broadcastBus.postMessage(payload);
        if (mqttClient && isMqttConnected) {
            try {
                mqttClient.publish('ottv2/v2/history', JSON.stringify(record));
            } catch (e) { console.warn('MQTT history publish error:', e); }
        }
    }
    if (window.onHistoryListChanged) window.onHistoryListChanged(matchHistoryStore);
}

function clearMatchHistory() {
    if (confirm('Bạn có chắc muốn xóa toàn bộ lịch sử trận đấu?')) {
        matchHistoryStore = [];
        saveHistoryToStorage();
        if (window.onHistoryListChanged) window.onHistoryListChanged(matchHistoryStore);
    }
}

function broadcastRoomUpdate(roomData) {
    if (roomData.deleted || roomData.status === 'cancelled') {
        delete roomsStore[roomData.roomId];
    } else if (roomData.status === 'finished') {
        delete roomsStore[roomData.roomId];
    } else {
        roomsStore[roomData.roomId] = roomData;
    }
    saveRoomsToStorage();

    const payload = JSON.stringify({ type: 'ROOM_UPDATE', data: roomData, sender: myUserId });

    if (broadcastBus) {
        broadcastBus.postMessage(payload);
    }

    if (mqttClient && isMqttConnected) {
        try {
            const msgStr = JSON.stringify({ type: 'ROOM_UPDATE', data: roomData, sender: myUserId });
            mqttClient.publish('ottv2/v2/room_list', msgStr);
            mqttClient.publish(`ottv2/v2/room/${roomData.roomId}`, msgStr);
        } catch (e) { console.warn('MQTT publish error:', e); }
    }

    if (window.onRoomDataReceived) window.onRoomDataReceived(roomData);
    if (window.onRoomListChanged) window.onRoomListChanged(Object.values(roomsStore));
}

function initMQTT() {
    const pillText = document.getElementById('connectionText');
    const pillEl = document.getElementById('connectionPill');

    if (typeof mqtt === 'undefined') {
        pillText.innerText = '🟡 Local Sync (Multi-Tab Active)';
        pillEl.className = 'flex items-center gap-2 bg-amber-950/80 border border-amber-500/40 text-amber-300 px-3 py-1.5 rounded-xl text-xs font-bold shadow-md';
        return;
    }

    try {
        mqttClient = mqtt.connect('wss://broker.emqx.io:8084/mqtt', {
            clientId: 'ottv2_client_' + Math.random().toString(16).substring(2, 8),
            reconnectPeriod: 5000,
            clean: true
        });

        mqttClient.on('connect', () => {
            isMqttConnected = true;
            pillText.innerText = '🟢 Đã kết nối Server (EMQX Broker)';
            pillEl.className = 'flex items-center gap-2 bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 px-3 py-1.5 rounded-xl text-xs font-bold shadow-md';
            mqttClient.subscribe('ottv2/v2/history');
            mqttClient.subscribe('ottv2/v2/room_list');
            mqttClient.subscribe('ottv2/v2/room/#');
        });

        mqttClient.on('reconnect', () => {
            isMqttConnected = false;
            pillText.innerText = '🟡 Đang kết nối lại Server...';
            pillEl.className = 'flex items-center gap-2 bg-amber-950/80 border border-amber-500/40 text-amber-300 px-3 py-1.5 rounded-xl text-xs font-bold shadow-md';
        });

        mqttClient.on('offline', () => {
            isMqttConnected = false;
            pillText.innerText = '🟡 Local Sync (Multi-Tab Active)';
            pillEl.className = 'flex items-center gap-2 bg-amber-950/80 border border-amber-500/40 text-amber-300 px-3 py-1.5 rounded-xl text-xs font-bold shadow-md';
        });

        mqttClient.on('message', (topic, message) => {
            try {
                if (topic === 'ottv2/v2/history') {
                    const data = JSON.parse(message.toString());
                    if (data && data.id) {
                        saveMatchRecord(data);
                    }
                }
                else if (topic === 'ottv2/v2/room_list') {
                    const payload = JSON.parse(message.toString());
                    const roomData = payload.data || payload;
                    if (roomData && roomData.roomId) {
                        if (roomData.deleted || roomData.status === 'cancelled' || roomData.status === 'finished') {
                            delete roomsStore[roomData.roomId];
                        } else {
                            roomsStore[roomData.roomId] = roomData;
                        }
                        saveRoomsToStorage();
                        if (window.onRoomListChanged) window.onRoomListChanged(Object.values(roomsStore));
                    }
                }
                else if (topic.startsWith('ottv2/v2/room/')) {
                    const payload = JSON.parse(message.toString());
                    const roomData = payload.data || payload;
                    if (roomData && roomData.roomId) {
                        if (roomData.deleted || roomData.status === 'cancelled' || roomData.status === 'finished') {
                            delete roomsStore[roomData.roomId];
                        } else {
                            roomsStore[roomData.roomId] = roomData;
                        }
                        saveRoomsToStorage();
                        if (window.onRoomDataReceived) window.onRoomDataReceived(roomData);
                        if (window.onRoomListChanged) window.onRoomListChanged(Object.values(roomsStore));
                    }
                }
            } catch (e) {}
        });
    } catch (e) {
        console.warn('MQTT connection fallback:', e);
    }
}

if (broadcastBus) {
    broadcastBus.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            if (!msg || !msg.type) return;

            if (msg.type === 'ROOM_UPDATE' && msg.data && msg.sender !== myUserId) {
                const roomData = msg.data;
                if (roomData.deleted || roomData.status === 'cancelled') delete roomsStore[roomData.roomId];
                else if (roomData.status === 'finished') delete roomsStore[roomData.roomId];
                else roomsStore[roomData.roomId] = roomData;
                saveRoomsToStorage();
                if (window.onRoomListChanged) window.onRoomListChanged(Object.values(roomsStore));
                if (window.onRoomDataReceived && roomData.roomId === currentRoomCode) window.onRoomDataReceived(roomData);
            }

            if (msg.type === 'MATCH_HISTORY_UPDATE' && msg.data && msg.sender !== myUserId) {
                const record = msg.data;
                if (!matchHistoryStore.some(item => item.id === record.id)) {
                    matchHistoryStore.unshift(record);
                    saveHistoryToStorage();
                    if (window.onHistoryListChanged) window.onHistoryListChanged(matchHistoryStore);
                }
            }
        } catch (e) {}
    };
}

window.gameFirebase = {
    createRoom: async function(roomName, initialGameState, hostName) {
        const roomCode = Math.floor(100000 + Math.random() * 900000).toString();

        const roomData = {
            roomId: roomCode,
            roomName: roomName || 'Phòng mới',
            hostUid: myUserId,
            hostName: hostName || 'Người Chơi 1',
            guestUid: null,
            guestName: null,
            guestReady: false,
            spectatorsCount: 0,
            status: 'waiting',
            gameState: initialGameState,
            lastEmote: null,
            updatedAt: Date.now()
        };

        roomsStore[roomCode] = roomData;
        saveRoomsToStorage();
        broadcastRoomUpdate(roomData);
        return roomCode;
    },

    joinRoom: async function(roomCode, playerName) {
        loadRoomsFromStorage();
        const roomData = roomsStore[roomCode];

        if (!roomData) {
            throw new Error('Phòng không tồn tại hoặc đã bị hủy!');
        }

        if (roomData.hostUid === myUserId) {
            return { role: 1, data: roomData };
        }

        if (!roomData.guestUid || roomData.guestUid === myUserId) {
            roomData.guestUid = myUserId;
            roomData.guestName = playerName || 'Người Chơi 2';
            roomData.updatedAt = Date.now();
            broadcastRoomUpdate(roomData);
            return { role: 2, data: roomData };
        }

        roomData.spectatorsCount = (roomData.spectatorsCount || 0) + 1;
        roomData.updatedAt = Date.now();
        broadcastRoomUpdate(roomData);
        return { role: 'spectator', data: roomData };
    },

    toggleGuestReady: async function(roomCode, isReady) {
        const roomData = roomsStore[roomCode];
        if (!roomData) return;
        roomData.guestReady = isReady;
        roomData.updatedAt = Date.now();
        broadcastRoomUpdate(roomData);
    },

    startMatch: async function(roomCode) {
        const roomData = roomsStore[roomCode];
        if (!roomData) return;
        roomData.status = 'playing';
        roomData.gameState.startTime = Date.now();
        roomData.updatedAt = Date.now();
        broadcastRoomUpdate(roomData);
    },

    subscribeRoomsList: function(onData) {
        window.onRoomListChanged = onData;
        onData(Object.values(roomsStore));
    },

    subscribeHistoryList: function(onData) {
        window.onHistoryListChanged = onData;
        onData(matchHistoryStore);
    },

    subscribeRoom: function(roomCode, onDataChange) {
        if (mqttClient && isMqttConnected) {
            try {
                mqttClient.subscribe(`ottv2/v2/room/${roomCode}`);
            } catch (e) {}
        }
        window.onRoomDataReceived = (data) => {
            if (data && data.roomId === roomCode) {
                onDataChange(data);
            }
        };
        if (roomsStore[roomCode]) {
            onDataChange(roomsStore[roomCode]);
        }
    },

    updateGameState: async function(roomCode, newGameState, isFinished = false) {
        const roomData = roomsStore[roomCode];
        if (!roomData) return;
        roomData.gameState = newGameState;
        roomData.updatedAt = Date.now();
        if (isFinished) roomData.status = 'finished';
        broadcastRoomUpdate(roomData);
    },

    deleteUnstartedRoom: async function(roomCode) {
        const roomData = roomsStore[roomCode];
        if (!roomData) return;
        roomData.status = 'cancelled';
        roomData.deleted = true;
        roomData.updatedAt = Date.now();
        broadcastRoomUpdate(roomData);
    },

    sendEmote: async function(roomCode, senderName, emoteMsg) {
        const roomData = roomsStore[roomCode];
        if (!roomData) return;
        roomData.lastEmote = { senderName, msg: emoteMsg, id: Date.now() };
        roomData.updatedAt = Date.now();
        broadcastRoomUpdate(roomData);
    }
};

window.addEventListener('load', () => {
    initMQTT();
});
