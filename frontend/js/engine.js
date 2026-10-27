/**
 * frontend/js/engine.js
 * Lõi game engine chạy phía client, nhận rules từ shared/rules.json hoặc API.
 */

const PureGameEngine = {
    rules: null,

    init(rulesConfig) {
        this.rules = rulesConfig;
    },

    toNotation(r, c) {
        return `${String.fromCharCode(97 + c)}${9 - r}`;
    },

    fromNotation(not) {
        if (!not || not.length < 2) return null;
        const c = not.charCodeAt(0) - 97;
        const r = 9 - parseInt(not.substring(1), 10);
        return { r, c };
    },

    isValidCoord(r, c, size = 9) {
        return r >= 0 && r < size && c >= 0 && c < size;
    },

    createEmptyBoard(size = 9) {
        return Array(size).fill(null).map(() => Array(size).fill(null));
    },

    cloneBoard(board) {
        return board.map(row => row.map(cell => cell ? { ...cell } : null));
    },

    createSymmetricalBoard(rules = this.rules) {
        const size = rules.boardSize || 9;
        const b = this.createEmptyBoard(size);
        const home1 = rules.homes[1];

        const candidates = [];
        for (let r = 0; r < size; r++) {
            for (let c = 0; c < size; c++) {
                if (r - c >= 2) {
                    if (r === home1.r && c === home1.c) continue;
                    candidates.push({ r, c });
                }
            }
        }

        for (let i = candidates.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [candidates[i], candidates[j]] = [candidates[j], candidates[i]];
        }

        const pieceList = [];
        for (const [pType, count] of Object.entries(rules.pieceCountsPerPlayer)) {
            for (let k = 0; k < count; k++) pieceList.push(pType);
        }

        for (let i = pieceList.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [pieceList[i], pieceList[j]] = [pieceList[j], pieceList[i]];
        }

        for (let i = 0; i < pieceList.length; i++) {
            const pos = candidates[i];
            const type = pieceList[i];
            b[pos.r][pos.c] = { owner: 1, type };
            b[pos.c][pos.r] = { owner: 2, type };
        }

        return b;
    },

    beats(type1, type2, rules = this.rules) {
        return rules.beats[type1] === type2;
    },

    getValidMovesForPiece(board, r, c, rules = this.rules) {
        const piece = board[r][c];
        if (!piece) return [];

        const size = rules.boardSize || 9;
        const moves = [];
        const directions = [
            [-1, -1], [-1, 0], [-1, 1],
            [0, -1],           [0, 1],
            [1, -1],  [1, 0],  [1, 1]
        ];

        const ownHome = rules.homes[piece.owner];

        for (const [dr, dc] of directions) {
            const nr = r + dr;
            const nc = c + dc;

            if (this.isValidCoord(nr, nc, size)) {
                if (!rules.allowEnterOwnHome && nr === ownHome.r && nc === ownHome.c) {
                    continue;
                }

                const target = board[nr][nc];
                if (!target) {
                    moves.push({
                        from: { r, c },
                        to: { r: nr, c: nc },
                        r: nr,
                        c: nc,
                        isCapture: false,
                        targetPiece: null
                    });
                } else if (target.owner !== piece.owner) {
                    if (this.beats(piece.type, target.type, rules)) {
                        moves.push({
                            from: { r, c },
                            to: { r: nr, c: nc },
                            r: nr,
                            c: nc,
                            isCapture: true,
                            targetPiece: target
                        });
                    } else if (rules.sameTypeRule === 'eliminate' && piece.type === target.type) {
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
                }
            }
        }
        return moves;
    },

    getAllLegalMoves(board, player, rules = this.rules) {
        const legalMoves = [];
        const size = rules.boardSize || 9;
        for (let r = 0; r < size; r++) {
            for (let c = 0; c < size; c++) {
                const p = board[r][c];
                if (p && p.owner === player) {
                    legalMoves.push(...this.getValidMovesForPiece(board, r, c, rules));
                }
            }
        }
        return legalMoves;
    },

    applyMove(board, move, rules = this.rules) {
        const newBoard = this.cloneBoard(board);
        const { from, to } = move;
        const movingPiece = newBoard[from.r][from.c];
        const destPiece = newBoard[to.r][to.c];

        let isCapture = !!destPiece;
        let capturedPiece = destPiece;

        if (move.isMutualElimination) {
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

    checkVictory(board, rules = this.rules, moveCount = 0) {
        const p1Goal = rules.goals[1];
        const p2Goal = rules.goals[2];

        if (rules.winConditions.reachGoal) {
            if (board[p1Goal.r][p1Goal.c]?.owner === 1) {
                return { winner: 1, reason: `P1 chiếm thành công ô đích ${p1Goal.notation}!`, reasonType: 'base' };
            }
            if (board[p2Goal.r][p2Goal.c]?.owner === 2) {
                return { winner: 2, reason: `P2 chiếm thành công ô đích ${p2Goal.notation}!`, reasonType: 'base' };
            }
        }

        const counts = this.countRemainingPieces(board);
        if (counts[1].total === 0 && counts[2].total === 0) {
            return { winner: 0, reason: 'Hòa do cả 2 bên cùng hết quân cờ!', reasonType: 'draw' };
        }
        if (counts[1].total === 0) {
            return { winner: 2, reason: 'P2 thắng do P1 đã hết sạch toàn bộ quân!', reasonType: 'extinction' };
        }
        if (counts[2].total === 0) {
            return { winner: 1, reason: 'P1 thắng do P2 đã hết sạch toàn bộ quân!', reasonType: 'extinction' };
        }

        if (rules.winConditions.extinctionAnyType) {
            const p1Extinct = rules.pieceTypes.some(t => counts[1][t] === 0);
            const p2Extinct = rules.pieceTypes.some(t => counts[2][t] === 0);

            if (p1Extinct && p2Extinct) {
                return { winner: 0, reason: 'Hòa do cả 2 bên cùng bị diệt chủng 1 loại quân!', reasonType: 'draw' };
            }
            if (p2Extinct) {
                return { winner: 1, reason: 'P1 thắng do đối thủ bị diệt chủng 1 loại quân!', reasonType: 'extinction' };
            }
            if (p1Extinct) {
                return { winner: 2, reason: 'P2 thắng do đối thủ bị diệt chủng 1 loại quân!', reasonType: 'extinction' };
            }
        }

        if (rules.winConditions.turnLimit && rules.maxTurns && moveCount >= rules.maxTurns) {
            if (counts[1].total > counts[2].total) {
                return { winner: 1, reason: `Hết ${rules.maxTurns} lượt: P1 thắng vì còn nhiều quân hơn!`, reasonType: 'turn_limit' };
            } else if (counts[2].total > counts[1].total) {
                return { winner: 2, reason: `Hết ${rules.maxTurns} lượt: P2 thắng vì còn nhiều quân hơn!`, reasonType: 'turn_limit' };
            } else {
                return { winner: 0, reason: `Hết ${rules.maxTurns} lượt: Hòa do bằng quân!`, reasonType: 'turn_limit' };
            }
        }

        return null;
    }
};

window.PureGameEngine = PureGameEngine;