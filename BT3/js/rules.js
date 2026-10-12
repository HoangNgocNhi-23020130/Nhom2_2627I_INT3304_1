/**
 * ===== MODULE: LUẬT CHƠI & CẤU HÌNH (RULES CONFIG) =====
 * Dựa trên tài liệu thiết kế BT3 - Version 2: Bảng đầy đủ
 * Cho phép cấu hình kích thước bàn, bảng tương khắc, điều kiện thắng và version luật
 */

const OTT_RULES_VERSION = "2.0";

const DEFAULT_RULES = {
    version: OTT_RULES_VERSION,
    name: "OanTuTi Tactics 9x9 Standard",
    boardSize: 9,
    maxTurns: 200,
    goals: {
        1: { r: 0, c: 8, notation: "i9", name: "Đích P1 (Phải-Trên)" },
        2: { r: 8, c: 0, notation: "a1", name: "Đích P2 (Trái-Dưới)" }
    },
    // Ô nhà xuất phát của mỗi bên (cấm quân của chính bên đó đi vào)
    homes: {
        1: { r: 8, c: 0, notation: "a1", name: "Nhà P1 (Trái-Dưới)" },
        2: { r: 0, c: 8, notation: "i9", name: "Nhà P2 (Phải-Trên)" }
    },
    allowEnterOwnHome: false, // Tuyệt đối cấm quân đi vào ô nhà của chính mình
    // Bảng tương khắc: Key ăn được Value
    beats: {
        'R': 'S', // Đấm (Rock) > Kéo (Scissors)
        'S': 'P', // Kéo (Scissors) > Lá (Paper)
        'P': 'R'  // Lá (Paper) > Đấm (Rock)
    },
    // Quy tắc khi gặp quân cùng loại:
    // 'block': Hai quân cùng loại chặn đường nhau (luật chiến thuật)
    // 'eliminate': Hai quân cùng loại cùng bị loại bỏ (luật gốc)
    sameTypeRule: 'block',
    
    // Điều kiện chiến thắng kích hoạt
    winConditions: {
        reachGoal: true,           // Đưa quân chiếm ô đích đối phương
        extinctionAnyType: true,   // Tiêu diệt hết 1 loài quân của đối phương
        forfeit: true,             // Đối thủ bỏ cuộc / mất kết nối
        turnLimit: true            // Hết số lượt tối đa
    },
    
    pieceTypes: ['R', 'P', 'S'],
    pieceNames: {
        'R': 'Đấm',
        'P': 'Lá',
        'S': 'Kéo'
    },
    pieceEmojis: {
        'R': '✊',
        'P': '✋',
        'S': '✌️'
    },
    defaultPieceCounts: {
        'R': 6,
        'P': 6,
        'S': 6
    }
};

// Cung cấp biến toàn cục
window.OTT_RULES_VERSION = OTT_RULES_VERSION;
window.OTT_RULES = DEFAULT_RULES;
