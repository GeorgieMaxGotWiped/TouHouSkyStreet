# 仓库出征准备：从本地仓库选择携带物品与金币后开始新远征
# 界面样式：Hypixel SkyBlock “Equipment and Stats” 菜单（浅灰容器 + 9 列槽位网格 + 悬停提示框）

import pygame
from src.engine import settings as cfg
from src.engine.game import GameState
from src.systems.item_system import (
    ITEM_TYPE_LABELS,
    SKYBLOCK_ITEMS,
)
from src.systems.item_icons import draw_item_icon
from src.systems.warehouse import load_warehouse, save_warehouse
from src.ui import skyblock_ui as sui


# 布局常量（与 draw / 命中区域共享）
_GRID_TOP = 92
_SLOT = 56
_GAP = 6
_GRID_COLS = 9
_GRID_ROWS = 7
_CAPACITY = _GRID_COLS * _GRID_ROWS
_HOTBAR_LABEL_Y = 540
_HOTBAR_Y = 566
_HOTBAR_SLOT = 44
_COIN_Y = 612
_COIN_TRACK_W = 320
_COIN_TRACK_H = 10
_COIN_HANDLE_W = 20
_COIN_HANDLE_H = 22
_HINT_Y = 648


class LoadoutState(GameState):
    """从仓库挑选本局携带物品与金币（出征准备）。"""

    def __init__(self, game):
        super().__init__(game)
        self.warehouse = load_warehouse()
        self.entries = self.warehouse.get_inventory_entries()
        self.carried = {}          # (item_id, prefix) -> 携带数量
        self.carried_coins = 0     # 携带金币
        self.selected = 0
        self.carried_sel = None    # 鼠标在携带热键栏中选中的 (item_id, prefix)
        self.message = ""
        self.message_timer = 0
        self.coin_step = 1000
        self._coin_dragging = False
        self._last_mouse_pos = (0, 0)

    def enter(self, game):
        self.game.stop_music()
        self.selected = 0
        self.carried_sel = None
        self._coin_dragging = False

    def _set_message(self, text, frames=90):
        self.message = text
        self.message_timer = frames

    def _confirm_pressed(self, keys):
        return (keys.get(pygame.K_RETURN, False)
                or keys.get(pygame.K_z, False)
                or keys.get(pygame.K_SPACE, False))

    def _carry_total(self):
        return sum(self.carried.values())

    def _grid_start(self):
        """当前可见网格的起始条目序号（分页）。"""
        if len(self.entries) <= _CAPACITY:
            return 0
        return max(0, min(self.selected - _CAPACITY // 2,
                          len(self.entries) - _CAPACITY))

    def _visible_grid_entries(self):
        start = self._grid_start()
        return self.entries[start:start + _CAPACITY], start

    def _grid_geometry(self):
        """返回网格 Origin 与每格 Rect 列表（行优先，与 _visible_grid_entries 对应）。"""
        visible, start = self._visible_grid_entries()
        x0 = (cfg.SCREEN_WIDTH - (_GRID_COLS * _SLOT + (_GRID_COLS - 1) * _GAP)) // 2
        rows = max(1, (len(visible) + _GRID_COLS - 1) // _GRID_COLS)
        rects = sui.draw_grid((x0, _GRID_TOP), _GRID_COLS, rows, _SLOT, _GAP)
        return x0, rects, visible, start

    def _grid_item_rects(self):
        """返回 (全局序号, rect) 列表，仅包含实际有物品的槽位。"""
        _x0, rects, visible, start = self._grid_geometry()
        out = []
        for offset, _entry in enumerate(visible):
            out.append((start + offset, rects[offset]))
        return out

    def _carried_slot_rects(self):
        """返回 ((item_id, prefix), rect) 列表（底部携带热键栏）。"""
        rects = []
        x0 = (cfg.SCREEN_WIDTH - (_GRID_COLS * _HOTBAR_SLOT + (_GRID_COLS - 1) * _GAP)) // 2
        grid = sui.draw_grid((x0, _HOTBAR_Y), _GRID_COLS, 1, _HOTBAR_SLOT, _GAP)
        for i, stack_key in enumerate(self.carried.keys()):
            if i < len(grid):
                rects.append((stack_key, grid[i]))
        return rects

    def _coin_slider_rect(self):
        """金币滑条轨道区域（水平居中）。"""
        cx = cfg.SCREEN_WIDTH // 2
        return pygame.Rect(cx - _COIN_TRACK_W // 2, _COIN_Y + 16,
                           _COIN_TRACK_W, _COIN_TRACK_H)

    def _coin_handle_rect(self):
        """金币滑条手柄位置，随当前携带金币比例移动。"""
        track = self._coin_slider_rect()
        if self.warehouse.coins <= 0:
            ratio = 0.0
        else:
            ratio = max(0.0, min(1.0, self.carried_coins / self.warehouse.coins))
        hx = track.x + int(round(ratio * track.width)) - _COIN_HANDLE_W // 2
        hy = track.centery - _COIN_HANDLE_H // 2
        return pygame.Rect(hx, hy, _COIN_HANDLE_W, _COIN_HANDLE_H)

    def _set_coins_from_mouse_x(self, mouse_x):
        """根据鼠标横向位置设置携带金币（按仓库金币比例）。"""
        if self.warehouse.coins <= 0:
            self.carried_coins = 0
            return
        track = self._coin_slider_rect()
        ratio = max(0.0, min(1.0, (mouse_x - track.x) / track.width))
        self.carried_coins = int(round(ratio * self.warehouse.coins))

    def _loadout_action_defs(self):
        """底部动作按钮定义：返回 [(索引, 按钮文字), ...]（1=N，2=Esc）。"""
        return [(1, "N：进入休整"), (2, "Esc：返回主菜单")]

    def _loadout_action_rects(self):
        """底部动作按钮的可点击区域（与 draw 使用同一布局）。"""
        labels = self._loadout_action_defs()
        gap = 14
        pad = 20
        widths = [self.game.font_medium.size(label)[0] + pad * 2 for _i, label in labels]
        total = sum(widths) + gap * (len(labels) - 1)
        x = (cfg.SCREEN_WIDTH - total) // 2
        y = _HINT_Y + 30
        rects = []
        for (i, _label), w in zip(labels, widths):
            rects.append((i, pygame.Rect(x, y, w, 30)))
            x += w + gap
        return rects

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
            if keys.get(pygame.K_LEFT, False) or keys.get(pygame.K_a, False):
                self.selected = max(0, (self.selected - 1) % len(self.entries))
            if keys.get(pygame.K_RIGHT, False) or keys.get(pygame.K_d, False):
                self.selected = min(len(self.entries) - 1, self.selected + 1)
            wheel_dir = self.game.wheel_direction()
            if wheel_dir:
                self.selected = (self.selected + wheel_dir) % len(self.entries)

            entry = self.entries[self.selected]
            item_id = entry["id"]
            prefix = entry.get("prefix")
            if self._confirm_pressed(keys):
                self._carry_one(item_id, prefix)
                self.carried_sel = None
            if keys.get(pygame.K_x, False) or keys.get(pygame.K_c, False):
                self._unload_one(item_id, prefix)
                if (item_id, prefix) not in self.carried:
                    self.carried_sel = None
        else:
            if self._confirm_pressed(keys):
                self._set_message("仓库为空，可直接出发（N）")

        # 调整携带金币（- / = 微调，主界面为可拖动滑条）
        if keys.get(pygame.K_MINUS, False) or keys.get(pygame.K_KP_MINUS, False):
            self.carried_coins = max(0, self.carried_coins - self.coin_step)
        if keys.get(pygame.K_EQUALS, False) or keys.get(pygame.K_KP_PLUS, False):
            self.carried_coins = min(self.warehouse.coins, self.carried_coins + self.coin_step)

        if keys.get(pygame.K_n, False):
            self._start_run()

        # 鼠标交互
        mp = self.game.mouse_pos
        clicked = self.game.mouse_clicked(1)
        # 金币滑条：按住左键后持续跟随鼠标拖动
        if self._coin_dragging:
            if self.game.mouse_buttons_held.get(1):
                self._set_coins_from_mouse_x(mp[0])
            else:
                self._coin_dragging = False
        elif clicked:
            for global_idx, rect in self._grid_item_rects():
                if rect.collidepoint(mp):
                    entry = self.entries[global_idx]
                    if global_idx == self.selected:
                        self._carry_one(entry["id"], entry.get("prefix"))
                    else:
                        self.selected = global_idx
                    self.carried_sel = None
                    return
            for stack_key, rect in self._carried_slot_rects():
                if rect.collidepoint(mp):
                    item_id, prefix = stack_key
                    if stack_key == self.carried_sel:
                        self._unload_one(item_id, prefix)
                        if stack_key not in self.carried:
                            self.carried_sel = None
                    else:
                        self.carried_sel = stack_key
                        # 同步网格选中，便于查看该物品信息
                        for gi, e in enumerate(self.entries):
                            if e["id"] == item_id and e.get("prefix") == prefix:
                                self.selected = gi
                                break
                    return
            track = self._coin_slider_rect()
            handle = self._coin_handle_rect()
            if track.collidepoint(mp) or handle.collidepoint(mp):
                self._set_coins_from_mouse_x(mp[0])
                self._coin_dragging = True
                return
            for i, rect in self._loadout_action_rects():
                if rect.collidepoint(mp):
                    if i == 1:
                        self._start_run()
                    else:
                        from src.ui.menu import MenuState
                        self.game.switch_state(MenuState(self.game))
                    return

    def _carry_one(self, item_id, prefix=None):
        entry = None
        for e in self.entries:
            if e["id"] == item_id and e.get("prefix") == prefix:
                entry = e
                break
        if entry is None:
            self._set_message("仓库中没有该物品")
            return
        key = (item_id, prefix)
        if self.carried.get(key, 0) < entry["count"]:
            self.carried[key] = self.carried.get(key, 0) + 1
        else:
            self._set_message("仓库中没有更多该物品")

    def _unload_one(self, item_id, prefix=None):
        key = (item_id, prefix)
        if self.carried.get(key, 0) > 0:
            self.carried[key] -= 1
            if self.carried[key] <= 0:
                self.carried.pop(key, None)
        else:
            self._set_message("未携带该物品")

    def _start_run(self):
        """从仓库扣减携带物资，写入本局背包并进入出发前休整界面。"""
        from src.systems.item_system import ItemInventory

        for (item_id, prefix), count in list(self.carried.items()):
            if count <= 0:
                continue
            self.warehouse.remove_item(item_id, count, prefix)
        self.warehouse.coins = max(0, self.warehouse.coins - self.carried_coins)
        save_warehouse(self.warehouse)

        run = ItemInventory()
        for (item_id, prefix), count in self.carried.items():
            if count <= 0:
                continue
            run.add_item(item_id, count, prefix)
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

    def _tooltip_lines(self, item, count=None, carried=0, prefix=None):
        """生成 SkyBlock 悬停提示框内容：[(文本, 颜色), ...]。"""
        if item is None:
            return []
        lines = []
        lines.append((self.warehouse_display_name(item.id, prefix), item.rarity_color))
        lines.append((item.rarity_display, item.rarity_color))
        lines.append((ITEM_TYPE_LABELS.get(item.item_type, item.item_type), cfg.COLOR_GRAY))
        stat_text = item.stat_text()
        if stat_text:
            lines.append((stat_text, cfg.COLOR_WHITE))
        for lore_line in (item.lore or []):
            lines.append((lore_line, cfg.COLOR_WHITE))
        if count is not None:
            lines.append((f"库存：{count}", cfg.COLOR_GRAY))
        if carried > 0:
            lines.append((f"已携带：{carried}", cfg.COLOR_GREEN))
        lines.append(("左键：携带   X/C：卸下", cfg.COLOR_GRAY))
        return lines

    def warehouse_display_name(self, item_id, prefix=None):
        return self.warehouse.get_display_name(item_id, prefix)

    def draw(self, screen):
        content = sui.draw_menu_frame(
            screen,
            title="仓库 · 出征准备",
            subtitle="选择携带物品与金币   ·   未携带的物资保留在仓库",
            coins=self.warehouse.coins,
            font_title=self.game.font_large,
            font_small=self.game.font_small,
        )

        # 深灰分区（内容层底板）：主网格区 + 底部携带/操作区
        grid_panel = pygame.Rect(content.x, content.y, content.width, 440)
        bottom_panel = pygame.Rect(content.x, 536, content.width,
                                   cfg.SCREEN_HEIGHT - 544)
        sui.draw_section(screen, grid_panel)
        sui.draw_section(screen, bottom_panel)

        # —— 仓库物品网格 ——
        x0, rects, visible, start = self._grid_geometry()
        if self.entries:
            # 先铺满整张空槽网格（结构感），再叠物品
            full_rects = sui.draw_grid((x0, _GRID_TOP), _GRID_COLS, _GRID_ROWS,
                                       _SLOT, _GAP)
            for rect in full_rects:
                sui.draw_slot(screen, rect)
            for offset, entry in enumerate(visible):
                idx = start + offset
                rect = rects[offset]
                selected = idx == self.selected
                hover = self.game.mouse_hover(rect)
                sui.draw_slot(screen, rect, selected=selected, hover=hover)
                item = entry["item"]
                draw_item_icon(screen, item.id, rect.x, rect.y, size=_SLOT, padding=4)
                sui.draw_count_badge(screen, rect, entry["count"], self.game.font_small)
                carried_n = self.carried.get((entry["id"], entry.get("prefix")), 0)
                if carried_n > 0:
                    # 已携带标记：左上角绿色小方块
                    badge = pygame.Rect(rect.x, rect.y, 14, 14)
                    pygame.draw.rect(screen, cfg.COLOR_GREEN, badge)
                    pygame.draw.rect(screen, (10, 60, 30), badge, 1)
                    self._draw_text(screen, str(carried_n), badge.centerx, badge.y - 2,
                                    (10, 40, 20), self.game.font_small)

        # 网格为空
        if not self.entries:
            self._draw_text(screen, "仓库为空，可直接出发（N）",
                            cfg.SCREEN_WIDTH // 2, content.y + 40,
                            sui.PANEL_TEXT_DIM, self.game.font_medium, align="center")

        # —— 底部：携带清单 / 金币 / 提示 ——
        self._draw_bottom(screen, content)

        # —— 悬停提示框 ——
        self._draw_hover_tooltip(screen)

        if self.message:
            self._draw_text(screen, self.message, cfg.SCREEN_WIDTH // 2,
                            cfg.SCREEN_HEIGHT - 88, cfg.COLOR_GREEN,
                            self.game.font_medium, align="center")

    def _draw_bottom(self, screen, content):
        # 左侧：携带清单标题 + 所选物品信息
        y = _HOTBAR_LABEL_Y
        sui.draw_text(screen, "携带清单", 34, y, sui.PANEL_TEXT, self.game.font_medium)
        if self.entries:
            entry = self.entries[self.selected]
            item = entry["item"]
            name = self.warehouse_display_name(entry["id"], entry.get("prefix"))
            self._draw_text(screen, f"选中：{name}", 34, y + 30,
                            item.rarity_color, self.game.font_small)
            self._draw_text(screen, f"数量：{entry['count']}", 34, y + 50,
                            sui.PANEL_TEXT_DIM, self.game.font_small)
        if not self.carried:
            self._draw_text(screen, "尚未携带物品", 34, y + 70,
                            sui.PANEL_TEXT_DIM, self.game.font_small)

        # 携带热键栏（空时也绘制一排空槽，便于视觉对齐）
        hot_x0 = (cfg.SCREEN_WIDTH - (_GRID_COLS * _HOTBAR_SLOT + (_GRID_COLS - 1) * _GAP)) // 2
        hot_rects = sui.draw_grid((hot_x0, _HOTBAR_Y), _GRID_COLS, 1, _HOTBAR_SLOT, _GAP)
        for i, rect in enumerate(hot_rects):
            if i < len(self.carried):
                stack_key = list(self.carried.keys())[i]
                item_id = stack_key[0]
                item = SKYBLOCK_ITEMS.get(item_id)
                if item:
                    selected = (stack_key == self.carried_sel)
                    sui.draw_slot(screen, rect, selected=selected,
                                  hover=self.game.mouse_hover(rect))
                    draw_item_icon(screen, item_id, rect.x, rect.y, size=_HOTBAR_SLOT, padding=4)
                    sui.draw_count_badge(screen, rect, self.carried[stack_key], self.game.font_small)
                else:
                    sui.draw_slot(screen, rect)
            else:
                sui.draw_slot(screen, rect)

        # 金币滑条
        self._draw_text(screen,
                        f"携带金币：{self.carried_coins} / 仓库：{self.warehouse.coins}",
                        cfg.SCREEN_WIDTH // 2, _COIN_Y + 4, cfg.COLOR_YELLOW,
                        self.game.font_medium, align="center")
        self._draw_coin_slider(screen)

        # 底部操作提示（纯文本）
        sui.draw_text(screen,
                      "↑↓←→ 选择   Enter/Z 携带   X/C 卸下   拖动滑条调整金币（-/= 微调）   鼠标：点击选中再次点击执行",
                      cfg.SCREEN_WIDTH // 2, _HINT_Y,
                      sui.PANEL_TEXT_DIM, self.game.font_small, align="center")
        # 底部动作按钮（N / Esc）
        action_labels = dict(self._loadout_action_defs())
        for i, rect in self._loadout_action_rects():
            sui.draw_button(screen, rect, action_labels[i], self.game.font_medium,
                            hover=self.game.mouse_hover(rect))

    def _draw_hover_tooltip(self, screen):
        mp = self.game.mouse_pos
        for global_idx, rect in self._grid_item_rects():
            if rect.collidepoint(mp):
                entry = self.entries[global_idx]
                carried = self.carried.get((entry["id"], entry.get("prefix")), 0)
                lines = self._tooltip_lines(entry["item"], entry["count"], carried,
                                            prefix=entry.get("prefix"))
                sui.draw_item_tooltip(screen, mp, lines, self.game.font_small)
                return
        for stack_key, rect in self._carried_slot_rects():
            if rect.collidepoint(mp):
                item_id = stack_key[0]
                item = SKYBLOCK_ITEMS.get(item_id)
                if item:
                    lines = self._tooltip_lines(item, self.carried[stack_key],
                                                self.carried[stack_key], prefix=stack_key[1])
                    sui.draw_item_tooltip(screen, mp, lines, self.game.font_small)
                    return

    def _draw_coin_slider(self, screen):
        """绘制金币滑条：凹陷轨道 + 金币黄进度 + Minecraft 风格手柄。"""
        track = self._coin_slider_rect()
        handle = self._coin_handle_rect()
        # 轨道：凹陷槽（上/左暗边，下/右高光）
        pygame.draw.rect(screen, sui.EDGE, track, 1)
        pygame.draw.rect(screen, sui.SLOT_DARK,
                         (track.x + 1, track.y + 1, track.w - 2, track.h - 2))
        pygame.draw.rect(screen, sui.SLOT_LIGHT,
                         (track.x + 1, track.bottom - 1 - 2, track.w - 2, 2))
        pygame.draw.rect(screen, sui.SLOT_LIGHT,
                         (track.right - 1 - 2, track.y + 1, 2, track.h - 2))
        # 已选比例：金币黄填充
        if self.warehouse.coins > 0:
            ratio = max(0.0, min(1.0, self.carried_coins / self.warehouse.coins))
        else:
            ratio = 0.0
        if ratio > 0:
            fill_w = max(1, int(track.width * ratio))
            pygame.draw.rect(screen, cfg.COLOR_YELLOW,
                             (track.x + 1, track.y + 2, fill_w, track.h - 4))
        # 手柄：上亮下暗渐变 + 拖动时金边
        top_c = (190, 190, 190)
        bot_c = (70, 70, 70)
        for y in range(handle.height):
            t = y / max(1, handle.height - 1)
            c = tuple(int(top_c[i] + (bot_c[i] - top_c[i]) * t) for i in range(3))
            pygame.draw.line(screen, c, (handle.x, handle.y + y), (handle.right, handle.y + y))
        pygame.draw.rect(screen, sui.EDGE, handle, 1)
        if self._coin_dragging or self.game.mouse_hover(handle):
            pygame.draw.rect(screen, sui.SELECT_COLOR, handle, 2)
        else:
            pygame.draw.rect(screen, sui.SLOT_LIGHT, handle, 1)
        # 手柄中心竖向指示线（贴合轨道）
        pygame.draw.line(screen, sui.SLOT_LIGHT,
                         (handle.centerx, track.y + 2), (handle.centerx, track.bottom - 2), 2)

    def _draw_text(self, screen, text, x, y, color, font, align="left", shadow=True):
        return sui.draw_text(screen, text, x, y, color, font,
                             shadow=shadow, align=align) + 6
