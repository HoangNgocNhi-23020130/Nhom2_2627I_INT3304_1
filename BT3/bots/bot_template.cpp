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

// Hàm trích xuất nhanh các nước đi từ chuỗi JSON đơn giản (chống lỗi khoảng trắng)
std::vector<Move> extractMoves(const std::string& line) {
    std::vector<Move> moves;
    size_t pos = 0;
    while ((pos = line.find("\"from_notation\"", pos)) != std::string::npos) {
        size_t colonFrom = line.find(':', pos);
        if (colonFrom == std::string::npos) break;
        size_t q1 = line.find('"', colonFrom);
        if (q1 == std::string::npos) break;
        size_t q2 = line.find('"', q1 + 1);
        if (q2 == std::string::npos) break;
        std::string from = line.substr(q1 + 1, q2 - q1 - 1);

        size_t toKey = line.find("\"to_notation\"", q2);
        if (toKey == std::string::npos || toKey - q2 > 150) {
            pos = q2;
            continue;
        }
        size_t colonTo = line.find(':', toKey);
        if (colonTo == std::string::npos) break;
        size_t q3 = line.find('"', colonTo);
        if (q3 == std::string::npos) break;
        size_t q4 = line.find('"', q3 + 1);
        if (q4 == std::string::npos) break;
        std::string to = line.substr(q3 + 1, q4 - q3 - 1);

        moves.push_back({from, to, false});
        pos = q4;
    }
    return moves;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    srand(static_cast<unsigned int>(time(NULL)));

    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;

        if (line.find("\"type\"") != std::string::npos && line.find("\"move\"") != std::string::npos) {
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
