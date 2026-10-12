# 🎮 Nhom2_2627I_INT3304_1 - Kho Bài Tập & Nền Tảng Cờ Oẳn Tù Tì Chiến Thuật

> **Nhóm 2 - Lớp học phần: INT3304_1 (Mạng máy tính)**  
> **Giảng viên hướng dẫn:** Bộ môn Mạng & Truyền thông máy tính  
> **Thành viên nhóm:**
> 1. **Dương Văn Hiệu**
> 2. **Hoàng Ngọc Nhi**
> 3. **Nguyễn Hoàng Vũ**
> 4. **Nguyễn Lưu Vũ**

---

## 🌐 Đường Dẫn Trực Tiếp Đến Web Game Mới (BT3)

Trải nghiệm trực tiếp trên trình duyệt qua GitHub Pages:

👉 **[https://hoangngocnhi-23020130.github.io/Nhom2_2627I_INT3304_1/BT3/](https://hoangngocnhi-23020130.github.io/Nhom2_2627I_INT3304_1/BT3/)**  
*(Hoặc truy cập link gốc tự động chuyển hướng: [https://hoangngocnhi-23020130.github.io/Nhom2_2627I_INT3304_1/](https://hoangngocnhi-23020130.github.io/Nhom2_2627I_INT3304_1/))*

---

## 📂 Danh Sách Bài Tập Trong Repository

| Thư mục | Tên Bài Tập | Mô Tả & Tính Năng Nổi Bật | Đường Dẫn Web |
| :--- | :--- | :--- | :--- |
| **`BT3/`** *(Mới nhất)* | **OanTuTi Arena (Đấu Bot & Live Stream)** | • Tách Pure Game Engine thuần logic độc lập (Python & JS).<br>• Giao thức đấu Bot qua Standard I/O (Python/C++).<br>• Trọng tài phát sóng **LIVE STREAM** lên Web qua MQTT broker.<br>• Bộ chạy giải đấu vòng tròn tự động (`run_tournament.py`) xuất BXH HTML.<br>• Hệ thống Replay chuyên nghiệp (tua bước, fork nhánh mới). | [👉 Vào xem BT3](https://hoangngocnhi-23020130.github.io/Nhom2_2627I_INT3304_1/BT3/) |
| **`BT2/`** | **Socket Programming (C/C++)** | • Lập trình mạng TCP Socket Server & Client đa luồng. | [Thư mục BT2](BT2/) |
| **`BT1/`** | **OanTuTi Online v2 (Web)** | • Phiên bản web cờ Oẳn Tù Tì ban đầu kết hợp MQTT và đấu AI cơ bản. | [👉 Vào xem BT1](https://hoangngocnhi-23020130.github.io/Nhom2_2627I_INT3304_1/BT1/) |

---

## 🚀 Hướng Dẫn Chạy Cục Bộ (Local)

### 1. Khởi chạy Web Client (BT3):
```bash
cd BT3
python3 -m http.server 8080
```
Mở trình duyệt tại: `http://localhost:8080`

### 2. Chạy Trận Đấu 2 Bot & Phát Sóng Trực Tiếp:
```bash
cd BT3
python3 run_match.py bots/bot_smart.py bots/bot_rusher.py --room ARENA_01 --delay 0.4
```

### 3. Chạy Giải Đấu Tự Động (Tournament):
```bash
cd BT3
python3 run_tournament.py --timeout 0.2
```
Xem Bảng xếp hạng tại `BT3/leaderboard.html`.
