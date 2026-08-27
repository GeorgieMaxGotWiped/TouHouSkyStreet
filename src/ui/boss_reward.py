# 关底 Boss 击败后的 4 选 1 奖励界面

import random
import pygame
from src.engine import settings as cfg
from src.engine.game import GameState
from src.systems.item_system import (
    SKYBLOCK_ITEMS,
    SLOT_LABELS,
    ITEM_TYPE_LABELS,
    ItemInventory,
)
from src.systems.item_icons import draw_item_icon


class BossRewardState(GameState):
    """从 Boss 专属物品池随机 3 件中挑选 1 件加入背包"""

    def __init__(self, game, stage_num, pool):
        super().__init__(game)
        self.stage_num = stage_num
        self.inventory = ItemInventory.from_global_data(game.global_data)
        # 4 件中随机抽 3 件
        valid = [i for i in pool if i in SKYBLOCK_ITEMS]
        self.offer = [SKYBLOCK_ITEMS[i] for i in random.sample(valid, min(3, len(valid)))]
        self.selected = 0
        self.confirming = False
        self.confirm_choice = 0
        self._last_mouse_pos = (0, 0)

    def enter(self, game):
        self.game.stop_music()
        self.selected = 0
        self.confirming = False
        self.confirm_choice = 0

    def exit(self):
        self.inventory.save_to_global_data(self.game.global_data)

    def _confirm_pressed(self, keys):
        return (keys.get(pygame.K_RETURN, False)
                or keys.get(pygame.K_z, False)
                or keys.get(pygame.K_SPACE, False))

    def update(self, dt):
        keys = self.game.keys_just_pressed
        if self.confirming:
            self._update_confirm(keys)
            return
        if keys.get(pygame.K_LEFT, False) or keys.get(pygame.K_a, False):
            self.selected = (self.selected - 1) % len(self.offer)
        if keys.get(pygame.K_RIGHT, False) or keys.get(pygame.K_d, False):
            self.selected = (self.selected + 1) % len(self.offer)
        if self._confirm_pressed(keys) and self.offer:
            self.confirming = True
            self.confirm_choice = 0
            return

        # 鼠标：悬停选中卡片；单击已选中卡片或“确认领取”打开确认框
        mp = self.game.mouse_pos
        clicked = self.game.mouse_clicked(1)
        moved = mp != self._last_mouse_pos
        if moved:
            self._last_mouse_pos = mp
        if not clicked and moved:
            for idx, rect in self._card_rects():
                if rect.collidepoint(mp):
                    if self.selected != idx:
                        self.selected = idx
                    break
        if clicked:
            for idx, rect in self._card_rects():
                if rect.collidepoint(mp):
                    if self.selected != idx:
                        self.selected = idx
                    else:
                        self.confirming = True
                        self.confirm_choice = 0
                    return
            if self._confirm_claim_rect().collidepoint(mp):
                self.confirming = True
                self.confirm_choice = 0
                return

    def _card_rects(self):
        """三张奖励卡的可点击区域（与 draw 布局一致）"""
        card_w = 250
        gap = 22
        total = card_w * 3 + gap * 2
        start_x = (cfg.SCREEN_WIDTH - total) // 2
        card_y = 150
        pad = 12
        text_w = card_w - pad * 2
        font_small = self.game.font_small
        font_medium = self.game.font_medium
        line_h = font_small.get_height() + 4
        rects = []
        for idx, item in enumerate(self.offer):
            x = start_x + idx * (card_w + gap)
            name_surf = font_medium.render(item.name, True, item.rarity_color)
            if name_surf.get_width() > text_w:
                name_surf = font_small.render(item.name, True, item.rarity_color)
            raw_lines = []
            price_text = self._price_text(item)
            if price_text:
                raw_lines.append((cfg.COLOR_YELLOW, price_text))
            if item.stat_text():
                raw_lines.append((cfg.COLOR_GREEN, item.stat_text()))
            for lore_line in item.lore[:3]:
                raw_lines.append((cfg.COLOR_WHITE, lore_line))
            text_lines = []
            for color, text in raw_lines:
                for line in self._wrap_text(font_small, text, text_w):
                    text_lines.append((color, line))
            shown = text_lines[:9]
            rarity_y = card_y + 78 + name_surf.get_height() + 4
            content_y = rarity_y + font_small.get_height() + 4
            if item.slot:
                content_y += font_small.get_height() + 4
            hint_y = content_y + len(shown) * line_h + 10
            card_h = max(250, (hint_y - card_y) + 34)
            rects.append((idx, pygame.Rect(x, card_y, card_w, card_h)))
        return rects

    def _confirm_claim_rect(self):
        """“确认领取”按钮区域"""
        return pygame.Rect(cfg.SCREEN_WIDTH // 2 - 90, 585, 180, 40)

    def _confirm_button_rects(self):
        """确认框中的“确定/返回”按钮区域（与 _draw_confirm 布局一致）"""
        labels = ["确定", "返回"]
        gap = 48
        box_w = 620
        box = pygame.Rect((cfg.SCREEN_WIDTH - box_w) // 2, 280, box_w, 220)
        total_w = sum(self.game.font_medium.size(label)[0] + 44 for label in labels) + gap
        x = (cfg.SCREEN_WIDTH - total_w) // 2
        y = box.y + box.h - 60
        rects = []
        for label in labels:
            w = self.game.font_medium.size(label)[0] + 44
            rects.append(pygame.Rect(x, y, w, 38))
            x += w + gap
        return rects

    def _update_confirm(self, keys):
        """确认领取环节：确定 / 返回。"""
        # 鼠标：点击按钮直接确定 / 返回
        mp = self.game.mouse_pos
        clicked = self.game.mouse_clicked(1)
        if clicked:
            button_rects = self._confirm_button_rects()
            for i, rect in enumerate(button_rects):
                if rect.collidepoint(mp):
                    self.confirm_choice = i
                    if i == 0:
                        item = self.offer[self.selected]
                        self.inventory.add_item(item.id, 1)
                        self.inventory.save_to_global_data(self.game.global_data)
                        from src.ui.intermission import IntermissionState
                        self.game.switch_state(IntermissionState(self.game, self.stage_num))
                    else:
                        self.confirming = False
                    return
            return
        if keys.get(pygame.K_ESCAPE, False) or keys.get(pygame.K_x, False):
            self.confirming = False
            return
        if keys.get(pygame.K_LEFT, False) or keys.get(pygame.K_a, False):
            self.confirm_choice = (self.confirm_choice - 1) % 2
        if keys.get(pygame.K_RIGHT, False) or keys.get(pygame.K_d, False):
            self.confirm_choice = (self.confirm_choice + 1) % 2
        if self._confirm_pressed(keys):
            if self.confirm_choice == 0:
                item = self.offer[self.selected]
                self.inventory.add_item(item.id, 1)
                self.inventory.save_to_global_data(self.game.global_data)
                from src.ui.intermission import IntermissionState
                self.game.switch_state(IntermissionState(self.game, self.stage_num))
            else:
                self.confirming = False

    def _fmt_price(self, value):
        if value <= 0:
            return "—"
        if value >= 1000000000:
            v = value / 1000000000.0
            return ("%gB" % v) if float(v).is_integer() else f"{v:.1f}B"
        if value >= 1000000:
            v = value / 1000000.0
            return ("%gM" % v) if float(v).is_integer() else f"{v:.1f}M"
        if value >= 1000:
            v = value / 1000.0
            return ("%gk" % v) if float(v).is_integer() else f"{v:.1f}k"
        return str(value)

    def _price_text(self, item):
        buy_s = self._fmt_price(item.buy_price) if item.buy_price > 0 else "—"
        sell_s = self._fmt_price(item.sell_price) if item.sell_price > 0 else "—"
        return f"买入 {buy_s}   卖出 {sell_s}"

    def _wrap_text(self, font, text, max_width):
        """word-wrap text by spaces; split overlong single words char by char."""
        lines = []
        cur = ""
        for word in text.split(" "):
            if not word:
                continue
            while word:
                trial = (cur + " " + word).strip()
                if font.size(trial)[0] <= max_width:
                    cur = trial
                    word = ""
                elif cur:
                    lines.append(cur)
                    cur = ""
                else:
                    cut = 1
                    while cut < len(word) and font.size(word[:cut + 1])[0] <= max_width:
                        cut += 1
                    lines.append(word[:cut])
                    word = word[cut:]
        if cur:
            lines.append(cur)
        return lines
    def draw(self, screen):
        screen.fill((7, 10, 25))
        title = self.game.font_large.render("Boss 奖励", True, cfg.COLOR_YELLOW)
        screen.blit(title, ((cfg.SCREEN_WIDTH - title.get_width()) // 2, 40))
        sub = self.game.font_medium.render(
            f'第 {self.stage_num} 面关底 Boss 已被击破：从 3 件战利品中选择 1 件',
            True, cfg.COLOR_WHITE)
        screen.blit(sub, ((cfg.SCREEN_WIDTH - sub.get_width()) // 2, 90))

        card_w = 250
        gap = 22
        total = card_w * 3 + gap * 2
        start_x = (cfg.SCREEN_WIDTH - total) // 2
        card_y = 150
        pad = 12
        text_w = card_w - pad * 2
        font_small = self.game.font_small
        font_medium = self.game.font_medium
        line_h = font_small.get_height() + 4

        for idx, item in enumerate(self.offer):
            x = start_x + idx * (card_w + gap)
            selected = idx == self.selected

            name_surf = font_medium.render(item.name, True, item.rarity_color)
            if name_surf.get_width() > text_w:
                name_surf = font_small.render(item.name, True, item.rarity_color)

            raw_lines = []
            price_text = self._price_text(item)
            if price_text:
                raw_lines.append((cfg.COLOR_YELLOW, price_text))
            if item.stat_text():
                raw_lines.append((cfg.COLOR_GREEN, item.stat_text()))
            for lore_line in item.lore[:3]:
                raw_lines.append((cfg.COLOR_WHITE, lore_line))
            text_lines = []
            for color, text in raw_lines:
                for line in self._wrap_text(font_small, text, text_w):
                    text_lines.append((color, line))
            shown = text_lines[:9]

            rarity_y = card_y + 78 + name_surf.get_height() + 4
            content_y = rarity_y + font_small.get_height() + 4
            if item.slot:
                content_y += font_small.get_height() + 4
            hint_y = content_y + len(shown) * line_h + 10
            card_h = max(250, (hint_y - card_y) + 34)

            panel = pygame.Rect(x, card_y, card_w, card_h)
            screen.blit(pygame.Surface((0, 0)), (0, 0))  # no-op keep pygame import
            pygame.draw.rect(screen, cfg.COLOR_PANEL_BG, panel)
            pygame.draw.rect(screen, item.rarity_color, panel, 3 if selected else 1)
            if self.game.mouse_hover(panel) and not selected:
                pygame.draw.rect(screen, cfg.COLOR_YELLOW, panel, 1)
            if selected:
                arrow = self.game.font_large.render(">", True, cfg.COLOR_YELLOW)
                screen.blit(arrow, (x - 24, card_y + card_h // 2 - 16))

            draw_item_icon(screen, item.id, x + (card_w - 48) // 2, card_y + 24, size=48)

            screen.blit(name_surf, (x + (card_w - name_surf.get_width()) // 2, card_y + 78))

            rarity = font_small.render(
                f"{item.rarity} · {ITEM_TYPE_LABELS.get(item.item_type, item.item_type)}",
                True, cfg.COLOR_GRAY)
            screen.blit(rarity, (x + (card_w - rarity.get_width()) // 2, rarity_y))

            ty = content_y
            if item.slot:
                slot_text = font_small.render(
                    SLOT_LABELS.get(item.slot, item.slot), True, cfg.COLOR_GRAY)
                screen.blit(slot_text, (x + (card_w - slot_text.get_width()) // 2, ty))
                ty += font_small.get_height() + 4
            for color, line in shown:
                surf = font_small.render(line, True, color)
                screen.blit(surf, (x + (card_w - surf.get_width()) // 2, ty))
                ty += line_h

            if selected:
                mark = font_medium.render("按 Enter 确认领取", True, cfg.COLOR_YELLOW)
                screen.blit(mark, (x + (card_w - mark.get_width()) // 2, hint_y))

        claim_rect = self._confirm_claim_rect()
        claim_hover = self.game.mouse_hover(claim_rect)
        pygame.draw.rect(screen, cfg.COLOR_PANEL_BG, claim_rect)
        pygame.draw.rect(screen, cfg.COLOR_YELLOW if claim_hover else cfg.COLOR_GRAY,
                         claim_rect, 2 if claim_hover else 1)
        claim_text = self.game.font_medium.render(
            "确认领取", True, cfg.COLOR_YELLOW if claim_hover else cfg.COLOR_WHITE)
        screen.blit(claim_text, (claim_rect.x + (claim_rect.width - claim_text.get_width()) // 2,
                                 claim_rect.y + (claim_rect.height - claim_text.get_height()) // 2))

        hint = self.game.font_small.render(
            "← → / A D：选择     Enter / Z / Space：确认领取", True, cfg.COLOR_DARK_GRAY)
        screen.blit(hint, ((cfg.SCREEN_WIDTH - hint.get_width()) // 2, cfg.SCREEN_HEIGHT - 70))

        if self.confirming:
            self._draw_confirm(screen)

    def _draw_confirm(self, screen):
        """确认领取环节：确定 / 返回。"""
        item = self.offer[self.selected]
        overlay = pygame.Surface((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        box_w = 620
        box_h = 220
        box = pygame.Rect((cfg.SCREEN_WIDTH - box_w) // 2, 280, box_w, box_h)
        pygame.draw.rect(screen, cfg.COLOR_PANEL_BG, box)
        pygame.draw.rect(screen, item.rarity_color, box, 2)

        q = self.game.font_medium.render("确定领取这件战利品吗？", True, cfg.COLOR_WHITE)
        screen.blit(q, ((cfg.SCREEN_WIDTH - q.get_width()) // 2, box.y + 30))

        name = self.game.font_medium.render(item.name, True, item.rarity_color)
        screen.blit(name, ((cfg.SCREEN_WIDTH - name.get_width()) // 2, box.y + 72))

        labels = ["确定", "返回"]
        gap = 48
        total_w = sum(self.game.font_medium.size(label)[0] + 44 for label in labels) + gap
        x = (cfg.SCREEN_WIDTH - total_w) // 2
        y = box.y + box_h - 60
        for idx, label in enumerate(labels):
            w = self.game.font_medium.size(label)[0] + 44
            rect = pygame.Rect(x, y, w, 38)
            selected = idx == self.confirm_choice
            pygame.draw.rect(screen,
                             cfg.COLOR_YELLOW if selected else cfg.COLOR_DARK_GRAY,
                             rect, 2 if selected else 1)
            color = cfg.COLOR_YELLOW if selected else cfg.COLOR_GRAY
            surf = self.game.font_medium.render(label, True, color)
            screen.blit(surf, (rect.x + (w - surf.get_width()) // 2,
                               rect.y + (38 - surf.get_height()) // 2))
            x += w + gap

        hint = self.game.font_small.render(
            "← → 选择　Enter / Z / Space：确认　Esc / X：取消", True, cfg.COLOR_DARK_GRAY)
        screen.blit(hint, ((cfg.SCREEN_WIDTH - hint.get_width()) // 2, box.y + box_h + 10))
