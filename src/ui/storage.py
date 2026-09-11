# 仓库界面：查看已有物品 + 使用重铸石锻造

import pygame
from src.engine import settings as cfg
from src.systems.warehouse import load_warehouse, save_warehouse
from src.ui.intermission import IntermissionState, _HINT_Y


class StorageState(IntermissionState):
    """从主菜单进入的本地仓库：查看库存物品 / 对仓库装备进行锻造。"""

    def __init__(self, game):
        # 复用休整界面的全部布局与锻造/背包绘制；stage_num 仅占位
        super().__init__(game, 0)
        self.bag_name = "仓库"
        self.page_names = ["inventory", "forge"]
        self.page_labels = ["背包", "锻造"]
        self.page_idx = 0
        self.inventory = load_warehouse()

    def enter(self, game):
        self.game.stop_music()
        self.inventory = load_warehouse()
        self.page_idx = 0
        self.selected = 0
        self.choosing_slot = None
        self.equip_scroll = 0
        self.forge_mode = "stone"
        self.forge_stone_idx = 0
        self.forge_item_idx = 0
        self.placed_item_id = None
        self.placed_stone_id = None
        self.placed_item_prefix = None
        self.message = ""
        self.message_timer = 0
        self.confirm_action = None
        self.confirm_choice = 0

    def _save_inventory(self):
        save_warehouse(self.inventory)

    def _frame_title(self):
        return "仓库 · 物品锻造", "查看仓库已有物品 / 使用重铸石锻造"

    def _draw_current_page(self, screen):
        page = self.page_names[self.page_idx]
        if page == "inventory":
            self._draw_inventory_page(screen)
        elif page == "forge":
            self._draw_forge_page(screen)

    def _bottom_action_defs(self):
        return [(3, "Esc：返回")]

    def _bottom_action_rects(self):
        """底部动作按钮（仅“返回”），与 draw 使用同一布局。"""
        defs = self._bottom_action_defs()
        labels = dict(defs)
        idxs = sorted(labels.keys())
        gap = 14
        pad = 20
        widths = [self.game.font_medium.size(labels[i])[0] + pad * 2 for i in idxs]
        total = sum(widths) + gap * (len(widths) - 1)
        x = (cfg.SCREEN_WIDTH - total) // 2
        y = _HINT_Y + 18
        rects = []
        for pos, i in enumerate(idxs):
            rects.append((i, pygame.Rect(x, y, widths[pos], 32)))
            x += widths[pos] + gap
        return rects

    def _mouse_ui_click(self, mp):
        for i, rect in self._page_tab_rects():
            if rect.collidepoint(mp):
                self._set_page(i)
                return
        for idx, rect in self._bottom_action_rects():
            if rect.collidepoint(mp):
                if idx == 3:
                    self._go_menu()
                return
        page = self.page_names[self.page_idx]
        if page == "inventory":
            self._mouse_inventory_click(mp)
        elif page == "forge":
            self._mouse_forge_click(mp)

    def _mouse_inventory_click(self, mp):
        """仓库背包：点击仅选中物品查看详情，不做装备/卸下。"""
        entries = self.inventory.get_inventory_entries()
        for idx, rect in self._inventory_row_rects():
            if rect.collidepoint(mp):
                self.selected = idx
                return

    def update(self, dt):
        keys = self.game.keys_just_pressed
        mp = self.game.mouse_pos
        clicked = self.game.mouse_clicked(1)
        if clicked:
            self._mouse_ui_click(mp)
            return
        if keys.get(pygame.K_ESCAPE, False) or keys.get(pygame.K_b, False):
            self._go_menu()
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
        page = self.page_names[self.page_idx]
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
            elif self._confirm_pressed(keys):
                self._set_message(f"{self.bag_name}是空的")
        elif page == "forge":
            self._update_forge_page(keys)
