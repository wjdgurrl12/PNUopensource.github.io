import sys
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

    def cell_rect(self, col: int, row: int) -> pygame.Rect:
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
            base_color = config.color_highlight if highlighted else config.color_cell_hidden
            pygame.draw.rect(self.screen, base_color, rect)

            # 깃발 그리기 (상세 로직 적용)
            if cell.state.is_flagged:
                flag_w = max(6, rect.width // 3)
                flag_h = max(8, rect.height // 2)
                pole_x = rect.left + rect.width // 3
                pole_y = rect.top + 4
                pygame.draw.line(self.screen, config.color_flag, (pole_x, pole_y), (pole_x, pole_y + flag_h), 2)
                pygame.draw.polygon(self.screen, config.color_flag, [
                    (pole_x + 2, pole_y),
                    (pole_x + 2 + flag_w, pole_y + flag_h // 3),
                    (pole_x + 2, pole_y + flag_h // 2),
                ])
            # 물음표 그리기
            elif cell.state.is_question:
                q = self.font.render("?", True, config.color_question if hasattr(config, 'color_question') else (120, 120, 255))
                self.screen.blit(q, q.get_rect(center=rect.center))

        pygame.draw.rect(self.screen, config.color_grid, rect, 1)

    def draw_header(self, remaining: int, time_text: str, best_text: str, difficulty_label: str) -> None:
        pygame.draw.rect(self.screen, config.color_header, Rect(0, 0, config.width, config.margin_top - 4))
        left = self.header_font.render(f"Mines: {remaining}", True, config.color_header_text)
        mid = self.header_font.render(f"Best: {best_text}", True, config.color_header_text)
        right = self.header_font.render(f"{difficulty_label}  Time: {time_text}", True, config.color_header_text)
        self.screen.blit(left, (10, 12))
        self.screen.blit(mid, (config.width // 2 - mid.get_width() // 2, 12))
        self.screen.blit(right, (config.width - right.get_width() - 10, 12))

    def draw_pause_overlay(self, text: str) -> None:
        overlay = pygame.Surface((config.width, config.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        label = self.result_font.render(text, True, config.color_result)
        self.screen.blit(label, label.get_rect(center=(config.width // 2, config.height // 2)))

    def draw_result_overlay(self, text: str | None) -> None:
        if not text: return
        overlay = pygame.Surface((config.width, config.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, config.result_overlay_alpha))
        self.screen.blit(overlay, (0, 0))
        label = self.result_font.render(text, True, config.color_result)
        self.screen.blit(label, label.get_rect(center=(config.width // 2, config.height // 2)))

# ============================ Input ============================
class InputController:
    def __init__(self, game: "Game"):
        self.game = game

    def pos_to_grid(self, x: int, y: int):
        if not (config.margin_left <= x < config.width - config.margin_right): return -1, -1
        if not (config.margin_top <= y < config.height - config.margin_bottom): return -1, -1
        col = (x - config.margin_left) // config.cell_size
        row = (y - config.margin_top) // config.cell_size
        return (col, row) if self.game.board.is_inbounds(col, row) else (-1, -1)

    def handle_mouse(self, pos, button) -> None:
        col, row = self.pos_to_grid(pos[0], pos[1])
        if col == -1: return
        game = self.game
        if button == config.mouse_left:
            if not game.started:
                game.started, game.start_ticks_ms = True, pygame.time.get_ticks()
            game.board.reveal(col, row)
        elif button == config.mouse_right:
            game.board.toggle_flag(col, row)
        elif button == config.mouse_middle: # 휠 클릭 기능 유지
            neighbors = game.board.neighbors(col, row)
            game.highlight_targets = {(nc, nr) for (nc, nr) in neighbors if not game.board.cells[game.board.index(nc, nr)].state.is_revealed}
            game.highlight_until_ms = pygame.time.get_ticks() + config.highlight_duration_ms

# ============================ Game ============================
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(config.title)
        self.clock = pygame.time.Clock()
        self.difficulty = config.DEFAULT_DIFFICULTY
        self._load_difficulty()
        self.screen = pygame.display.set_mode(config.display_dimension)
        self.board = Board(self.cols, self.rows, self.mines)
        self.renderer = Renderer(self.screen, self.board)
        self.input = InputController(self)
        
        # 통합된 State 관리
        self.started = False
        self.start_ticks_ms = 0
        self.end_ticks_ms = 0
        self.highlight_targets = set()
        self.highlight_until_ms = 0
        self.hint_used = False
        self.paused = False
        self.pause_reason = None
        self.pause_start_ms = 0
        self.paused_accum_ms = 0
        self.best_times = self._load_best_times()

    def _load_difficulty(self):
        preset = config.DIFFICULTY_PRESETS[self.difficulty]
        self.cols, self.rows, self.mines = preset["cols"], preset["rows"], preset["mines"]
        config.cols, config.rows, config.num_mines = self.cols, self.rows, self.mines
        config.width = config.margin_left + self.cols * config.cell_size + config.margin_right
        config.height = config.margin_top + self.rows * config.cell_size + config.margin_bottom
        config.display_dimension = (config.width, config.height)

    def set_difficulty(self, difficulty: str):
        if difficulty in config.DIFFICULTY_PRESETS:
            self.difficulty = difficulty
            self.reset()

    def use_hint(self):
        if self.hint_used or self.board.game_over or self.board.win: return
        safe = [(c, r) for r in range(self.board.rows) for c in range(self.board.cols)
                if not self.board.cells[self.board.index(c, r)].state.is_revealed and not self.board.cells[self.board.index(c, r)].state.is_mine]
        if not safe: return
        self.highlight_targets, self.highlight_until_ms, self.hint_used = {random.choice(safe)}, pygame.time.get_ticks() + 2000, True

    def toggle_pause(self, reason: str = "PAUSED"):
        if not self.started or self.board.game_over or self.board.win: return
        now = pygame.time.get_ticks()
        if not self.paused:
            self.paused, self.pause_reason, self.pause_start_ms = True, reason, now
        else:
            self.paused, self.pause_reason = False, None
            self.paused_accum_ms += now - self.pause_start_ms

    def reset(self):
        self._load_difficulty()
        self.screen = pygame.display.set_mode(config.display_dimension)
        self.board = Board(self.cols, self.rows, self.mines)
        self.renderer.board = self.board
        self.started = False
        self.start_ticks_ms = self.end_ticks_ms = self.hint_used = self.highlight_until_ms = 0
        self.highlight_targets.clear()
        self.paused, self.pause_reason = False, None
        self.pause_start_ms = self.paused_accum_ms = 0

    def _load_best_times(self) -> dict:
        if not os.path.exists("best_time.json"): return {}
        try:
            with open("best_time.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except: return {}

    def _save_best_times(self) -> None:
        with open("best_time.json", "w", encoding="utf-8") as f:
            json.dump(self.best_times, f, indent=2)

    def _elapsed_ms(self):
        if not self.started: return 0
        if self.end_ticks_ms: return self.end_ticks_ms - self.start_ticks_ms - self.paused_accum_ms
        now = pygame.time.get_ticks()
        if self.paused: return self.pause_start_ms - self.start_ticks_ms - self.paused_accum_ms
        return now - self.start_ticks_ms - self.paused_accum_ms

    def _format_time(self, ms):
        s = max(0, ms) // 1000
        return f"{s//60:02d}:{s%60:02d}"

    def draw(self):
        self.screen.fill(config.color_bg)
        now = pygame.time.get_ticks()
        if now > self.highlight_until_ms: self.highlight_targets.clear()
        
        remaining = max(0, self.mines - self.board.flagged_count())
        time_text = self._format_time(self._elapsed_ms())
        best_ms = self.best_times.get(self.difficulty)
        best_text = "--:--" if best_ms is None else self._format_time(best_ms)
        
        difficulty_map = {"EASY": "Lv.1", "NORMAL": "Lv.2", "HARD": "Lv.3"}
        self.renderer.draw_header(remaining, time_text, best_text, difficulty_map.get(self.difficulty, ""))

        for r in range(self.board.rows):
            for c in range(self.board.cols):
                self.renderer.draw_cell(c, r, (c, r) in self.highlight_targets)
        
        self.renderer.draw_result_overlay("GAME CLEAR" if self.board.win else ("GAME OVER" if self.board.game_over else None))
        if self.paused and self.pause_reason:
            self.renderer.draw_pause_overlay(self.pause_reason)
        pygame.display.flip()

    def run_step(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r: self.reset()
                elif event.key == pygame.K_1: self.set_difficulty("EASY")
                elif event.key == pygame.K_2: self.set_difficulty("NORMAL")
                elif event.key == pygame.K_3: self.set_difficulty("HARD")
                elif event.key == pygame.K_h: self.use_hint()
                elif event.key == pygame.K_p: self.toggle_pause("PAUSED")
                elif event.key == pygame.K_w: self.toggle_pause("WAIT") # 대기 모드
            if event.type == pygame.MOUSEBUTTONDOWN and not self.paused:
                self.input.handle_mouse(event.pos, event.button)

        if (self.board.game_over or self.board.win) and self.started and not self.end_ticks_ms:
            self.end_ticks_ms = pygame.time.get_ticks()
            if self.board.win:
                elapsed = self._elapsed_ms()
                prev = self.best_times.get(self.difficulty)
                if prev is None or elapsed < prev:
                    self.best_times[self.difficulty] = elapsed
                    self._save_best_times()
        self.draw()
        self.clock.tick(config.fps)
        return True

def main():
    game = Game()
    while game.run_step(): pass
    pygame.quit()

if __name__ == "__main__":
    main()