# 🎮 OanTuTi Arena (BT3) - Nền Tảng Thi Đấu Bot & Cờ Oẳn Tù Tì Chiến Thuật

> **Bài tập 3 - Nhóm 2 - Lớp học phần INT3304_1**  
> Dự án nâng cấp nền tảng thi đấu chiến thuật cờ Oẳn Tù Tì 9x9: Tách biệt Pure Game Engine thuần logic, hỗ trợ thi đấu Bot độc lập qua Standard I/O (Python/C++), phát sóng trực tiếp (Live Stream) lên Web theo thời gian thực qua MQTT, hệ thống Replay chuyên nghiệp và tổ chức giải đấu tự động (Tournament Runner).

---

## 🌐 Đường Dẫn Trực Tiếp Đến Web Game

Bạn có thể truy cập và trải nghiệm game trực tiếp trên trình duyệt tại:

👉 **[https://hoangngocnhi-23020130.github.io/Nhom2_2627I_INT3304_1/BT3/](https://hoangngocnhi-23020130.github.io/Nhom2_2627I_INT3304_1/BT3/)**  
👉 *(Hoặc qua link gốc repository tự động chuyển hướng: [https://hoangngocnhi-23020130.github.io/Nhom2_2627I_INT3304_1/](https://hoangngocnhi-23020130.github.io/Nhom2_2627I_INT3304_1/))*

---

## 🚀 Hướng Dẫn Khởi Chạy Nhanh Trên Máy Cục Bộ

Dự án không yêu cầu cài đặt dependencies phức tạp. Bạn có thể khởi chạy bằng một trong các cách sau:

### Cách 1: Sử dụng Python HTTP Server (Khuyên dùng)
```bash
# Di chuyển vào thư mục BT3
cd BT3

# Khởi chạy server ở cổng 8080 (hoặc 5500, 8000)
python3 -m http.server 8080
```
Mở trình duyệt truy cập: `http://localhost:8080`

### Cách 2: Sử dụng Live Server (VS Code / Antigravity IDE)
1. Mở thư mục `BT3` trong VS Code hoặc Antigravity IDE.
2. Nhấp chuột phải vào file `index.html` chọn **"Open with Live Server"**.

---

## 📖 Luật Chơi OanTuTi Chiến Thuật 9x9 (Version 2.0)

### 1. Bàn cờ và Bố cục quân cờ
- **Bàn cờ:** Kích thước **9x9** (cột `a`..`i`, hàng `1`..`9`).
- **Quân cờ:** Mỗi bên sở hữu **18 quân cờ**, chia đều:
  - ✊ **6 quân Đấm (Rock)**
  - ✋ **6 quân Lá (Paper)**
  - ✌️ **6 quân Kéo (Scissors)**
- **Ô Nhà & Ô Đích:**
  - **P1 (Người chơi 1 - Xanh Dương):** Xuất phát ở nửa dưới. Ô nhà là **`a1`**, ô đích cần chiếm là **`i9`** (góc trên phải).
  - **P2 (Người chơi 2 - Đỏ Hồng):** Xuất phát ở nửa trên. Ô nhà là **`i9`**, ô đích cần chiếm là **`a1`** (góc dưới trái).
  - 🚫 **Ràng buộc quan trọng:** Quân của người chơi **tuyệt đối không được đi vào ô nhà của chính mình** (`a1` cho P1 và `i9` cho P2). Chỉ quân đối phương mới được phép tiến vào ô nhà của đối thủ để giành chiến thắng.
- **Bố trí khởi đầu:** Các quân được xếp đối xứng qua đường chéo chính. 3 đường chéo trung tâm ban đầu và 2 ô nhà hoàn toàn để trống.

---

### 2. Quy tắc di chuyển & Giao tranh
- **Di chuyển:** Mỗi lượt đi 1 quân theo **8 hướng** (ngang, dọc, chéo), mỗi lần đi **1 ô**.
- **Giao tranh (Ăn quân):**
  - ✊ **Đấm** ăn ✌️ **Kéo**
  - ✌️ **Kéo** ăn ✋ **Lá**
  - ✋ **Lá** ăn ✊ **Đấm**
- **Quy tắc chặn đường:** Hai quân **cùng loại** (Đấm gặp Đấm, Kéo gặp Kéo, Lá gặp Lá) **không thể ăn nhau** mà chỉ đứng chặn đường nhau. Quân yếu hơn không thể đi vào ô quân khắc mình.

---

### 3. Điều kiện chiến thắng (4 cách kết thúc)
1. 🎯 **Chiếm ô đích đối phương:** P1 đưa quân vào `i9` hoặc P2 đưa quân vào `a1`.
2. ⚔️ **Diệt chủng 1 loại quân (Extinction):** Tiêu diệt toàn bộ quân của bất kỳ 1 loài nào của đối thủ (hết sạch Đấm, hoặc Lá, hoặc Kéo).
3. 💀 **Hết sạch quân:** Bên nào hết sạch 18 quân cờ trên bàn trước thì thua.
4. ⏱️ **Giới hạn lượt (Turn Limit):** Sau **200 lượt**, bên nào còn nhiều quân cờ hơn sẽ thắng; nếu bằng quân thì hòa.

---

## 🤖 Hệ Thống Đấu Bot & Xem Trực Tiếp (Live Stream)

### 1. Giao thức nạp Bot (Bot Protocol qua `stdin/stdout`)
Hệ thống cho phép nạp bot viết bằng **Python**, **C++**, hoặc bất kỳ ngôn ngữ nào mà không cần lập trình mạng:
- **Đọc vào (`stdin`):** Nhận dòng JSON chứa thế cờ và danh sách nước đi hợp lệ `legal_moves`:
  ```json
  {"type": "move", "turn": 1, "move_count": 14, "board": [...], "legal_moves": [{"from_notation": "b2", "to_notation": "c3"}, ...]}
  ```
- **In ra (`stdout`):** Bot in JSON nước đi đã chọn trong thời gian $\le 200\text{ms}$:
  ```json
  {"from": "b2", "to": "c3"}
  ```

### 2. Thư mục Bot mẫu (`bots/`)
- `bots/bot_random.py`: Bot chọn ngẫu nhiên nước đi hợp lệ.
- `bots/bot_rusher.py`: Bot chạy nước rút nhanh nhất về ô đích đối phương.
- `bots/bot_smart.py`: Bot AI công - thủ toàn diện, săn lùng loài sắp diệt chủng của đối thủ.
- `bots/bot_template.cpp`: Mẫu chuẩn viết bằng C++ (tự động biên dịch khi chạy).

---

### 3. Trọng tài chạy trận đấu & Phát sóng LIVE (`run_match.py`)
Khởi chạy trận đấu giữa 2 bot và phát sóng trực tiếp lên Web qua MQTT:
```bash
python3 run_match.py bots/bot_smart.py bots/bot_rusher.py --room ARENA_01 --delay 0.4
```
- Khán giả chỉ cần mở Web game, nhấp **"🔴 XEM LIVE"** tại phòng `ARENA_01` để xem từng nước đi của 2 bot theo thời gian thực (hiệu ứng ăn quân, âm thanh, thời gian phản hồi ms).
- Tự động xuất file Replay trận đấu vào `replays/`.

---

### 4. Giải đấu Vòng tròn tự động (`run_tournament.py`)
Tự động quét các bot trong thư mục `bots/`, cho đấu vòng tròn 2 lượt (lượt đi và lượt về đổi bên) và xuất Bảng Xếp Hạng:
```bash
python3 run_tournament.py --timeout 0.2
```
- Tự động tính điểm: Thắng = 3 điểm, Hòa = 1 điểm, Thua = 0 điểm.
- Tự động xuất file **`leaderboard.html`** đẹp mắt và lưu trữ toàn bộ Replay của từng trận đấu.

---

## 🎬 Trình Phát & Phân Tích Replay (Replay Viewer)

- **Xem lại từng nước đi:** Thanh trượt Slider tua nhanh đến bất kỳ bước nào ($0 \dots N$), nút Tới/Lùi, Nhảy về đầu/cuối.
- **Tự động phát lại:** Tùy chỉnh tốc độ $0.5\times, 1\times, 2\times$.
- **Xuất / Nhập JSON:** Lưu trữ ván đấu thành file `.json` hoặc tải file từ máy tính lên xem lại.
- **🎯 Tính năng "Thử đi khác từ nước này":** Cho phép rẽ nhánh (fork) ván đấu từ bất kỳ thế cờ nào trong Replay để người chơi trực tiếp cầm quân đấu tiếp với AI.

---

## 📁 Cấu Trúc Mã Nguồn

```
BT3/
├── index.html             # Giao diện chính Web Client
├── leaderboard.html       # Bảng xếp hạng giải đấu Bot HTML
├── engine.py              # Pure Game Engine (Python)
├── run_match.py           # Trọng tài điều phối trận đấu & Livestream MQTT
├── run_tournament.py      # Bộ chạy giải đấu tự động Round-Robin
├── bots/                  # Thư mục chứa các Bot dự thi
│   ├── bot_random.py
│   ├── bot_rusher.py
│   ├── bot_smart.py
│   └── bot_template.cpp
├── js/                    # Client JavaScript Modules
│   ├── rules.js           # Cấu hình luật chuẩn (Version 2.0)
│   ├── engine.js          # Pure Game Engine độc lập DOM/UI
│   ├── replay.js          # Replay Manager & Replay Viewer
│   ├── network.js         # Kết nối mạng MQTT & Lobby Sync
│   ├── audio.js           # Bộ phát âm thanh Web Audio API
│   ├── game.js            # Điều phối trò chơi & Chế độ Bot Arena
│   └── ui.js              # Xử lý giao diện & Sự kiện người dùng
└── replays/               # Kho lưu trữ các file Replay JSON
```

---

## 👥 Nhóm Tác Giả

- **Nhóm 2** - Lớp môn học: **INT3304_1**
- **Danh sách thành viên:**
  1. **Dương Văn Hiệu**
  2. **Hoàng Ngọc Nhi**
  3. **Nguyễn Hoàng Vũ**
  4. **Nguyễn Lưu Vũ**
