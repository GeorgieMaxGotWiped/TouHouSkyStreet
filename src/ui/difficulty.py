# -*- coding: utf-8 -*-
# 难度选择界面：远征出征前选择本局难度（当前仅开放 Easy）

import pygame

from src.engine import settings as cfg
from src.engine import hires, painter
from src.engine.game import GameState
from src.ui.menu import load_background, refresh_background
from src.ui.anim import Entrance


# 难度定义：(ID, 显示名, 是否已开放)
DIFFICULTIES = [
    ("EASY", "Easy", True),
    ("NORMAL", "Normal", False),
    ("HARD", "Hard", False),
    ("LUNATIC", "Lunatic", False),
]


class DifficultySelectState(GameState):
    """出征前的难度选择界面。当前仅有 Easy 开放，其余难度显示为锁定。"""

    def __init__(self, game, extra=False):
        super().__init__(game)
        # extra=True：Ex 面（裂隙 ~ The Rift）流程，选完难度直接开打（不经仓库出征）
        self.extra = bool(extra)
        # 背景按渲染倍率准备（与主菜单同一个助手）：以前这里是把图缩到 960x720
        # 再整体放大，等于先丢细节再放大，所以这一屏的背景一直是糊的
        self.background = load_background(cfg.MENU_BACKGROUND,
                                          (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT),
                                          game.screen.bake_factor())
        # 光标位置：只能落在唯一开放的 EASY 上
        self.selected = self._available_indexes()[0]
        self._last_mouse_pos = (0, 0)
        self.intro = Entrance()

    def enter(self, game):
        self.game.stop_music()
        self.selected = self._available_indexes()[0]
        self.intro.reset()

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
        if self.extra:
            self._launch_extra_stage()
            return
        from src.ui.loadout import LoadoutState
        self.game.switch_state(LoadoutState(self.game))

    def _launch_extra_stage(self):
        """Ex 面入场：不经仓库出征，直接满火力开打（装备物品效果本面不生效）。"""
        from src.stages import get_extra_stage_class
        from src.ui.loading import start_stage

        self.game.global_data["score"] = 0
        self.game.global_data["lives"] = cfg.PLAYER_START_LIVES
        self.game.global_data["bombs"] = cfg.PLAYER_START_BOMBS
        self.game.global_data["power"] = cfg.EX_STAGE_START_POWER
        self.game.global_data["graze"] = 0
        start_stage(self.game, get_extra_stage_class())

    def _difficulty_rects(self):
        """各难度行的可点击区域（与 draw 布局一致）"""
        rects = []
        for i, (_, name, _) in enumerate(DIFFICULTIES):
            w, _h = self.game.font_medium.size(name)
            rects.append(pygame.Rect(480 - w // 2 - 60, 280 + i * 58 - 8,
                                     w + 120, 58))
        return rects

    def update(self, dt):
        self.intro.update(dt)
        keys = self.game.keys_just_pressed
        if (keys.get(pygame.K_ESCAPE, False) or keys.get(pygame.K_x, False)
                or keys.get(pygame.K_BACKSPACE, False)):
            # 退回上一步：自机选择
            from src.ui.character_select import CharacterSelectState
            self.game.switch_state(CharacterSelectState(self.game, extra=self.extra))
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
        background = refresh_background(self, screen)
        if background:
            screen.blit_gpu(background, (0, 0))
        else:
            screen.fill_gpu((4, 4, 16))

        title = self.game.font_large.render("选择难度", True, cfg.COLOR_YELLOW)
        # 进场动效：标题 -> 副标题 -> 各难度行 -> 底部提示，依次错位淡入
        alpha, dy = self.intro.item(0)
        screen.blit_gpu(title, ((cfg.SCREEN_WIDTH - title.get_width()) // 2, 110 - dy),
                        alpha=alpha)

        sub_text = ("Extra Stage · 裂隙 ~ The Rift" if self.extra else "Difficulty")
        sub = self.game.font_small.render(
            sub_text, True, cfg.COLOR_YELLOW if self.extra else cfg.COLOR_GRAY)
        alpha, dy = self.intro.item(0.5)
        screen.blit_gpu(sub, ((cfg.SCREEN_WIDTH - sub.get_width()) // 2, 162 - dy),
                        alpha=alpha)

        rects = self._difficulty_rects()
        for i, (_, name, available) in enumerate(DIFFICULTIES):
            alpha, dy = self.intro.item(1.0 + i * 0.5)
            if alpha <= 0:
                continue
            is_sel = i == self.selected
            rect = rects[i].move(0, -dy)
            color = (cfg.COLOR_YELLOW if is_sel else cfg.COLOR_WHITE) if available else cfg.COLOR_DARK_GRAY
            text = self.game.font_medium.render(name, True, color)

            # 各难度的底板 / 外框同样预烤后由显卡 1:1 贴出（1x 画布上的矩形放大
            # 时边缘会被线性过滤糊掉）
            screen.blit_baked(("diff_row", rect.size, available), rect.topleft,
                              rect.size, self._build_row(available), alpha)

            if available and is_sel:
                glow = self.game.font_medium.render(
                    name, True, hires.pulse_color(cfg.COLOR_YELLOW))
                screen.blit_gpu(glow, (rect.x + (rect.width - glow.get_width()) // 2,
                                       rect.y + (rect.height - glow.get_height()) // 2),
                                alpha=alpha)
                ind = self.game.font_medium.render("> ", True, cfg.COLOR_YELLOW)
                screen.blit_gpu(ind, (rect.x + 10,
                                      rect.y + (rect.height - ind.get_height()) // 2),
                                alpha=alpha)
            else:
                screen.blit_gpu(text, (rect.x + (rect.width - text.get_width()) // 2,
                                       rect.y + (rect.height - text.get_height()) // 2),
                                alpha=alpha)

            if not available:
                lock = self.game.font_small.render("未开放", True, cfg.COLOR_DARK_GRAY)
                screen.blit_gpu(lock, (rect.right - lock.get_width() - 10,
                                       rect.y + (rect.height - lock.get_height()) // 2),
                                alpha=alpha)

        hint = self.game.font_small.render(
            "↑↓ 选择    Enter/Z 确认    Esc 返回", True, cfg.COLOR_GRAY)
        alpha, dy = self.intro.item(4.0)
        screen.blit_gpu(hint, ((cfg.SCREEN_WIDTH - hint.get_width()) // 2, 620 - dy),
                        alpha=alpha)

        summary = self.game.font_small.render(
            "当前仅有 Easy 难度开放" if not self.extra
            else "Ex 面：不经仓库出征，装备物品效果不生效，通关后回主菜单",
            True, cfg.COLOR_GREEN)
        alpha, dy = self.intro.item(4.4)
        screen.blit_gpu(summary, ((cfg.SCREEN_WIDTH - summary.get_width()) // 2, 654 - dy),
                        alpha=alpha)

    @staticmethod
    def _build_row(available):
        """难度行的底板 / 外框预烤画法（尺寸取自 blit_baked 建好的目标表面）"""
        def build(target, k):
            size = pygame.Surface.get_size(target)
            rect = (0, 0, size[0], size[1])
            painter.bake_rect(target, 1, cfg.COLOR_PANEL_BG, rect)
            painter.bake_rect(target, 1,
                              cfg.COLOR_GRAY if available else cfg.COLOR_DARK_GRAY,
                              rect, 1)
        return build
