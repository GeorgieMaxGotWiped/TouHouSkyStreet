# 游戏内HUD - 右侧信息面板
# 显示 Score / 残机 / 炸弹 / Power / Graze / 技能等

import pygame
from src.engine import settings as cfg

class HUD:
    """右侧信息面板"""
    def __init__(self, game):
        self.game = game
        self.font_small = game.font_small    # 16
        self.font_medium = game.font_medium  # 24
        self.font_large = game.font_large    # 36
        self.font_huge = game.font_huge      # 48

        # 面板布局
        self.panel_x = cfg.PANEL_LEFT
        self.panel_w = cfg.PANEL_WIDTH

    def _draw_icon_row(self, screen, icon, count, color, y, max_width):
        """?????????????????????????? 12 ??????"""
        if count <= 0:
            return
        surf = self.font_medium.render(icon, True, color)
        icon_w = surf.get_width()
        if icon_w * count > max_width:
            surf = self.font_small.render(icon, True, color)
            icon_w = surf.get_width()
        x = self.panel_x + self.panel_w - 24 - icon_w * count
        for _ in range(count):
            screen.blit(surf, (x, y))
            x += icon_w

    def draw(self, screen, player, score, lives, bombs, power, graze, stage_name="", stage_timer=0, boss=None):
        """绘制右侧信息面板"""
        # 面板背景
        pygame.draw.rect(screen, cfg.COLOR_PANEL_BG,
                         (self.panel_x, 0, self.panel_w, cfg.SCREEN_HEIGHT))
        # 左侧分隔线
        pygame.draw.line(screen, cfg.COLOR_GRAY, (self.panel_x, 0), (self.panel_x, cfg.SCREEN_HEIGHT), 2)

        cx = self.panel_x + self.panel_w // 2
        y = 24

        # --- 标题 ---
        title = self.font_medium.render("东方天空街", True, cfg.COLOR_WHITE)
        screen.blit(title, (cx - title.get_width() // 2, y))
        y += 26

        if stage_name:
            stage_text = self.font_small.render(stage_name, True, cfg.COLOR_GRAY)
            screen.blit(stage_text, (cx - stage_text.get_width() // 2, y))
            y += 22

        # 分隔线
        pygame.draw.line(screen, cfg.COLOR_DARK_GRAY, (self.panel_x + 20, y), (self.panel_x + self.panel_w - 20, y))
        y += 16

        # --- Score ---
        score_label = self.font_small.render("SCORE", True, cfg.COLOR_GRAY)
        screen.blit(score_label, (cx - score_label.get_width() // 2, y))
        y += 22
        score_text = self.font_large.render(f"{score:,}", True, cfg.COLOR_YELLOW)
        screen.blit(score_text, (cx - score_text.get_width() // 2, y))
        y += 44

        # 分隔线
        pygame.draw.line(screen, cfg.COLOR_DARK_GRAY, (self.panel_x + 20, y), (self.panel_x + self.panel_w - 20, y))
        y += 16

        # --- 残机 ---
        lives_label = self.font_small.render("残机", True, cfg.COLOR_GRAY)
        screen.blit(lives_label, (self.panel_x + 24, y))
        # 内部残机仍为 PLAYER_START_LIVES(3)，但界面从 2 颗心开始显示
        # （少显示 1 条隐藏命）：3->2 心，2->1 心，1->0 心，0 即 GameOver
        self._draw_icon_row(screen, "♥", max(0, lives - 1), cfg.COLOR_RED,
                             y, self.panel_w - 48)
        y += 34

        # --- 炸弹 ---
        bombs_label = self.font_small.render("炸弹", True, cfg.COLOR_GRAY)
        screen.blit(bombs_label, (self.panel_x + 24, y))
        self._draw_icon_row(screen, "✿", bombs, cfg.COLOR_ORANGE,
                             y, self.panel_w - 48)
        y += 34

        # --- Power ---
        power_label = self.font_small.render("POWER", True, cfg.COLOR_GRAY)
        screen.blit(power_label, (self.panel_x + 24, y))
        power_text = self.font_medium.render(f"{power}/400", True, cfg.COLOR_BLUE)
        screen.blit(power_text, (self.panel_x + self.panel_w - 24 - power_text.get_width(), y))
        y += 30
        # Power 进度条
        bar_w = self.panel_w - 48
        bar_h = 6
        bar_x = self.panel_x + 24
        ratio = min(1.0, power / 400)
        pygame.draw.rect(screen, cfg.COLOR_DARK_GRAY, (bar_x, y, bar_w, bar_h))
        pygame.draw.rect(screen, cfg.COLOR_BLUE, (bar_x, y, int(bar_w * ratio), bar_h))
        pygame.draw.rect(screen, cfg.COLOR_GRAY, (bar_x, y, bar_w, bar_h), 1)
        y += 22

        # --- Graze ---
        graze_label = self.font_small.render("GRAZE", True, cfg.COLOR_GRAY)
        screen.blit(graze_label, (self.panel_x + 24, y))
        graze_text = self.font_medium.render(f"{graze}", True, cfg.COLOR_GREEN)
        screen.blit(graze_text, (self.panel_x + self.panel_w - 24 - graze_text.get_width(), y))
        y += 34

        # 分隔线
        pygame.draw.line(screen, cfg.COLOR_DARK_GRAY, (self.panel_x + 20, y), (self.panel_x + self.panel_w - 20, y))
        y += 16

        # --- Skyblock 技能 ---
        skills = self.game.global_data.get("skills", {})
        if skills:
            combat = skills.get("COMBAT", {})
            clv = combat.get("level", 0)
            cxp = combat.get("xp", 0)
            combat_text = self.font_small.render(f"Combat Lv.{clv}  {cxp} XP", True, cfg.COLOR_YELLOW)
            screen.blit(combat_text, (self.panel_x + 24, y))
            y += 26

        # --- 操作提示（底部）---
        hint_lines = [
            "Z/Space: 射击",
            "Shift: 低速模式",
            "X: 炸弹",
            "ESC: 暂停",
            "F11: 全屏",
        ]
        hint_y = cfg.SCREEN_HEIGHT - 100
        for line in hint_lines:
            hint = self.font_small.render(line, True, cfg.COLOR_DARK_GRAY)
            screen.blit(hint, (self.panel_x + 24, hint_y))
            hint_y += 22

        # --- Enemy 位置指示（最底部，实时显示Boss水平位置）---
        self.draw_enemy_marker(screen, boss)

    def draw_enemy_marker(self, screen, boss):
        """底部 Enemy 指示条：沿水平方向实时标记Boss当前X坐标"""
        label = self.font_small.render("Enemy", True, cfg.COLOR_GRAY)
        bar_y = cfg.SCREEN_HEIGHT - 13
        left = cfg.BATTLE_OFFSET_X
        right = cfg.BATTLE_OFFSET_X + cfg.BATTLE_AREA_WIDTH

        screen.blit(label, (left, bar_y - 10))
        line_left = left + label.get_width() + 10
        pygame.draw.line(screen, cfg.COLOR_DARK_GRAY,
                         (line_left, bar_y), (right, bar_y), 2)

        if boss is None or not getattr(boss, "alive", False):
            return

        # 将Boss水平坐标映射到指示条
        mx = int(cfg.BATTLE_OFFSET_X + boss.x)
        mx = max(line_left, min(mx, right))

        pygame.draw.line(screen, cfg.COLOR_RED, (mx, bar_y - 4), (mx, bar_y + 4), 2)
        pygame.draw.polygon(screen, cfg.COLOR_RED, [
            (mx, bar_y - 9),
            (mx - 4, bar_y - 3),
            (mx + 4, bar_y - 3),
        ])

    def draw_game_over(self, screen, score):
        """游戏结束画面（全屏）"""
        overlay = pygame.Surface((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        go_text = self.font_huge.render("GAME OVER", True, cfg.COLOR_RED)
        screen.blit(go_text, (cfg.SCREEN_WIDTH // 2 - go_text.get_width() // 2, 200))

        score_text = self.font_large.render(f"Final Score: {score:,}", True, cfg.COLOR_WHITE)
        screen.blit(score_text, (cfg.SCREEN_WIDTH // 2 - score_text.get_width() // 2, 280))

        retry_text = self.font_small.render("Press R to Retry  |  ESC to Menu", True, cfg.COLOR_GRAY)
        screen.blit(retry_text, (cfg.SCREEN_WIDTH // 2 - retry_text.get_width() // 2, 340))

        lost_text = self.font_small.render("本轮获得的装备与金币不会保留", True, cfg.COLOR_GRAY)
        screen.blit(lost_text, (cfg.SCREEN_WIDTH // 2 - lost_text.get_width() // 2, 375))

    def draw_stage_clear(self, screen, score, stage_name):
        """关卡通关（全屏）"""
        overlay = pygame.Surface((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
        overlay.set_alpha(160)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        clear_text = self.font_huge.render("STAGE CLEAR!", True, cfg.COLOR_YELLOW)
        screen.blit(clear_text, (cfg.SCREEN_WIDTH // 2 - clear_text.get_width() // 2, 200))

        stage_text = self.font_medium.render(stage_name, True, cfg.COLOR_WHITE)
        screen.blit(stage_text, (cfg.SCREEN_WIDTH // 2 - stage_text.get_width() // 2, 260))

        score_text = self.font_large.render(f"Score: {score:,}", True, cfg.COLOR_WHITE)
        screen.blit(score_text, (cfg.SCREEN_WIDTH // 2 - score_text.get_width() // 2, 310))

        cont_text = self.font_small.render("Press ENTER to continue", True, cfg.COLOR_GRAY)
        screen.blit(cont_text, (cfg.SCREEN_WIDTH // 2 - cont_text.get_width() // 2, 380))

    def draw_pause(self, screen):
        """暂停画面（全屏）"""
        overlay = pygame.Surface((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
        overlay.set_alpha(160)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        pause_text = self.font_huge.render("PAUSED", True, cfg.COLOR_WHITE)
        screen.blit(pause_text, (cfg.SCREEN_WIDTH // 2 - pause_text.get_width() // 2, 280))

        resume_text = self.font_small.render("Press ESC to Resume", True, cfg.COLOR_GRAY)
        screen.blit(resume_text, (cfg.SCREEN_WIDTH // 2 - resume_text.get_width() // 2, 340))

    def draw_item_popup(self, screen, item, timer=0):
        """物品掉落弹窗（右侧面板底部）"""
        if timer > 180:
            return

        alpha = min(255, (180 - timer) * 10) if timer > 150 else 255
        width = self.panel_w - 32
        height = 52
        x = self.panel_x + 16
        y = cfg.SCREEN_HEIGHT - 170 - (timer * 2 if timer < 30 else 0)

        popup = pygame.Surface((width, height))
        popup.set_alpha(min(200, alpha))
        popup.fill((24, 28, 48))
        screen.blit(popup, (x, y))

        try:
            from src.systems.item_icons import draw_item_icon
            draw_item_icon(screen, item.id, x + 8, y + 10, size=32)
        except Exception:
            pass

        rarity_color = item.rarity_color if hasattr(item, 'rarity_color') else cfg.COLOR_WHITE
        item_text = self.font_small.render(item.name, True, rarity_color)
        screen.blit(item_text, (x + 48, y + 6))

        type_text = self.font_small.render(f"{item.rarity} {item.item_type}", True, cfg.COLOR_GRAY)
        screen.blit(type_text, (x + 48, y + 28))
