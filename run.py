"""
Pygame presentation layer for Minesweeper.
"""

import pygame
import random
import json
import os
import config
from components import Board
from pygame.locals import Rect


# ============================ Renderer ============================

class Renderer:
    def __init__(self, screen: pygame.Surface, board: Board):
        self.screen = screen
        self.board = board
        self.font = pygame.font.Font(config.font_name, config.font_size)
        self.header_font = pygame.font.Font(config.font_name, config.header_font_size)
        self.result_font = pygame.font.Font(config.font_name, config.result_font_size)

    def cell_rect(self, col: int, row: int):
        x = config.margin_left + col * config.cell_size
        y = config.margin_top + row * config.cell_size
        return Rect(x, y, config.cell_size, config.cell_size)

    def draw_cell(self, col: int, row: int, highlighted: bool) -> None:
        cell = self.board.cells[self.board.index(col, row)]
        rect = self.cell_rect(col, row)

        if cell.state.is_revealed:
            pygame.draw.rect(self.screen, config.color_cell_revealed, rect)
            if cell.state.is_mine:
                pygame.draw.circle(
                    self.screen,
                    config.color_cell_mine,
                    rect.center,
                    rect.width // 4,
                )
            elif cell.state.adjacent > 0:
                label = self.font.render(
                    str(cell.state.adjacent),
                    True,
                    config.number_colors.get(cell.state.adjacent, config.color_text),
                )
                self.screen.blit(label, label.get_rect(center=rect.center))
        else:
            base_color = config.color_highlight if highlighted else config.color_cell_hidden
            pygame.draw.rect(self.screen, base_color, rect)

            # FLAG
            if cell.state.is_flagged:
                flag_w = max(6, rect.width // 3)
                flag_h = max(8, rect.height // 2)
                pole_x = rect.left + rect.width // 3
                pole_y = rect.top + 4

                pygame.draw.line(
                    self.screen,
                    config.color_flag,
                    (pole_x, pole_y),
                    (pole_x, pole_y + flag_h),
                    2,
                )
                pygame.draw.polygon(
                    self.screen,
                    config.color_flag,
                    [
                        (pole_x + 2, pole_y),
                        (pole_x + 2 + flag_w, pole_y + flag_h // 3),
                        (pole_x + 2, pole_y + flag_h // 2),
                    ],
                )

            # QUESTION MARK
            elif cell.state.is_question:
                q = self.font.render("?", True, config.color_header_text)
                self.screen.blit(q, q.get_rect(center=rect.center))

        pygame.draw.rect(self.screen, config.color_grid, rect, 1)

    def draw_header(self, remaining: int, time_text: str, best_text: str, difficulty_label: int) -> None:
     pygame.draw.rect(
        self.screen,
        config.color_header,
        Rect(0, 0, config.width, config.margin_top - 4),
    )

     left = self.header_font.render(
        f"Mines: {remaining}", True, config.color_header_text
        )
     mid = self.header_font.render(
        f"Best: {best_text}", True, config.color_header_text
    )
     right = self.header_font.render(
        f"{difficulty_label}  Time: {time_text}",
        True,
        config.color_header_text,
    )

     self.screen.blit(left, (10, 12))
     self.screen.blit(mid, (10, 36))
     self.screen.blit(right, (config.width - right.get_width() - 10, 12))


    def draw_result_overlay(self, text: str | None) -> None:
        if not text:
            return
        overlay = pygame.Surface((config.width, config.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, config.result_overlay_alpha))
        self.screen.blit(overlay, (0, 0))
        label = self.result_font.render(text, True, config.color_result)
        self.screen.blit(label, label.get_rect(center=(config.width // 2, config.height // 2)))

    def draw_pause_overlay(self) -> None:
        overlay = pygame.Surface((config.width, config.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))
        label = self.result_font.render("PAUSED", True, config.color_result)
        self.screen.blit(label, label.get_rect(center=(config.width // 2, config.height // 2)))


# ============================ Input ============================

class InputController:
    def __init__(self, game: "Game"):
        self.game = game

    def pos_to_grid(self, x: int, y: int):
        if not (config.margin_left <= x < config.width - config.margin_right):
            return -1, -1
        if not (config.margin_top <= y < config.height - config.margin_bottom):
            return -1, -1
        col = (x - config.margin_left) // config.cell_size
        row = (y - config.margin_top) // config.cell_size
        return (col, row) if self.game.board.is_inbounds(col, row) else (-1, -1)

    def handle_mouse(self, pos, button) -> None:
        col, row = self.pos_to_grid(pos[0], pos[1])
        if col == -1:
            return

        game = self.game

        if button == config.mouse_left:
            if not game.started:
                game.started = True
                game.start_ticks_ms = pygame.time.get_ticks()
            game.board.reveal(col, row)
        elif button == config.mouse_right:
            game.board.toggle_flag(col, row)


# ============================ Game ============================

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(config.title)
        self.clock = pygame.time.Clock()

        # Difficulty (#1)
        self.difficulty = config.DEFAULT_DIFFICULTY
        self._load_difficulty()

        self.screen = pygame.display.set_mode(config.display_dimension)
        self.board = Board(self.cols, self.rows, self.mines)
        self.renderer = Renderer(self.screen, self.board)
        self.input = InputController(self)

        # State / timing
        self.started = False
        self.start_ticks_ms = 0
        self.end_ticks_ms = 0

        # Hint (#2)
        self.hint_used = False
        self.highlight_targets = set()
        self.highlight_until_ms = 0

        # High score (#3)
        self.best_ms = self._load_best_time()

        # Pause (#4)
        self.paused = False
        self.pause_start_ms = 0
        self.paused_accum_ms = 0

    # -------- Difficulty --------
    def _load_difficulty(self):
        preset = config.DIFFICULTY_PRESETS[self.difficulty]
        self.cols = preset["cols"]
        self.rows = preset["rows"]
        self.mines = preset["mines"]

        config.cols = self.cols
        config.rows = self.rows
        config.num_mines = self.mines
        config.width = config.margin_left + self.cols * config.cell_size + config.margin_right
        config.height = config.margin_top + self.rows * config.cell_size + config.margin_bottom
        config.display_dimension = (config.width, config.height)

    def set_difficulty(self, difficulty: str):
        if difficulty in config.DIFFICULTY_PRESETS:
            self.difficulty = difficulty
            self.reset()
    def _difficulty_label(self) -> int:
    # EASY/NORMAL/HARD -> 1/2/3
     mapping = {"EASY": 1, "NORMAL": 2, "HARD": 3}
     return mapping.get(self.difficulty, 0)


    # -------- Hint --------
    def use_hint(self):
        if self.hint_used or self.board.game_over or self.board.win:
            return

        safe = [
            (c, r)
            for r in range(self.board.rows)
            for c in range(self.board.cols)
            if not self.board.cells[self.board.index(c, r)].state.is_revealed
            and not self.board.cells[self.board.index(c, r)].state.is_mine
        ]
        if not safe:
            return

        self.highlight_targets = {random.choice(safe)}
        self.highlight_until_ms = pygame.time.get_ticks() + 2000
        self.hint_used = True

    # -------- High score --------
    def _load_best_time(self):
        if not os.path.exists("best_time.json"):
            return None
        try:
            with open("best_time.json", "r", encoding="utf-8") as f:
                return json.load(f).get("best_ms")
        except Exception:
            return None

    def _save_best_time(self, ms):
        with open("best_time.json", "w", encoding="utf-8") as f:
            json.dump({"best_ms": ms}, f)

    # -------- Pause --------
    def toggle_pause(self):
        if not self.started or self.board.game_over or self.board.win:
            return

        now = pygame.time.get_ticks()
        if not self.paused:
            self.paused = True
            self.pause_start_ms = now
        else:
            self.paused = False
            self.paused_accum_ms += now - self.pause_start_ms

    # -------- Shared --------
    def reset(self):
        self._load_difficulty()
        self.screen = pygame.display.set_mode(config.display_dimension)
        self.board = Board(self.cols, self.rows, self.mines)
        self.renderer.board = self.board

        self.started = False
        self.start_ticks_ms = 0
        self.end_ticks_ms = 0

        self.hint_used = False
        self.highlight_targets.clear()
        self.highlight_until_ms = 0

        self.paused = False
        self.pause_start_ms = 0
        self.paused_accum_ms = 0

    def _elapsed_ms(self):
        if not self.started:
            return 0

        if self.end_ticks_ms:
            return self.end_ticks_ms - self.start_ticks_ms - self.paused_accum_ms

        now = pygame.time.get_ticks()
        if self.paused:
            return self.pause_start_ms - self.start_ticks_ms - self.paused_accum_ms

        return now - self.start_ticks_ms - self.paused_accum_ms

    def _format_time(self, ms):
        s = max(0, ms) // 1000
        return f"{s//60:02d}:{s%60:02d}"

    def _result_text(self):
        if self.board.game_over:
            return "GAME OVER"
        if self.board.win:
            return "GAME CLEAR"
        return None

    def draw(self):
        self.screen.fill(config.color_bg)

        if pygame.time.get_ticks() > self.highlight_until_ms:
            self.highlight_targets.clear()

        remaining = max(0, self.mines - self.board.flagged_count())
        time_text = self._format_time(self._elapsed_ms())
        best_text = "--:--" if self.best_ms is None else self._format_time(self.best_ms)
        difficulty_map = {
        "EASY": "Lv.1",
        "NORMAL": "Lv.2",
        "HARD": "Lv.3",
         }

        difficulty_label = difficulty_map.get(self.difficulty, "")

        self.renderer.draw_header(remaining, time_text, best_text, difficulty_label,)


        for r in range(self.board.rows):
            for c in range(self.board.cols):
                self.renderer.draw_cell(c, r, (c, r) in self.highlight_targets)

        self.renderer.draw_result_overlay(self._result_text())
        if self.paused:
            self.renderer.draw_pause_overlay()

        pygame.display.flip()

    def run_step(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reset()
                elif event.key == pygame.K_1:
                    self.set_difficulty("EASY")
                elif event.key == pygame.K_2:
                    self.set_difficulty("NORMAL")
                elif event.key == pygame.K_3:
                    self.set_difficulty("HARD")
                elif event.key == pygame.K_h:
                    self.use_hint()
                elif event.key == pygame.K_p:
                    self.toggle_pause()

            if event.type == pygame.MOUSEBUTTONDOWN and not self.paused:
                self.input.handle_mouse(event.pos, event.button)

        if (self.board.game_over or self.board.win) and self.started and not self.end_ticks_ms:
            self.end_ticks_ms = pygame.time.get_ticks()

        if self.board.win and self.end_ticks_ms:
            elapsed = self._elapsed_ms()
            if self.best_ms is None or elapsed < self.best_ms:
                self.best_ms = elapsed
                self._save_best_time(elapsed)

        self.draw()
        self.clock.tick(config.fps)
        return True


def main():
    game = Game()
    while game.run_step():
        pass
    pygame.quit()


if __name__ == "__main__":
    main()