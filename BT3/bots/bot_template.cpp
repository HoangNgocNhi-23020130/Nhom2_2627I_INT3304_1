/**
 * BOT MẪU C++: bot_template.cpp
 * Mẫu chuẩn cho thí sinh viết bot bằng C++:
 * - Đọc từng dòng JSON từ std::cin
 * - Trích xuất danh sách nước đi legal_moves
 * - Chọn nước đi và in JSON ra std::cout kèm std::endl (flush)
 */

#include <iostream>
#include <string>
#include <vector>
#include <cstdlib>
#include <ctime>

// Cấu trúc nước đi đơn giản
struct Move {
    std::string from;
    std::string to;
    bool isCapture;
};

// Hàm trích xuất nhanh các nước đi từ chuỗi JSON đơn giản
std::vector<Move> extractMoves(const std::string& line) {
    std::vector<Move> moves;
    size_t pos = 0;
    while ((pos = line.find("\"from_notation\":\"", pos)) != std::string::npos) {
        pos += 17;
        std::string from = line.substr(pos, 2);
        
        size_t toPos = line.find("\"to_notation\":\"", pos);
        if (toPos != std::string::npos && toPos - pos < 50) {
            toPos += 15;
            std::string to = line.substr(toPos, 2);
            moves.push_back({from, to, false});
        }
    }
    return moves;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    srand(time(NULL));

    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;

        if (line.find("\"type\":\"move\"") != std::string::npos || line.find("\"type\": \"move\"") != std::string::npos) {
            std::vector<Move> legalMoves = extractMoves(line);

            if (legalMoves.empty()) {
                std::cout << "{}" << std::endl;
                continue;
            }

            // Chọn ngẫu nhiên 1 nước đi hợp lệ
            int idx = rand() % legalMoves.size();
            Move chosen = legalMoves[idx];

            // In kết quả ra stdout
            std::cout << "{\"from\":\"" << chosen.from << "\",\"to\":\"" << chosen.to << "\"}" << std::endl;
        }
    }
    return 0;
}
