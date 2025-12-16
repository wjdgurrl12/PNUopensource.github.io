"""
Core game logic for Minesweeper.

This module contains pure domain logic without any pygame or pixel-level
concerns. It defines:
- CellState: the state of a single cell
- Cell: a cell positioned by (col,row) with an attached CellState
- Board: grid management, mine placement, adjacency computation, reveal/flag

The Board exposes imperative methods that the presentation layer (run.py)
can call in response to user inputs, and does not know anything about
rendering, timing, or input devices.
"""

import random
from typing import List, Tuple


class CellState:
    """Mutable state of a single cell.

    Attributes:
        is_mine: Whether this cell contains a mine.
        is_revealed: Whether the cell has been revealed to the player.
        is_flagged: Whether the player flagged this cell as a mine.
        is_question: Whether the player marked this cell as '?'.
        adjacent: Number of adjacent mines in the 8 neighboring cells.
    """

    def __init__(
        self,
        is_mine: bool = False,
        is_revealed: bool = False,
        is_flagged: bool = False,
        is_question: bool = False,
        adjacent: int = 0,
    ):
        self.is_mine = is_mine
        self.is_revealed = is_revealed
        self.is_flagged = is_flagged
        self.is_question = is_question
        self.adjacent = adjacent



class Cell:
    """Logical cell positioned on the board by column and row."""

    def __init__(self, col: int, row: int):
        self.col = col
        self.row = row
        self.state = CellState()


class Board:
    """Minesweeper board state and rules.

    Responsibilities:
    - Generate and place mines with first-click safety
    - Compute adjacency counts for every cell
    - Reveal cells (iterative flood fill when adjacent == 0)
    - Toggle flags, check win/lose conditions
    """

    def __init__(self, cols: int, rows: int, mines: int):
        self.cols = cols
        self.rows = rows
        self.num_mines = mines
        self.cells: List[Cell] = [Cell(c, r) for r in range(rows) for c in range(cols)]
        self._mines_placed = False
        self.revealed_count = 0
        self.game_over = False
        self.win = False

    def index(self, col: int, row: int) -> int:
        """Return the flat list index for (col,row)."""
        return row * self.cols + col

    def is_inbounds(self, col: int, row: int) -> bool:
        # 좌표가 0 이상이고, 보드 크기(cols, rows)보다 작은지 검사
        return 0 <= col < self.cols and 0 <= row < self.rows

    def neighbors(self, col: int, row: int) -> List[Tuple[int, int]]:
        deltas = [
            (-1, -1), (0, -1), (1, -1),
            (-1, 0),            (1, 0),
            (-1, 1),  (0, 1),  (1, 1),
        ]
        result = []
        for dc, dr in deltas:
            nc, nr = col + dc, row + dr
            if self.is_inbounds(nc, nr):
                result.append((nc, nr))
        return result

    def place_mines(self, safe_col: int, safe_row: int) -> None:
        # 1. 모든 좌표 리스트 생성
        all_positions = [(c, r) for r in range(self.rows) for c in range(self.cols)]
        
        # 2. 첫 클릭 위치와 그 주변 8칸은 지뢰 금지 구역 설정
        forbidden = {(safe_col, safe_row)} | set(self.neighbors(safe_col, safe_row))
        
        # 3. 금지 구역을 뺀 위치들 중에서 지뢰 개수만큼 랜덤 샘플링
        pool = [p for p in all_positions if p not in forbidden]
        mine_positions = random.sample(pool, self.num_mines)

        # 4. 지뢰 배치
        for c, r in mine_positions:
            idx = self.index(c, r)
            self.cells[idx].state.is_mine = True

        # 5. 모든 셀에 대해 인접 지뢰 수 계산 (Adjacency counts)
        for cell in self.cells:
            nbs = self.neighbors(cell.col, cell.row)
            mine_count = 0
            for nc, nr in nbs:
                neighbor_idx = self.index(nc, nr)
                if self.cells[neighbor_idx].state.is_mine:
                    mine_count += 1
            cell.state.adjacent = mine_count

        self._mines_placed = True

    def reveal(self, col: int, row: int) -> None:
        if not self.is_inbounds(col, row):
            return

        # 1. 첫 클릭이면 지뢰 배치부터 수행
        if not self._mines_placed:
            self.place_mines(col, row)

        idx = self.index(col, row)
        cell = self.cells[idx]

        # 이미 열렸거나 깃발이 있으면 무시
        if cell.state.is_revealed or cell.state.is_flagged:
            return

        # 2. 셀 오픈
        cell.state.is_revealed = True
        self.revealed_count += 1

        # 3. 지뢰를 밟았을 경우 -> Game Over
        if cell.state.is_mine:
            self.game_over = True
            self._reveal_all_mines()
            return

        # 4. 주변 지뢰가 0개(빈 칸)라면 주변 셀들도 자동으로 재귀 오픈 (Flood Fill)
        if cell.state.adjacent == 0:
            for nc, nr in self.neighbors(col, row):
                self.reveal(nc, nr)

        # 5. 승리 조건 체크
        self._check_win()

    def toggle_flag(self, col: int, row: int) -> None:
        if not self.is_inbounds(col, row):
            return

        idx = self.index(col, row)
        cell = self.cells[idx]

        # 이미 열린 셀은 표식 불가
        if cell.state.is_revealed:
          return

        # 없음 -> 깃발 -> 물음표 -> 없음
        if (not cell.state.is_flagged) and (not cell.state.is_question):
          cell.state.is_flagged = True
          cell.state.is_question = False
        elif cell.state.is_flagged:
          cell.state.is_flagged = False
          cell.state.is_question = True
        else:  # question 상태
          cell.state.is_flagged = False
          cell.state.is_question = False


    def flagged_count(self) -> int:
        count = 0
        for cell in self.cells:
            if cell.state.is_flagged:
                count += 1
        return count

    def _reveal_all_mines(self) -> None:
        """Reveal all mines; called on game over."""
        for cell in self.cells:
            if cell.state.is_mine:
                cell.state.is_revealed = True

    def _check_win(self) -> None:
        """Set win=True when all non-mine cells have been revealed."""
        total_cells = self.cols * self.rows
        if self.revealed_count == total_cells - self.num_mines and not self.game_over:
            self.win = True
            for cell in self.cells:
                if not cell.state.is_revealed and not cell.state.is_mine:
                    cell.state.is_revealed = True
