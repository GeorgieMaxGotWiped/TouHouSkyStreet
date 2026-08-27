# 每面结束后的休整界面
# 包含装备 / 背包 / 商店三个页面

import pygame
from src.engine import settings as cfg
from src.engine.game import GameState
from src.systems.item_system import (
    C_SKILLS,
    EQUIPMENT_SLOTS,
    SLOT_LABELS,
    SKYBLOCK_ITEMS,
    ITEM_TYPE_LABELS,
    SHOP_CATEGORY_ORDER,
    REFORGE_STONES,
    REFORGES,
    build_lore,
    ItemInventory,
)
from src.systems.item_effects import aggregate_effects
from src.systems.item_icons import draw_item_icon


# 物品基础属性 -> 中文名（装备页“总属性”显示用）
_STAT_LABELS = {
    "health": "生命",
    "defense": "防御",
    "intelligence": "智力",
    "speed": "速度",
    "health_regen": "生命回复",
    "crit_damage": "暴击伤害",
}

# Skyblock 技能 -> 中文名（装备页“技能”显示用）
_SKILL_LABELS = {
    "COMBAT": "战斗",
    "MINING": "采矿",
    "FARMING": "农业",
    "FORAGING": "伐木",
    "FISHING": "钓鱼",
    "ENCHANTING": "附魔",
    "ALCHEMY": "炼金",
}


class IntermissionState(GameState):
    """关卡间休整界面"""

    def __init__(self, game, stage_num, pre_start=False):
        super().__init__(game)
        self.stage_num = stage_num
        self.pre_start = pre_start
        self.inventory = ItemInventory.from_global_data(game.global_data)
        self.page_names = ["equipment", "inventory", "shop", "forge"]
        self.page_labels = ["装备", "背包", "商店", "锻造"]
        self.page_idx = 0
        self.selected = 0
        self.choosing_slot = None
        self.choose_selected = 0
        self.equip_scroll = 0
        self.shop_mode = "buy"
        self.forge_mode = "stone"   # stone：选重铸石 / item：选物品
        self.forge_stone_idx = 0
        self.forge_item_idx = 0
        self.message = ""
        self.message_timer = 0
        self._last_mouse_pos = (0, 0)
        self.confirm_action = None   # None / "exit" / "extract" / "next"
        self.confirm_choice = 0      # 0=取消 1=确定

    def enter(self, game):
        self.game.stop_music()
        self.selected = 0
        self.choosing_slot = None
        self.equip_scroll = 0
        self.shop_mode = "buy"
        self.forge_mode = "stone"
        self.forge_stone_idx = 0
        self.forge_item_idx = 0
        self.message = ""
        self.confirm_action = None
        self.confirm_choice = 0

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
        self.equip_scroll = 0
        self.shop_mode = "buy"
        self.forge_mode = "stone"
        self.forge_stone_idx = 0
        self.forge_item_idx = 0
        self.message = ""

    def _current_shop_entries(self):
        if self.shop_mode == "buy":
            # 购买页按物品类型分类，组间插入不可选中的表头行
            entries = []
            groups = self.inventory.get_shop_stock_grouped()
            for item_type in SHOP_CATEGORY_ORDER:
                group = groups.get(item_type)
                if not group:
                    continue
                entries.append({"header": ITEM_TYPE_LABELS.get(item_type, item_type)})
                entries.extend(group)
            return entries
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

    def _extract(self):
        """撤离：将本局全部物资（物品/金币/重铸前缀）存入本地仓库并结束远征。"""
        self._save_inventory()
        from src.systems.warehouse import load_warehouse, save_warehouse
        warehouse = load_warehouse()
        warehouse.merge_from(self.inventory)
        save_warehouse(warehouse)
        if self.pre_start:
            self.game.notice = "已取消出征：携带的物资已退回仓库"
        else:
            self.game.notice = "已撤离：本局物资已存入仓库"
        from src.ui.menu import MenuState
        self.game.switch_state(MenuState(self.game))

    def _open_confirm(self, action):
        """打开确认弹窗：action 为 exit / extract / next 之一"""
        self.confirm_action = action
        self.confirm_choice = 0

    def _update_confirm_dialog(self, keys):
        """确认弹窗交互：↑↓ 选择，Enter 确认，Esc 取消"""
        if keys.get(pygame.K_ESCAPE, False) or keys.get(pygame.K_x, False):
            self.confirm_action = None
            return
        if (keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False)
                or keys.get(pygame.K_LEFT, False) or keys.get(pygame.K_a, False)):
            self.confirm_choice = (self.confirm_choice - 1) % 2
        if (keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False)
                or keys.get(pygame.K_RIGHT, False) or keys.get(pygame.K_d, False)):
            self.confirm_choice = (self.confirm_choice + 1) % 2
        if self._confirm_pressed(keys):
            action = self.confirm_action
            self.confirm_action = None
            if self.confirm_choice != 1:
                return
            if action == "exit":
                self._go_menu()
            elif action == "extract":
                self._extract()
            elif action == "next":
                self._continue_next_stage()

    def update(self, dt):
        keys = self.game.keys_just_pressed
        mp = self.game.mouse_pos
        clicked = self.game.mouse_clicked(1)

        if self.confirm_action is not None:
            if clicked:
                self._mouse_confirm_click(mp)
            else:
                self._update_confirm_dialog(keys)
            return

        if self.choosing_slot is not None and clicked:
            self._mouse_chooser_click(mp)
            return

        if clicked:
            self._mouse_ui_click(mp)
            return

        # 未点击时，悬停自动切换列表选中项
        if self.choosing_slot is None:
            self._mouse_hover()

        if keys.get(pygame.K_ESCAPE, False):
            if self.choosing_slot is not None:
                self.choosing_slot = None
                self.choose_selected = 0
                return
            # 出发前休整：Esc 直接放弃出征（物资退回仓库），避免丢失已携带物资
            self._open_confirm("extract" if self.pre_start else "exit")
            return
        if keys.get(pygame.K_n, False):
            self._open_confirm("next")
            return
        if self.choosing_slot is None and keys.get(pygame.K_b, False):
            self._open_confirm("extract")
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
            wheel_dir = self.game.wheel_direction()
            if wheel_dir:
                self.choose_selected = (self.choose_selected + wheel_dir) % len(entries)

            if self._confirm_pressed(keys):
                entry = entries[self.choose_selected]
                ok, err = self.inventory.equip(entry["id"])
                if not ok:
                    self._set_message(err or "装备失败")
                    return
                self._save_inventory()
                self._set_message(f"已装备：{entry['item'].name}")
                self.choosing_slot = None
                self.choose_selected = 0
            return

        page = self.page_names[self.page_idx]

        if page == "equipment":
            # 右侧属性面板滚动（滚轮 / PageUp / PageDown）
            wheel_up = bool(self.game.mouse_buttons_just_pressed.get(4))
            wheel_down = bool(self.game.mouse_buttons_just_pressed.get(5))
            if keys.get(pygame.K_PAGEUP, False) or wheel_up:
                self.equip_scroll = max(0, self.equip_scroll - 3)
            if keys.get(pygame.K_PAGEDOWN, False) or wheel_down:
                self.equip_scroll += 3
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
                wheel_dir = self.game.wheel_direction()
                if wheel_dir:
                    self.selected = (self.selected + wheel_dir) % len(entries)
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
                        ok, err = self.inventory.equip(item.id)
                        if not ok:
                            self._set_message(err or "装备失败")
                            return
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
                wheel_dir = self.game.wheel_direction()
                if wheel_dir:
                    if self.shop_mode == "buy":
                        for _ in range(len(entries)):
                            self.selected = (self.selected + wheel_dir) % len(entries)
                            if not entries[self.selected].get("header"):
                                break
                    else:
                        self.selected = (self.selected + wheel_dir) % len(entries)

                if self._confirm_pressed(keys):
                    entry = entries[self.selected]
                    if entry.get("header"):
                        return
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

    # --- 鼠标交互辅助 ---

    def _page_tab_rects(self):
        """页面页签的可点击区域（与 draw 布局一致）"""
        tab_y = 88
        tab_x = 120
        tab_gap = 250
        rects = []
        for i, label in enumerate(self.page_labels):
            w = self.game.font_medium.size(label)[0]
            rects.append((i, pygame.Rect(tab_x + i * tab_gap - 10, tab_y - 6, w + 20, 36)))
        return rects

    def _bottom_action_rects(self):
        """底部操作提示的可点击区域（index 2=N,3=B,4=Esc）"""
        hint_y = cfg.SCREEN_HEIGHT - 88
        labels = [
            "Q/E 或 1/2/3/4：切换页面",
            "↑↓：选择   Enter/Z/Space：确认",
            ("N：出发（进入第 1 面）" if self.pre_start else "N：进入下一关"),
            ("B：放弃出征（物资退回仓库）" if self.pre_start else "B：撤离（物资存入仓库）"),
            ("Esc：放弃出征（物资退回仓库）" if self.pre_start else "Esc：返回主菜单（不保存本局）"),
        ]
        rects = []
        for i, line in enumerate(labels):
            w = self.game.font_small.size(line)[0]
            rects.append((i, pygame.Rect(28, hint_y - 3, w + 16, 24)))
            hint_y += 19
        return rects

    def _equipment_slot_rects(self):
        """装备页左侧装备槽的可点击区域（与 _draw_equipment_page 的槽位y对齐）"""
        rects = []
        y = 150 + 42  # 与绘制时“装备槽”标题下方第一个槽位的 y 对齐
        for i, _slot in enumerate(EQUIPMENT_SLOTS):
            rects.append((i, pygame.Rect(70, y - 4, 430, 42)))
            y += 46
        return rects

    def _inventory_row_rects(self):
        """背包含物品行的可点击区域（返回 (全局序号, rect)）"""
        entries = self.inventory.get_inventory_entries()
        if not entries:
            return []
        visible, start = self._visible_slice(entries, self.selected, 9)
        rects = []
        y = 192
        for offset, _entry in enumerate(visible):
            rects.append((start + offset, pygame.Rect(70, y - 4, 660, 30)))
            y += 30
        return rects

    def _shop_mode_rects(self):
        """商店页“购买/出售”切换的可点击区域"""
        return pygame.Rect(76, 142, 100, 36), pygame.Rect(176, 142, 100, 36)

    def _shop_row_rects(self):
        """商店页商品行的可点击区域（返回 (全局序号, rect)）"""
        entries = self._current_shop_entries()
        if not entries:
            return []
        visible, start = self._visible_slice(entries, self.selected, 9)
        rects = []
        y = 198
        for offset, _entry in enumerate(visible):
            rects.append((start + offset, pygame.Rect(70, y - 4, 660, 30)))
            y += 30
        return rects

    def _forge_stone_rects(self):
        """锻造页左侧重铸石行的可点击区域（返回 (全局序号, rect)）"""
        stones, _ = self.inventory.get_forge_entries()
        if not stones:
            return []
        visible, start = self._visible_slice(stones, self.forge_stone_idx, 8)
        rects = []
        y = 190
        for offset, _entry in enumerate(visible):
            rects.append((start + offset, pygame.Rect(60, y - 4, 390, 40)))
            y += 40
        return rects

    def _forge_item_rects(self):
        """锻造页右侧可锻造物品行的可点击区域（返回 (全局序号, rect)）"""
        _, forge_items = self.inventory.get_forge_entries()
        if not forge_items:
            return []
        visible, start = self._visible_slice(forge_items, self.forge_item_idx, 8)
        rects = []
        y = 190
        for offset, _entry in enumerate(visible):
            rects.append((start + offset, pygame.Rect(470, y - 4, 450, 40)))
            y += 40
        return rects

    def _chooser_cancel_rect(self):
        """装备选择覆盖层的“取消”按钮区域"""
        return pygame.Rect(260 + 380, 120 + 420 - 48, 110, 36)

    def _chooser_row_rects(self):
        """装备选择覆盖层中的物品行（返回 (全局序号, rect)）"""
        entries = self.inventory.get_equippable_entries_for_slot(self.choosing_slot)
        if not entries:
            return []
        visible, start = self._visible_slice(entries, self.choose_selected, 9)
        rects = []
        y = 120 + 62
        for offset, _entry in enumerate(visible):
            rects.append((start + offset, pygame.Rect(260, y - 4, 500, 34)))
            y += 32
        return rects

    def _confirm_choice_rects(self):
        """确认弹窗“取消/确定”按钮的可点击区域"""
        panel = pygame.Rect(230, 240, 500, 240)
        rects = []
        for i, label in enumerate(["取消", "确定"]):
            y = panel.y + 110 + i * 46
            w = self.game.font_medium.size("> " + label)[0]
            rects.append((i, pygame.Rect(panel.x + 180, y - 10, w + 20, 44)))
        return rects

    def _forge_confirm_rect(self):
        """锻造页底部“确认”按钮区域"""
        panel = pygame.Rect(36, 470, cfg.SCREEN_WIDTH - 72, 190)
        return pygame.Rect(panel.x + panel.width - 200, panel.y + 78, 180, 40)

    def _mouse_ui_click(self, mp):
        """非确认/非装备选择覆盖状态下，处理所有鼠标点击区域"""
        for i, rect in self._page_tab_rects():
            if rect.collidepoint(mp):
                self._set_page(i)
                return
        for idx, rect in self._bottom_action_rects():
            if rect.collidepoint(mp):
                if idx == 2:
                    self._open_confirm("next")
                elif idx == 3:
                    self._open_confirm("extract")
                elif idx == 4:
                    self._open_confirm("extract" if self.pre_start else "exit")
                return
        page = self.page_names[self.page_idx]
        if page == "equipment":
            self._mouse_equipment_click(mp)
        elif page == "inventory":
            self._mouse_inventory_click(mp)
        elif page == "shop":
            self._mouse_shop_click(mp)
        elif page == "forge":
            self._mouse_forge_click(mp)

    def _mouse_equipment_click(self, mp):
        for i, rect in self._equipment_slot_rects():
            if rect.collidepoint(mp):
                self.selected = i
                self.choosing_slot = EQUIPMENT_SLOTS[i]
                self.choose_selected = 0
                return

    def _mouse_inventory_click(self, mp):
        entries = self.inventory.get_inventory_entries()
        for idx, rect in self._inventory_row_rects():
            if rect.collidepoint(mp):
                self.selected = idx
                entry = entries[idx]
                item = entry["item"]
                if not item.is_equippable:
                    self._set_message("该物品不能装备")
                elif self.inventory.is_equipped(item.id):
                    self.inventory.unequip_item(item.id)
                    self._save_inventory()
                    self._set_message(f"已卸下：{item.name}")
                else:
                    ok, err = self.inventory.equip(item.id)
                    if not ok:
                        self._set_message(err or "装备失败")
                        return
                    self._save_inventory()
                    self._set_message(f"已装备：{item.name}")
                return

    def _mouse_shop_click(self, mp):
        buy_rect, sell_rect = self._shop_mode_rects()
        if buy_rect.collidepoint(mp):
            self.shop_mode = "buy"
            self.selected = 0
            return
        if sell_rect.collidepoint(mp):
            self.shop_mode = "sell"
            self.selected = 0
            return
        entries = self._current_shop_entries()
        for idx, rect in self._shop_row_rects():
            if rect.collidepoint(mp):
                self.selected = idx
                entry = entries[idx]
                if entry.get("header"):
                    return
                if self.shop_mode == "buy":
                    price = entry["buy_price"]
                    if self.inventory.spend_coins(price):
                        self.inventory.add_item(entry["item"].id, 1)
                        self._save_inventory()
                        self._set_message(f"购买成功：{entry['item'].name}（-{price} 金币）")
                    else:
                        self._set_message("金币不足")
                else:
                    price = entry["sell_price"]
                    self.inventory.remove_item(entry["item"].id, 1)
                    self.inventory.add_coins(price)
                    self._save_inventory()
                    self._set_message(f"出售成功：{entry['item'].name}（+{price} 金币）")
                return

    def _mouse_forge_click(self, mp):
        for idx, rect in self._forge_stone_rects():
            if rect.collidepoint(mp):
                self.forge_stone_idx = idx
                self.forge_mode = "item"
                self.forge_item_idx = 0
                return
        for idx, rect in self._forge_item_rects():
            if rect.collidepoint(mp):
                self.forge_item_idx = idx
                if self.forge_mode != "item":
                    self.forge_mode = "item"
                return
        if self._forge_confirm_rect().collidepoint(mp):
            self._forge_confirm_click()
            return

    def _mouse_chooser_click(self, mp):
        if self._chooser_cancel_rect().collidepoint(mp):
            self.choosing_slot = None
            self.choose_selected = 0
            return
        entries = self.inventory.get_equippable_entries_for_slot(self.choosing_slot)
        for idx, rect in self._chooser_row_rects():
            if rect.collidepoint(mp):
                self.choose_selected = idx
                entry = entries[idx]
                ok, err = self.inventory.equip(entry["id"])
                if not ok:
                    self._set_message(err or "装备失败")
                    return
                self._save_inventory()
                self._set_message(f"已装备：{entry['item'].name}")
                self.choosing_slot = None
                self.choose_selected = 0
                return

    def _mouse_confirm_click(self, mp):
        for i, rect in self._confirm_choice_rects():
            if rect.collidepoint(mp):
                self.confirm_choice = i
                action = self.confirm_action
                self.confirm_action = None
                if i == 1:
                    if action == "exit":
                        self._go_menu()
                    elif action == "extract":
                        self._extract()
                    elif action == "next":
                        self._continue_next_stage()
                return

    def _mouse_hover(self):
        mp = self.game.mouse_pos
        if mp == self._last_mouse_pos:
            return
        self._last_mouse_pos = mp
        page = self.page_names[self.page_idx]
        if page == "equipment":
            # 装备槽只有 7 个且始终可见，悬停切换选中项不会造成长列表滚动
            for i, rect in self._equipment_slot_rects():
                if rect.collidepoint(mp):
                    if self.selected != i:
                        self.selected = i
                    return
        # 其余物品长列表不再靠悬停滚动，改用鼠标滚轮（见各页 update）

    def _forge_confirm_click(self):
        stones, forge_items = self.inventory.get_forge_entries()
        if self.forge_mode == "stone":
            if not stones:
                self._set_message("背包中没有重铸石")
                return
            self.forge_mode = "item"
            self.forge_item_idx = 0
            return
        if not forge_items:
            self.forge_mode = "stone"
            self._set_message("没有可锻造的物品")
            return
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
            self._set_message(f"重铸成功：{prefix_name} {entry['item'].name}（-{entry['cost']} 金币）")
            self.forge_mode = "stone"
            self.forge_stone_idx = 0
        else:
            self._set_message(err or "重铸失败")

    def _update_forge_page(self, keys):
        """锻造页交互：先选重铸石，再选物品，确认后打上前缀"""
        stones, forge_items = self.inventory.get_forge_entries()

        # 滚轮：滚动光标所指列（左=重铸石，右=可锻造物品）
        wheel_dir = self.game.wheel_direction()
        if wheel_dir:
            if self.game.mouse_pos[0] < 460:
                if stones:
                    self.forge_stone_idx = (self.forge_stone_idx + wheel_dir) % len(stones)
            else:
                if forge_items:
                    self.forge_item_idx = (self.forge_item_idx + wheel_dir) % len(forge_items)

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
        if self.pre_start:
            title_text = "出发前休整 · 穿戴携带物品"
        else:
            title_text = f"第 {self.stage_num} 面结束 · 休整"
        title = self.game.font_large.render(title_text, True, cfg.COLOR_YELLOW)
        screen.blit(title, ((cfg.SCREEN_WIDTH - title.get_width()) // 2, 28))

        coins = self.game.font_medium.render(f"金币：{self.inventory.coins}", True, cfg.COLOR_YELLOW)
        screen.blit(coins, (cfg.SCREEN_WIDTH - coins.get_width() - 28, 34))

        # 顶部页签
        tab_y = 88
        tab_x = 120
        tab_gap = 250
        tab_rects = self._page_tab_rects()
        for i, label in enumerate(self.page_labels):
            x = tab_x + i * tab_gap
            color = cfg.COLOR_YELLOW if i == self.page_idx else cfg.COLOR_GRAY
            text = self.game.font_medium.render(label, True, color)
            screen.blit(text, (x, tab_y))
            if self.game.mouse_hover(tab_rects[i][1]) and i != self.page_idx:
                pygame.draw.rect(screen, cfg.COLOR_YELLOW, tab_rects[i][1], 1)
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
            ("N：出发（进入第 1 面）" if self.pre_start else "N：进入下一关"),
            ("B：放弃出征（物资退回仓库）" if self.pre_start else "B：撤离（物资存入仓库）"),
            ("Esc：放弃出征（物资退回仓库）" if self.pre_start else "Esc：返回主菜单（不保存本局）"),
        ]
        hint_y = cfg.SCREEN_HEIGHT - 88
        action_rects = self._bottom_action_rects()
        for i, line in enumerate(hints):
            hint = self.game.font_small.render(line, True, cfg.COLOR_DARK_GRAY)
            screen.blit(hint, (36, hint_y))
            if i in (2, 3, 4):
                rect = action_rects[i][1]
                if self.game.mouse_hover(rect):
                    color = cfg.COLOR_YELLOW if i == 2 else cfg.COLOR_GREEN
                    pygame.draw.rect(screen, color, rect, 1)
            hint_y += 19

        if self.message:
            msg = self.game.font_medium.render(self.message, True, cfg.COLOR_GREEN)
            screen.blit(msg, ((cfg.SCREEN_WIDTH - msg.get_width()) // 2, cfg.SCREEN_HEIGHT - 120))

        self._draw_confirm_dialog(screen)

    def _draw_confirm_dialog(self, screen):
        """“是否确定”弹窗：覆盖在休整界面之上"""
        if self.confirm_action is None:
            return
        texts = {
            "exit": "确定要退出并返回主菜单吗？（本局物资不会保留）",
            "extract": ("确定要放弃出征吗？携带的物资将退回仓库。"
                        if self.pre_start else "确定要撤离吗？本局全部物资将存入仓库并结束远征。"),
            "next": ("确定要出发进入第 1 面吗？"
                     if self.pre_start else "确定要进入下一关吗？"),
        }
        panel = pygame.Rect(230, 240, 500, 240)
        overlay = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        overlay.fill((14, 18, 40, 242))
        screen.blit(overlay, panel.topleft)
        pygame.draw.rect(screen, cfg.COLOR_YELLOW, panel, 2)

        title = self.game.font_medium.render(
            texts.get(self.confirm_action, "确定吗？"), True, cfg.COLOR_WHITE)
        screen.blit(title, (panel.x + 40, panel.y + 46))

        choice_rects = self._confirm_choice_rects()
        for i, label in enumerate(["取消", "确定"]):
            selected = i == self.confirm_choice
            color = cfg.COLOR_YELLOW if selected else cfg.COLOR_WHITE
            prefix = "> " if selected else "  "
            surf = self.game.font_medium.render(prefix + label, True, color)
            rect = choice_rects[i][1]
            if selected or self.game.mouse_hover(rect):
                pygame.draw.rect(screen, color, rect, 2 if selected else 1)
            screen.blit(surf, (panel.x + 190, panel.y + 110 + i * 46))

        hint = self.game.font_small.render(
            "↑↓ 选择   Enter 确认   Esc 取消（鼠标可点击按钮）", True, cfg.COLOR_GRAY)
        screen.blit(hint, (panel.x + 40, panel.y + panel.height - 36))

    # --- 物品详情 / 自机属性 ---

    def _item_detail_lines(self, item):
        """生成物品功能说明行 [(文本, 颜色)]：基础属性 + lore"""
        lines = []
        if item is None:
            return lines
        stat_text = item.stat_text()
        if stat_text:
            lines.append((stat_text, cfg.COLOR_GRAY))
        lines.extend((line, cfg.COLOR_WHITE) for line in (item.lore or []))
        return lines

    def _draw_item_detail_panel(self, screen, item, x=36, y=470, w=None, h=190):
        """底部物品功能说明面板：名称 / 基础属性 / lore"""
        if w is None:
            w = cfg.SCREEN_WIDTH - 72
        panel = pygame.Rect(x, y, w, h)
        pygame.draw.rect(screen, cfg.COLOR_PANEL_BG, panel)
        pygame.draw.rect(screen, cfg.COLOR_DARK_GRAY, panel, 1)
        py = panel.y + 12
        if item is None:
            self._draw_text(screen, "未选择物品", panel.x + 16, py,
                            cfg.COLOR_GRAY, self.game.font_small)
            return
        name = self.game.font_medium.render(item.name, True, item.rarity_color)
        screen.blit(name, (panel.x + 16, py))
        py += 30
        for text, color in self._item_detail_lines(item):
            if py > panel.y + panel.height - 10:
                break
            py = self._draw_text(screen, text, panel.x + 16, py, color, self.game.font_small)

    def _equipment_panel_lines(self):
        """装备页右侧面板：总属性 / 被动效果 / 技能 -> [(文本, 颜色)]"""
        lines = []

        # 总属性（装备基础属性）
        stats = self.inventory.get_equipped_stats()
        lines.append(("—— 总属性 ——", cfg.COLOR_WHITE))
        if not stats:
            lines.append(("暂无装备属性", cfg.COLOR_GRAY))
        for key, value in stats.items():
            label = _STAT_LABELS.get(key, key)
            lines.append((f"{label}: {value}", cfg.COLOR_GREEN))

        # 被动效果（装备 + 重铸前缀 + 套装；过滤默认值 0 / 1.0）
        eff = aggregate_effects(self.inventory, self.stage_num)
        shown_eff = {}
        for key, value in eff.items():
            if isinstance(value, bool):
                if value:
                    shown_eff[key] = value
            elif isinstance(value, (int, float)):
                if value not in (0, 1.0):
                    shown_eff[key] = value
            elif value is not None:
                shown_eff[key] = value
        effect_lines = build_lore(shown_eff)
        lines.append(("—— 被动效果 ——", cfg.COLOR_WHITE))
        if not effect_lines:
            lines.append(("无", cfg.COLOR_GRAY))
        lines.extend((text, cfg.COLOR_GREEN) for text in effect_lines)

        # 技能：C技能 + Skyblock 技能等级
        lines.append(("—— 技能 ——", cfg.COLOR_WHITE))
        c_id = self.inventory.get_c_skill_equipped_id()
        if c_id:
            item = SKYBLOCK_ITEMS.get(c_id)
            skill = C_SKILLS.get(c_id, {})
            sname = skill.get("name", "C技能")
            desc = skill.get("desc", "")
            per = skill.get("per_stage", 1)
            shown_name = item.name if item else c_id
            lines.append((f"C技能·{sname}（{shown_name}）：{desc}（每面{per}次）",
                          cfg.COLOR_YELLOW))
        else:
            lines.append(("未装备C技能物品", cfg.COLOR_GRAY))
        skills_data = self.game.global_data.get("skills", {}) or {}
        for sk, data in skills_data.items():
            level = data.get("level", 0) if isinstance(data, dict) else 0
            if level > 0:
                lines.append((f"{_SKILL_LABELS.get(sk, sk)} Lv.{level}", cfg.COLOR_YELLOW))
        return lines

    def _draw_equipment_page(self, screen):
        # 左侧：装备槽
        y = 150
        left_x = 80
        header = self.game.font_medium.render("装备槽", True, cfg.COLOR_WHITE)
        screen.blit(header, (left_x, y))
        y += 42

        selected_item = None
        for i, slot in enumerate(EQUIPMENT_SLOTS):
            selected = i == self.selected
            row_color = cfg.COLOR_YELLOW if selected else cfg.COLOR_WHITE
            slot_rect = pygame.Rect(70, y - 4, 430, 42)
            if selected:
                pygame.draw.rect(screen, (60, 60, 22), slot_rect)
            elif self.game.mouse_hover(slot_rect):
                pygame.draw.rect(screen, (110, 110, 40), slot_rect, 1)
            item = self.inventory.get_equipped_item(slot)
            if selected:
                selected_item = item
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
                    screen.blit(stat, (left_x + 178, y + 26))
            else:
                empty = self.game.font_medium.render("（空）", True, cfg.COLOR_GRAY)
                screen.blit(empty, (left_x + 178, y))
            y += 46

        # 左侧下方：当前选中装备的功能说明
        self._draw_item_detail_panel(screen, selected_item, x=60, y=478, w=400, h=152)

        # 右侧：自机属性（总属性 / 被动效果 / 技能，可滚动）
        panel = pygame.Rect(488, 142, cfg.SCREEN_WIDTH - 508, 486)
        pygame.draw.rect(screen, cfg.COLOR_PANEL_BG, panel)
        pygame.draw.rect(screen, cfg.COLOR_DARK_GRAY, panel, 1)
        header = self.game.font_medium.render("自机属性", True, cfg.COLOR_WHITE)
        screen.blit(header, (panel.x + 14, panel.y + 10))

        lines = self._equipment_panel_lines()
        line_h = 22
        top = panel.y + 56
        bottom = panel.y + panel.height - 10
        max_rows = max(1, (bottom - top) // line_h)
        self.equip_scroll = max(0, min(self.equip_scroll, max(0, len(lines) - max_rows)))
        if len(lines) > max_rows:
            scroll_hint = self.game.font_small.render(
                "（滚轮 / PageUp / PageDown 滚动）", True, cfg.COLOR_GRAY)
            screen.blit(scroll_hint, (panel.x + 14, panel.y + 34))
        visible = lines[self.equip_scroll:self.equip_scroll + max_rows]
        py = top
        for text, color in visible:
            py = self._draw_text(screen, text, panel.x + 14, py, color, self.game.font_small)

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
            hint = self.game.font_small.render("Enter / Esc 返回（鼠标点击关闭）", True, cfg.COLOR_GRAY)
            screen.blit(hint, (panel.x + 24, panel.y + 112))
            cancel_rect = self._chooser_cancel_rect()
            cancel_hover = self.game.mouse_hover(cancel_rect)
            pygame.draw.rect(screen, cfg.COLOR_PANEL_BG, cancel_rect)
            pygame.draw.rect(screen, cfg.COLOR_YELLOW if cancel_hover else cfg.COLOR_GRAY,
                             cancel_rect, 2 if cancel_hover else 1)
            cancel_text = self.game.font_small.render(
                "取消", True, cfg.COLOR_YELLOW if cancel_hover else cfg.COLOR_WHITE)
            screen.blit(cancel_text, (cancel_rect.x + (cancel_rect.width - cancel_text.get_width()) // 2,
                                      cancel_rect.y + (cancel_rect.height - cancel_text.get_height()) // 2))
            return

        visible, start = self._visible_slice(entries, self.choose_selected, 9)
        y = panel.y + 62
        for offset, entry in enumerate(visible):
            idx = start + offset
            selected = idx == self.choose_selected
            color = cfg.COLOR_YELLOW if selected else cfg.COLOR_WHITE
            row_rect = pygame.Rect(panel.x, y - 4, panel.width, 34)
            if selected:
                pygame.draw.rect(screen, (60, 60, 22), row_rect)
            elif self.game.mouse_hover(row_rect):
                pygame.draw.rect(screen, (110, 110, 40), row_rect, 1)
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

        hint = self.game.font_small.render("Enter 装备   Esc 取消（鼠标点击关闭）", True, cfg.COLOR_GRAY)
        screen.blit(hint, (panel.x + 24, panel.y + panel.height - 34))

        cancel_rect = self._chooser_cancel_rect()
        cancel_hover = self.game.mouse_hover(cancel_rect)
        pygame.draw.rect(screen, cfg.COLOR_PANEL_BG, cancel_rect)
        pygame.draw.rect(screen, cfg.COLOR_YELLOW if cancel_hover else cfg.COLOR_GRAY,
                         cancel_rect, 2 if cancel_hover else 1)
        cancel_text = self.game.font_small.render(
            "取消", True, cfg.COLOR_YELLOW if cancel_hover else cfg.COLOR_WHITE)
        screen.blit(cancel_text, (cancel_rect.x + (cancel_rect.width - cancel_text.get_width()) // 2,
                                  cancel_rect.y + (cancel_rect.height - cancel_text.get_height()) // 2))

        # 面板底部：所选物品功能说明
        entry = entries[self.choose_selected]
        item = entry["item"]
        pygame.draw.line(screen, cfg.COLOR_DARK_GRAY,
                         (panel.x + 20, panel.y + 360),
                         (panel.x + panel.width - 20, panel.y + 360))
        py = panel.y + 374
        for text, color in self._item_detail_lines(item):
            if py > panel.y + panel.height - 40:
                break
            py = self._draw_text(screen, text, panel.x + 24, py, color, self.game.font_small)

    def _draw_inventory_page(self, screen):
        entries = self.inventory.get_inventory_entries()
        y = 150
        header = self.game.font_medium.render("背包物品", True, cfg.COLOR_WHITE)
        screen.blit(header, (80, y))
        y += 42

        if not entries:
            self._draw_text(screen, "背包是空的", 80, y, cfg.COLOR_GRAY, self.game.font_medium)
            return

        visible, start = self._visible_slice(entries, self.selected, 9)
        for offset, entry in enumerate(visible):
            idx = start + offset
            selected = idx == self.selected
            row_rect = pygame.Rect(70, y - 4, 660, 30)
            if selected:
                pygame.draw.rect(screen, (60, 60, 22), row_rect)
            elif self.game.mouse_hover(row_rect):
                pygame.draw.rect(screen, (110, 110, 40), row_rect, 1)
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

        # 底部：所选物品功能说明
        if entries:
            if self.selected >= len(entries):
                self.selected = len(entries) - 1
            self._draw_item_detail_panel(screen, entries[self.selected]["item"])

    def _draw_shop_page(self, screen):
        y = 150
        buy_color = cfg.COLOR_YELLOW if self.shop_mode == "buy" else cfg.COLOR_GRAY
        sell_color = cfg.COLOR_YELLOW if self.shop_mode == "sell" else cfg.COLOR_GRAY
        buy_text = self.game.font_medium.render("购买", True, buy_color)
        sell_text = self.game.font_medium.render("出售", True, sell_color)
        screen.blit(buy_text, (80, y))
        screen.blit(sell_text, (180, y))
        buy_rect, sell_rect = self._shop_mode_rects()
        if self.game.mouse_hover(buy_rect) and self.shop_mode != "buy":
            pygame.draw.rect(screen, cfg.COLOR_YELLOW, buy_rect, 1)
        if self.game.mouse_hover(sell_rect) and self.shop_mode != "sell":
            pygame.draw.rect(screen, cfg.COLOR_YELLOW, sell_rect, 1)
        pygame.draw.line(screen, cfg.COLOR_DARK_GRAY, (36, y + 32), (cfg.SCREEN_WIDTH - 36, y + 32), 2)
        y += 48

        entries = self._current_shop_entries()
        if not entries:
            text = "商店暂无商品" if self.shop_mode == "buy" else "没有可出售的装备"
            self._draw_text(screen, text, 80, y, cfg.COLOR_GRAY, self.game.font_medium)
            return

        visible, start = self._visible_slice(entries, self.selected, 9)
        for offset, entry in enumerate(visible):
            idx = start + offset
            if entry.get("header"):
                header = self.game.font_medium.render(f"— {entry['header']} —", True, cfg.COLOR_GRAY)
                screen.blit(header, (80, y))
                y += 30
                continue
            selected = idx == self.selected
            row_rect = pygame.Rect(70, y - 4, 660, 30)
            if selected:
                pygame.draw.rect(screen, (60, 60, 22), row_rect)
            elif self.game.mouse_hover(row_rect):
                pygame.draw.rect(screen, (110, 110, 40), row_rect, 1)
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

        # 底部：所选物品功能说明（分类表头不可选中，跳过）
        if entries:
            if self.selected >= len(entries):
                self.selected = len(entries) - 1
            entry = entries[self.selected]
            if not entry.get("header"):
                self._draw_item_detail_panel(screen, entry["item"])

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
                stone_rect = pygame.Rect(left_x, y - 4, 390, 40)
                if selected:
                    pygame.draw.rect(screen, (60, 60, 22), stone_rect)
                elif self.game.mouse_hover(stone_rect):
                    pygame.draw.rect(screen, (110, 110, 40), stone_rect, 1)
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
                forge_rect = pygame.Rect(right_x, y - 4, 450, 40)
                if selected:
                    pygame.draw.rect(screen, (60, 60, 22), forge_rect)
                elif self.game.mouse_hover(forge_rect):
                    pygame.draw.rect(screen, (110, 110, 40), forge_rect, 1)
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
        forge_confirm_rect = self._forge_confirm_rect()
        forge_confirm_hover = self.game.mouse_hover(forge_confirm_rect)
        pygame.draw.rect(screen, cfg.COLOR_PANEL_BG, forge_confirm_rect)
        pygame.draw.rect(screen, cfg.COLOR_YELLOW if forge_confirm_hover else cfg.COLOR_GRAY,
                         forge_confirm_rect, 2 if forge_confirm_hover else 1)
        forge_btn_text = self.game.font_medium.render(
            "确认 / 下一步", True,
            cfg.COLOR_YELLOW if forge_confirm_hover else cfg.COLOR_WHITE)
        screen.blit(forge_btn_text, (forge_confirm_rect.x + (forge_confirm_rect.width - forge_btn_text.get_width()) // 2,
                                     forge_confirm_rect.y + (forge_confirm_rect.height - forge_btn_text.get_height()) // 2))
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
            py = self._draw_text(screen, tip, panel.x + 20, py, cfg.COLOR_YELLOW, self.game.font_small)
            if prefix:
                for lore_line in prefix.get("lore", []):
                    py = self._draw_text(screen, lore_line, panel.x + 24, py + 2,
                                         cfg.COLOR_GREEN, self.game.font_small)
            hint = self.game.font_small.render("Enter：选择该重铸石 → 选物品", True, cfg.COLOR_GRAY)
            screen.blit(hint, (panel.x + 20, panel.y + panel.height - 30))
        else:
            entry = forge_items[self.forge_item_idx]
            item = entry["item"]
            py = self._draw_text(screen, line, panel.x + 20, py, cfg.COLOR_YELLOW, self.game.font_small)
            if prefix:
                for lore_line in prefix.get("lore", []):
                    py = self._draw_text(screen, lore_line, panel.x + 24, py + 2,
                                         cfg.COLOR_GREEN, self.game.font_small)
            old = self.inventory.get_item_prefix(item.id)
            old_name = REFORGES[old]["name"] if old in REFORGES else "无"
            py = self._draw_text(screen, f"当前前缀：{old_name}    费用：{entry['cost']} 金币",
                                 panel.x + 20, py + 4, cfg.COLOR_GRAY, self.game.font_small)
            hint = self.game.font_small.render("Enter：重铸并消耗重铸石   Esc：返回选石头", True, cfg.COLOR_GRAY)
            screen.blit(hint, (panel.x + 20, panel.y + panel.height - 30))
