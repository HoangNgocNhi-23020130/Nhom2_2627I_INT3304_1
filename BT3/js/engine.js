/**
 * ===== MODULE: PURE GAME ENGINE (LÕI LUẬT & ĐỘNG CƠ BOT) =====
 * Độc lập 100% với DOM, UI và Mạng.
 * Dùng chung được cho Client, Server, Bot Runner và Trình xem Replay.
 */

const PureGameEngine = {
    // Chuyển đổi tọa độ [0..8][0..8] sang ký hiệu cờ 'a1'..'i9'
    toNotation(r, c) {
        return `${String.fromCharCode(97 + c)}${9 - r}`;
    },

    // Chuyển đổi ký hiệu cờ 'a1'..'i9' sang tọa độ { r, c }
    fromNotation(not) {
        if (!not || not.length < 2) return null;
        const c = not.charCodeAt(0) - 97;
        const r = 9 - parseInt(not.substring(1), 10);
        return { r, c };
    },

    // Kiểm tra tọa độ hợp lệ trong bàn cờ
    isValidCoord(r, c, size = 9) {
        return r >= 0 && r < size && c >= 0 && c < size;
    },

    // Tạo bàn cờ rỗng
    createEmptyBoard(size = 9) {
        return Array(size).fill(null).map(() => Array(size).fill(null));
    },

    // Deep clone bàn cờ
    cloneBoard(board) {
        return board.map(row => row.map(cell => cell ? { ...cell } : null));
    },

    // Khởi tạo bàn cờ đối xứng chuẩn (18 quân/bên: 6 Đấm, 6 Lá, 6 Kéo)
    createSymmetricalBoard(rules = window.OTT_RULES) {
        const size = rules.boardSize || 9;
        const b = this.createEmptyBoard(size);

        const p1CandidateSquares = [];
        for (let r = 0; r < size; r++) {
            for (let c = 0; c < size; c++) {
                // Vùng dàn quân P1: nửa dưới đường chéo chính (r - c >= 2), loại trừ ô nhà a1 (r=8, c=0)
                if (r - c >= 2) {
                    if (r === size - 1 && c === 0) continue;
                    p1CandidateSquares.push({ r, c });
                }
            }
        }

        // Xáo trộn ngẫu nhiên các ô hợp lệ
        for (let i = p1CandidateSquares.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [p1CandidateSquares[i], p1CandidateSquares[j]] = [p1CandidateSquares[j], p1CandidateSquares[i]];
        }

        const chosenP1Positions = p1CandidateSquares.slice(0, 18);

        // Danh sách 18 quân cờ
        const pieceList = [
            'R', 'R', 'R', 'R', 'R', 'R',
            'P', 'P', 'P', 'P', 'P', 'P',
            'S', 'S', 'S', 'S', 'S', 'S'
        ];

        // Xáo trộn thứ tự quân cờ
        for (let i = pieceList.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [pieceList[i], pieceList[j]] = [pieceList[j], pieceList[i]];
        }

        // Đặt quân đối xứng qua đường chéo chính (r <-> c)
        for (let i = 0; i < 18; i++) {
            const posP1 = chosenP1Positions[i];
            const type = pieceList[i];

            b[posP1.r][posP1.c] = { owner: 1, type };
            b[posP1.c][posP1.r] = { owner: 2, type };
        }

        return b;
    },

    // Kiểm tra quân type1 có ăn được quân type2 không theo bảng beats
    beats(type1, type2, rules = window.OTT_RULES) {
        return rules.beats[type1] === type2;
    },

    // Tính toán các nước đi hợp lệ của 1 quân cờ tại tọa độ (r, c)
    getValidMovesForPiece(board, r, c, rules = window.OTT_RULES) {
        const piece = board[r][c];
        if (!piece) return [];

        const size = rules.boardSize || 9;
        const moves = [];
        const directions = [
            [-1, -1], [-1, 0], [-1, 1],
            [0, -1],           [0, 1],
            [1, -1],  [1, 0],  [1, 1]
        ];

        for (const [dr, dc] of directions) {
            const nr = r + dr;
            const nc = c + dc;

            if (this.isValidCoord(nr, nc, size)) {
                // RÀNG BUỘC LUẬT CHƠI: Tuyệt đối không được đi vào ô nhà của chính mình
                const ownHome = (piece.owner === 1)
                    ? (rules.homes?.[1] || { r: size - 1, c: 0 })
                    : (rules.homes?.[2] || { r: 0, c: size - 1 });

                if (rules.allowEnterOwnHome === false && nr === ownHome.r && nc === ownHome.c) {
                    continue; // Cấm đi vào ô nhà mình!
                }

                const target = board[nr][nc];

                if (!target) {
                    // Ô trống: đi được bình thường
                    moves.push({
                        from: { r, c },
                        to: { r: nr, c: nc },
                        r: nr,
                        c: nc,
                        isCapture: false,
                        targetPiece: null
                    });
                } else if (target.owner !== piece.owner) {
                    // Ô có quân đối phương
                    if (this.beats(piece.type, target.type, rules)) {
                        // Khắc chế: ăn được quân đối phương!
                        moves.push({
                            from: { r, c },
                            to: { r: nr, c: nc },
                            r: nr,
                            c: nc,
                            isCapture: true,
                            targetPiece: target
                        });
                    } else if (rules.sameTypeRule === 'eliminate' && piece.type === target.type) {
                        // Luật biến thể triệt tiêu: cùng loại thì cả 2 cùng bị loại
                        moves.push({
                            from: { r, c },
                            to: { r: nr, c: nc },
                            r: nr,
                            c: nc,
                            isCapture: true,
                            isMutualElimination: true,
                            targetPiece: target
                        });
                    }
                    // Nếu cùng loại (ở chế độ 'block') hoặc bị đối phương khắc: bị chặn đường, không thể đi vào.
                }
            }
        }
        return moves;
    },

    // Lấy toàn bộ các nước đi hợp lệ của một người chơi (cho Bot protocol & Engine)
    getAllLegalMoves(board, player, rules = window.OTT_RULES) {
        const legalMoves = [];
        const size = rules.boardSize || 9;

        for (let r = 0; r < size; r++) {
            for (let c = 0; c < size; c++) {
                const p = board[r][c];
                if (p && p.owner === player) {
                    const pieceMoves = this.getValidMovesForPiece(board, r, c, rules);
                    legalMoves.push(...pieceMoves);
                }
            }
        }
        return legalMoves;
    },

    // Thực hiện 1 nước đi thuần logic và trả về bàn cờ mới cùng chi tiết nước đi
    applyMove(board, move, rules = window.OTT_RULES) {
        const newBoard = this.cloneBoard(board);
        const { from, to } = move;
        const movingPiece = newBoard[from.r][from.c];
        const destPiece = newBoard[to.r][to.c];

        let isCapture = false;
        let capturedPiece = null;

        if (destPiece) {
            isCapture = true;
            capturedPiece = destPiece;
        }

        if (move.isMutualElimination) {
            // Cả hai cùng bị loại
            newBoard[from.r][from.c] = null;
            newBoard[to.r][to.c] = null;
        } else {
            newBoard[to.r][to.c] = movingPiece;
            newBoard[from.r][from.c] = null;
        }

        return {
            newBoard,
            movingPiece,
            isCapture,
            capturedPiece,
            fromNotation: this.toNotation(from.r, from.c),
            toNotation: this.toNotation(to.r, to.c)
        };
    },

    // Đếm số lượng quân của từng bên
    countRemainingPieces(board) {
        const counts = {
            1: { R: 0, P: 0, S: 0, total: 0 },
            2: { R: 0, P: 0, S: 0, total: 0 }
        };

        for (let r = 0; r < board.length; r++) {
            for (let c = 0; c < board[r].length; c++) {
                const p = board[r][c];
                if (p && counts[p.owner]) {
                    counts[p.owner][p.type] = (counts[p.owner][p.type] || 0) + 1;
                    counts[p.owner].total++;
                }
            }
        }
        return counts;
    },

    // Kiểm tra điều kiện thắng cuộc
    checkVictory(board, rules = window.OTT_RULES, moveCount = 0) {
        const p1Goal = rules.goals[1];
        const p2Goal = rules.goals[2];

        // 1. Điều kiện chiếm ô đích
        if (rules.winConditions.reachGoal) {
            if (board[p1Goal.r][p1Goal.c] && board[p1Goal.r][p1Goal.c].owner === 1) {
                return {
                    winner: 1,
                    reason: `Người chơi 1 (Blue) đã đưa quân chiếm thành công ô đích ${p1Goal.notation}!`,
                    reasonType: 'base'
                };
            }
            if (board[p2Goal.r][p2Goal.c] && board[p2Goal.r][p2Goal.c].owner === 2) {
                return {
                    winner: 2,
                    reason: `Người chơi 2 (Red) đã đưa quân chiếm thành công ô đích ${p2Goal.notation}!`,
                    reasonType: 'base'
                };
            }
        }

        // 2. Điều kiện hết sạch toàn bộ quân
        const counts = this.countRemainingPieces(board);

        if (counts[1].total === 0 && counts[2].total === 0) {
            return { winner: 0, reason: 'Ván đấu hòa do cả 2 bên cùng hết sạch quân cờ!', reasonType: 'draw' };
        }
        if (counts[1].total === 0) {
            return { winner: 2, reason: 'P2 thắng do P1 đã hết sạch toàn bộ quân cờ trên bàn!', reasonType: 'extinction' };
        }
        if (counts[2].total === 0) {
            return { winner: 1, reason: 'P1 thắng do P2 đã hết sạch toàn bộ quân cờ trên bàn!', reasonType: 'extinction' };
        }

        // 3. Điều kiện diệt chủng 1 loài quân
        if (rules.winConditions.extinctionAnyType) {
            const p1Extinct = (counts[1].R === 0 ? 'Đấm (✊)' : (counts[1].P === 0 ? 'Lá (✋)' : (counts[1].S === 0 ? 'Kéo (✌️)' : null)));
            const p2Extinct = (counts[2].R === 0 ? 'Đấm (✊)' : (counts[2].P === 0 ? 'Lá (✋)' : (counts[2].S === 0 ? 'Kéo (✌️)' : null)));

            if (p1Extinct && p2Extinct) {
                return { winner: 0, reason: 'Ván đấu hòa do cả 2 bên cùng bị tuyệt chủng một loại quân cùng lúc!', reasonType: 'draw' };
            }
            if (p2Extinct) {
                return { winner: 1, reason: `P1 thắng do P2 đã bị tiêu diệt sạch toàn bộ quân ${p2Extinct}!`, reasonType: 'extinction' };
            }
            if (p1Extinct) {
                return { winner: 2, reason: `P2 thắng do P1 đã bị tiêu diệt sạch toàn bộ quân ${p1Extinct}!`, reasonType: 'extinction' };
            }
        }

        // 4. Giới hạn số lượt (Turn Limit)
        if (rules.winConditions.turnLimit && rules.maxTurns && moveCount >= rules.maxTurns) {
            if (counts[1].total > counts[2].total) {
                return { winner: 1, reason: `Hết giới hạn ${rules.maxTurns} lượt: P1 thắng do còn nhiều quân hơn (${counts[1].total} vs ${counts[2].total})!`, reasonType: 'turn_limit' };
            } else if (counts[2].total > counts[1].total) {
                return { winner: 2, reason: `Hết giới hạn ${rules.maxTurns} lượt: P2 thắng do còn nhiều quân hơn (${counts[2].total} vs ${counts[1].total})!`, reasonType: 'turn_limit' };
            } else {
                return { winner: 0, reason: `Hết giới hạn ${rules.maxTurns} lượt: Ván đấu kết thúc hòa (ngang số lượng quân)!`, reasonType: 'turn_limit' };
            }
        }

        return null;
    },

    // ===== BỘ THUẬT TOÁN BOT ĐA CHIẾN THUẬT (PLUGGABLE BOT ENGINES) =====
    BOT_STRATEGIES: {
        // 1. Bot Ngẫu nhiên (Random): Đi một nước ngẫu nhiên trong legal moves
        random(board, player, legalMoves) {
            if (!legalMoves || legalMoves.length === 0) return null;
            return legalMoves[Math.floor(Math.random() * legalMoves.length)];
        },

        // 2. Bot Tham lam (Greedy): Ưu tiên ăn quân có lợi, né ăn đòn
        greedy(board, player, legalMoves, rules) {
            if (!legalMoves || legalMoves.length === 0) return null;

            const scoredMoves = legalMoves.map(m => {
                let score = 0;
                const oppGoal = rules.goals[player];

                // Nếu chiếm được đích -> thắng ngay!
                if (m.to.r === oppGoal.r && m.to.c === oppGoal.c) {
                    score += 10000;
                }

                // Điểm ăn quân
                if (m.isCapture) {
                    score += 350;
                }

                // Điểm kiểm tra an toàn sau khi đi
                const movingPiece = board[m.from.r][m.from.c];
                let inDanger = false;
                for (let dr = -1; dr <= 1; dr++) {
                    for (let dc = -1; dc <= 1; dc++) {
                        const er = m.to.r + dr;
                        const ec = m.to.c + dc;
                        if (PureGameEngine.isValidCoord(er, ec, rules.boardSize)) {
                            const enemy = board[er][ec];
                            if (enemy && enemy.owner !== player && PureGameEngine.beats(enemy.type, movingPiece.type, rules)) {
                                inDanger = true;
                            }
                        }
                    }
                }
                if (inDanger) score -= 200;

                score += Math.random() * 15;
                return { ...m, score };
            });

            scoredMoves.sort((a, b) => b.score - a.score);
            return scoredMoves[0];
        },

        // 3. Bot Lao Nhanh (Rusher): Tối đa hóa tốc độ tiến về ô đích đối phương
        rusher(board, player, legalMoves, rules) {
            if (!legalMoves || legalMoves.length === 0) return null;
            const oppGoal = rules.goals[player];

            const scoredMoves = legalMoves.map(m => {
                let score = 0;
                if (m.to.r === oppGoal.r && m.to.c === oppGoal.c) score += 10000;

                // Khoảng cách Chebyshev tới đích
                const curDist = Math.max(Math.abs(oppGoal.r - m.from.r), Math.abs(oppGoal.c - m.from.c));
                const newDist = Math.max(Math.abs(oppGoal.r - m.to.r), Math.abs(oppGoal.c - m.to.c));
                score += (curDist - newDist) * 50;

                if (m.isCapture) score += 150;
                score += Math.random() * 10;
                return { ...m, score };
            });

            scoredMoves.sort((a, b) => b.score - a.score);
            return scoredMoves[0];
        },

        // 4. Bot Đa Năng Thông Minh (Smart): Cân bằng công thủ, săn lùng loài sắp diệt chủng
        smart(board, player, legalMoves, rules) {
            if (!legalMoves || legalMoves.length === 0) return null;
            const oppGoal = rules.goals[player];
            const ownGoal = rules.goals[player === 1 ? 2 : 1];
            const counts = PureGameEngine.countRemainingPieces(board);
            const opponent = player === 1 ? 2 : 1;

            const scoredMoves = legalMoves.map(m => {
                let score = 0;
                const movingPiece = board[m.from.r][m.from.c];

                // Ưu tiên 1: Chiếm đích thắng ngay!
                if (m.to.r === oppGoal.r && m.to.c === oppGoal.c) {
                    return { ...m, score: 999999 };
                }

                // Ưu tiên 2: Tiến gần ô đích đối phương
                const curDist = Math.max(Math.abs(oppGoal.r - m.from.r), Math.abs(oppGoal.c - m.from.c));
                const newDist = Math.max(Math.abs(oppGoal.r - m.to.r), Math.abs(oppGoal.c - m.to.c));
                score += (curDist - newDist) * 35;

                // Ưu tiên 3: Ăn quân đối phương
                if (m.isCapture && m.targetPiece) {
                    score += 300;
                    // Nếu loài quân này của đối thủ chỉ còn <= 2 con -> Săn lùng để diệt chủng!
                    if (counts[opponent][m.targetPiece.type] <= 2) {
                        score += 500;
                    }
                }

                // Ưu tiên 4: Bảo vệ ô nhà mình nếu đối phương áp sát
                const enemyDistToHome = Math.max(Math.abs(ownGoal.r - m.to.r), Math.abs(ownGoal.c - m.to.c));
                if (enemyDistToHome <= 1) {
                    score += 80;
                }

                // Ưu tiên 5: Tránh rơi vào ô bị địch ăn thịt
                let inDanger = false;
                for (let dr = -1; dr <= 1; dr++) {
                    for (let dc = -1; dc <= 1; dc++) {
                        const er = m.to.r + dr;
                        const ec = m.to.c + dc;
                        if (PureGameEngine.isValidCoord(er, ec, rules.boardSize)) {
                            const enemy = board[er][ec];
                            if (enemy && enemy.owner === opponent && PureGameEngine.beats(enemy.type, movingPiece.type, rules)) {
                                inDanger = true;
                            }
                        }
                    }
                }
                if (inDanger) {
                    score -= 220;
                    // Nếu loài quân này của mình chỉ còn <= 2 con -> bảo toàn tính mạng tuyệt đối!
                    if (counts[player][movingPiece.type] <= 2) {
                        score -= 300;
                    }
                }

                score += Math.random() * 8;
                return { ...m, score };
            });

            scoredMoves.sort((a, b) => b.score - a.score);
            return scoredMoves[0];
        }
    },

    // Hàm gọi nước đi của Bot theo tên chiến thuật
    getBotMove(board, player, strategyName = 'smart', rules = window.OTT_RULES) {
        const legalMoves = this.getAllLegalMoves(board, player, rules);
        if (!legalMoves || legalMoves.length === 0) return null;

        const strategy = this.BOT_STRATEGIES[strategyName] || this.BOT_STRATEGIES.smart;
        return strategy(board, player, legalMoves, rules);
    }
};

window.PureGameEngine = PureGameEngine;
