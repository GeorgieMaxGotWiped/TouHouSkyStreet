# 每面结束后的休整界面
# 包含装备 / 背包 / 商店三个页面

import pygame
from src.engine import settings as cfg
from src.engine.game import GameState
from src.systems.item_system import (
    EQUIPMENT_SLOTS,
    SLOT_LABELS,
    ITEM_TYPE_LABELS,
    REFORGE_STONES,
    REFORGES,
    ItemInventory,
)
from src.systems.item_icons import draw_item_icon


class IntermissionState(GameState):
    """关卡间休整界面"""

    def __init__(self, game, stage_num):
        super().__init__(game)
        self.stage_num = stage_num
        self.inventory = ItemInventory.from_global_data(game.global_data)
        self.page_names = ["equipment", "inventory", "shop", "forge"]
        self.page_labels = ["装备", "背包", "商店", "锻造"]
        self.page_idx = 0
        self.selected = 0
        self.choosing_slot = None
        self.choose_selected = 0
        self.shop_mode = "buy"
        self.forge_mode = "stone"   # stone：选重铸石 / item：选物品
        self.forge_stone_idx = 0
        self.forge_item_idx = 0
        self.message = ""
        self.message_timer = 0

    def enter(self, game):
        self.game.stop_music()
        self.selected = 0
        self.choosing_slot = None
        self.shop_mode = "buy"
        self.forge_mode = "stone"
        self.forge_stone_idx = 0
        self.forge_item_idx = 0
        self.message = ""

    def exit(self):
        self._save_inventory()

    def _save_inventory(self):
        self.inventory.save_to_global_data(self.game.global_data)

    def _set_message(self, text, frames=90):
        self.message = text
        self.message_timer = frames

    def _confirm_pressed(self, keys):
        return (keys.get(pygame.K_RETURN, False)
                or keys.get(pygame.K_z, False)
                or keys.get(pygame.K_SPACE, False))

    def _set_page(self, idx):
        self.page_idx = idx % len(self.page_names)
        self.selected = 0
        self.choosing_slot = None
        self.choose_selected = 0
        self.shop_mode = "buy"
        self.forge_mode = "stone"
        self.forge_stone_idx = 0
        self.forge_item_idx = 0
        self.message = ""

    def _current_shop_entries(self):
        if self.shop_mode == "buy":
            return self.inventory.get_shop_stock()
        return self.inventory.get_sellable_entries()

    def _go_menu(self):
        self._save_inventory()
        from src.ui.menu import MenuState
        self.game.switch_state(MenuState(self.game))

    def _continue_next_stage(self):
        self._save_inventory()
        from src.stages import get_next_stage_class
        from src.ui.menu import MenuState, PlayingState
        next_cls = get_next_stage_class(self.stage_num)
        if next_cls is None:
            self.game.switch_state(MenuState(self.game))
            return
        stage = next_cls()
        stage.setup_waves()
        self.game.switch_state(PlayingState(self.game, stage))

    def update(self, dt):
        keys = self.game.keys_just_pressed

        if keys.get(pygame.K_ESCAPE, False):
            if self.choosing_slot is not None:
                self.choosing_slot = None
                self.choose_selected = 0
                return
            self._go_menu()
            return
        if keys.get(pygame.K_n, False):
            self._continue_next_stage()
            return

        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer <= 0:
                self.message = ""

        if keys.get(pygame.K_q, False):
            self._set_page(self.page_idx - 1)
            return
        if keys.get(pygame.K_e, False):
            self._set_page(self.page_idx + 1)
            return
        if keys.get(pygame.K_1, False):
            self._set_page(0)
            return
        if keys.get(pygame.K_2, False):
            self._set_page(1)
            return
        if keys.get(pygame.K_3, False):
            self._set_page(2)
            return
        if keys.get(pygame.K_4, False):
            self._set_page(3)
            return

        # 装备选择子界面
        if self.choosing_slot is not None:
            entries = self.inventory.get_equippable_entries_for_slot(self.choosing_slot)
            if keys.get(pygame.K_ESCAPE, False) or keys.get(pygame.K_x, False):
                self.choosing_slot = None
                self.choose_selected = 0
                return
            if not entries:
                if self._confirm_pressed(keys):
                    self.choosing_slot = None
                    self.choose_selected = 0
                    self._set_message("背包中没有可装备的物品")
                return

            if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
                self.choose_selected = (self.choose_selected - 1) % len(entries)
            if keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
                self.choose_selected = (self.choose_selected + 1) % len(entries)

            if self._confirm_pressed(keys):
                entry = entries[self.choose_selected]
                self.inventory.equip(entry["id"])
                self._save_inventory()
                self._set_message(f"已装备：{entry['item'].name}")
                self.choosing_slot = None
                self.choose_selected = 0
            return

        page = self.page_names[self.page_idx]

        if page == "equipment":
            if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
                self.selected = (self.selected - 1) % len(EQUIPMENT_SLOTS)
            if keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
                self.selected = (self.selected + 1) % len(EQUIPMENT_SLOTS)
            if self._confirm_pressed(keys):
                self.choosing_slot = EQUIPMENT_SLOTS[self.selected]
                self.choose_selected = 0
            return

        if page == "inventory":
            entries = self.inventory.get_inventory_entries()
            if entries:
                if self.selected >= len(entries):
                    self.selected = len(entries) - 1
                if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
                    self.selected = (self.selected - 1) % len(entries)
                if keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
                    self.selected = (self.selected + 1) % len(entries)
                if self._confirm_pressed(keys):
                    entry = entries[self.selected]
                    item = entry["item"]
                    if not item.is_equippable:
                        self._set_message("该物品不能装备")
                    elif self.inventory.is_equipped(item.id):
                        self.inventory.unequip_item(item.id)
                        self._save_inventory()
                        self._set_message(f"已卸下：{item.name}")
                    else:
                        self.inventory.equip(item.id)
                        self._save_inventory()
                        self._set_message(f"已装备：{item.name}")
            elif self._confirm_pressed(keys):
                self._set_message("背包是空的")
            return

        if page == "shop":
            if keys.get(pygame.K_LEFT, False) or keys.get(pygame.K_a, False):
                self.shop_mode = "buy"
                self.selected = 0
            if keys.get(pygame.K_RIGHT, False) or keys.get(pygame.K_d, False):
                self.shop_mode = "sell"
                self.selected = 0

            entries = self._current_shop_entries()
            if entries:
                if self.selected >= len(entries):
                    self.selected = len(entries) - 1
                if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
                    self.selected = (self.selected - 1) % len(entries)
                if keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
                    self.selected = (self.selected + 1) % len(entries)

                if self._confirm_pressed(keys):
                    entry = entries[self.selected]
                    if self.shop_mode == "buy":
                        price = entry["buy_price"]
                        item = entry["item"]
                        if self.inventory.spend_coins(price):
                            self.inventory.add_item(item.id, 1)
                            self._save_inventory()
                            self._set_message(f"购买成功：{item.name}（-{price} 金币）")
                        else:
                            self._set_message("金币不足")
                    else:
                        price = entry["sell_price"]
                        item = entry["item"]
                        self.inventory.remove_item(item.id, 1)
                        self.inventory.add_coins(price)
                        self._save_inventory()
                        self._set_message(f"出售成功：{item.name}（+{price} 金币）")
            elif self._confirm_pressed(keys):
                if self.shop_mode == "buy":
                    self._set_message("商店暂无商品")
                else:
                    self._set_message("没有可出售的装备")
            return

        if page == "forge":
            self._update_forge_page(keys)
            return

    def _update_forge_page(self, keys):
        """锻造页交互：先选重铸石，再选物品，确认后打上前缀"""
        stones, forge_items = self.inventory.get_forge_entries()

        # 取消/返回：从选物品退回选重铸石
        if self.forge_mode == "item" and (keys.get(pygame.K_ESCAPE, False)
                                          or keys.get(pygame.K_x, False)):
            self.forge_mode = "stone"
            self.forge_stone_idx = 0
            return

        if self.forge_mode == "stone":
            if not stones:
                if self._confirm_pressed(keys):
                    self._set_message("背包中没有重铸石")
                return
            if self.forge_stone_idx >= len(stones):
                self.forge_stone_idx = 0
            if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
                self.forge_stone_idx = (self.forge_stone_idx - 1) % len(stones)
            if keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
                self.forge_stone_idx = (self.forge_stone_idx + 1) % len(stones)
            if self._confirm_pressed(keys):
                self.forge_mode = "item"
                self.forge_item_idx = 0
            return

        # forge_mode == "item"
        if not forge_items:
            self.forge_mode = "stone"
            self.forge_stone_idx = 0
            self._set_message("没有可锻造的物品")
            return
        if self.forge_item_idx >= len(forge_items):
            self.forge_item_idx = 0
        if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
            self.forge_item_idx = (self.forge_item_idx - 1) % len(forge_items)
        if keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
            self.forge_item_idx = (self.forge_item_idx + 1) % len(forge_items)
        if self._confirm_pressed(keys):
            stone = stones[self.forge_stone_idx] if stones else None
            entry = forge_items[self.forge_item_idx]
            if stone is None:
                self.forge_mode = "stone"
                self._set_message("背包中没有重铸石")
                return
            ok, err = self.inventory.apply_reforge(entry["id"], stone["id"])
            self._save_inventory()
            if ok:
                prefix = REFORGE_STONES.get(stone["id"])
                prefix_name = REFORGES[prefix]["name"] if prefix in REFORGES else prefix
                self._set_message(f"重铸成功：{prefix_name} {entry['item'].name}"
                                  f"（-{entry['cost']} 金币）")
                # 物品被重铸后回到选石头阶段，方便连续锻造
                self.forge_mode = "stone"
                self.forge_stone_idx = 0
            else:
                self._set_message(err or "重铸失败")
        return

    # --- 绘制辅助 ---

    def _draw_text(self, screen, text, x, y, color, font):
        surf = font.render(text, True, color)
        screen.blit(surf, (x, y))
        return y + surf.get_height() + 6

    def _visible_slice(self, entries, selected, max_rows):
        if len(entries) <= max_rows:
            return entries, 0
        start = max(0, min(selected - max_rows // 2, len(entries) - max_rows))
        return entries[start:start + max_rows], start

    def draw(self, screen):
        screen.fill((7, 10, 25))

        # 标题与金币
        title = self.game.font_large.render(f"第 {self.stage_num} 面结束 · 休整", True, cfg.COLOR_YELLOW)
        screen.blit(title, ((cfg.SCREEN_WIDTH - title.get_width()) // 2, 28))

        coins = self.game.font_medium.render(f"金币：{self.inventory.coins}", True, cfg.COLOR_YELLOW)
        screen.blit(coins, (cfg.SCREEN_WIDTH - coins.get_width() - 28, 34))

        # 顶部页签
        tab_y = 88
        tab_x = 120
        tab_gap = 250
        for i, label in enumerate(self.page_labels):
            x = tab_x + i * tab_gap
            color = cfg.COLOR_YELLOW if i == self.page_idx else cfg.COLOR_GRAY
            text = self.game.font_medium.render(label, True, color)
            screen.blit(text, (x, tab_y))
            if i == self.page_idx:
                pygame.draw.line(screen, cfg.COLOR_YELLOW, (x, tab_y + 28), (x + text.get_width(), tab_y + 28), 2)

        pygame.draw.line(screen, cfg.COLOR_DARK_GRAY, (36, 126), (cfg.SCREEN_WIDTH - 36, 126), 2)

        if self.page_idx == 0:
            self._draw_equipment_page(screen)
        elif self.page_idx == 1:
            self._draw_inventory_page(screen)
        elif self.page_idx == 2:
            self._draw_shop_page(screen)
        else:
            self._draw_forge_page(screen)

        # 底部操作提示
        hints = [
            "Q/E 或 1/2/3/4：切换页面",
            "↑↓：选择   Enter/Z/Space：确认",
            "N：进入下一关",
            "Esc：返回主菜单",
        ]
        hint_y = cfg.SCREEN_HEIGHT - 88
        for line in hints:
            hint = self.game.font_small.render(line, True, cfg.COLOR_DARK_GRAY)
            screen.blit(hint, (36, hint_y))
            hint_y += 19

        if self.message:
            msg = self.game.font_medium.render(self.message, True, cfg.COLOR_GREEN)
            screen.blit(msg, ((cfg.SCREEN_WIDTH - msg.get_width()) // 2, cfg.SCREEN_HEIGHT - 120))

    def _draw_equipment_page(self, screen):
        y = 150
        left_x = 80
        right_x = 500
        header = self.game.font_medium.render("装备槽", True, cfg.COLOR_WHITE)
        screen.blit(header, (left_x, y))
        y += 42

        stats = self.inventory.get_equipped_stats()
        for i, slot in enumerate(EQUIPMENT_SLOTS):
            selected = i == self.selected
            row_color = cfg.COLOR_YELLOW if selected else cfg.COLOR_WHITE
            item = self.inventory.get_equipped_item(slot)
            prefix = "> " if selected else "  "
            label = self.game.font_medium.render(
                f"{prefix}{SLOT_LABELS[slot]}", True, row_color)
            screen.blit(label, (left_x, y))

            if item is not None:
                name_color = item.rarity_color
                draw_item_icon(screen, item.id, left_x + 138, y, size=32)
                name = self.game.font_medium.render(
                    self.inventory.get_display_name(item.id), True, name_color)
                screen.blit(name, (left_x + 178, y))
                stat_text = item.stat_text()
                if stat_text:
                    stat = self.game.font_small.render(stat_text, True, cfg.COLOR_GRAY)
                    screen.blit(stat, (left_x + 178, y + 28))
            else:
                empty = self.game.font_medium.render("（空）", True, cfg.COLOR_GRAY)
                screen.blit(empty, (left_x + 178, y))
            y += 58

        # 总属性
        y = 150
        header = self.game.font_medium.render("总属性", True, cfg.COLOR_WHITE)
        screen.blit(header, (right_x, y))
        y += 42
        if not stats:
            self._draw_text(screen, "暂无装备属性", right_x, y, cfg.COLOR_GRAY, self.game.font_small)
        else:
            for key, value in stats.items():
                y = self._draw_text(screen, f"{key}: {value}", right_x, y,
                                    cfg.COLOR_GREEN, self.game.font_small)

        # 装备选择覆盖层
        if self.choosing_slot is not None:
            self._draw_equip_chooser(screen)

    def _draw_equip_chooser(self, screen):
        entries = self.inventory.get_equippable_entries_for_slot(self.choosing_slot)
        panel = pygame.Rect(260, 120, 500, 420)
        overlay = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        overlay.fill((14, 18, 40, 238))
        screen.blit(overlay, panel.topleft)
        pygame.draw.rect(screen, cfg.COLOR_YELLOW, panel, 2)

        title = self.game.font_medium.render(
            f"选择 {SLOT_LABELS[self.choosing_slot]}", True, cfg.COLOR_YELLOW)
        screen.blit(title, (panel.x + 24, panel.y + 18))

        if not entries:
            text = self.game.font_small.render("背包中没有可装备的物品", True, cfg.COLOR_GRAY)
            screen.blit(text, (panel.x + 24, panel.y + 80))
            hint = self.game.font_small.render("Enter / Esc 返回", True, cfg.COLOR_GRAY)
            screen.blit(hint, (panel.x + 24, panel.y + 112))
            return

        visible, start = self._visible_slice(entries, self.choose_selected, 9)
        y = panel.y + 62
        for offset, entry in enumerate(visible):
            idx = start + offset
            selected = idx == self.choose_selected
            color = cfg.COLOR_YELLOW if selected else cfg.COLOR_WHITE
            name = entry["item"]
            prefix = "> " if selected else "  "
            draw_item_icon(screen, name.id, panel.x + 24, y, size=28)
            line = self.game.font_small.render(
                f"{prefix}{entry['display_name']}  x{entry['count']}", True,
                name.rarity_color if selected else color)
            screen.blit(line, (panel.x + 58, y))
            if entry["equipped"]:
                badge = self.game.font_small.render("当前已装备", True, cfg.COLOR_GREEN)
                screen.blit(badge, (panel.x + 340, y))
            y += 32

        hint = self.game.font_small.render("Enter 装备   Esc 取消", True, cfg.COLOR_GRAY)
        screen.blit(hint, (panel.x + 24, panel.y + panel.height - 34))

    def _draw_inventory_page(self, screen):
        entries = self.inventory.get_inventory_entries()
        y = 150
        header = self.game.font_medium.render("背包物品", True, cfg.COLOR_WHITE)
        screen.blit(header, (80, y))
        y += 42

        if not entries:
            self._draw_text(screen, "背包是空的", 80, y, cfg.COLOR_GRAY, self.game.font_medium)
            return

        visible, start = self._visible_slice(entries, self.selected, 14)
        for offset, entry in enumerate(visible):
            idx = start + offset
            selected = idx == self.selected
            item = entry["item"]
            prefix = "> " if selected else "  "
            color = item.rarity_color
            draw_item_icon(screen, item.id, 80, y, size=28)
            line = f"{prefix}{entry['display_name']}"
            if entry["count"] > 1:
                line += f"  x{entry['count']}"
            surf = self.game.font_small.render(line, True, color)
            screen.blit(surf, (116, y))

            tags = []
            if entry["equipped"]:
                tags.append(f"已装备：{SLOT_LABELS.get(entry['equipped'], entry['equipped'])}")
            if item.stat_text():
                tags.append(item.stat_text())
            if tags:
                tag = self.game.font_small.render(" | ".join(tags), True, cfg.COLOR_GRAY)
                screen.blit(tag, (430, y))
            y += 30

    def _draw_shop_page(self, screen):
        y = 150
        buy_color = cfg.COLOR_YELLOW if self.shop_mode == "buy" else cfg.COLOR_GRAY
        sell_color = cfg.COLOR_YELLOW if self.shop_mode == "sell" else cfg.COLOR_GRAY
        buy_text = self.game.font_medium.render("购买", True, buy_color)
        sell_text = self.game.font_medium.render("出售", True, sell_color)
        screen.blit(buy_text, (80, y))
        screen.blit(sell_text, (180, y))
        pygame.draw.line(screen, cfg.COLOR_DARK_GRAY, (36, y + 32), (cfg.SCREEN_WIDTH - 36, y + 32), 2)
        y += 48

        entries = self._current_shop_entries()
        if not entries:
            text = "商店暂无商品" if self.shop_mode == "buy" else "没有可出售的装备"
            self._draw_text(screen, text, 80, y, cfg.COLOR_GRAY, self.game.font_medium)
            return

        visible, start = self._visible_slice(entries, self.selected, 13)
        for offset, entry in enumerate(visible):
            idx = start + offset
            selected = idx == self.selected
            item = entry["item"]
            prefix = "> " if selected else "  "
            name_color = item.rarity_color
            draw_item_icon(screen, item.id, 80, y, size=28)
            name = f"{prefix}{item.name}"
            if self.shop_mode == "sell" and entry.get("count", 0) > 1:
                name += f"  x{entry['count']}"
            name_surf = self.game.font_small.render(name, True, name_color)
            screen.blit(name_surf, (116, y))

            if self.shop_mode == "buy":
                price = self.game.font_small.render(f"购买 {entry['buy_price']} 金币", True, cfg.COLOR_YELLOW)
                screen.blit(price, (500, y))
            else:
                price = self.game.font_small.render(f"出售 +{entry['sell_price']} 金币", True, cfg.COLOR_GREEN)
                screen.blit(price, (500, y))
                if entry.get("equipped"):
                    badge = self.game.font_small.render("已装备", True, cfg.COLOR_GREEN)
                    screen.blit(badge, (700, y))
            y += 30

    def _draw_forge_page(self, screen):
        """锻造页：左侧重铸石，右侧可锻造物品，底部预览与操作提示"""
        stones, forge_items = self.inventory.get_forge_entries()
        left_x = 60
        right_x = 470
        y = 150

        # 左列：重铸石
        header = self.game.font_medium.render("重铸石", True, cfg.COLOR_WHITE)
        screen.blit(header, (left_x, y))
        y += 40
        if not stones:
            self._draw_text(screen, "背包中没有重铸石", left_x, y, cfg.COLOR_GRAY, self.game.font_small)
        else:
            visible, start = self._visible_slice(stones, self.forge_stone_idx, 8)
            for offset, entry in enumerate(visible):
                idx = start + offset
                selected = (self.forge_mode == "stone" and idx == self.forge_stone_idx)
                item = entry["item"]
                prefix = REFORGES.get(entry["prefix"])
                prefix_name = prefix.get("name", "") if prefix else ""
                color = item.rarity_color if selected else cfg.COLOR_WHITE
                draw_item_icon(screen, item.id, left_x, y)
                line = f"{'> ' if selected else '  '}{item.name} x{entry['count']}"
                surf = self.game.font_small.render(line, True, color)
                screen.blit(surf, (left_x + 42, y + 8))
                if prefix_name:
                    eff = self.game.font_small.render(f"→ {prefix_name}", True, cfg.COLOR_GRAY)
                    screen.blit(eff, (left_x + 250, y + 8))
                y += 40

        # 右列：可锻造物品
        y = 150
        header = self.game.font_medium.render("可锻造物品", True, cfg.COLOR_WHITE)
        screen.blit(header, (right_x, y))
        y += 40
        if not forge_items:
            self._draw_text(screen, "背包中没有可锻造的物品", right_x, y, cfg.COLOR_GRAY, self.game.font_small)
        else:
            visible, start = self._visible_slice(forge_items, self.forge_item_idx, 8)
            for offset, entry in enumerate(visible):
                idx = start + offset
                selected = (self.forge_mode == "item" and idx == self.forge_item_idx)
                item = entry["item"]
                color = item.rarity_color if selected else cfg.COLOR_WHITE
                draw_item_icon(screen, item.id, right_x, y)
                name = entry["display_name"]
                line = f"{'> ' if selected else '  '}{name}"
                surf = self.game.font_small.render(line, True, color)
                screen.blit(surf, (right_x + 42, y + 8))
                cost = self.game.font_small.render(f"{entry['cost']} 金币", True, cfg.COLOR_YELLOW)
                screen.blit(cost, (right_x + 300, y + 8))
                if entry.get("equipped"):
                    badge = self.game.font_small.render("已装备", True, cfg.COLOR_GREEN)
                    screen.blit(badge, (right_x + 380, y + 8))
                y += 40

        # 底部预览面板
        panel = pygame.Rect(36, 470, cfg.SCREEN_WIDTH - 72, 190)
        pygame.draw.rect(screen, cfg.COLOR_PANEL_BG, panel)
        pygame.draw.rect(screen, cfg.COLOR_DARK_GRAY, panel, 1)
        py = panel.y + 12
        stone = stones[self.forge_stone_idx] if stones else None
        prefix = REFORGES.get(stone["prefix"]) if stone else None
        if stone is None:
            self._draw_text(screen, "请先获得重铸石（道中Boss / 关底Boss / 商店）", panel.x + 20, py,
                            cfg.COLOR_GRAY, self.game.font_small)
        elif self.forge_mode == "stone" or not forge_items:
            tip = f"选择 {stone['item'].name}：锻造后获得前缀 "
            tip += prefix["name"] if prefix else "?"
            if prefix:
                tip += f"（{prefix['label']}）"
            self._draw_text(screen, tip, panel.x + 20, py, cfg.COLOR_YELLOW, self.game.font_small)
            if prefix:
                py = self._draw_text(screen, "加成：", panel.x + 20, py + 4,
                                     cfg.COLOR_WHITE, self.game.font_small)
                for key, value in prefix["stats"].items():
                    py = self._draw_text(screen, f"  {key}: +{value}", panel.x + 20, py,
                                         cfg.COLOR_GREEN, self.game.font_small)
            hint = self.game.font_small.render("Enter：选择该重铸石 → 选物品", True, cfg.COLOR_GRAY)
            screen.blit(hint, (panel.x + 20, panel.y + panel.height - 30))
        else:
            entry = forge_items[self.forge_item_idx]
            item = entry["item"]
            line = f"将 {stone['item'].name} 锻造到 {entry['display_name']}"
            self._draw_text(screen, line, panel.x + 20, py, cfg.COLOR_YELLOW, self.game.font_small)
            if prefix:
                py = self._draw_text(screen, "前缀加成：", panel.x + 20, py + 4,
                                     cfg.COLOR_WHITE, self.game.font_small)
                for key, value in prefix["stats"].items():
                    py = self._draw_text(screen, f"  {key}: +{value}", panel.x + 20, py,
                                         cfg.COLOR_GREEN, self.game.font_small)
            old = self.inventory.get_item_prefix(item.id)
            old_name = REFORGES[old]["name"] if old in REFORGES else "无"
            py = self._draw_text(screen, f"当前前缀：{old_name}    费用：{entry['cost']} 金币",
                                 panel.x + 20, py + 4, cfg.COLOR_GRAY, self.game.font_small)
            hint = self.game.font_small.render("Enter：重铸并消耗重铸石   Esc：返回选石头", True, cfg.COLOR_GRAY)
            screen.blit(hint, (panel.x + 20, panel.y + panel.height - 30))
