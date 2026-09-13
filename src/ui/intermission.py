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
from src.engine import hires
from src.ui import skyblock_ui as sui


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


def _fit_text(text, font, max_width):
    """若文本宽度超过 max_width 则截断并加省略号，避免文字溢出行。"""
    if font.size(text)[0] <= max_width:
        return text
    result = text
    while result and font.size(result + "...")[0] > max_width:
        result = result[:-1]
    return result + "..."


# --- SkyBlock 菜单布局常量（与 draw / 命中区域共享） ---
_PAGE_TAB_Y = 84          # 页签顶部
_DIVIDER_Y = 132          # 页签下方分隔线
_GRID_TOP = 176           # 主网格顶部
_GRID_LEFT = 40
_SLOT = 54
_GAP = 6
_GRID_COLS = 9
_GRID_MAX_ROWS = 5
_GRID_CAPACITY = _GRID_COLS * _GRID_MAX_ROWS
_FORGE_LIST_ROWS = 7        # 锻造页列表最多行数（再大会压到底部面板/重铸按钮）
_BOTTOM_Y = 544           # 底部详情/预览面板顶部
_HINT_Y = 652             # 底部操作提示顶部


class IntermissionState(GameState):
    """关卡间休整界面"""

    def __init__(self, game, stage_num, pre_start=False):
        super().__init__(game)
        self.stage_num = stage_num
        self.pre_start = pre_start
        self.inventory = ItemInventory.from_global_data(game.global_data)
        self.bag_name = "背包"
        self.page_names = ["equipment", "inventory", "shop", "forge"]
        self.page_labels = ["装备", "背包", "商店", "锻造"]
        self.page_idx = 0
        self.selected = 0
        self.equip_grid_sel = 0
        self.equip_slot_clicked = False  # 装备槽是否已由鼠标点击选中（用于“再次点击”打开替换）
        self.choosing_slot = None
        self.choose_selected = 0
        self.equip_scroll = 0
        self.shop_mode = "buy"
        self.forge_mode = "stone"   # stone：选重铸石 / item：选物品
        self.forge_stone_idx = 0
        self.forge_item_idx = 0
        self.placed_item_id = None      # 已放入锻造格子的物品 id
        self.placed_stone_id = None     # 已放入锻造格子的重铸石 id
        self.placed_item_prefix = None  # 待重铸的物品堆的前缀
        self.message = ""
        self.message_timer = 0
        self._last_mouse_pos = (0, 0)
        self.confirm_action = None   # None / "exit" / "extract" / "next"
        self.confirm_choice = 0      # 0=取消 1=确定

    def enter(self, game):
        self.game.stop_music()
        self.selected = 0
        self.equip_grid_sel = 0
        self.equip_slot_clicked = False
        self.choosing_slot = None
        self.equip_scroll = 0
        self.shop_mode = "buy"
        self.forge_mode = "stone"
        self.forge_stone_idx = 0
        self.forge_item_idx = 0
        self.placed_item_id = None
        self.placed_stone_id = None
        self.placed_item_prefix = None
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
        self.equip_grid_sel = 0
        self.equip_slot_clicked = False
        self.choosing_slot = None
        self.choose_selected = 0
        self.equip_scroll = 0
        self.shop_mode = "buy"
        self.forge_mode = "stone"
        self.forge_stone_idx = 0
        self.forge_item_idx = 0
        self.placed_item_id = None
        self.placed_stone_id = None
        self.placed_item_prefix = None
        self.message = ""

    def _current_shop_entries(self):
        if self.shop_mode == "buy":
            # 购买页按物品类型分类（组间不再插入表头，网格更简洁）
            entries = []
            groups = self.inventory.get_shop_stock_grouped()
            for item_type in SHOP_CATEGORY_ORDER:
                group = groups.get(item_type)
                if not group:
                    continue
                entries.extend(group)
            # 补齐未在分类顺序中的剩余物品
            seen = {e["item"].id for e in entries}
            for item_type, group in groups.items():
                for e in group:
                    if e["item"].id not in seen:
                        entries.append(e)
            return entries
        return self.inventory.get_sellable_entries()

    def _go_menu(self):
        self._save_inventory()
        from src.ui.menu import MenuState
        self.game.switch_state(MenuState(self.game))

    def _continue_next_stage(self):
        self._save_inventory()
        from src.stages import get_next_stage_class
        from src.ui.loading import start_stage
        from src.ui.menu import MenuState
        next_cls = get_next_stage_class(self.stage_num)
        if next_cls is None:
            self.game.switch_state(MenuState(self.game))
            return
        # 下一面经载入界面入场（构建关卡 + 预热贴图）
        start_stage(self.game, next_cls)

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
                ok, err = self.inventory.equip(entry["id"], entry.get("prefix"))
                if not ok:
                    self._set_message(err or "装备失败")
                    return
                self._save_inventory()
                self._set_message(f"已装备：{entry['display_name']}")
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
            # ←/→ 浏览已装备槽位（查看详情），↑/↓ 在下方物品网格中选中
            if keys.get(pygame.K_LEFT, False) or keys.get(pygame.K_a, False):
                self.selected = (self.selected - 1) % len(EQUIPMENT_SLOTS)
                self.equip_slot_clicked = False
            if keys.get(pygame.K_RIGHT, False) or keys.get(pygame.K_d, False):
                self.selected = (self.selected + 1) % len(EQUIPMENT_SLOTS)
                self.equip_slot_clicked = False
            entries = self.inventory.get_inventory_entries()
            if entries:
                if self.equip_grid_sel >= len(entries):
                    self.equip_grid_sel = len(entries) - 1
                if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
                    self.equip_grid_sel = (self.equip_grid_sel - 1) % len(entries)
                if keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
                    self.equip_grid_sel = (self.equip_grid_sel + 1) % len(entries)
                if self._confirm_pressed(keys):
                    self._equip_or_unequip(entries[self.equip_grid_sel])
            elif self._confirm_pressed(keys):
                self._set_message(f"{self.bag_name}是空的")
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
                    self._equip_or_unequip(entries[self.selected])
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
        rects = []
        widths = []
        for label in self.page_labels:
            widths.append(self.game.font_medium.size(label)[0] + 32)
        total = sum(widths) + (len(widths) - 1) * 14
        x = (cfg.SCREEN_WIDTH - total) // 2
        for i, label in enumerate(self.page_labels):
            rects.append((i, pygame.Rect(x, _PAGE_TAB_Y - 6, widths[i], 40)))
            x += widths[i] + 14
        return rects

    def _bottom_action_rects(self):
        """底部动作按钮的可点击区域（与 draw 使用同一布局）。"""
        labels = dict(self._bottom_action_defs())
        gap = 14
        pad = 20
        widths = [self.game.font_medium.size(labels[i])[0] + pad * 2 for i in (1, 2, 3)]
        total = sum(widths) + gap * (len(widths) - 1)
        x = (cfg.SCREEN_WIDTH - total) // 2
        y = _HINT_Y + 18
        rects = []
        for i in (1, 2, 3):
            w = widths[i - 1]
            rects.append((i, pygame.Rect(x, y, w, 32)))
            x += w + gap
        return rects

    def _bottom_action_defs(self):
        """底部动作按钮定义：返回 [(索引, 按钮文字), ...]（1=N，2=B，3=Esc）。"""
        if self.pre_start:
            return [(1, "N：出发"), (2, "B：放弃"), (3, "Esc：放弃")]
        return [(1, "N：下一关"), (2, "B：撤离"), (3, "Esc：返回")]

    def _equipment_slot_rects(self):
        """装备页顶部装备槽（横向一排）的可点击区域。"""
        rects = []
        n = len(EQUIPMENT_SLOTS)
        slot = 54
        gap = 8
        total = n * slot + (n - 1) * gap
        # 右侧留给自机属性面板（x=608 起），把整排槽位放在左侧内容区内居中
        x0 = (36 + (608 - 20) - total) // 2
        y = 172
        for i in range(n):
            rects.append((i, pygame.Rect(x0 + i * (slot + gap), y, slot, slot)))
        return rects

    def _inventory_row_rects(self):
        """背包/仓库物品网格的可点击区域（返回 (全局序号, rect)）。"""
        entries = self.inventory.get_inventory_entries()
        if not entries:
            return []
        visible, start = self._visible_slice(entries, self._inventory_focus_index(),
                                             self._current_grid_rows() * _GRID_COLS)
        rects = self._grid_rects(len(visible), top=self._current_grid_top(),
                                 left=self._current_grid_left())
        return [(start + offset, rects[offset]) for offset in range(len(visible))]

    def _inventory_focus_index(self):
        """当前主物品网格的焦点：装备页用 equip_grid_sel（由鼠标/键盘控制的选中项），
        其余页面用 selected。"""
        if self.page_names[self.page_idx] == "equipment":
            return self.equip_grid_sel
        return self.selected

    def _shop_mode_rects(self):
        """商店页“购买/出售”切换的可点击区域"""
        w = 132
        x0 = (cfg.SCREEN_WIDTH - (2 * w + 16)) // 2
        return pygame.Rect(x0, _DIVIDER_Y + 4, w, 36), pygame.Rect(x0 + w + 16, _DIVIDER_Y + 4, w, 36)

    def _shop_row_rects(self):
        """商店页商品网格的可点击区域（返回 (全局序号, rect)）。"""
        entries = self._current_shop_entries()
        if not entries:
            return []
        visible, start = self._visible_slice(entries, self.selected,
                                             self._current_grid_rows() * _GRID_COLS)
        rects = self._grid_rects(len(visible), top=self._current_grid_top(),
                                 left=self._current_grid_left())
        return [(start + offset, rects[offset]) for offset in range(len(visible))]

    def _forge_stone_rects(self):
        """锻造页左侧重铸石的可点击区域（返回 (全局序号, rect)）。"""
        stones, _ = self.inventory.get_forge_entries()
        if not stones:
            return []
        visible, start = self._visible_slice(stones, self.forge_stone_idx,
                                             _FORGE_LIST_ROWS)
        rects = []
        y = _GRID_TOP + 6
        for offset, _entry in enumerate(visible):
            rects.append((start + offset, pygame.Rect(_GRID_LEFT, y, 430, 48)))
            y += 52
        return rects

    def _forge_item_rects(self):
        """锻造页右侧可锻造物品的可点击区域（返回 (全局序号, rect)）。"""
        view = self._forge_item_view()
        real = [i for i, e in enumerate(view) if not e.get("header")]
        if not real:
            return []
        if self.forge_item_idx not in real:
            self.forge_item_idx = real[0]
        visible, start = self._visible_slice(view, self.forge_item_idx,
                                             _FORGE_LIST_ROWS)
        rects = []
        y = _GRID_TOP + 6
        for offset, _entry in enumerate(visible):
            rects.append((start + offset, pygame.Rect(490, y, 430, 48)))
            y += 52
        return rects

    def _forge_item_view(self):
        """锻造页可锻造物品的分组视图：未重铸在前，已重铸按前缀分组。
        返回扁平条目列表，分组表头为 {'header': True, 'label': ...}。"""
        _, forge_items = self.inventory.get_forge_entries()
        groups = {}
        for e in forge_items:
            groups.setdefault(e["prefix"], []).append(e)
        keys = sorted(groups.keys(), key=lambda k: (k is not None,
                                                    REFORGES[k]["name"] if k else ""))
        view = []
        for k in keys:
            label = "未重铸" if k is None else REFORGES[k]["name"]
            view.append({"header": True, "label": label})
            view.extend(groups[k])
        return view

    def _chooser_cancel_rect(self):
        """装备选择覆盖层的“取消”按钮区域"""
        panel = pygame.Rect(210, 90, 540, 540)
        return pygame.Rect(panel.right - 128, panel.bottom - 50, 112, 38)

    def _chooser_row_rects(self):
        """装备选择覆盖层中的物品网格（返回 (全局序号, rect)）。"""
        entries = self.inventory.get_equippable_entries_for_slot(self.choosing_slot)
        if not entries:
            return []
        visible, start = self._visible_slice(entries, self.choose_selected, 12)
        panel = pygame.Rect(210, 90, 540, 540)
        rects = self._grid_rects(len(visible), top=panel.y + 88,
                                 cols=4, slot=52, gap=8, left=panel.x + 30)
        return [(start + offset, rects[offset]) for offset in range(len(visible))]

    def _confirm_choice_rects(self):
        """确认弹窗“取消/确定”按钮的可点击区域"""
        panel = self._confirm_panel()
        rects = []
        for i, label in enumerate(["取消", "确定"]):
            y = panel.y + 110 + i * 46
            w = self.game.font_medium.size("> " + label)[0]
            rects.append((i, pygame.Rect(panel.x + (panel.width - w) // 2 - 24, y - 10, w + 24, 44)))
        return rects

    def _forge_item_slot_rect(self):
        """锻造页底部“物品”放入格子的区域。"""
        panel = self._bottom_panel()
        return pygame.Rect(panel.x + 16, panel.y + 18, 56, 56)

    def _forge_stone_slot_rect(self):
        """锻造页底部“重铸石”放入格子的区域。"""
        panel = self._bottom_panel()
        return pygame.Rect(panel.x + 92, panel.y + 18, 56, 56)

    def _forge_confirm_rect(self):
        """锻造页底部“重铸”按钮区域（不溢出底部面板）。"""
        panel = self._bottom_panel()
        return pygame.Rect(panel.x + panel.width - 186, panel.y + 22, 170, 44)

    def _grid_rects(self, count, top=_GRID_TOP, cols=_GRID_COLS, slot=_SLOT,
                    gap=_GAP, left=None):
        """计算 count 个槽位组成的 9 列网格 Rect 列表（行优先）。"""
        if left is None:
            left = (cfg.SCREEN_WIDTH - (cols * slot + (cols - 1) * gap)) // 2
        rects = []
        for i in range(count):
            r, c = divmod(i, cols)
            rects.append(pygame.Rect(left + c * (slot + gap),
                                     top + r * (slot + gap), slot, slot))
        return rects

    def _current_grid_top(self):
        """当前页面的主网格顶部 y（装备页网格比其它页低，给装备槽留空间）。"""
        if self.page_names[self.page_idx] == "equipment":
            return 272
        return _GRID_TOP

    def _current_grid_rows(self):
        """当前页面的主网格行数（装备页为给底部面板留空间而减少）。"""
        if self.page_names[self.page_idx] == "equipment":
            return 4
        return _GRID_MAX_ROWS

    def _current_grid_left(self):
        """当前页面的主网格最左侧 x（装备页网格靠左，右侧留给自机属性）。"""
        if self.page_names[self.page_idx] == "equipment":
            return 36
        return None

    def _draw_empty_grid(self, screen):
        """在内容区铺满完整的空槽位网格（作为背景结构感）。"""
        top = self._current_grid_top()
        left = self._current_grid_left()
        rows = self._current_grid_rows()
        rects = self._grid_rects(rows * _GRID_COLS, top=top, left=left)
        for rect in rects:
            sui.draw_slot(screen, rect)

    def _confirm_panel(self):
        """确认弹窗面板 Rect。"""
        return pygame.Rect(230, 240, 500, 240)

    def _bottom_panel(self):
        """各页底部详情/预览面板 Rect。"""
        return pygame.Rect(36, _BOTTOM_Y, cfg.SCREEN_WIDTH - 72, 104)

    def _mouse_ui_click(self, mp):
        """非确认/非装备选择覆盖状态下，处理所有鼠标点击区域"""
        for i, rect in self._page_tab_rects():
            if rect.collidepoint(mp):
                self._set_page(i)
                return
        for idx, rect in self._bottom_action_rects():
            if rect.collidepoint(mp):
                if idx == 1:
                    self._open_confirm("next")
                elif idx == 2:
                    self._open_confirm("extract")
                elif idx == 3:
                    self._open_confirm("extract" if self.pre_start else "exit")
                return
        page = self.page_names[self.page_idx]
        if page == "equipment":
            self._mouse_equipment_click(mp)
            self._mouse_inventory_click(mp)
        elif page == "inventory":
            self._mouse_inventory_click(mp)
        elif page == "shop":
            self._mouse_shop_click(mp)
        elif page == "forge":
            self._mouse_forge_click(mp)

    def _mouse_equipment_click(self, mp):
        for i, rect in self._equipment_slot_rects():
            if rect.collidepoint(mp):
                # 第一次点击仅选中（查看详情），再次点击才打开替换界面
                if i == self.selected and self.equip_slot_clicked:
                    self.choosing_slot = EQUIPMENT_SLOTS[i]
                    self.choose_selected = 0
                    self.equip_slot_clicked = False
                else:
                    self.selected = i
                    self.equip_slot_clicked = True
                return

    def _mouse_inventory_click(self, mp):
        page = self.page_names[self.page_idx]
        on_equip = page == "equipment"
        entries = self.inventory.get_inventory_entries()
        for idx, rect in self._inventory_row_rects():
            if rect.collidepoint(mp):
                if on_equip:
                    # 装备页下方物品：第一次点击仅选中，第二次点击再装备/卸下
                    if idx == self.equip_grid_sel:
                        self._equip_or_unequip(entries[idx])
                    else:
                        self.equip_grid_sel = idx
                else:
                    # 背包页物品：第一次点击仅选中，第二次点击再装备/卸下
                    if idx == self.selected:
                        self._equip_or_unequip(entries[idx])
                    else:
                        self.selected = idx
                return

    def _equip_or_unequip(self, entry):
        """对当前选中的物品执行装备 / 卸下（鼠标第二次点击或键盘确认触发）。"""
        item = entry["item"]
        prefix = entry.get("prefix")
        on_equip = self.page_names[self.page_idx] == "equipment"
        if not item.is_equippable:
            self._set_message("该物品不能装备")
            return
        if self.inventory.is_equipped(item.id, prefix):
            if not self.inventory.unequip_item(item.id):
                self._set_message("卸下失败")
                return
            self._save_inventory()
            if on_equip:
                self.selected = EQUIPMENT_SLOTS.index(item.slot)
                self.equip_slot_clicked = False
                max_idx = len(self.inventory.get_inventory_entries()) - 1
                self.equip_grid_sel = min(self.equip_grid_sel, max(0, max_idx))
            else:
                max_idx = len(self.inventory.get_inventory_entries()) - 1
                self.selected = min(self.selected, max(0, max_idx))
            self._set_message(f"已卸下：{self.inventory.get_display_name(item.id, prefix)}")
        else:
            ok, err = self.inventory.equip(item.id, prefix)
            if not ok:
                self._set_message(err or "装备失败")
                return
            self._save_inventory()
            if on_equip:
                self.selected = EQUIPMENT_SLOTS.index(item.slot)
                self.equip_slot_clicked = False
                max_idx = len(self.inventory.get_inventory_entries()) - 1
                self.equip_grid_sel = min(self.equip_grid_sel, max(0, max_idx))
            else:
                max_idx = len(self.inventory.get_inventory_entries()) - 1
                self.selected = min(self.selected, max(0, max_idx))
            self._set_message(f"已装备：{self.inventory.get_display_name(item.id, prefix)}")

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
        stones, _ = self.inventory.get_forge_entries()
        for idx, rect in self._forge_stone_rects():
            if rect.collidepoint(mp):
                entry = stones[idx]
                if self.forge_mode == "stone" and idx == self.forge_stone_idx:
                    self.placed_stone_id = entry["id"]
                else:
                    self.forge_stone_idx = idx
                    self.forge_mode = "stone"
                return
        view = self._forge_item_view()
        for idx, rect in self._forge_item_rects():
            if rect.collidepoint(mp):
                if view[idx].get("header"):
                    continue
                entry = view[idx]
                if self.forge_mode == "item" and idx == self.forge_item_idx:
                    self.placed_item_id = entry["id"]
                    self.placed_item_prefix = entry.get("prefix")
                else:
                    self.forge_item_idx = idx
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
                ok, err = self.inventory.equip(entry["id"], entry.get("prefix"))
                if not ok:
                    self._set_message(err or "装备失败")
                    return
                self._save_inventory()
                self._set_message(f"已装备：{entry['display_name']}")
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
        # 悬停仅作“将选”视觉提示（由各槽位 hover 高亮处理），不再改变实际选中项。

    def _forge_confirm_click(self):
        if self.placed_item_id is None or self.placed_stone_id is None:
            missing = ("物品和重铸石" if self.placed_item_id is None and self.placed_stone_id is None
                       else ("物品" if self.placed_item_id is None else "重铸石"))
            self._set_message(f"请先放入{missing}")
            return
        item = SKYBLOCK_ITEMS.get(self.placed_item_id)
        stone = SKYBLOCK_ITEMS.get(self.placed_stone_id)
        ok, err = self.inventory.apply_reforge(
            self.placed_item_id, self.placed_stone_id, prefix=self.placed_item_prefix)
        self._save_inventory()
        if ok:
            prefix = REFORGE_STONES.get(self.placed_stone_id)
            prefix_name = REFORGES[prefix]["name"] if prefix in REFORGES else prefix
            cost = self.inventory.get_reforge_cost(self.placed_item_id)
            shown = self.inventory.get_display_name(self.placed_item_id, prefix)
            self._set_message(f"重铸成功：{shown}（-{cost} 金币）")
            self.placed_item_id = None
            self.placed_stone_id = None
            self.placed_item_prefix = None
            self.forge_mode = "stone"
            self.forge_stone_idx = 0
        else:
            self._set_message(err or "重铸失败")

    def _update_forge_page(self, keys):
        """锻造页交互：←→ 切换列表焦点，↑↓ 选择，Enter 放入格子，R 重铸。"""
        stones, _ = self.inventory.get_forge_entries()

        # 滚轮：滚动光标所指列（左=重铸石，右=可锻造物品）
        wheel_dir = self.game.wheel_direction()
        if wheel_dir:
            if self.forge_mode == "item":
                view = self._forge_item_view()
                real = [i for i, e in enumerate(view) if not e.get("header")]
                if real:
                    if self.forge_item_idx not in real:
                        self.forge_item_idx = real[0]
                    pos = (real.index(self.forge_item_idx) + wheel_dir) % len(real)
                    self.forge_item_idx = real[pos]
            elif stones:
                self.forge_stone_idx = (self.forge_stone_idx + wheel_dir) % len(stones)

        # ←→ 切换列表焦点
        if keys.get(pygame.K_LEFT, False) or keys.get(pygame.K_a, False):
            self.forge_mode = "stone"
        if keys.get(pygame.K_RIGHT, False) or keys.get(pygame.K_d, False):
            self.forge_mode = "item"

        # X：清空已放入的格子，回到选重铸石（Esc 由主 update 拦截用于退出确认）
        if keys.get(pygame.K_x, False):
            self.placed_item_id = None
            self.placed_stone_id = None
            self.placed_item_prefix = None
            self.forge_mode = "stone"
            return

        # R 键触发重铸（无论焦点在哪，只要两格已放入）
        if keys.get(pygame.K_r, False):
            self._forge_confirm_click()
            return

        if self.forge_mode == "stone":
            if not stones:
                self._set_message(f"{self.bag_name}中没有重铸石")
                return
            if self.forge_stone_idx >= len(stones):
                self.forge_stone_idx = 0
            if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
                self.forge_stone_idx = (self.forge_stone_idx - 1) % len(stones)
            if keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
                self.forge_stone_idx = (self.forge_stone_idx + 1) % len(stones)
            if self._confirm_pressed(keys):
                self.placed_stone_id = stones[self.forge_stone_idx]["id"]
            return

        # 焦点在物品列表（分组视图，跳过表头）
        view = self._forge_item_view()
        real = [i for i, e in enumerate(view) if not e.get("header")]
        if not real:
            self._set_message(f"{self.bag_name}中没有可锻造的物品")
            return
        if self.forge_item_idx not in real:
            self.forge_item_idx = real[0]
        if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
            pos = (real.index(self.forge_item_idx) - 1) % len(real)
            self.forge_item_idx = real[pos]
        if keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
            pos = (real.index(self.forge_item_idx) + 1) % len(real)
            self.forge_item_idx = real[pos]
        if self._confirm_pressed(keys):
            self.placed_item_id = view[self.forge_item_idx]["id"]
            self.placed_item_prefix = view[self.forge_item_idx].get("prefix")

    # --- 绘制辅助 ---

    def _draw_text(self, screen, text, x, y, color, font, align="left", shadow=True):
        return sui.draw_text(screen, text, x, y, color, font,
                             shadow=shadow, align=align) + 6

    def _panel_color(self, color):
        """把深色文字颜色映射为深灰分区上可读的浅色。"""
        if color == sui.TIMBER:
            return sui.PANEL_TEXT
        if color in (sui.MENU_MID, cfg.COLOR_GRAY):
            return sui.PANEL_TEXT_DIM
        return color

    def _visible_slice(self, entries, selected, max_rows):
        if len(entries) <= max_rows:
            return entries, 0
        start = max(0, min(selected - max_rows // 2, len(entries) - max_rows))
        return entries[start:start + max_rows], start

    def _frame_title(self):
        if self.pre_start:
            return "出发前休整 · 穿戴携带物品", "选择携带物品，确认后出发"
        return f"第 {self.stage_num} 面结束 · 休整", "装备 / 背包 / 商店 / 锻造"

    def _draw_current_page(self, screen):
        if self.page_idx == 0:
            self._draw_equipment_page(screen)
        elif self.page_idx == 1:
            self._draw_inventory_page(screen)
        elif self.page_idx == 2:
            self._draw_shop_page(screen)
        else:
            self._draw_forge_page(screen)

    def draw(self, screen):
        # 标题与金币（SkyBlock 菜单外框）
        title_text, subtitle = self._frame_title()
        content = sui.draw_menu_frame(
            screen,
            title=title_text,
            subtitle=subtitle,
            coins=self.inventory.coins,
            font_title=self.game.font_large,
            font_small=self.game.font_small,
        )

        # 顶部页签
        tab_rects = self._page_tab_rects()
        for i, label in enumerate(self.page_labels):
            rect = tab_rects[i][1]
            sui.draw_button(screen, rect, label, self.game.font_medium,
                            selected=(i == self.page_idx),
                            hover=self.game.mouse_hover(rect))

        # 页签下方的分隔线
        hires.ui_line(screen, sui.SLOT_DARK,
                         (36, _DIVIDER_Y), (cfg.SCREEN_WIDTH - 36, _DIVIDER_Y), 2)
        hires.ui_line(screen, sui.SLOT_LIGHT,
                         (36, _DIVIDER_Y + 1), (cfg.SCREEN_WIDTH - 36, _DIVIDER_Y + 1), 1)

        # 深灰分区（内容层底板）：主内容区 + 底部操作区
        page = self.page_names[self.page_idx]
        if page == "forge":
            stones, forge_items = self.inventory.get_forge_entries()
            view = self._forge_item_view()
            rows = max(1, min(_FORGE_LIST_ROWS, max(len(stones), len(view))))
            panel_bottom = _GRID_TOP + 6 + rows * 52 + 12
            panel_bottom = min(panel_bottom, _BOTTOM_Y - 12)
        else:
            grid_rows = self._current_grid_rows()
            panel_bottom = (self._current_grid_top()
                            + grid_rows * (_SLOT + _GAP) - _GAP + 18)
        main_panel = pygame.Rect(18, _DIVIDER_Y + 6, cfg.SCREEN_WIDTH - 36,
                                 panel_bottom - (_DIVIDER_Y + 6))
        bottom_panel = pygame.Rect(36, _BOTTOM_Y, cfg.SCREEN_WIDTH - 72,
                                   cfg.SCREEN_HEIGHT - _BOTTOM_Y - 14)
        sui.draw_section(screen, main_panel)
        sui.draw_section(screen, bottom_panel)

        self._draw_current_page(screen)

        # 底部操作提示（纯文本）
        sui.draw_text(screen,
                      self._bottom_hint_text(),
                      cfg.SCREEN_WIDTH // 2, _HINT_Y, sui.PANEL_TEXT_DIM,
                      self.game.font_small, align="center")
        # 底部动作按钮（N / B / Esc）
        action_labels = dict(self._bottom_action_defs())
        for i, rect in self._bottom_action_rects():
            sui.draw_button(screen, rect, action_labels[i], self.game.font_medium,
                            hover=self.game.mouse_hover(rect))

        if self.message:
            self._draw_text(screen, self.message, cfg.SCREEN_WIDTH // 2,
                            _BOTTOM_Y - 30, cfg.COLOR_GREEN,
                            self.game.font_medium, align="center")

        self._draw_confirm_dialog(screen)

    def _bottom_hint_text(self):
        """底部操作提示（根据当前页面/仓库模式给出准确的按键说明）。"""
        page = self.page_names[self.page_idx]
        nav = "Q/E 或 " + "/".join(str(i + 1) for i in range(len(self.page_names))) + "：切换页面"
        if page == "equipment":
            return f"{nav}    ↑↓：选择物品    ←→：切换装备槽    Enter/Z/Space：确认"
        if page == "inventory":
            # 仓库背包仅查看，不在此执行装备/卸下
            if self.bag_name == "仓库":
                return f"{nav}    ↑↓：选择"
            return f"{nav}    ↑↓：选择    Enter/Z/Space：确认"
        if page == "shop":
            return f"{nav}    A/D：购买/出售    ↑↓：选择    Enter/Z/Space：确认"
        if page == "forge":
            return f"{nav}    ←→：切换列表    ↑↓：选择    Enter：放入格子    R：重铸"
        return f"{nav}    ↑↓：选择"

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
        panel = self._confirm_panel()
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))
        sui.draw_container(screen, panel)

        msg = texts.get(self.confirm_action, "确定吗？")
        self._draw_text(screen, msg, panel.centerx, panel.y + 34, sui.TIMBER,
                        self.game.font_small, align="center")
        choice_rects = self._confirm_choice_rects()
        for i, label in enumerate(["取消", "确定"]):
            rect = choice_rects[i][1]
            sui.draw_button(screen, rect, label, self.game.font_medium,
                            selected=(i == self.confirm_choice),
                            hover=self.game.mouse_hover(rect))
        self._draw_text(screen, "↑↓ 选择   Enter 确认   Esc 取消（鼠标可点击按钮）",
                        panel.x + 40, panel.y + panel.height - 36,
                        sui.MENU_MID, self.game.font_small)

    # --- 物品详情 / 自机属性 ---

    def _item_detail_lines(self, item):
        """生成物品功能说明行 [(文本, 颜色)]：基础属性 + lore"""
        lines = []
        if item is None:
            return lines
        stat_text = item.stat_text()
        if stat_text:
            lines.append((stat_text, cfg.COLOR_GRAY))
        lines.extend((line, sui.TIMBER) for line in (item.lore or []))
        return lines

    def _draw_item_detail_panel(self, screen, item, x=36, y=470, w=None, h=190,
                                display_name=None):
        """底部物品功能说明面板：名称 / 基础属性 / lore"""
        if w is None:
            w = cfg.SCREEN_WIDTH - 72
        panel = pygame.Rect(x, y, w, h)
        sui.draw_container(screen, panel, fill=sui.PANEL_BG)
        py = panel.y + 14
        if item is None:
            self._draw_text(screen, "未选择物品", panel.x + 20, py,
                            sui.PANEL_TEXT_DIM, self.game.font_small)
            return
        self._draw_text(screen, display_name or item.name, panel.x + 20, py,
                        item.rarity_color, self.game.font_medium)
        py += 32
        for text, color in self._item_detail_lines(item):
            if py > panel.y + panel.height - 14:
                break
            py = self._draw_text(screen, text, panel.x + 20, py,
                                 self._panel_color(color), self.game.font_small)

    def _equipment_panel_lines(self):
        """装备页右侧面板：总属性 / 被动效果 / 技能 -> [(文本, 颜色)]"""
        lines = []

        # 总属性（装备基础属性）
        stats = self.inventory.get_equipped_stats()
        lines.append(("—— 总属性 ——", sui.TIMBER))
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
        lines.append(("—— 被动效果 ——", sui.TIMBER))
        if not effect_lines:
            lines.append(("无", cfg.COLOR_GRAY))
        lines.extend((text, cfg.COLOR_GREEN) for text in effect_lines)

        # 技能：C技能 + Skyblock 技能等级
        lines.append(("—— 技能 ——", sui.TIMBER))
        c_id = self.inventory.get_c_skill_equipped_id()
        if c_id:
            item = SKYBLOCK_ITEMS.get(c_id)
            skill = C_SKILLS.get(c_id, {})
            sname = skill.get("name", "C技能")
            desc = skill.get("desc", "")
            per = skill.get("per_stage", 1)
            c_slot = self.inventory.get_equipped_slot(c_id)
            c_prefix = self.inventory.get_equipped_prefix(c_slot) if c_slot else None
            shown_name = self.inventory.get_display_name(c_id, c_prefix) if item else c_id
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

    def _tooltip_lines(self, item, extra=None, display_name=None):
        """生成 SkyBlock 悬停提示框内容：[(文本, 颜色), ...]。"""
        if item is None:
            return []
        lines = [
            (display_name or item.name, item.rarity_color),
            (item.rarity_display, item.rarity_color),
            (ITEM_TYPE_LABELS.get(item.item_type, item.item_type), cfg.COLOR_GRAY),
        ]
        stat_text = item.stat_text()
        if stat_text:
            lines.append((stat_text, cfg.COLOR_WHITE))
        for lore_line in (item.lore or []):
            lines.append((lore_line, cfg.COLOR_WHITE))
        if extra:
            lines.extend(extra)
        return lines

    def _grid_hover_entries(self):
        """返回当前页面的 (条目, rect) 列表，供悬停提示框使用。"""
        page = self.page_names[self.page_idx]
        if page == "inventory":
            entries = self.inventory.get_inventory_entries()
            return [(entries[idx], rect) for idx, rect in self._inventory_row_rects()]
        if page == "shop":
            entries = self._current_shop_entries()
            return [(entries[idx], rect) for idx, rect in self._shop_row_rects()]
        if page == "forge":
            stones, _ = self.inventory.get_forge_entries()
            items = self.inventory.get_inventory_entries()
            out = []
            for idx, rect in self._forge_stone_rects():
                out.append((stones[idx], rect))
            return out
        if page == "equipment":
            entries = self.inventory.get_inventory_entries()
            return [(entries[idx], rect) for idx, rect in self._inventory_row_rects()]
        return []

    def _draw_hover_tooltip(self, screen):
        mp = self.game.mouse_pos
        page = self.page_names[self.page_idx]
        for entry, rect in self._grid_hover_entries():
            if rect.collidepoint(mp):
                item = entry["item"]
                extra = []
                if "count" in entry and entry["count"] > 1:
                    extra.append((f"数量：{entry['count']}", cfg.COLOR_GRAY))
                if page == "shop":
                    if self.shop_mode == "buy" and "buy_price" in entry:
                        extra.append((f"购买价格：{entry['buy_price']} 金币", cfg.COLOR_YELLOW))
                    elif self.shop_mode == "sell" and "sell_price" in entry:
                        extra.append((f"出售价格：{entry['sell_price']} 金币", cfg.COLOR_GREEN))
                sui.draw_item_tooltip(screen, mp,
                                      self._tooltip_lines(item, extra,
                                                          display_name=entry.get("display_name")),
                                      self.game.font_small)
                return

    def _draw_slot_item(self, screen, rect, entry, selected=False, show_count=True):
        """绘制一个槽位中的物品图标（含选中/悬停高亮与数量角标）。"""
        item = entry["item"]
        hover = self.game.mouse_hover(rect)
        sui.draw_slot(screen, rect, selected=selected, hover=hover)
        draw_item_icon(screen, item.id, rect.x, rect.y, size=rect.width, padding=4)
        if show_count and entry.get("count", 0) > 1:
            sui.draw_count_badge(screen, rect, entry["count"], self.game.font_small)
        if entry.get("equipped"):
            # 已装备角标：底边小绿条
            hires.ui_line(screen, cfg.COLOR_GREEN,
                             (rect.x + 6, rect.bottom - 4),
                             (rect.right - 6, rect.bottom - 4), 3)

    def _draw_equipment_page(self, screen):
        # 顶部：装备槽（一排，图标 + 槽位名）
        sui.draw_text(screen, "已装备", 40, 146, sui.PANEL_TEXT, self.game.font_medium)
        eq_rects = self._equipment_slot_rects()
        for i, slot in enumerate(EQUIPMENT_SLOTS):
            rect = eq_rects[i][1]
            item = self.inventory.get_equipped_item(slot)
            selected = i == self.selected
            hover = self.game.mouse_hover(rect)
            sui.draw_slot(screen, rect, selected=selected, hover=hover)
            if item:
                draw_item_icon(screen, item.id, rect.x, rect.y, size=rect.width, padding=4)
            label = SLOT_LABELS[slot]
            label_color = item.rarity_color if item else sui.PANEL_TEXT_DIM
            self._draw_text(screen, label, rect.centerx, rect.bottom + 4,
                            label_color, self.game.font_small, align="center")
        # 左侧主网格：背包 / 携带物品
        sui.draw_text(screen, "背包 / 携带物品", 40, 246, sui.PANEL_TEXT, self.game.font_medium)
        sui.draw_text(screen, "点击选中，再次点击装备", 300, 252, sui.PANEL_TEXT_DIM, self.game.font_small)
        entries = self.inventory.get_inventory_entries()
        if entries:
            self._draw_empty_grid(screen)
            focus = self._inventory_focus_index()
            visible, start = self._visible_slice(entries, focus,
                                                 self._current_grid_rows() * _GRID_COLS)
            rects = self._grid_rects(len(visible), top=self._current_grid_top(),
                                     left=self._current_grid_left())
            for offset, entry in enumerate(visible):
                self._draw_slot_item(screen, rects[offset], entry,
                                     selected=(start + offset == focus),
                                     show_count=True)
        else:
            self._draw_text(screen, f"{self.bag_name}是空的", 40, 296,
                            sui.PANEL_TEXT_DIM, self.game.font_medium)

        # 右侧：自机属性（可滚动），底部附选中装备详情
        self._draw_equipment_stats(screen)

        # 装备选择覆盖层打开时优先绘制覆盖层，避免装备槽/背包 tooltip 提前 return 导致覆盖层闪没
        if self.choosing_slot is not None:
            self._draw_equip_chooser(screen)
            return

        # 悬停提示框（仅背包物品；装备槽详情见底部「装备详情」，可再次点击打开替换）
        self._draw_hover_tooltip(screen)

    def _draw_equipment_stats(self, screen):
        """装备页右侧自机属性面板（深灰分区，可滚动）。"""
        panel = pygame.Rect(608, 146, cfg.SCREEN_WIDTH - 644, 500)
        sui.draw_container(screen, panel, fill=sui.PANEL_BG)
        sui.draw_text(screen, "自机属性", panel.x + 16, panel.y + 10,
                      sui.PANEL_TEXT, self.game.font_medium)
        lines = self._equipment_panel_lines()
        line_h = 21
        top = panel.y + 40
        bottom = panel.y + panel.height - 70
        max_rows = max(1, (bottom - top) // line_h)
        self.equip_scroll = max(0, min(self.equip_scroll, max(0, len(lines) - max_rows)))
        visible = lines[self.equip_scroll:self.equip_scroll + max_rows]
        py = top
        for text, color in visible:
            py = self._draw_text(screen, text, panel.x + 16, py,
                                 self._panel_color(color), self.game.font_small)
        if len(lines) > max_rows:
            self._draw_text(screen, "滚轮滚动", panel.x + panel.width - 78, panel.y + 10,
                            sui.PANEL_TEXT_DIM, self.game.font_small)

        # 底部：当前选中装备槽的物品详情
        selected_item = None
        if self.selected < len(EQUIPMENT_SLOTS):
            selected_item = self.inventory.get_equipped_item(EQUIPMENT_SLOTS[self.selected])
        divider_y = panel.y + panel.height - 58
        hires.ui_line(screen, sui.SLOT_DARK, (panel.x + 14, divider_y),
                         (panel.right - 14, divider_y), 2)
        self._draw_text(screen, "装备详情", panel.x + 16, divider_y + 8,
                        sui.PANEL_TEXT, self.game.font_medium)
        if selected_item:
            selected_slot = EQUIPMENT_SLOTS[self.selected]
            self._draw_text(screen, self.inventory.get_display_name(
                                selected_item.id, self.inventory.get_equipped_prefix(selected_slot)),
                            panel.x + 16, divider_y + 38, selected_item.rarity_color,
                            self.game.font_small)
        else:
            self._draw_text(screen, "（空）", panel.x + 16, divider_y + 38,
                            sui.PANEL_TEXT_DIM, self.game.font_small)

    def _draw_equip_chooser(self, screen):
        entries = self.inventory.get_equippable_entries_for_slot(self.choosing_slot)
        panel = pygame.Rect(210, 90, 540, 540)
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((30, 30, 30, 170))
        screen.blit(overlay, (0, 0))
        sui.draw_container(screen, panel)

        self._draw_text(screen, f"选择 {SLOT_LABELS[self.choosing_slot]}",
                        panel.x + 24, panel.y + 18, sui.TIMBER, self.game.font_medium)
        cancel_rect = self._chooser_cancel_rect()
        sui.draw_button(screen, cancel_rect, "取消", self.game.font_small,
                        hover=self.game.mouse_hover(cancel_rect))

        if not entries:
            self._draw_text(screen, "背包中没有可装备的物品", panel.x + 24, panel.y + 90,
                            sui.MENU_MID, self.game.font_small)
            self._draw_text(screen, "Enter / Esc 返回（鼠标点击关闭）",
                            panel.x + 24, panel.y + 122, sui.MENU_MID, self.game.font_small)
            return

        visible, start = self._visible_slice(entries, self.choose_selected, 12)
        rects = self._grid_rects(len(visible), top=panel.y + 88,
                                 cols=4, slot=52, gap=8, left=panel.x + 30)
        for offset, entry in enumerate(visible):
            idx = start + offset
            selected = idx == self.choose_selected
            rect = rects[offset]
            self._draw_slot_item(screen, rect, entry, selected=selected, show_count=True)

        self._draw_text(screen, "Enter 装备   Esc 取消（鼠标点击关闭）",
                        panel.x + 24, panel.y + panel.height - 40,
                        sui.MENU_MID, self.game.font_small)

        # 面板底部：所选物品功能说明
        entry = entries[self.choose_selected]
        item = entry["item"]
        pygame.draw.line(screen, sui.SLOT_DARK,
                         (panel.x + 20, panel.y + 300),
                         (panel.x + panel.width - 20, panel.y + 300))
        py = panel.y + 316
        py = self._draw_text(screen, entry["display_name"], panel.x + 24, py,
                             entry["item"].rarity_color, self.game.font_small)
        for text, color in self._item_detail_lines(item):
            if py > panel.y + panel.height - 40:
                break
            py = self._draw_text(screen, text, panel.x + 24, py, color, self.game.font_small)

        # 悬停提示框
        mp = self.game.mouse_pos
        for offset, entry in enumerate(visible):
            if rects[offset].collidepoint(mp):
                extra = [(f"数量：{entry['count']}", cfg.COLOR_GRAY)]
                if entry["equipped"]:
                    extra.append(("当前已装备", cfg.COLOR_GREEN))
                sui.draw_item_tooltip(screen, mp,
                                      self._tooltip_lines(entry["item"], extra,
                                                          display_name=entry["display_name"]),
                                      self.game.font_small)
                return

    def _draw_inventory_page(self, screen):
        entries = self.inventory.get_inventory_entries()
        sui.draw_text(screen, f"{self.bag_name}物品", 40, 152, sui.PANEL_TEXT, self.game.font_medium)

        if not entries:
            self._draw_text(screen, f"{self.bag_name}是空的", 40, 184,
                            sui.PANEL_TEXT_DIM, self.game.font_medium)
            self._draw_hover_tooltip(screen)
            return

        self._draw_empty_grid(screen)
        visible, start = self._visible_slice(entries, self.selected, _GRID_CAPACITY)
        rects = self._grid_rects(len(visible), top=self._current_grid_top())
        for offset, entry in enumerate(visible):
            idx = start + offset
            selected = idx == self.selected
            self._draw_slot_item(screen, rects[offset], entry, selected=selected, show_count=True)

        # 底部：所选物品功能说明
        if entries:
            if self.selected >= len(entries):
                self.selected = len(entries) - 1
            self._draw_item_detail_panel(screen, entries[self.selected]["item"],
                                         x=36, y=_BOTTOM_Y, w=cfg.SCREEN_WIDTH - 72, h=104,
                                         display_name=entries[self.selected]["display_name"])
        self._draw_hover_tooltip(screen)

    def _draw_shop_page(self, screen):
        buy_rect, sell_rect = self._shop_mode_rects()
        sui.draw_button(screen, buy_rect, "购买", self.game.font_medium,
                        selected=(self.shop_mode == "buy"),
                        hover=self.game.mouse_hover(buy_rect))
        sui.draw_button(screen, sell_rect, "出售", self.game.font_medium,
                        selected=(self.shop_mode == "sell"),
                        hover=self.game.mouse_hover(sell_rect))

        entries = self._current_shop_entries()
        if not entries:
            text = "商店暂无商品" if self.shop_mode == "buy" else "没有可出售的装备"
            self._draw_text(screen, text, 40, _GRID_TOP + 30,
                            sui.PANEL_TEXT_DIM, self.game.font_medium)
            self._draw_hover_tooltip(screen)
            return

        self._draw_empty_grid(screen)
        visible, start = self._visible_slice(entries, self.selected, _GRID_CAPACITY)
        rects = self._grid_rects(len(visible), top=self._current_grid_top())
        for offset, entry in enumerate(visible):
            idx = start + offset
            selected = idx == self.selected
            self._draw_slot_item(screen, rects[offset], entry, selected=selected, show_count=True)

        # 底部：所选物品功能说明
        if entries:
            if self.selected >= len(entries):
                self.selected = len(entries) - 1
            entry = entries[self.selected]
            extra = []
            if self.shop_mode == "buy":
                extra = [(f"购买价格：{entry['buy_price']} 金币", cfg.COLOR_YELLOW)]
            else:
                extra = [(f"出售价格：{entry['sell_price']} 金币", cfg.COLOR_GREEN)]
            sui.draw_container(screen, pygame.Rect(36, _BOTTOM_Y,
                                                   cfg.SCREEN_WIDTH - 72, 104), fill=sui.PANEL_BG)
            self._draw_text(screen, entry.get("display_name") or entry["item"].name,
                            56, _BOTTOM_Y + 14,
                            entry["item"].rarity_color, self.game.font_medium)
            py = _BOTTOM_Y + 44
            for text, color in extra + self._item_detail_lines(entry["item"]):
                if py > _BOTTOM_Y + 100:
                    break
                py = self._draw_text(screen, text, 56, py,
                                     self._panel_color(color), self.game.font_small)
        self._draw_hover_tooltip(screen)

    def _draw_forge_page(self, screen):
        """锻造页：物品/重铸石列表 + 底部两个放入格子与重铸按钮。"""
        stones, _ = self.inventory.get_forge_entries()
        left_x = 60
        right_x = 470

        # 左列：重铸石
        sui.draw_text(screen, "重铸石", left_x, 152, sui.PANEL_TEXT, self.game.font_medium)
        sui.draw_text(screen, "点击选中，再次点击放入", left_x + 78, 158,
                      sui.PANEL_TEXT_DIM, self.game.font_small)
        if not stones:
            self._draw_text(screen, f"{self.bag_name}中没有重铸石", left_x, 184,
                            sui.PANEL_TEXT_DIM, self.game.font_small)
        else:
            for idx, rect in self._forge_stone_rects():
                entry = stones[idx]
                selected = (self.forge_mode == "stone" and idx == self.forge_stone_idx)
                is_placed = (self.placed_stone_id == entry["id"])
                sui.draw_row_frame(screen, rect, selected, self.game.mouse_hover(rect))
                item = entry["item"]
                prefix = REFORGES.get(entry["prefix"])
                prefix_name = prefix.get("name", "") if prefix else ""
                sui.draw_slot(screen, pygame.Rect(rect.x + 6, rect.y + 5, 38, 38))
                draw_item_icon(screen, item.id, rect.x + 8, rect.y + 7, size=34)
                color = cfg.COLOR_GREEN if is_placed else (
                    item.rarity_color if selected else sui.PANEL_TEXT)
                marker = "> " if selected else ""
                name_text = _fit_text(f"{item.name} x{entry['count']}",
                                      self.game.font_small,
                                      202 - self.game.font_small.size(marker)[0])
                self._draw_text(screen, marker + name_text,
                                rect.x + 52, rect.y + 12, color, self.game.font_small)
                if prefix_name:
                    self._draw_text(screen, f"→ {prefix_name}", rect.x + 260, rect.y + 12,
                                    sui.PANEL_TEXT_DIM, self.game.font_small)
                if is_placed:
                    self._draw_text(screen, "已放入", rect.x + 360, rect.y + 12,
                                    cfg.COLOR_GREEN, self.game.font_small)

        # 右列：可锻造物品
        sui.draw_text(screen, "可锻造物品", right_x, 152, sui.PANEL_TEXT, self.game.font_medium)
        sui.draw_text(screen, "点击选中，再次点击放入", right_x + 96, 158,
                      sui.PANEL_TEXT_DIM, self.game.font_small)
        view = self._forge_item_view()
        if not view:
            self._draw_text(screen, f"{self.bag_name}中没有可锻造的物品", right_x, 184,
                            sui.PANEL_TEXT_DIM, self.game.font_small)
        else:
            for idx, rect in self._forge_item_rects():
                entry = view[idx]
                if entry.get("header"):
                    self._draw_text(screen, f"— {entry['label']} —", rect.centerx,
                                    rect.centery, sui.PANEL_TEXT_DIM,
                                    self.game.font_small, align="center")
                    continue
                selected = (self.forge_mode == "item" and idx == self.forge_item_idx)
                is_placed = (self.placed_item_id == entry["id"]
                             and self.placed_item_prefix == entry.get("prefix"))
                sui.draw_row_frame(screen, rect, selected, self.game.mouse_hover(rect))
                item = entry["item"]
                sui.draw_slot(screen, pygame.Rect(rect.x + 6, rect.y + 5, 38, 38))
                draw_item_icon(screen, item.id, rect.x + 8, rect.y + 7, size=34)
                color = cfg.COLOR_GREEN if is_placed else (
                    item.rarity_color if selected else sui.PANEL_TEXT)
                marker = "> " if selected else ""
                name_text = _fit_text(entry["display_name"], self.game.font_small,
                                      243 - self.game.font_small.size(marker)[0])
                self._draw_text(screen, marker + name_text,
                                rect.x + 52, rect.y + 12, color, self.game.font_small)
                self._draw_text(screen, f"{entry['cost']} 金币", rect.x + 300, rect.y + 12,
                                cfg.COLOR_YELLOW, self.game.font_small)
                if is_placed:
                    self._draw_text(screen, "已放入", rect.x + 375, rect.y + 12,
                                    cfg.COLOR_GREEN, self.game.font_small)
                elif entry.get("equipped"):
                    self._draw_text(screen, "已装备", rect.x + 375, rect.y + 12,
                                    cfg.COLOR_GREEN, self.game.font_small)

        # 底部面板：物品格子 + 重铸石格子 + 重铸按钮
        panel = self._bottom_panel()
        sui.draw_container(screen, panel, fill=sui.PANEL_BG)
        item_slot = self._forge_item_slot_rect()
        stone_slot = self._forge_stone_slot_rect()
        sui.draw_slot(screen, item_slot)
        sui.draw_slot(screen, stone_slot)
        placed_item = SKYBLOCK_ITEMS.get(self.placed_item_id) if self.placed_item_id else None
        placed_stone = SKYBLOCK_ITEMS.get(self.placed_stone_id) if self.placed_stone_id else None
        if placed_item:
            draw_item_icon(screen, self.placed_item_id, item_slot.x, item_slot.y,
                           size=item_slot.width, padding=4)
        if placed_stone:
            draw_item_icon(screen, self.placed_stone_id, stone_slot.x, stone_slot.y,
                           size=stone_slot.width, padding=4)
        self._draw_text(screen, "物品", item_slot.centerx, item_slot.bottom + 2,
                        sui.PANEL_TEXT_DIM, self.game.font_small, align="center")
        self._draw_text(screen, "重铸石", stone_slot.centerx, stone_slot.bottom + 2,
                        sui.PANEL_TEXT_DIM, self.game.font_small, align="center")

        info_x = stone_slot.right + 16
        info_y = panel.y + 20
        if placed_item and placed_stone:
            prefix = REFORGE_STONES.get(self.placed_stone_id)
            prefix_name = REFORGES[prefix]["name"] if prefix in REFORGES else "?"
            cost = self.inventory.get_reforge_cost(self.placed_item_id)
            shown_name = self.inventory.get_display_name(self.placed_item_id, self.placed_item_prefix)
            self._draw_text(screen, f"将给 {shown_name} 打上 {prefix_name} 前缀",
                            info_x, info_y, cfg.COLOR_YELLOW, self.game.font_small)
            self._draw_text(screen, f"费用：{cost} 金币", info_x, info_y + 22,
                            sui.PANEL_TEXT_DIM, self.game.font_small)
        elif placed_item or placed_stone:
            missing = "重铸石" if not placed_stone else "物品"
            self._draw_text(screen, f"还需放入{missing}", info_x, info_y,
                            sui.PANEL_TEXT_DIM, self.game.font_small)
        else:
            self._draw_text(screen, "请分别选择物品和重铸石放入", info_x, info_y,
                            sui.PANEL_TEXT_DIM, self.game.font_small)

        forge_confirm_rect = self._forge_confirm_rect()
        forge_confirm_hover = self.game.mouse_hover(forge_confirm_rect)
        enabled = bool(placed_item and placed_stone)
        sui.draw_button(screen, forge_confirm_rect, "重铸", self.game.font_medium,
                        enabled=enabled, hover=forge_confirm_hover)

        # 悬停提示框
        mp = self.game.mouse_pos
        for idx, rect in self._forge_stone_rects():
            if rect.collidepoint(mp):
                entry = stones[idx]
                extra = [(f"数量：{entry['count']}", cfg.COLOR_GRAY)]
                sui.draw_item_tooltip(screen, mp, self._tooltip_lines(entry["item"], extra),
                                      self.game.font_small)
                return
        for idx, rect in self._forge_item_rects():
            if rect.collidepoint(mp):
                entry = view[idx]
                if entry.get("header"):
                    continue
                extra = [(f"费用：{entry['cost']} 金币", cfg.COLOR_YELLOW)]
                sui.draw_item_tooltip(screen, mp,
                                      self._tooltip_lines(entry["item"], extra,
                                                          display_name=entry["display_name"]),
                                      self.game.font_small)
                return
