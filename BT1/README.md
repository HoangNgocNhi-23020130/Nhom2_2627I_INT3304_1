# 🎮 Trò Chơi Oẳn Tù Tì v2 (OTTv2) - Cờ Oẳn Tù Tì Online

> **Bài tập 1 - Nhóm 2 - Lớp học phần INT3304_1**  
> Dự án game đối kháng chiến thuật kết hợp giữa cờ bàn 9x9 và quy tắc Oẳn Tù Tì kinh điển, hỗ trợ chơi Online nhiều người qua WebSockets/MQTT và chế độ đấu với Máy (AI).

---

## 🌐 Đường Dẫn Trực Tiếp Đến Web

Bạn có thể truy cập và trải nghiệm game trực tiếp tại địa chỉ:

👉 **[https://hoangngocnhi-23020130.github.io/Nhom2_2627I_INT3304_1/BT1/](https://hoangngocnhi-23020130.github.io/Nhom2_2627I_INT3304_1/BT1/)**

---

## 🚀 Hướng Dẫn Chạy Web Trên Máy Cục Bộ

Dự án được xây dựng hoàn toàn bằng HTML5, CSS (Tailwind CSS) và Vanilla JavaScript, không yêu cầu cài đặt dependencies phức tạp. Bạn có thể khởi chạy web bằng một trong các cách sau:

### Cách 1: Sử dụng Live Server (VS Code / Antigravity IDE) - Khuyên Dùng
1. Mở thư mục dự án trong **VS Code** hoặc **Antigravity IDE**.
2. Cài đặt Extension **Live Server** (của *Ritwick Dey*) nếu chưa có.
3. Nhấp chuột phải vào file [`index.html`](file:///Users/hoangngocnhi/Documents/BT1_Nhom2_2627I_INT3304_1/BT1/index.html) và chọn **"Open with Live Server"** (mặc định cổng `5500`).
4. Truy cập trình duyệt tại: `http://localhost:5500/BT1/index.html`.

---

### Cách 2: Sử dụng Python HTTP Server
Nếu máy đã cài đặt Python:
```bash
# Di chuyển vào thư mục BT1
cd BT1

# Chạy server ở cổng 5500 (hoặc cổng bất kỳ như 8000)
python3 -m http.server 5500
```
Sau đó mở trình duyệt và truy cập: `http://localhost:5500`

---

### Cách 3: Sử dụng Node.js (`npx serve` hoặc `http-server`)
```bash
npx -y serve . -p 5500
```

---

## 📖 Hướng Dẫn Luật Chơi Oẳn Tù Tì v2 (OTTv2)

### 1. Bàn cờ và Bố cục quân cờ
- **Bàn cờ:** Kích thước **9x9** (các cột từ `a` đến `i`, các hàng từ `1` đến `9`).
- **Quân cờ:** Mỗi người chơi (P1 & P2) sở hữu **18 quân cờ**, chia đều làm 3 loại:
  - ✊ **6 quân Đấm (Búa)**
  - ✋ **6 quân Lá (Bao)**
  - ✌️ **6 quân Kéo**
- **Ô Đích (Goal):**
  - **P1 (Người chơi 1 - Xanh Dương):** Xuất phát ở nửa dưới, ô đích cần chiếm là **`i9`** (góc trên bên phải).
  - **P2 (Người chơi 2 - Đỏ Hồng):** Xuất phát ở nửa trên, ô đích cần chiếm là **`a1`** (góc dưới bên trái).
- **Bố trí ban đầu:** Các quân được xếp ngẫu nhiên và đối xứng qua đường chéo chính. 3 đường chéo trung tâm ban đầu hoàn toàn để trống để tạo không gian cơ động.

---

### 2. Quy tắc di chuyển
- Mỗi lượt, người chơi được chọn **1 quân cờ** của mình để di chuyển.
- Quân cờ có thể đi **1 ô theo 8 hướng** (trên, dưới, trái, phải và 4 đường chéo) — tương tự như nước đi của quân **Vua trong Cờ Vua**.

---

### 3. Quy tắc ăn quân & Chặn đường
Khi di chuyển vào ô đang có quân của đối phương:
- ✊ **Đấm** ăn ✌️ **Kéo**
- ✌️ **Kéo** ăn ✋ **Lá**
- ✋ **Lá** ăn ✊ **Đấm**
- **Trường hợp CÙNG LOẠI hoặc BỊ ĐỐI PHƯƠNG KHẮC:**
  - Hai quân **cùng loại** (ví dụ Đấm gặp Đấm, Kéo gặp Kéo): **Không thể ăn nhau**, quân đối phương đóng vai trò là vật cản chặn đường.
  - Quân yếu thế hơn không thể đi vào ô của quân khắc chế mình.

---

### 4. Điều kiện chiến thắng (3 cách thắng)
Trận đấu kết thúc ngay lập tức khi một trong các điều kiện sau được thỏa mãn:
1. 🎯 **Chiếm ô đích:**
   - **P1** đưa được bất kỳ quân cờ nào vào ô **`i9`**.
   - **P2** đưa được bất kỳ quân cờ nào vào ô **`a1`**.
2. ⚔️ **Diệt chủng 1 loại quân (Extinction):**
   - Tiêu diệt toàn bộ **6 quân** của bất kỳ loại nào (hết sạch Đấm, hoặc hết sạch Lá, hoặc hết sạch Kéo) của đối thủ.
3. 🏳️ **Đối phương bỏ cuộc:**
   - Đối thủ bấm nút đầu hàng hoặc thoát khỏi phòng giữa chừng.

---

## ✨ Các Chế Độ Chơi & Tính Năng Nổi Bật

### 🌐 1. Chơi Online Đối Kháng (PVP)
- **Tạo phòng (Create Room):** Tự đặt tên phòng, thời gian mỗi lượt đi (15s, 30s, 45s, 60s), và mật khẩu phòng (tùy chọn).
- **Tham gia nhanh (Quick Join):** Tìm và vào ngay các phòng công khai đang chờ đối thủ.
- **Đồng bộ thời gian thực:** Sử dụng kết nối MQTT WebSocket tốc độ cao, không cần cấu hình backend server riêng.

### 🤖 2. Đấu Với Máy (PvE - AI Bot)
- Hỗ trợ 3 cấp độ thông minh:
  - **Dễ (Easy):** Máy đi ngẫu nhiên các nước đi hợp lệ.
  - **Vừa (Medium):** Ưu tiên ăn quân khi có cơ hội và né bị bắt.
  - **Khó (Hard):** Tính toán chiến thuật, nhắm vào việc phong tỏa loại quân ít ỏi của đối thủ hoặc chạy nước rút về ô đích.

### 📜 3. Lịch Sử Đấu (Match History)
- Tự động lưu trữ thông tin kết quả các trận đấu gần nhất:
  - Người chiến thắng, tên hai đấu thủ.
  - Lý do chiến thắng (Chiếm đích, Diệt chủng loại quân, Bỏ cuộc).
  - Tổng số nước đi và tổng thời lượng trận đấu.

### 🎨 4. Giao diện & Hiệu ứng
- Thiết kế hiện đại chuẩn phong cách **Glassmorphism**, hiệu ứng thị giác sắc nét, hỗ trợ âm thanh sống động (nước đi, ăn quân, âm thanh đếm ngược, chiến thắng).

---

## 👥 Nhóm Tác Giả
- **Nhóm 2** - Lớp môn học: **INT3304_1**
- **Danh sách thành viên:**
  1. **Dương Văn Hiệu**
  2. **Hoàng Ngọc Nhi**
  3. **Nguyễn Hoàng Vũ**
  4. **Nguyễn Lưu Vũ**
