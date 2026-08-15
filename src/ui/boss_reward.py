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

    def enter(self, game):
        self.game.stop_music()
        self.selected = 0

    def exit(self):
        self.inventory.save_to_global_data(self.game.global_data)

    def _confirm_pressed(self, keys):
        return (keys.get(pygame.K_RETURN, False)
                or keys.get(pygame.K_z, False)
                or keys.get(pygame.K_SPACE, False))

    def update(self, dt):
        keys = self.game.keys_just_pressed
        if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
            self.selected = (self.selected - 1) % len(self.offer)
        if keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
            self.selected = (self.selected + 1) % len(self.offer)
        if self._confirm_pressed(keys) and self.offer:
            item = self.offer[self.selected]
            self.inventory.add_item(item.id, 1)
            self.inventory.save_to_global_data(self.game.global_data)
            from src.ui.intermission import IntermissionState
            self.game.switch_state(IntermissionState(self.game, self.stage_num))

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
                mark = font_medium.render("按 Enter 领取", True, cfg.COLOR_YELLOW)
                screen.blit(mark, (x + (card_w - mark.get_width()) // 2, hint_y))

        hint = self.game.font_small.render(
            "↑↓ / W S：选择     Enter / Z / Space：领取并进入休整", True, cfg.COLOR_DARK_GRAY)
        screen.blit(hint, ((cfg.SCREEN_WIDTH - hint.get_width()) // 2, cfg.SCREEN_HEIGHT - 70))
