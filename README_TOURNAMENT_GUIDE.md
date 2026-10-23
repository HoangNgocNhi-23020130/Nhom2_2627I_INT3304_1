# 🏆 HƯỚNG DẪN TỔ CHỨC GIẢI ĐẤU (ONLINE & ON-LAN) VÀ CÁCH SỬA LUẬT CHƠI
### Dự án: OanTuTi Arena (OTTv2 Bot Arena) - Môn học: Mạng máy tính (INT3304_1)

Tài liệu này cung cấp hướng dẫn toàn diện từ A đến Z cho Ban Tổ Chức (giảng viên, chủ trì giải) và người chơi về:
1. **Tổ chức giải đấu Online** (qua Cloud / VPS công khai).
2. **Tổ chức giải đấu On-LAN** (trong phòng máy / phòng thi nội bộ, **cách ly hoàn toàn với Internet để chống gian lận**).
3. **Cách tùy biến và sửa đổi luật chơi** (kích thước bàn, tương khắc, số quân, biến thể triệt tiêu, bàn cờ chữ thập).

---

## 1. TỔNG QUAN KIẾN TRÚC HỆ THỐNG

Hệ thống được xây dựng theo kiến trúc **Fullstack Decoupled** hiện đại:
```
Nhom2_2627I_INT3304_1/
├── backend/                  # API Server (FastAPI + SQLite/PostgreSQL)
│   ├── app/api/              # Các endpoint: auth, bots, tournaments, matches, leaderboard, admin
│   ├── app/core/             # Pure Game Engine (Python) & Bảo mật JWT
│   ├── app/services/         # Compiler (C++), Match Runner (Sandbox), Matchmaking Scheduler
│   ├── main.py               # File chạy chính tích hợp cả Backend và phát Frontend
│   └── seed_data.py          # Script nạp dữ liệu mẫu ban đầu (admin, mùa giải, bot mẫu)
├── frontend/                 # Giao diện người dùng Web (SPA thuần, responsive)
│   ├── index.html            # Trang chủ, xem BXH, nộp bot, xem Replay
│   ├── admin.html            # Bảng điều khiển Quản trị viên (Admin Dashboard)
│   └── js/                   # Modules: api.js, app.js, leaderboard.js, replay.js, engine.js
├── shared/                   # Dữ liệu dùng chung
│   └── rules.json            # NGUỒN LUẬT TRUNG TÂM (Single Source of Truth)
├── storage/                  # Lưu trữ mã nguồn bot và file Replay JSON
└── Dockerfile                # Đóng gói toàn bộ hệ thống để chạy 1 lệnh duy nhất
```

---

## 2. HƯỚNG DẪN TỔ CHỨC ĐẤU ONLINE (CLOUD / INTERNET)

Áp dụng khi tổ chức giải đấu dài hạn, cho phép sinh viên nộp code từ xa qua mạng Internet.

### 2.1. Triển khai Server lên Cloud (0đ hoặc VPS)
Bạn có thể triển khai hệ thống lên các nền tảng miễn phí như **Render.com**, **Railway.app** hoặc VPS cá nhân:
* **Cách 1: Sử dụng Docker (Khuyên dùng)**
  ```bash
  # Build Docker Image
  docker build -t oantuti-arena .
  
  # Chạy Container trên cổng 8000
  docker run -d -p 8000:8000 -v $(pwd)/storage:/app/storage --name arena oantuti-arena
  ```
* **Cách 2: Chạy trực tiếp bằng Python**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r backend/requirements.txt
  
  # Nạp dữ liệu mẫu ban đầu
  cd backend && python3 seed_data.py
  
  # Khởi chạy server
  python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
  ```

### 2.2. Quy trình dành cho Thí sinh / Người chơi
1. Thí sinh truy cập tên miền web (ví dụ: `https://arena.yourdomain.com`).
2. Bấm **"Đăng ký"** tạo tài khoản $\rightarrow$ Đăng nhập.
3. Vào mục **"Nộp Bot"**:
   - Nhập tên Bot (ví dụ: `bot_alpha`).
   - Chọn ngôn ngữ: **Python (.py)** hoặc **C++ (.cpp)** hoặc **JavaScript (.js)**.
   - Upload file code hoặc dán trực tiếp vào khung soạn thảo.
   - Bấm **"Lưu & Đăng Ký Thi Đấu"**.

### 2.3. Cơ chế Ghép cặp & Tự động Thi đấu
Hệ thống có sẵn 2 cơ chế thi đấu Online:
1. **Hệ thống Xếp hạng Elo tự động (Ladder Matchmaking):**
   - Bộ lập lịch `scheduler.py` chạy ngầm định kỳ (mặc định mỗi 15 phút hoặc hàng tuần).
   - Tự động lấy các bot đang hoạt động ghép cặp đấu với nhau theo khoảng cách điểm Elo tương đồng.
   - Cập nhật điểm Elo theo công thức quốc tế: Thắng cộng điểm, thua trừ điểm, thắng đối thủ mạnh cộng nhiều điểm hơn.
2. **Giải đấu chính thức theo Mùa (Season Tournaments):**
   - Admin vào `https://arena.yourdomain.com/admin` (đăng nhập `admin` / `123456`).
   - Tạo giải đấu: Đặt tên giải, chọn Mùa giải, chọn thời gian bắt đầu.
   - Khi đến giờ hẹn, hệ thống tự động bốc thăm đấu vòng tròn (Round-Robin), cập nhật Bảng xếp hạng và lưu Replay đầy đủ.

---

## 3. HƯỚNG DẪN TỔ CHỨC ĐẤU ON-LAN (PHÒNG THI NỘI BỘ - CHỐNG GIAN LẬN)

Áp dụng cho các kỳ thi Offline tại phòng máy/phòng lab: **Rút hoàn toàn dây mạng Internet (chỉ bật mạng LAN nội bộ) để thí sinh không thể tra cứu Google, ChatGPT hay trao đổi ra ngoài**.

```
[Máy Thí Sinh 1] (192.168.1.10) ──┐
[Máy Thí Sinh 2] (192.168.1.11) ──┼──> [Router LAN Phòng Máy] ──> [Máy Ban Tổ Chức] (192.168.1.100:8000)
[Máy Thí Sinh N] (192.168.1.12) ──┘    (Ngắt cáp Internet WAN)            │
                                                                           ▼
                                                                  • Nhận nộp code tức thì
                                                                  • Chạy giải đấu trực tiếp
                                                                  • Chiếu BXH lên máy chiếu
```

### 3.1. Thiết lập phía Ban Tổ Chức (Host)
1. Kết nối máy tính của BTC vào mạng Switch/Wifi của phòng thi.
2. Xem địa chỉ IP LAN của máy BTC:
   - Trên macOS / Linux: Chạy `ifconfig` hoặc `ip a` (ví dụ: `192.168.1.100`).
   - Trên Windows: Chạy `ipconfig`.
3. Khởi động hệ thống trên máy BTC:
   ```bash
   source .venv/bin/activate
   cd backend
   python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```
   *(Tham số `--host 0.0.0.0` là bắt buộc để các máy khác trong mạng LAN truy cập được).*

### 3.2. Hướng dẫn Thí sinh trong phòng thi nộp bài
1. Thí sinh mở trình duyệt (Chrome, Cốc Cốc, Edge, Firefox).
2. Gõ địa chỉ IP của máy BTC: `http://192.168.1.100:8000`
3. Thí sinh đăng ký tài khoản theo Mã sinh viên (ví dụ: `23020130`).
4. Nộp file code `bot_mssv.py` hoặc `bot_mssv.cpp` lên hệ thống.
5. Mã nguồn lập tức được lưu vào thư mục `storage/bots/` trên máy BTC qua đường truyền nội bộ cực nhanh ($< 0.1$ giây).

### 3.3. Ban Tổ Chức tiến hành chấm giải và Chiếu máy chiếu
1. Hết giờ làm bài, BTC mở `http://127.0.0.1:8000/admin`.
2. Vào mục **"Giải Đấu"** $\rightarrow$ bấm **"Tạo Giải Đấu Mới"** $\rightarrow$ Chọn danh sách các Bot vừa nộp $\rightarrow$ Bấm **"Bắt đầu ngay"**.
3. Hệ thống sẽ cho các bot đấu tự động trong môi trường Sandbox an toàn (kiểm soát timeout 500ms mỗi nước, ngăn bot crash).
4. Chiếu trang **Bảng Xếp Hạng** lên máy chiếu phòng thi để tất cả thí sinh cùng theo dõi huy chương Vàng, Bạc, Đồng và xem lại Replay từng ván đấu!

---

## 4. HƯỚNG DẪN SỬA ĐỔI LUẬT CHƠI (GAME RULES CONFIGURATION)

Trong kiến trúc mới, toàn bộ luật chơi được kiểm soát bởi **1 FILE JSON DUY NHẤT**:
👉 [`shared/rules.json`](shared/rules.json)

Cả **Backend Engine (Python)** và **Frontend Web (JavaScript)** đều đọc trực tiếp từ file này. Khi bạn sửa file này, toàn bộ hệ thống sẽ lập tức cập nhật luật mới mà **không cần viết lại code**.

```json
{
  "version": "2.0",
  "name": "OanTuTi Tactics 9x9 Standard",
  "boardSize": 9,
  "maxTurns": 200,
  "goals": {
    "1": { "r": 0, "c": 8, "notation": "i9", "name": "Đích P1 (Phải-Trên)" },
    "2": { "r": 8, "c": 0, "notation": "a1", "name": "Đích P2 (Trái-Dưới)" }
  },
  "homes": {
    "1": { "r": 8, "c": 0, "notation": "a1", "name": "Nhà P1 (Trái-Dưới)" },
    "2": { "r": 0, "c": 8, "notation": "i9", "name": "Nhà P2 (Phải-Trên)" }
  },
  "allowEnterOwnHome": false,
  "beats": {
    "R": "S",
    "S": "P",
    "P": "R"
  },
  "sameTypeRule": "block",
  "winConditions": {
    "reachGoal": true,
    "extinctionAnyType": true,
    "turnLimit": true,
    "forfeit": true
  },
  "pieceTypes": ["R", "P", "S"],
  "pieceEmojis": { "R": "✊", "P": "✋", "S": "✌️" },
  "pieceCountsPerPlayer": { "R": 6, "P": 6, "S": 6 }
}
```

---

### 4.1. Đổi kích thước bàn cờ (Ví dụ từ 9x9 thành 10x10)
Chỉ cần sửa trong `shared/rules.json`:
1. Đổi `"boardSize": 10`
2. Đổi tọa độ ô đích và ô nhà:
   - P1: Ô nhà `(9, 0)` (`a1`), ô đích `(0, 9)` (`j10`).
   - P2: Ô nhà `(0, 9)` (`j10`), ô đích `(9, 0)` (`a1`).
```json
"boardSize": 10,
"goals": {
  "1": { "r": 0, "c": 9, "notation": "j10", "name": "Đích P1 (Phải-Trên)" },
  "2": { "r": 9, "c": 0, "notation": "a1", "name": "Đích P2 (Trái-Dưới)" }
},
"homes": {
  "1": { "r": 9, "c": 0, "notation": "a1", "name": "Nhà P1 (Trái-Dưới)" },
  "2": { "r": 0, "c": 9, "notation": "j10", "name": "Nhà P2 (Phải-Trên)" }
}
```

### 4.2. Đổi quy tắc khi hai quân cùng loại gặp nhau (`sameTypeRule`)
* **Chặn đường nhau (Mặc định):** Giữ `"sameTypeRule": "block"`. Hai quân cùng loại không thể đi vào ô của nhau.
* **Triệt tiêu nhau (Luật gốc):** Đổi thành `"sameTypeRule": "eliminate"`. Khi hai quân cùng loại va chạm, **cả 2 quân cùng biến mất khỏi bàn cờ**.

### 4.3. Đổi số lượng quân cờ & Giới hạn lượt đi
* Muốn trận đấu nhanh hơn: Đổi `"maxTurns": 100` (giới hạn 100 nước).
* Muốn mỗi bên có 9 quân (3 Đấm, 3 Lá, 3 Kéo):
  ```json
  "pieceCountsPerPlayer": {
    "R": 3,
    "P": 3,
    "S": 3
  }
  ```

### 4.4. Thêm quân mới hoặc đổi bảng tương khắc (Oẳn Tù Tì mở rộng)
Ví dụ thêm 2 quân **Thằn Lằn (Lizard - L)** và **Spock (K)** theo chuẩn quốc tế:
```json
"beats": {
  "R": ["S", "L"],
  "P": ["R", "K"],
  "S": ["P", "L"],
  "L": ["K", "P"],
  "K": ["S", "R"]
},
"pieceTypes": ["R", "P", "S", "L", "K"],
"pieceEmojis": {
  "R": "✊",
  "P": "✋",
  "S": "✌️",
  "L": "🦎",
  "K": "🖖"
},
"pieceCountsPerPlayer": {
  "R": 3, "P": 3, "S": 3, "L": 3, "K": 3
}
```
Engine sẽ tự động áp dụng bảng tương khắc mới vào tất cả các trận đấu tiếp theo!

---

## 5. TÀI KHOẢN & THÔNG TIN MẶC ĐỊNH

Khi chạy lệnh nạp dữ liệu mẫu (`python3 seed_data.py`), hệ thống tạo sẵn các tài khoản:

| Tài Khoản | Mật Khẩu | Vai Trò | Quyền Hạn |
| :--- | :--- | :--- | :--- |
| **`admin`** | `123456` | Quản trị viên (Admin) | Tạo giải đấu, xếp lịch, đổi mùa, quản lý bot |
| **`player1`** $\dots$ **`player20`** | `123456` | Thí sinh (Player) | Nạp bot, xem thứ hạng cá nhân, xem replay |

---

*Tài liệu được biên soạn phục vụ đồ án môn học INT3304_1 - Nhóm 2.*
