# 仓库出征准备：从本地仓库选择携带物品与金币后开始新远征

import pygame
from src.engine import settings as cfg
from src.engine.game import GameState
from src.systems.item_system import ITEM_TYPE_LABELS, SKYBLOCK_ITEMS, SLOT_LABELS
from src.systems.item_icons import draw_item_icon
from src.systems.warehouse import load_warehouse, save_warehouse


class LoadoutState(GameState):
    """从仓库挑选本局携带物品与金币（出征准备）。"""

    def __init__(self, game):
        super().__init__(game)
        self.warehouse = load_warehouse()
        self.entries = self.warehouse.get_inventory_entries()
        self.carried = {}          # item_id -> 携带数量
        self.carried_coins = 0     # 携带金币
        self.selected = 0
        self.message = ""
        self.message_timer = 0
        self.coin_step = 100

    def enter(self, game):
        self.game.stop_music()
        self.selected = 0

    def _set_message(self, text, frames=90):
        self.message = text
        self.message_timer = frames

    def _confirm_pressed(self, keys):
        return (keys.get(pygame.K_RETURN, False)
                or keys.get(pygame.K_z, False)
                or keys.get(pygame.K_SPACE, False))

    def _carry_total(self):
        return sum(self.carried.values())

    def update(self, dt):
        keys = self.game.keys_just_pressed

        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer <= 0:
                self.message = ""

        if keys.get(pygame.K_ESCAPE, False):
            from src.ui.menu import MenuState
            self.game.switch_state(MenuState(self.game))
            return

        if self.entries:
            if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
                self.selected = (self.selected - 1) % len(self.entries)
            if keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
                self.selected = (self.selected + 1) % len(self.entries)

            entry = self.entries[self.selected]
            item_id = entry["id"]
            if self._confirm_pressed(keys):
                if self.carried.get(item_id, 0) < entry["count"]:
                    self.carried[item_id] = self.carried.get(item_id, 0) + 1
                else:
                    self._set_message("仓库中没有更多该物品")
            if keys.get(pygame.K_x, False) or keys.get(pygame.K_c, False):
                if self.carried.get(item_id, 0) > 0:
                    self.carried[item_id] -= 1
                    if self.carried[item_id] <= 0:
                        self.carried.pop(item_id, None)
                else:
                    self._set_message("未携带该物品")

        # 调整携带金币
        if keys.get(pygame.K_RIGHT, False) or keys.get(pygame.K_d, False):
            self.carried_coins = min(self.warehouse.coins, self.carried_coins + self.coin_step)
        if keys.get(pygame.K_LEFT, False) or keys.get(pygame.K_a, False):
            self.carried_coins = max(0, self.carried_coins - self.coin_step)

        if keys.get(pygame.K_n, False):
            self._start_run()

    def _start_run(self):
        """从仓库扣减携带物资，写入本局背包并进入出发前休整界面。"""
        from src.systems.item_system import ItemInventory

        carried_ref = {}
        for item_id, count in list(self.carried.items()):
            if count <= 0:
                continue
            prefix = self.warehouse.applied_reforges.pop(item_id, None)
            if prefix is not None:
                carried_ref[item_id] = prefix
            self.warehouse.remove_item(item_id, count)
        self.warehouse.coins = max(0, self.warehouse.coins - self.carried_coins)
        save_warehouse(self.warehouse)

        run = ItemInventory()
        for item_id, count in self.carried.items():
            if count <= 0:
                continue
            run.add_item(item_id, count)
            if item_id in carried_ref:
                run.applied_reforges[item_id] = carried_ref[item_id]
        run.coins = self.carried_coins
        run.save_to_global_data(self.game.global_data)

        # 重置本局数值
        self.game.global_data["score"] = 0
        self.game.global_data["lives"] = cfg.PLAYER_START_LIVES
        self.game.global_data["bombs"] = cfg.PLAYER_START_BOMBS
        self.game.global_data["power"] = 0
        self.game.global_data["graze"] = 0

        # 先进入出发前休整界面：可穿戴携带的物品，确认后再进入第一面
        from src.ui.intermission import IntermissionState
        self.game.switch_state(IntermissionState(self.game, 0, pre_start=True))

    def draw(self, screen):
        screen.fill((7, 10, 25))

        title = self.game.font_large.render("仓库 · 出征准备", True, cfg.COLOR_YELLOW)
        screen.blit(title, ((cfg.SCREEN_WIDTH - title.get_width()) // 2, 28))

        sub = self.game.font_small.render(
            "选择携带物品与金币进入远征（未携带的物资保留在仓库）", True, cfg.COLOR_GRAY)
        screen.blit(sub, ((cfg.SCREEN_WIDTH - sub.get_width()) // 2, 72))

        # 左列：仓库物品
        left_x = 60
        y = 120
        header = self.game.font_medium.render("仓库物品", True, cfg.COLOR_WHITE)
        screen.blit(header, (left_x, y))
        y += 38
        if not self.entries:
            self._draw_text(screen, "仓库为空，可直接出发（N）", left_x, y,
                            cfg.COLOR_GRAY, self.game.font_medium)
        else:
            visible, start = self._visible_slice(self.entries, self.selected, 10)
            for offset, entry in enumerate(visible):
                idx = start + offset
                selected = idx == self.selected
                item = entry["item"]
                color = cfg.COLOR_YELLOW if selected else item.rarity_color
                prefix = "> " if selected else "  "
                draw_item_icon(screen, item.id, left_x, y, size=28)
                name = self.game.font_small.render(
                    f"{prefix}{entry['display_name']}  x{entry['count']}", True, color)
                screen.blit(name, (left_x + 40, y + 4))
                carried_n = self.carried.get(entry["id"], 0)
                if carried_n > 0:
                    badge = self.game.font_small.render(f"携带 {carried_n}", True, cfg.COLOR_GREEN)
                    screen.blit(badge, (left_x + 430, y + 4))
                y += 32

        # 右列：携带清单
        right_x = 600
        y = 120
        header = self.game.font_medium.render("携带清单", True, cfg.COLOR_WHITE)
        screen.blit(header, (right_x, y))
        y += 38
        if not self.carried:
            self._draw_text(screen, "未携带物品", right_x, y, cfg.COLOR_GRAY, self.game.font_small)
            y += 26
        else:
            for item_id, count in self.carried.items():
                item = SKYBLOCK_ITEMS.get(item_id)
                if not item:
                    continue
                line = self.game.font_small.render(f"{item.name}  x{count}", True, item.rarity_color)
                screen.blit(line, (right_x, y))
                y += 24
        y += 10
        coins_line = self.game.font_small.render(
            f"携带金币：{self.carried_coins}  /  仓库：{self.warehouse.coins}",
            True, cfg.COLOR_YELLOW)
        screen.blit(coins_line, (right_x, y))
        y += 30
        total_line = self.game.font_small.render(
            f"共携带 {self._carry_total()} 件物品", True, cfg.COLOR_GRAY)
        screen.blit(total_line, (right_x, y))

        # 底部：当前选中仓库物品的属性
        selected_item = None
        if self.entries:
            selected_item = self.entries[self.selected]["item"]
        self._draw_item_detail_panel(screen, selected_item)

        # 底部操作提示
        hints = [
            "↑↓：选择   Enter/Z：携带   X：卸下",
            "A/D 或 ←→：调整携带金币（步进 100）",
            "N：进入休整（穿戴携带物品）   Esc：返回主菜单",
        ]
        hint_y = cfg.SCREEN_HEIGHT - 74
        for line in hints:
            hint = self.game.font_small.render(line, True, cfg.COLOR_DARK_GRAY)
            screen.blit(hint, ((cfg.SCREEN_WIDTH - hint.get_width()) // 2, hint_y))
            hint_y += 20

        if self.message:
            msg = self.game.font_medium.render(self.message, True, cfg.COLOR_GREEN)
            screen.blit(msg, ((cfg.SCREEN_WIDTH - msg.get_width()) // 2, cfg.SCREEN_HEIGHT - 84))

    def _item_detail_lines(self, item):
        """生成物品功能说明行 [(文本, 颜色)]：类型/部位 + 基础属性 + lore"""
        lines = []
        if item is None:
            return lines
        type_label = ITEM_TYPE_LABELS.get(item.item_type, item.item_type)
        if item.is_equippable:
            type_label += f"  部位：{SLOT_LABELS.get(item.slot, item.slot)}"
        lines.append((f"类型：{type_label}", cfg.COLOR_YELLOW))
        stat_text = item.stat_text()
        if stat_text:
            lines.append((stat_text, cfg.COLOR_GRAY))
        lines.extend((line, cfg.COLOR_WHITE) for line in (item.lore or []))
        return lines

    def _draw_item_detail_panel(self, screen, item, x=36, y=500, w=None, h=132):
        """底部物品属性面板：名称 / 类型 / 基础属性 / lore"""
        if w is None:
            w = cfg.SCREEN_WIDTH - 72
        panel = pygame.Rect(x, y, w, h)
        pygame.draw.rect(screen, cfg.COLOR_PANEL_BG, panel)
        pygame.draw.rect(screen, cfg.COLOR_DARK_GRAY, panel, 1)
        py = panel.y + 10
        if item is None:
            self._draw_text(screen, "未选择物品", panel.x + 16, py,
                            cfg.COLOR_GRAY, self.game.font_small)
            return
        name = self.game.font_medium.render(item.name, True, item.rarity_color)
        screen.blit(name, (panel.x + 16, py))
        py += 28
        for text, color in self._item_detail_lines(item):
            if py > panel.y + panel.height - 8:
                break
            py = self._draw_text(screen, text, panel.x + 16, py, color, self.game.font_small)

    def _draw_text(self, screen, text, x, y, color, font):
        surf = font.render(text, True, color)
        screen.blit(surf, (x, y))
        return y + surf.get_height() + 6

    def _visible_slice(self, entries, selected, max_rows):
        if len(entries) <= max_rows:
            return entries, 0
        start = max(0, min(selected - max_rows // 2, len(entries) - max_rows))
        return entries[start:start + max_rows], start
