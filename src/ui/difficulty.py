# -*- coding: utf-8 -*-
# 难度选择界面：远征出征前选择本局难度（当前仅开放 Normal）

import math
import os
import pygame

from src.engine import settings as cfg
from src.engine.game import GameState


# 难度定义：(ID, 显示名, 是否已开放)
DIFFICULTIES = [
    ("EASY", "Easy", False),
    ("NORMAL", "Normal", True),
    ("HARD", "Hard", False),
    ("LUNATIC", "Lunatic", False),
]


def _load_background(path, size):
    try:
        if os.path.exists(path):
            img = pygame.image.load(path)
            return pygame.transform.smoothscale(img, size)
    except Exception as e:
        print(f"[Difficulty] Failed to load {path}: {e}")
    return None


class DifficultySelectState(GameState):
    """出征前的难度选择界面。当前仅有 Normal 开放，其余难度显示为锁定。"""

    def __init__(self, game):
        super().__init__(game)
        self.background = _load_background(
            cfg.MENU_BACKGROUND, (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
        # 光标位置：只能落在唯一开放的 NORMAL 上
        self.selected = self._available_indexes()[0]
        self._last_mouse_pos = (0, 0)

    def enter(self, game):
        self.game.stop_music()
        self.selected = self._available_indexes()[0]

    def _available_indexes(self):
        return [i for i, entry in enumerate(DIFFICULTIES) if entry[2]]

    def _move_selection(self, direction):
        available = self._available_indexes()
        if not available:
            return
        pos = available.index(self.selected) if self.selected in available else 0
        pos = (pos + direction) % len(available)
        self.selected = available[pos]
        self.game.play_sfx("cursor")

    def _confirm(self):
        if not DIFFICULTIES[self.selected][2]:
            self.game.play_sfx("cancel_menu")
            return
        self.game.global_data["difficulty"] = DIFFICULTIES[self.selected][0]
        self.game.play_sfx("ok")
        from src.ui.loadout import LoadoutState
        self.game.switch_state(LoadoutState(self.game))

    def _difficulty_rects(self):
        """各难度行的可点击区域（与 draw 布局一致）"""
        rects = []
        for i, (_, name, _) in enumerate(DIFFICULTIES):
            w, h = self.game.font_medium.size(name)
            rects.append(pygame.Rect(480 - w // 2 - 60, 280 + i * 58 - 8,
                                     w + 120, h + 16))
        return rects

    def update(self, dt):
        keys = self.game.keys_just_pressed
        if (keys.get(pygame.K_ESCAPE, False) or keys.get(pygame.K_x, False)
                or keys.get(pygame.K_BACKSPACE, False)):
            from src.ui.menu import MenuState
            self.game.switch_state(MenuState(self.game))
            return

        if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
            self._move_selection(-1)
        if keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
            self._move_selection(1)

        if (keys.get(pygame.K_RETURN, False) or keys.get(pygame.K_z, False)
                or keys.get(pygame.K_SPACE, False)):
            self._confirm()
            return

        # 鼠标：悬停到已开放难度时切换选中，点击确认；点击锁定难度仅提示
        mp = self.game.mouse_pos
        clicked = self.game.mouse_clicked(1)
        if clicked:
            for i, rect in enumerate(self._difficulty_rects()):
                if rect.collidepoint(mp):
                    if DIFFICULTIES[i][2]:
                        self.selected = i
                        self._confirm()
                    else:
                        self.game.play_sfx("cancel_menu")
                    return
        moved = mp != self._last_mouse_pos
        if moved:
            self._last_mouse_pos = mp
            for i, rect in enumerate(self._difficulty_rects()):
                if rect.collidepoint(mp) and i != self.selected:
                    if DIFFICULTIES[i][2]:
                        self.selected = i
                        self.game.play_sfx("cursor")
                    break

    def draw(self, screen):
        if self.background:
            screen.blit(self.background, (0, 0))
        else:
            screen.fill((4, 4, 16))

        title = self.game.font_large.render("选择难度", True, cfg.COLOR_YELLOW)
        screen.blit(title, ((cfg.SCREEN_WIDTH - title.get_width()) // 2, 110))

        sub = self.game.font_small.render("Difficulty", True, cfg.COLOR_GRAY)
        screen.blit(sub, ((cfg.SCREEN_WIDTH - sub.get_width()) // 2, 162))

        rects = self._difficulty_rects()
        for i, (_, name, available) in enumerate(DIFFICULTIES):
            is_sel = i == self.selected
            rect = rects[i]
            color = (cfg.COLOR_YELLOW if is_sel else cfg.COLOR_WHITE) if available else cfg.COLOR_DARK_GRAY
            text = self.game.font_medium.render(name, True, color)

            pygame.draw.rect(screen, cfg.COLOR_PANEL_BG, rect)
            pygame.draw.rect(screen,
                             cfg.COLOR_GRAY if available else cfg.COLOR_DARK_GRAY,
                             rect, 1)

            if available and is_sel:
                hl = pygame.Surface(rect.size, pygame.SRCALPHA)
                hl.fill((255, 255, 80, 22))
                screen.blit(hl, rect.topleft)
                pulse = math.sin(pygame.time.get_ticks() * 0.004) * 0.3 + 0.7
                glow_color = tuple(int(c * pulse) for c in cfg.COLOR_YELLOW)
                glow = self.game.font_medium.render(name, True, glow_color)
                screen.blit(glow, (rect.x + (rect.width - glow.get_width()) // 2,
                                   rect.y + (rect.height - glow.get_height()) // 2))
                ind = self.game.font_medium.render("> ", True, cfg.COLOR_YELLOW)
                screen.blit(ind, (rect.x + 10, rect.y + (rect.height - ind.get_height()) // 2))
            else:
                screen.blit(text, (rect.x + (rect.width - text.get_width()) // 2,
                                   rect.y + (rect.height - text.get_height()) // 2))

            if not available:
                lock = self.game.font_small.render("未开放", True, cfg.COLOR_DARK_GRAY)
                screen.blit(lock, (rect.right - lock.get_width() - 10,
                                   rect.y + (rect.height - lock.get_height()) // 2))

        hint = self.game.font_small.render(
            "↑↓ 选择    Enter/Z 确认    Esc 返回", True, cfg.COLOR_GRAY)
        screen.blit(hint, ((cfg.SCREEN_WIDTH - hint.get_width()) // 2, 620))

        summary = self.game.font_small.render(
            "当前仅有 Normal 难度开放", True, cfg.COLOR_GREEN)
        screen.blit(summary, ((cfg.SCREEN_WIDTH - summary.get_width()) // 2, 654))
