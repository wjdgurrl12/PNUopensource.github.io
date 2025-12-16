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


# =========================
# Renderer
# =========================
class Renderer:
    def __init__(self, screen: pygame.Surface, board: Board):
        self.screen = screen
        self.board = board
        self.font = pygame.font.Font(config.font_name, config.font_size)
        self.header_font = pygame.font.Font(config.font_name, config.header_font_size)
        self.result_font = pygame.font.Font(config.font_name, config.result_font_size)

    def cell_rect(self, col: int, row: int) -> Rect:
        x = config.margin_left + col * config.cell_size
        y = config.margin_top + row * config.cell_size
        return Rect(x, y, config.cell_size, config.cell_size)

    def draw_cell(self, col: int, row: int, highlighted: bool) -> None:
        cell = self.board.cells[self.board.index(col, row)]
        rect = self.cell_rect(col, row)

        if cell.state.is_revealed:
            pygame.draw.rect(self.screen, config.color_cell_revealed, rect)
            if cell.state.is_mine:
                pygame.draw.circle(self.screen, config.color_cell_mine, rect.center, rect.width // 4)
            elif cell.state.adjacent > 0:
                color = config.number_colors.get(cell.state.adjacent, config.color_text)
                label = self.font.render(str(cell.state.adjacent), True, color)
                self.screen.blit(label, label.get_rect(center=rect.center))
        else:
            color = config.color_highlight if highlighted else config.color_cell_hidden
            pygame.draw.rect(self.screen, color, rect)
            if cell.state.is_flagged:
                pygame.draw.circle(self.screen, config.color_flag, rect.center, rect.width // 4)

        pygame.draw.rect(self.screen, config.color_grid, rect, 1)

    def draw_header(self, remaining: int, time_text: str, best_text: str):
        pygame.draw.rect(
            self.screen,
            config.color_header,
            Rect(0, 0, config.width, config.margin_top - 4),
        )

        left = self.header_font.render(f"Mines: {remaining}", True, config.color_header_text)
        mid = self.header_font.render(f"Best: {best_text}", True, config.color_header_text)
        right = self.header_font.render(f"Time: {time_text}", True, config.color_header_text)

        self.screen.blit(left, (10, 10))
        self.screen.blit(mid, (10, 34))
        self.screen.blit(right, (config.width - right.get_width() - 10, 10))

    def draw_result_overlay(self, text: str | None):
        if not text:
            return
        overlay = pygame.Surface((config.width, config.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, config.result_overlay_alpha))
        self.screen.blit(overlay, (0, 0))
        label = self.result_font.render(text, True, config.color_result)
        self.screen.blit(label, label.get_rect(center=(config.width // 2, config.height // 2)))


# =========================
# Input Controller
# =========================
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
        if 0 <= col < self.game.board.cols and 0 <= row < self.game.board.rows:
            return int(col), int(row)
        return -1, -1

    def handle_mouse(self, pos, button):
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


# =========================
# Game
# =========================
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(config.title)

        self.difficulty = config.DEFAULT_DIFFICULTY
        self._load_difficulty()

        self.screen = pygame.display.set_mode(config.display_dimension)
        self.clock = pygame.time.Clock()

        self.board = Board(self.cols, self.rows, self.mines)
        self.renderer = Renderer(self.screen, self.board)
        self.input = InputController(self)

        self.started = False
        self.start_ticks_ms = 0
        self.end_ticks_ms = 0

        self.highlight_targets = set()
        self.highlight_until_ms = 0
        self.hint_used = False

        self.best_ms = self._load_best_time_ms()

    # ---------- Difficulty ----------
    def _load_difficulty(self):
        preset = config.DIFFICULTY_PRESETS[self.difficulty]
        self.cols = preset["cols"]
        self.rows = preset["rows"]
        self.mines = preset["mines"]

        config.width = config.margin_left + self.cols * config.cell_size + config.margin_right
        config.height = config.margin_top + self.rows * config.cell_size + config.margin_bottom
        config.display_dimension = (config.width, config.height)

    def set_difficulty(self, diff: str):
        if diff in config.DIFFICULTY_PRESETS:
            self.difficulty = diff
            self.reset()

    # ---------- Hint ----------
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

        c, r = random.choice(safe)
        self.highlight_targets = {(c, r)}
        self.highlight_until_ms = pygame.time.get_ticks() + config.highlight_duration_ms
        self.hint_used = True

    # ---------- Best Time ----------
    def _best_path(self):
        return os.path.join(os.path.dirname(__file__), config.best_time_file)

    def _load_best_time_ms(self):
        try:
            with open(self._best_path(), "r", encoding="utf-8") as f:
                return json.load(f).get("best_ms")
        except Exception:
            return None

    def _save_best_time_ms(self, ms: int):
        with open(self._best_path(), "w", encoding="utf-8") as f:
            json.dump({"best_ms": ms}, f)

    # ---------- Game Flow ----------
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

    def _elapsed_ms(self):
        if not self.started:
            return 0
        if self.end_ticks_ms:
            return self.end_ticks_ms - self.start_ticks_ms
        return pygame.time.get_ticks() - self.start_ticks_ms

    def _format_time(self, ms):
        s = ms // 1000
        return f"{s//60:02d}:{s%60:02d}"

    def draw(self):
        if pygame.time.get_ticks() > self.highlight_until_ms:
            self.highlight_targets.clear()

        self.screen.fill(config.color_bg)

        remaining = max(0, self.mines - self.board.flagged_count())
        time_text = self._format_time(self._elapsed_ms())
        best_text = "--:--" if self.best_ms is None else self._format_time(self.best_ms)

        self.renderer.draw_header(remaining, time_text, best_text)

        for r in range(self.board.rows):
            for c in range(self.board.cols):
                hl = (c, r) in self.highlight_targets
                self.renderer.draw_cell(c, r, hl)

        result = "GAME CLEAR" if self.board.win else "GAME OVER" if self.board.game_over else None
        self.renderer.draw_result_overlay(result)

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

            if event.type == pygame.MOUSEBUTTONDOWN:
                self.input.handle_mouse(event.pos, event.button)

        if self.board.win and self.started and not self.end_ticks_ms:
            self.end_ticks_ms = pygame.time.get_ticks()
            elapsed = self._elapsed_ms()
            if self.best_ms is None or elapsed < self.best_ms:
                self.best_ms = elapsed
                self._save_best_time_ms(elapsed)

        if self.board.game_over and self.started and not self.end_ticks_ms:
            self.end_ticks_ms = pygame.time.get_ticks()

        self.draw()
        self.clock.tick(config.fps)
        return True


def main():
    game = Game()
    running = True
    while running:
        running = game.run_step()
    pygame.quit()


if __name__ == "__main__":
    main()
