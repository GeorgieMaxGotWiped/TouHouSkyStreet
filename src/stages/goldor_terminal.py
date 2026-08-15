# -*- coding: utf-8 -*-
# 机械符「Terminal Pursuit」——Goldor 第一张符卡
# 方形环路 + 终端破解（Color / Order / Panes / Device）+ Goldor 单向追击
# 状态挂在 boss.goldor_terminal 上；绘制分两层：
#   Boss 本体之下：走廊 / 终端 / 追击标记（_gt_draw_boss_layer）
#   子弹之上：警告红幕 / 破解 GUI / 通关演出（_gt_draw_foreground）

import math
import os
import random

import pygame

from src.engine import settings as cfg
from src.entities.bullet import Bullet, create_bullet_angle

# ---------------------------------------------------------------------------
# 方形环路几何
# ---------------------------------------------------------------------------
GT_OUTER = 40.0
GT_OUTER_RIGHT = cfg.BATTLE_AREA_WIDTH - GT_OUTER      # 536
GT_OUTER_BOTTOM = cfg.BATTLE_AREA_HEIGHT - GT_OUTER    # 630
GT_IL, GT_IT, GT_IR, GT_IB = 168.0, 172.0, 408.0, 498.0
# 走廊中心线四角（顺时针：左下 -> 右下 -> 右上 -> 左上）
GT_BL = (104.0, 564.0)
GT_BR = (472.0, 564.0)
GT_TR = (472.0, 106.0)
GT_TL = (104.0, 106.0)
GT_SEGMENTS = ((GT_BL, GT_BR), (GT_BR, GT_TR), (GT_TR, GT_TL), (GT_TL, GT_BL))
GT_SEG_LEN = [math.hypot(p1[0] - p0[0], p1[1] - p0[1]) for p0, p1 in GT_SEGMENTS]
GT_SEG_START = []
_gt_acc = 0.0
for _gt_ln in GT_SEG_LEN:
    GT_SEG_START.append(_gt_acc)
    _gt_acc += _gt_ln
GT_LOOP_LEN = float(sum(GT_SEG_LEN))          # 1652
GT_GOLDOR_START_S = GT_LOOP_LEN - 560.0       # 开符时落后玩家 560px
GT_INTRO_FRAMES = 46
GT_TOUCH_RADIUS = 36.0
GT_CATCH_GAP = 20.0
GT_BARRIER_Y = 470.0                      # 左长廊封锁墙（阻断出生点直通 DEVICE 的捷径）
GT_HACK_APPROACH = 0.6
GT_HACK_RAMP_GAP = 850.0   # 破解中领先过远时加速阈值
GT_HACK_RAMP = 0.003       # 破解中加速斜率
GT_HACK_SPEED_MAX = 1.8    # 破解中速度上限                        # 破解中 Goldor 逼近速度（px/帧）
GT_RUN_SPEED = 1.5
GT_RUN_SPEED_MAX = 3.0
GT_RUN_RAMP_GAP = 900.0                       # 领先过远时加速
GT_RUN_RAMP = 0.0045
GT_ENTRANCE_Y0, GT_ENTRANCE_Y1 = 300.0, 396.0  # 最终入口在左墙中段
GT_CENTER = (288.0, 335.0)

# 终端（按顺时针路线依次出现；device 只出现一次且带特殊标记）
GT_TERMINAL_DEFS = (
    {"kind": "color",  "s": 70.0},    # 底 (174, 564)
    {"kind": "order",  "s": 200.0},   # 底 (304, 564)
    {"kind": "panes",  "s": 330.0},   # 底 (434, 564)
    {"kind": "color",  "s": 470.0},   # 右 (472, 462)
    {"kind": "order",  "s": 620.0},   # 右 (472, 312)
    {"kind": "panes",  "s": 770.0},   # 右 (472, 162)
    {"kind": "color",  "s": 870.0},   # 顶 (428, 106)
    {"kind": "order",  "s": 1000.0},  # 顶 (298, 106)
    {"kind": "device", "s": 1320.0, "final": True},  # 左·最终 (104, 232)
)

GT_COLOR_PALETTE = (
    ("红", (226, 78, 82)),
    ("橙", (235, 150, 70)),
    ("黄", (238, 212, 86)),
    ("绿", (96, 205, 110)),
    ("青", (86, 205, 215)),
    ("蓝", (88, 120, 232)),
    ("紫", (178, 96, 224)),
    ("粉", (232, 120, 190)),
    ("白", (226, 226, 226)),
)

_CHEST_SLOT = 44
_DEVICE_N = 5
_DEVICE_CELL = 52
_DEVICE_GAP = 8
# 键盘友好布局：各类谜题独立行列数（方向键移动光标 / Z 确认）
_COLOR_COLS, _COLOR_ROWS = 5, 2       # 10 格
_ORDER_COLS, _ORDER_ROWS = 6, 1       # 方向序列 6 格
_PANES_COLS, _PANES_ROWS = 5, 3       # 15 格
_GT_PANEL_TOP = 42                     # 标题区高度
_GT_PANEL_BOTTOM = 94                  # 提示/操作/逼近条 区高度
_DIR_VECS = ((-1, 0), (0, 1), (1, 0), (0, -1))   # 上 右 下 左
_DIR_ARROWS = ("▲", "▶", "▼", "◀")

_font_cache = {}


def _get_font(size):
    if size not in _font_cache:
        from src.engine.fallback_font import FallbackFont
        primary = os.path.join(cfg.ASSETS_DIR, "fonts", "font1.ttf")
        fallback = os.path.join(cfg.ASSETS_DIR, "fonts", "font2.otf")
        _font_cache[size] = FallbackFont(primary, fallback, size)
    return _font_cache[size]


def _lighten(color, amount):
    return tuple(min(255, int(c) + amount) for c in color)


def _darken(color, amount):
    return tuple(max(0, int(c) - amount) for c in color)


# ---------------------------------------------------------------------------
# 环路几何工具
# ---------------------------------------------------------------------------
def _gt_path_point(s):
    s = s % GT_LOOP_LEN
    for i, (p0, p1) in enumerate(GT_SEGMENTS):
        seg = GT_SEG_LEN[i]
        if s <= seg:
            t = s / seg
            return (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)
        s -= seg
    return GT_BL


def _gt_project_s(x, y):
    best_s, best_d2 = 0.0, float("inf")
    for i, (p0, p1) in enumerate(GT_SEGMENTS):
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        denom = dx * dx + dy * dy
        if denom <= 0:
            continue
        t = ((x - p0[0]) * dx + (y - p0[1]) * dy) / denom
        t = max(0.0, min(1.0, t))
        px, py = p0[0] + dx * t, p0[1] + dy * t
        d2 = (x - px) * (x - px) + (y - py) * (y - py)
        if d2 < best_d2:
            best_d2 = d2
            best_s = GT_SEG_START[i] + t * GT_SEG_LEN[i]
    return best_s % GT_LOOP_LEN


def _gt_path_dist(a, b):
    return (b - a) % GT_LOOP_LEN


def _gt_clamp_player(x, y, state):
    x = max(GT_OUTER, min(GT_OUTER_RIGHT, x))
    y = max(GT_OUTER, min(GT_OUTER_BOTTOM, y))
    if state.get("center_open"):
        if GT_ENTRANCE_Y0 <= y <= GT_ENTRANCE_Y1 and x <= GT_IL:
            return x, y
        if GT_IL <= x <= GT_IR and GT_IT <= y <= GT_IB:
            return x, y
    if GT_IL < x < GT_IR and GT_IT < y < GT_IB:
        dl = x - GT_IL
        dr = GT_IR - x
        dt = y - GT_IT
        db = GT_IB - y
        m = min(dl, dr, dt, db)
        if m == dl:
            x = GT_IL - 4.0
        elif m == dr:
            x = GT_IR + 4.0
        elif m == dt:
            y = GT_IT - 4.0
        else:
            y = GT_IB + 4.0
    # 封锁墙：出生点无法向上直通 DEVICE，只能顺时针绕行
    if (not state.get("center_open") and x < GT_IL
            and y < GT_BARRIER_Y and state.get("last_player_y") is not None
            and state["last_player_y"] > GT_BARRIER_Y + 6.0):
        y = GT_BARRIER_Y
    return x, y


# ---------------------------------------------------------------------------
# 状态初始化
# ---------------------------------------------------------------------------
def _gt_init(boss):
    terminals = []
    for i, spec in enumerate(GT_TERMINAL_DEFS):
        x, y = _gt_path_point(spec["s"])
        terminals.append({
            "idx": i,
            "kind": spec["kind"],
            "final": spec.get("final", False),
            "s": spec["s"],
            "x": x,
            "y": y,
            "solved": False,
        })
    # 符卡期间 Goldor 使用更小立绘，避免占满走廊
    boss._spell_sprite_restore = (boss.sprite_path, boss.sprite_height)
    boss.sprite_height = 64
    boss.goldor_terminal = {
        "timer": 0,
        "terminals": terminals,
        "goldor_s": GT_GOLDOR_START_S,
        "player_s": 0.0,
        "intro_frames": 0,
        "hacking": None,
        "puzzle": None,
        "cooldown": 0,
        "caught_active": False,
        "caught_frames": 0,
        "goldor_pause": 0,
        "input_locked": False,
        "teleport_to": (GT_BL[0], GT_BL[1]),
        "last_player_x": None,
        "last_player_y": None,
        "solved_count": 0,
        "center_open": False,
        "entering_center": False,
        "enter_timer": 0,
        "spell_done": False,
        "warning": 0.0,
        "spawn_timer": 0,
        "fx": [],
        "banner": None,
        "mouse_clicked": None,
        "mouse_battle": None,
        "keys_just_pressed": None,
    }


# ---------------------------------------------------------------------------
# Goldor 追击
# ---------------------------------------------------------------------------
def _gt_goldor_speed(state, gap):
    if state["hacking"] is not None:
        speed = GT_HACK_APPROACH
        if gap > GT_HACK_RAMP_GAP:
            speed += (gap - GT_HACK_RAMP_GAP) * GT_HACK_RAMP
        return min(speed, GT_HACK_SPEED_MAX)
    speed = GT_RUN_SPEED
    if gap > GT_RUN_RAMP_GAP:
        speed += (gap - GT_RUN_RAMP_GAP) * GT_RUN_RAMP
    return min(GT_RUN_SPEED_MAX, speed)


def _gt_on_caught(state):
    state["hacking"] = None
    state["puzzle"] = None
    state["input_locked"] = False
    state["cooldown"] = 50
    state["caught_active"] = True
    state["caught_frames"] = 30
    state["goldor_pause"] = 110
    # 击退 Goldor 到当前所在长廊段首（拐角起点）
    _gs = state["goldor_s"] % GT_LOOP_LEN
    _seg = 0.0
    for _st in GT_SEG_START:
        if _gs >= _st:
            _seg = _st
    state["goldor_s"] = _seg
    _sx0, _sy0 = _gt_path_point(_seg)
    state["fx"].append({
        "kind": "ring", "x": _sx0, "y": _sy0, "age": 0, "max_age": 34,
        "color": (255, 150, 90), "radius": 26,
    })
    state["fx"].append({
        "kind": "shock", "x": None, "y": None, "age": 0, "max_age": 26,
        "color": (255, 70, 60), "radius": 20,
    })


# ---------------------------------------------------------------------------
# 破解流程
# ---------------------------------------------------------------------------
def _gt_start_hack(state, bullet_manager, idx):
    t = state["terminals"][idx]
    state["hacking"] = idx
    state["puzzle"] = _make_puzzle(t["kind"])
    state["input_locked"] = True
    state["teleport_to"] = (t["x"], t["y"])
    state["cooldown"] = 0
    state["fx"].append({
        "kind": "ring", "x": t["x"], "y": t["y"], "age": 0, "max_age": 24,
        "color": (110, 230, 255), "radius": 14,
    })
    if bullet_manager is not None:
        bullet_manager.cancel_all_enemy_bullets()


def _gt_end_hack(state, bullet_manager, solved):
    idx = state["hacking"]
    t = state["terminals"][idx] if idx is not None else None
    state["hacking"] = None
    state["puzzle"] = None
    state["input_locked"] = False
    state["cooldown"] = 45
    if solved and t is not None:
        t["solved"] = True
        state["solved_count"] += 1
        color = (120, 255, 170) if not t["final"] else (255, 225, 110)
        state["fx"].append({
            "kind": "ring", "x": t["x"], "y": t["y"], "age": 0, "max_age": 30,
            "color": color, "radius": 18,
        })
        if t["final"]:
            state["center_open"] = True
            state["banner"] = ("中央入口已开启——进入中央完成符卡！", 200)
            state["fx"].append({
                "kind": "ring", "x": GT_CENTER[0], "y": GT_CENTER[1],
                "age": 0, "max_age": 60, "color": (255, 225, 110), "radius": 24,
            })


def _gt_update_hack(state, bullet_manager, player_x, player_y):
    idx = state["hacking"]
    if idx is None:
        # 开场传送/入场期间不触发破解，避免玩家旧位置误触终端
        if (state["timer"] < 50 or state["cooldown"] > 0
                or state.get("entering_center") or state.get("spell_done")):
            return
        for t in state["terminals"]:
            if t["solved"]:
                continue
            if math.hypot(player_x - t["x"], player_y - t["y"]) <= GT_TOUCH_RADIUS:
                _gt_start_hack(state, bullet_manager, t["idx"])
                return
        return

    puzzle = state["puzzle"]
    if puzzle is None:
        return
    puzzle.update()
    keys = state.get("keys_just_pressed") or {}
    if keys.get(pygame.K_ESCAPE):
        _gt_end_hack(state, bullet_manager, solved=False)
        return
    clicked = state.get("mouse_clicked")
    if clicked:
        puzzle.handle_click(clicked[0], clicked[1])
    elif keys:
        puzzle.handle_key(keys)
    if puzzle.complete:
        _gt_end_hack(state, bullet_manager, solved=True)


def _gt_update_center(state, player_x, player_y, boss, bullet_manager):
    if state.get("spell_done"):
        return
    if state.get("entering_center"):
        state["enter_timer"] += 1
        if state["enter_timer"] >= 70:
            state["spell_done"] = True
            boss.goldor_terminal = None
            boss._end_spell()
        return
    if state.get("center_open"):
        inside = (GT_IL <= player_x <= GT_IR and GT_IT <= player_y <= GT_IB)
        if inside:
            state["entering_center"] = True
            state["enter_timer"] = 0
            state["input_locked"] = True
            state["teleport_to"] = GT_CENTER
            state["goldor_pause"] = 10 ** 6
            state["banner"] = None
            state["fx"].append({
                "kind": "ring", "x": GT_CENTER[0], "y": GT_CENTER[1],
                "age": 0, "max_age": 70, "color": (255, 235, 140), "radius": 26,
            })
            if bullet_manager is not None:
                bullet_manager.cancel_all_enemy_bullets()


# ---------------------------------------------------------------------------
# 走廊弹幕：墙壁骨弹 + 转角金属弹
# ---------------------------------------------------------------------------
def _gt_spawn_bone(bullet_manager, side, track, lane):
    """side: 0顶 1底 2左 3右；从一侧墙横穿走廊。"""
    if side == 0:      # 顶墙 -> 向下
        w = GT_IT - GT_OUTER
        x = GT_OUTER + track * (GT_OUTER_RIGHT - GT_OUTER)
        y = GT_OUTER - 4.0 + lane * w / 3.0 + w / 6.0
        angle = math.pi / 2
        cross = w
    elif side == 1:    # 底墙 -> 向上
        w = GT_OUTER_BOTTOM - GT_IB
        x = GT_OUTER + track * (GT_OUTER_RIGHT - GT_OUTER)
        y = GT_OUTER_BOTTOM + 4.0 - (lane * w / 3.0 + w / 6.0)
        angle = -math.pi / 2
        cross = w
    elif side == 2:    # 左墙 -> 向右
        w = GT_IL - GT_OUTER
        x = GT_OUTER - 4.0 + lane * w / 3.0 + w / 6.0
        y = GT_IT + track * (GT_IB - GT_IT)
        angle = 0.0
        cross = w
    else:              # 右墙 -> 向左
        w = GT_OUTER_RIGHT - GT_IR
        x = GT_OUTER_RIGHT + 4.0 - (lane * w / 3.0 + w / 6.0)
        y = GT_IT + track * (GT_IB - GT_IT)
        angle = math.pi
        cross = w
    speed = 2.4
    lifetime = int(cross / speed) + 14
    bullet = create_bullet_angle(x, y, angle, speed,
                                 Bullet.TYPE_KNIFE, radius=2.6,
                                 color=(238, 230, 206), lifetime=lifetime)
    bullet_manager.add_enemy_bullet(bullet)


_CORNER_FANS = (
    ((40.0, 40.0), (0.39, 0.79, 1.18)),       # 外 左上
    ((536.0, 40.0), (1.96, 2.36, 2.75)),      # 外 右上
    ((536.0, 630.0), (3.93, 4.32, 4.71)),     # 外 右下
    ((40.0, 630.0), (5.10, 5.50, 5.89)),      # 外 左下
    ((168.0, 172.0), (3.93, 4.32, 4.71)),     # 内 左上
    ((408.0, 172.0), (5.50, 5.89, 0.0)),      # 内 右上
    ((408.0, 498.0), (0.39, 0.79, 1.18)),     # 内 右下
    ((168.0, 498.0), (1.96, 2.36, 2.75)),     # 内 左下
)


def _gt_spawn_corner_metal(bullet_manager, state):
    corners = random.sample(range(8), k=3 if state["solved_count"] >= 2 else 2)
    for ci in corners:
        (cx, cy), fan = _CORNER_FANS[ci]
        for angle in fan:
            bullet = create_bullet_angle(cx, cy, angle, 2.6,
                                         Bullet.TYPE_CIRCLE, radius=3.0,
                                         color=(166, 172, 184), lifetime=340)
            bullet_manager.add_enemy_bullet(bullet)


def _gt_spawn_corridor_bullets(state, bullet_manager):
    solved = state["solved_count"]
    state["spawn_timer"] += 1
    interval = max(34, 62 - solved * 7)
    if state["spawn_timer"] % interval == 0:
        sides = random.sample(range(4), k=2 if solved < 2 else 3)
        for side in sides:
            track = random.uniform(0.14, 0.86)
            lane = random.randint(0, 2)
            _gt_spawn_bone(bullet_manager, side, track, lane)
            if solved >= 3 and lane < 2:
                _gt_spawn_bone(bullet_manager, side, track, lane + 1)
    metal_interval = max(46, 76 - solved * 8)
    if state["spawn_timer"] % metal_interval == 0:
        _gt_spawn_corner_metal(bullet_manager, state)


# ---------------------------------------------------------------------------
# 破解谜题（箱子 GUI）
# ---------------------------------------------------------------------------
def _chest_panel_rect(cols, rows, slot_w=_CHEST_SLOT, slot_gap=0):
    w = cols * slot_w + (cols - 1) * slot_gap + 24
    slots_bottom = _GT_PANEL_TOP + rows * slot_w + (rows - 1) * slot_gap
    h = slots_bottom + _GT_PANEL_BOTTOM
    cx = cfg.BATTLE_AREA_WIDTH / 2
    cy = cfg.BATTLE_AREA_HEIGHT * 0.46
    return pygame.Rect(int(cx - w / 2), int(cy - h / 2), w, h)


class _ChestPuzzle:
    """键盘操作箱子面板基础类：方向键移动光标 / Z 确认 / ESC 放弃"""
    kind = "?"

    def __init__(self, cols, rows):
        self.complete = False
        self.flash_idx = -1
        self.flash_timer = 0
        self.cursor = 0
        self.cols = cols
        self.rows = rows
        self.panel = _chest_panel_rect(cols, rows)
        self.title = ""
        self.hint = ""
        self.controls = "←→↑↓ 移动　Z 选择　ESC 放弃"

    def slot_count(self):
        return self.cols * self.rows

    def slot_rect(self, idx):
        col = idx % self.cols
        row = idx // self.cols
        x = self.panel.x + 12 + col * _CHEST_SLOT
        y = self.panel.y + _GT_PANEL_TOP + row * _CHEST_SLOT
        return pygame.Rect(x, y, _CHEST_SLOT, _CHEST_SLOT)

    def hit_slot(self, bx, by):
        for i in range(self.slot_count()):
            if self.slot_rect(i).collidepoint(bx, by):
                return i
        return -1

    def handle_click(self, bx, by):
        """纯键盘谜题可留空；需要点击的谜题自行覆写。"""
        return

    def handle_key(self, keys):
        n = self.slot_count()
        cols = self.cols
        if keys.get(pygame.K_LEFT):
            if self.cursor % cols == 0:
                self.cursor += cols - 1
            else:
                self.cursor -= 1
        elif keys.get(pygame.K_RIGHT):
            if self.cursor % cols == cols - 1:
                self.cursor -= cols - 1
            else:
                self.cursor += 1
        elif keys.get(pygame.K_UP):
            self.cursor = (self.cursor - cols) % n
        elif keys.get(pygame.K_DOWN):
            self.cursor = (self.cursor + cols) % n
        elif keys.get(pygame.K_z) or keys.get(pygame.K_RETURN) or keys.get(pygame.K_SPACE):
            rect = self.slot_rect(self.cursor)
            self.handle_click(rect.centerx, rect.centery)

    def update(self):
        if self.flash_timer > 0:
            self.flash_timer -= 1

    def draw(self, screen, ox, oy, warn):
        rect = self.panel
        px, py = rect.x + ox, rect.y + oy
        panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        panel.fill((14, 16, 32, 242))
        screen.blit(panel, (px, py))
        pygame.draw.rect(screen, (130, 128, 160), (px, py, rect.w, rect.h), 2)
        title_font = _get_font(18)
        t = title_font.render(self.title, True, (255, 228, 120))
        screen.blit(t, (px + (rect.w - t.get_width()) // 2, py + 8))
        self._draw_slots(screen, px, py)
        hint_font = _get_font(14)
        h = hint_font.render(self.hint, True, (196, 206, 230))
        screen.blit(h, (px + 14, py + rect.h - 84))
        ctrl_font = _get_font(13)
        c = ctrl_font.render(self.controls, True, (150, 158, 190))
        screen.blit(c, (px + 14, py + rect.h - 62))
        bar_x = px + 14
        bar_y = py + rect.h - 22
        bar_w = rect.w - 28
        pygame.draw.rect(screen, (70, 74, 96), (bar_x, bar_y, bar_w, 10))
        fill = int(bar_w * max(0.0, min(1.0, warn)))
        if fill > 0:
            col = (255, 120, 70) if warn < 0.5 else (255, 60, 50)
            pygame.draw.rect(screen, col, (bar_x, bar_y, fill, 10))
        lbl = hint_font.render("GOLDOR 逼近" if warn > 0.15 else "GOLDOR", True, (255, 120, 90))
        screen.blit(lbl, (px + rect.w - 14 - lbl.get_width(), bar_y - 18))

    def _draw_slot_frame(self, screen, x, y, selected=False, flash=False):
        pygame.draw.rect(screen, (58, 56, 74), (x, y, _CHEST_SLOT, _CHEST_SLOT))
        pygame.draw.rect(screen, (122, 118, 144), (x, y, _CHEST_SLOT, _CHEST_SLOT), 1)
        if selected:
            pygame.draw.rect(screen, (255, 235, 150), (x - 2, y - 2,
                                                      _CHEST_SLOT + 4, _CHEST_SLOT + 4), 2)
        if flash:
            ov = pygame.Surface((_CHEST_SLOT, _CHEST_SLOT), pygame.SRCALPHA)
            ov.fill((255, 60, 60, 150))
            screen.blit(ov, (x, y))

    def _draw_item_square(self, screen, x, y, color, inset=5, size=_CHEST_SLOT):
        pygame.draw.rect(screen, _darken(color, 60),
                         (x + inset, y + inset, size - inset * 2, size - inset * 2))
        pygame.draw.rect(screen, color,
                         (x + inset, y + inset, size - inset * 2, size - inset * 2), 0)
        pygame.draw.rect(screen, _lighten(color, 70),
                         (x + inset, y + inset, size - inset * 2, 3))

    def _draw_slots(self, screen, px, py):
        raise NotImplementedError


class ColorPuzzle(_ChestPuzzle):
    kind = "color"

    def __init__(self):
        super().__init__(_COLOR_COLS, _COLOR_ROWS)
        self.target_idx = random.randrange(len(GT_COLOR_PALETTE))
        name, _col = GT_COLOR_PALETTE[self.target_idx]
        count = random.randint(3, 5)
        self.items = [self.target_idx] * count
        while len(self.items) < self.slot_count():
            self.items.append(random.randrange(len(GT_COLOR_PALETTE)))
        random.shuffle(self.items)
        self.matched = [False] * self.slot_count()
        self.title = "COLOR 终端 · 选中所有「" + name + "」色"
        self.hint = "目标颜色：" + name + "（" + str(count) + " 个）"

    def handle_click(self, bx, by):
        idx = self.hit_slot(bx, by)
        if idx < 0 or self.matched[idx]:
            return
        if self.items[idx] == self.target_idx:
            self.matched[idx] = True
            if all(self.matched[i] for i in range(self.slot_count())
                   if self.items[i] == self.target_idx):
                self.complete = True
        else:
            self.flash_idx = idx
            self.flash_timer = 10

    def _draw_slots(self, screen, px, py):
        for i in range(self.slot_count()):
            rect = self.slot_rect(i)
            x = rect.x + px - self.panel.x
            y = rect.y + py - self.panel.y
            selected = i == self.cursor
            flash = i == self.flash_idx and self.flash_timer > 0
            self._draw_slot_frame(screen, x, y, selected, flash)
            color = GT_COLOR_PALETTE[self.items[i]][1]
            self._draw_item_square(screen, x, y, color)
            if self.matched[i]:
                ov = pygame.Surface((_CHEST_SLOT, _CHEST_SLOT), pygame.SRCALPHA)
                ov.fill((20, 40, 24, 130))
                screen.blit(ov, (x, y))
                pygame.draw.rect(screen, (140, 255, 160), (x, y, _CHEST_SLOT, _CHEST_SLOT), 2)


class DirectionPuzzle(_ChestPuzzle):
    """ORDER 终端：按显示的箭头序列依次输入方向键（无需光标导航）。"""
    kind = "order"

    def __init__(self):
        super().__init__(_ORDER_COLS, _ORDER_ROWS)
        self.sequence = [random.randrange(4) for _ in range(6)]
        self.input_idx = 0
        self.title = "ORDER 终端 · 按箭头顺序输入方向键"
        self.hint = "序列：" + "".join(_DIR_ARROWS[d] for d in self.sequence)
        self.controls = "按对应方向键输入　ESC 放弃"

    def handle_key(self, keys):
        if self.complete:
            return
        key_dir = None
        if keys.get(pygame.K_UP):
            key_dir = 0
        elif keys.get(pygame.K_RIGHT):
            key_dir = 1
        elif keys.get(pygame.K_DOWN):
            key_dir = 2
        elif keys.get(pygame.K_LEFT):
            key_dir = 3
        if key_dir is None:
            return
        if key_dir == self.sequence[self.input_idx]:
            self.input_idx += 1
            if self.input_idx >= len(self.sequence):
                self.complete = True
        else:
            self.flash_idx = self.input_idx
            self.flash_timer = 10

    def _draw_slots(self, screen, px, py):
        for i, d in enumerate(self.sequence):
            rect = self.slot_rect(i)
            x = rect.x + px - self.panel.x
            y = rect.y + py - self.panel.y
            done = i < self.input_idx
            active = i == self.input_idx
            arrow_font = _get_font(26)
            pygame.draw.rect(screen, (58, 56, 74), (x, y, _CHEST_SLOT, _CHEST_SLOT))
            pygame.draw.rect(screen, (122, 118, 144), (x, y, _CHEST_SLOT, _CHEST_SLOT), 1)
            if done:
                pygame.draw.rect(screen, (26, 74, 58), (x, y, _CHEST_SLOT, _CHEST_SLOT))
                pygame.draw.rect(screen, (90, 220, 140), (x, y, _CHEST_SLOT, _CHEST_SLOT), 2)
                t = arrow_font.render(_DIR_ARROWS[d], True, (170, 255, 190))
                screen.blit(t, (x + (_CHEST_SLOT - t.get_width()) // 2,
                                y + (_CHEST_SLOT - t.get_height()) // 2))
            elif active:
                pygame.draw.rect(screen, (255, 235, 150), (x - 2, y - 2,
                                                           _CHEST_SLOT + 4, _CHEST_SLOT + 4), 2)
                t = arrow_font.render(_DIR_ARROWS[d], True, (255, 245, 180))
                screen.blit(t, (x + (_CHEST_SLOT - t.get_width()) // 2,
                                y + (_CHEST_SLOT - t.get_height()) // 2))
            else:
                t = arrow_font.render(_DIR_ARROWS[d], True, (150, 158, 190))
                screen.blit(t, (x + (_CHEST_SLOT - t.get_width()) // 2,
                                y + (_CHEST_SLOT - t.get_height()) // 2))
            if i == self.flash_idx and self.flash_timer > 0:
                ov = pygame.Surface((_CHEST_SLOT, _CHEST_SLOT), pygame.SRCALPHA)
                ov.fill((255, 60, 60, 150))
                screen.blit(ov, (x, y))


class PanesPuzzle(_ChestPuzzle):
    kind = "panes"

    def __init__(self):
        super().__init__(_PANES_COLS, _PANES_ROWS)
        self.red = [True] * 15
        for _ in range(random.randint(6, 8)):
            self.red[random.randrange(15)] = False
        self.title = "PANES 终端 · 按 Z 把红色全部变绿"
        self.hint = ""

    def _red_count(self):
        return sum(1 for r in self.red if r)

    def handle_click(self, bx, by):
        idx = self.hit_slot(bx, by)
        if idx < 0 or idx >= self.slot_count():
            return
        self.red[idx] = not self.red[idx]
        if not any(self.red):
            self.complete = True

    def _draw_slots(self, screen, px, py):
        for i in range(self.slot_count()):
            rect = self.slot_rect(i)
            x = rect.x + px - self.panel.x
            y = rect.y + py - self.panel.y
            selected = i == self.cursor
            flash = i == self.flash_idx and self.flash_timer > 0
            self._draw_slot_frame(screen, x, y, selected, flash)
            if self.red[i]:
                self._draw_item_square(screen, x, y, (214, 70, 66), inset=8)
            else:
                self._draw_item_square(screen, x, y, (90, 205, 110), inset=8)
        self.hint = "剩余红色：" + str(self._red_count())


def _gt_device_trace(state_grid):
    """从绿色羊毛(0,0)沿箭头行走；返回 (trace, reached_red)。
    trace 为依次经过的格子；越界或重复经过视为未连通。"""
    n = len(state_grid)
    visited = [[False] * n for _ in range(n)]
    trace = [(0, 0)]
    visited[0][0] = True
    r, c = 0, 0
    for _ in range(n * n + 2):
        dr, dc = _DIR_VECS[state_grid[r][c]]
        nr, nc = r + dr, c + dc
        if not (0 <= nr < n and 0 <= nc < n) or visited[nr][nc]:
            return trace, False
        r, c = nr, nc
        trace.append((r, c))
        if (r, c) == (n - 1, n - 1):
            return trace, True
    return trace, False


class DevicePuzzle(_ChestPuzzle):
    """DEVICE 终端：箭头随机，旋转箭头使从绿色沿箭头方向能到达红色即成功。"""
    kind = "device"

    def __init__(self):
        super().__init__(_DEVICE_N, _DEVICE_N)
        n = _DEVICE_N
        self.current = [[random.randrange(4) for _ in range(n)] for _ in range(n)]
        # 绿色羊毛固定朝右作为起点，红色羊毛为终点（两者均不可旋转）
        self.fixed = [[False] * n for _ in range(n)]
        self.fixed[0][0] = True
        self.fixed[n - 1][n - 1] = True
        self.current[0][0] = 1
        self.trace = [(0, 0)]
        self.title = "DEVICE 终端 · 旋转箭头连通 绿→红"
        self.hint = "从绿色沿箭头能走到红色即成功"
        self.controls = "←→↑↓ 移动　Z 旋转　ESC 放弃"
        self.panel = _chest_panel_rect(n, n, slot_w=_DEVICE_CELL,
                                       slot_gap=_DEVICE_GAP)
        self.check_path()

    def slot_rect(self, idx):
        r, c = divmod(idx, self.cols)
        x = self.panel.x + 12 + c * (_DEVICE_CELL + _DEVICE_GAP)
        y = self.panel.y + 42 + r * (_DEVICE_CELL + _DEVICE_GAP)
        return pygame.Rect(x, y, _DEVICE_CELL, _DEVICE_CELL)

    def cell_of(self, bx, by):
        for r in range(self.rows):
            for c in range(self.cols):
                if self.slot_rect(r * self.cols + c).collidepoint(bx, by):
                    return r, c
        return None

    def check_path(self):
        """从绿色行走：到达红色返回 True，并更新足迹与提示。"""
        trace, reached = _gt_device_trace(self.current)
        self.trace = trace
        if reached:
            self.complete = True
            self.hint = "已连通 绿→红！"
            return True
        self.complete = False
        self.hint = ("绿→红：走到 " + str(len(trace)) + " / "
                     + str(self.rows * self.cols) + " 格")
        return False

    def handle_click(self, bx, by):
        cell = self.cell_of(bx, by)
        if cell is None:
            return
        r, c = cell
        if self.fixed[r][c]:
            return
        self.current[r][c] = (self.current[r][c] + 1) % 4
        self.check_path()

    def _draw_slots(self, screen, px, py):
        trace_set = set(self.trace)
        for r in range(self.rows):
            for c in range(self.cols):
                rect = self.slot_rect(r * self.cols + c)
                x = rect.x + px - self.panel.x
                y = rect.y + py - self.panel.y
                selected = (r * self.cols + c) == self.cursor
                on_path = (r, c) in trace_set
                if (r, c) == (0, 0):
                    pygame.draw.rect(screen, (34, 90, 46),
                                     (x, y, _DEVICE_CELL, _DEVICE_CELL))
                    pygame.draw.rect(screen, (90, 215, 110),
                                     (x + 4, y + 4, _DEVICE_CELL - 8, _DEVICE_CELL - 8))
                    arrow_font = _get_font(22)
                    t = arrow_font.render("▶", True, (205, 255, 215))
                    screen.blit(t, (x + (_DEVICE_CELL - t.get_width()) // 2,
                                    y + (_DEVICE_CELL - t.get_height()) // 2))
                elif (r, c) == (self.rows - 1, self.cols - 1):
                    pygame.draw.rect(screen, (96, 32, 28),
                                     (x, y, _DEVICE_CELL, _DEVICE_CELL))
                    pygame.draw.rect(screen, (225, 80, 70),
                                     (x + 4, y + 4, _DEVICE_CELL - 8, _DEVICE_CELL - 8))
                else:
                    pygame.draw.rect(screen, (96, 70, 44),
                                     (x, y, _DEVICE_CELL, _DEVICE_CELL))
                    pygame.draw.rect(screen, (140, 108, 70),
                                     (x, y, _DEVICE_CELL, _DEVICE_CELL), 1)
                    inner = 6
                    pygame.draw.rect(screen, (26, 28, 40),
                                     (x + inner, y + inner,
                                      _DEVICE_CELL - inner * 2,
                                      _DEVICE_CELL - inner * 2))
                    if on_path:
                        glow = pygame.Surface((_DEVICE_CELL, _DEVICE_CELL), pygame.SRCALPHA)
                        glow.fill((120, 235, 235, 70))
                        screen.blit(glow, (x, y))
                    di = self.current[r][c]
                    arrow_font = _get_font(30)
                    t = arrow_font.render(_DIR_ARROWS[di], True,
                                          (190, 255, 255) if on_path else (240, 244, 255))
                    screen.blit(t, (x + (_DEVICE_CELL - t.get_width()) // 2,
                                    y + (_DEVICE_CELL - t.get_height()) // 2))
                if selected:
                    pygame.draw.rect(screen, (255, 235, 150), (x - 2, y - 2,
                                                               _DEVICE_CELL + 4,
                                                               _DEVICE_CELL + 4), 2)


def _make_puzzle(kind):
    if kind == "color":
        return ColorPuzzle()
    if kind == "order":
        return DirectionPuzzle()
    if kind == "panes":
        return PanesPuzzle()
    if kind == "device":
        return DevicePuzzle()
    return ColorPuzzle()


# ---------------------------------------------------------------------------
# 符卡主函数
# ---------------------------------------------------------------------------
def spell_goldor_terminal_pursuit(boss, bullet_manager, timer, dt,
                                  player_x=0, player_y=0):
    state = getattr(boss, "goldor_terminal", None)
    if state is None:
        _gt_init(boss)
        state = boss.goldor_terminal
    if state.get("spell_done"):
        return
    state["timer"] += 1

    player_s = _gt_project_s(player_x, player_y)
    state["player_s"] = player_s
    gap = _gt_path_dist(state["goldor_s"], player_s)

    state["last_player_x"], state["last_player_y"] = player_x, player_y

    # Goldor 沿环路单向追击
    if state["goldor_pause"] > 0:
        state["goldor_pause"] -= 1
    elif not state.get("entering_center"):
        speed = _gt_goldor_speed(state, gap)
        state["goldor_s"] = (state["goldor_s"] + speed) % GT_LOOP_LEN

    gx, gy = _gt_path_point(state["goldor_s"])
    if state["intro_frames"] < GT_INTRO_FRAMES:
        k = state["intro_frames"] / GT_INTRO_FRAMES
        sx0, sy0 = cfg.BATTLE_AREA_WIDTH / 2, 120.0
        gx = sx0 + (gx - sx0) * k
        gy = sy0 + (gy - sy0) * k
        state["intro_frames"] += 1
    boss.x, boss.y = gx, gy
    boss.target_x, boss.target_y = gx, gy

    state["warning"] = max(0.0, 1.0 - gap / 240.0) if gap < 240.0 else 0.0

    close = (gap < GT_CATCH_GAP
             or math.hypot(player_x - gx, player_y - gy) < 34.0)
    if (close and state["goldor_pause"] <= 0
            and not state.get("entering_center") and not state.get("spell_done")):
        _gt_on_caught(state)

    if state["caught_frames"] > 0:
        state["caught_frames"] -= 1
        if state["caught_frames"] <= 0:
            state["caught_active"] = False

    if state["cooldown"] > 0:
        state["cooldown"] -= 1

    if not state.get("entering_center"):
        _gt_update_hack(state, bullet_manager, player_x, player_y)

    _gt_update_center(state, player_x, player_y, boss, bullet_manager)

    if (state["hacking"] is None and not state.get("entering_center")
            and state["timer"] > 50 and not state.get("spell_done")):
        _gt_spawn_corridor_bullets(state, bullet_manager)

    if state["banner"] is not None:
        state["banner"] = (state["banner"][0], state["banner"][1] - 1)
        if state["banner"][1] <= 0:
            state["banner"] = None

    for fx in state["fx"]:
        fx["age"] += 1
    state["fx"] = [fx for fx in state["fx"] if fx["age"] < fx["max_age"]]


# ---------------------------------------------------------------------------
# 绘制：Boss 本体之下（走廊 / 终端 / 追击标记）
# ---------------------------------------------------------------------------
def _gt_draw_boss_layer(screen, boss, ox, oy):
    state = getattr(boss, "goldor_terminal", None)
    if state is None or state.get("spell_done"):
        return
    _gt_draw_corridor(screen, state, ox, oy)
    _gt_draw_terminals(screen, state, ox, oy)
    _gt_draw_goldor_marker(screen, boss, ox, oy)


def _gt_draw_wall_line(screen, p0, p1, ox, oy, width=3):
    pygame.draw.line(screen, (120, 96, 44), (p0[0] + ox, p0[1] + oy),
                     (p1[0] + ox, p1[1] + oy), width + 4)
    pygame.draw.line(screen, (255, 205, 90), (p0[0] + ox, p0[1] + oy),
                     (p1[0] + ox, p1[1] + oy), width)


def _gt_draw_corridor(screen, state, ox, oy):
    now = pygame.time.get_ticks()
    pulse = 0.5 + 0.5 * math.sin(now * 0.004)
    outer = pygame.Rect(int(GT_OUTER + ox), int(GT_OUTER + oy),
                        int(GT_OUTER_RIGHT - GT_OUTER), int(GT_OUTER_BOTTOM - GT_OUTER))
    inner = pygame.Rect(int(GT_IL + ox), int(GT_IT + oy),
                        int(GT_IR - GT_IL), int(GT_IB - GT_IT))
    pygame.draw.rect(screen, (34, 31, 28), outer)
    pygame.draw.rect(screen, (10, 10, 18), inner)
    cx, cy = int(GT_CENTER[0] + ox), int(GT_CENTER[1] + oy)
    for r, col in ((120, (30, 28, 40)), (84, (34, 32, 46)), (52, (40, 36, 52))):
        pygame.draw.circle(screen, col, (cx, cy), r, 1)
    pygame.draw.circle(screen, (70, 62, 60), (cx, cy), 26, 1)
    lane_color = (92, 80, 56)
    dash = 10
    for side_y in (GT_IT - (GT_IT - GT_OUTER) / 3.0,
                   GT_IT - (GT_IT - GT_OUTER) / 3.0 * 2.0,
                   GT_IB + (GT_OUTER_BOTTOM - GT_IB) / 3.0,
                   GT_IB + (GT_OUTER_BOTTOM - GT_IB) / 3.0 * 2.0):
        y = int(side_y + oy)
        x0, x1 = int(GT_OUTER + ox), int(GT_OUTER_RIGHT + ox)
        x = x0
        while x < x1:
            pygame.draw.line(screen, lane_color, (x, y), (min(x + dash, x1), y), 1)
            x += dash * 2
    for side_x in (GT_IL - (GT_IL - GT_OUTER) / 3.0,
                   GT_IL - (GT_IL - GT_OUTER) / 3.0 * 2.0,
                   GT_IR + (GT_OUTER_RIGHT - GT_IR) / 3.0,
                   GT_IR + (GT_OUTER_RIGHT - GT_IR) / 3.0 * 2.0):
        x = int(side_x + ox)
        y0, y1 = int(GT_IT + oy), int(GT_IB + oy)
        y = y0
        while y < y1:
            pygame.draw.line(screen, lane_color, (x, y), (x, min(y + dash, y1)), 1)
            y += dash * 2
    _gt_draw_wall_line(screen, (GT_OUTER, GT_OUTER), (GT_OUTER_RIGHT, GT_OUTER), ox, oy)
    _gt_draw_wall_line(screen, (GT_OUTER_RIGHT, GT_OUTER), (GT_OUTER_RIGHT, GT_OUTER_BOTTOM), ox, oy)
    _gt_draw_wall_line(screen, (GT_OUTER_RIGHT, GT_OUTER_BOTTOM), (GT_OUTER, GT_OUTER_BOTTOM), ox, oy)
    _gt_draw_wall_line(screen, (GT_OUTER, GT_OUTER_BOTTOM), (GT_OUTER, GT_OUTER), ox, oy)
    _gt_draw_wall_line(screen, (GT_IL, GT_IT), (GT_IR, GT_IT), ox, oy)
    _gt_draw_wall_line(screen, (GT_IR, GT_IT), (GT_IR, GT_IB), ox, oy)
    _gt_draw_wall_line(screen, (GT_IR, GT_IB), (GT_IL, GT_IB), ox, oy)
    _gt_draw_wall_line(screen, (GT_IL, GT_IB), (GT_IL, GT_IT), ox, oy)
    if not state.get("center_open"):
        by = int(GT_BARRIER_Y + oy)
        bx0, bx1 = int(GT_OUTER + ox), int(GT_IL + ox)
        pygame.draw.rect(screen, (110, 56, 38), (bx0, by - 10, bx1 - bx0, 20))
        for i in range(bx0, bx1, 16):
            pygame.draw.line(screen, (70, 34, 24), (i, by + 8),
                             (min(i + 12, bx1), by - 8), 2)
        pygame.draw.rect(screen, (255, 150, 70), (bx0, by - 10, bx1 - bx0, 20), 2)
        mid_x = (bx0 + bx1) // 2
        pygame.draw.circle(screen, (64, 22, 14), (mid_x, by), 11)
        pygame.draw.circle(screen, (255, 190, 90), (mid_x, by), 11, 2)
        warn = _get_font(15).render("!", True, (255, 215, 130))
        screen.blit(warn, (mid_x - warn.get_width() // 2,
                           by - warn.get_height() // 2))
    if state.get("center_open"):
        _gt_draw_entrance(screen, ox, oy, now, pulse)
    else:
        gy0 = int(GT_ENTRANCE_Y0 + oy)
        gy1 = int(GT_ENTRANCE_Y1 + oy)
        gx = int(GT_IL + ox)
        pygame.draw.rect(screen, (60, 52, 46), (gx - 3, gy0, 6, gy1 - gy0))


def _gt_draw_entrance(screen, ox, oy, now, pulse):
    gy0 = int(GT_ENTRANCE_Y0 + oy)
    gy1 = int(GT_ENTRANCE_Y1 + oy)
    gx = int(GT_IL + ox)
    pygame.draw.rect(screen, (10, 10, 18), (gx - 3, gy0, 6, gy1 - gy0))
    alpha = 90 + int(120 * pulse)
    layer = pygame.Surface((int(GT_CENTER[0] - GT_IL) + 8, gy1 - gy0), pygame.SRCALPHA)
    layer.fill((120, 230, 255, alpha))
    screen.blit(layer, (gx - 3, gy0))
    pygame.draw.line(screen, (255, 205, 90), (gx - 6, gy0), (gx + 4, gy0), 3)
    pygame.draw.line(screen, (255, 205, 90), (gx - 6, gy1), (gx + 4, gy1), 3)
    mid_y = gy0 + (gy1 - gy0) // 2
    for i in range(3):
        x = gx - 22 - i * 14
        pygame.draw.polygon(screen, (160, 240, 255),
                            [(x + 8, mid_y - 8), (x + 8, mid_y + 8), (x, mid_y)])


def _gt_draw_terminals(screen, state, ox, oy):
    now = pygame.time.get_ticks()
    pulse = 0.5 + 0.5 * math.sin(now * 0.005)
    for t in state["terminals"]:
        x, y = int(t["x"] + ox), int(t["y"] + oy)
        if t["solved"]:
            r = 16
            pygame.draw.rect(screen, (30, 74, 50), (x - r, y - r, r * 2, r * 2))
            pygame.draw.rect(screen, (110, 230, 150), (x - r, y - r, r * 2, r * 2), 2)
            pygame.draw.line(screen, (170, 255, 190), (x - 8, y), (x - 2, y + 7), 3)
            pygame.draw.line(screen, (170, 255, 190), (x - 2, y + 7), (x + 9, y - 8), 3)
            continue
        if t["final"]:
            r = 21 + int(3 * pulse)
            glow = pygame.Surface((r * 2 + 12, r * 2 + 12), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 220, 110, 70), (r + 6, r + 6), r + 4)
            screen.blit(glow, (x - r - 6, y - r - 6))
            pygame.draw.rect(screen, (70, 56, 26), (x - r, y - r, r * 2, r * 2))
            pygame.draw.rect(screen, (255, 210, 90), (x - r, y - r, r * 2, r * 2), 3)
            points = []
            for k in range(10):
                a = -math.pi / 2 + k * math.pi / 5
                rad = r - 4 if k % 2 == 0 else (r - 4) * 0.42
                points.append((x + math.cos(a) * rad, y + math.sin(a) * rad))
            pygame.draw.polygon(screen, (255, 235, 150), points)
            label = _get_font(13).render("DEVICE", True, (255, 225, 130))
            screen.blit(label, (x - label.get_width() // 2, y - r - 24))
            beam = pygame.Surface((5, 26), pygame.SRCALPHA)
            beam.fill((255, 220, 120, 90))
            screen.blit(beam, (x - 2, y - r - 26))
        else:
            r = 15
            pygame.draw.rect(screen, (26, 60, 66), (x - r, y - r, r * 2, r * 2))
            pygame.draw.rect(screen, (90, 220, 235), (x - r, y - r, r * 2, r * 2), 2)
            pygame.draw.circle(screen, (140, 240, 250), (x, y), int(5 + 2 * pulse))
            tr = int(GT_TOUCH_RADIUS)
            ring = pygame.Surface((tr * 2, tr * 2), pygame.SRCALPHA)
            pygame.draw.circle(ring, (110, 225, 240, 70), (tr, tr), tr, 1)
            screen.blit(ring, (x - tr, y - tr))


def _gt_draw_goldor_marker(screen, boss, ox, oy):
    now = pygame.time.get_ticks()
    pulse = 0.5 + 0.5 * math.sin(now * 0.01)
    x, y = int(boss.x + ox), int(boss.y + oy)
    r = int(30 + 8 * pulse)
    ring = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    pygame.draw.circle(ring, (255, 60, 50, 40), (r, r), r)
    pygame.draw.circle(ring, (255, 90, 70, 180), (r, r), r, 2)
    screen.blit(ring, (x - r, y - r))


# ---------------------------------------------------------------------------
# 绘制：子弹之上（警告 / 破解 GUI / 通关演出）
# ---------------------------------------------------------------------------
def _gt_draw_foreground(screen, boss, ox, oy):
    state = getattr(boss, "goldor_terminal", None)
    if state is None or state.get("spell_done"):
        return
    warn = state.get("warning", 0.0)
    if state.get("caught_active"):
        layer = pygame.Surface((cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT),
                               pygame.SRCALPHA)
        layer.fill((255, 40, 30, 110))
        screen.blit(layer, (ox, oy))
    elif warn > 0.05:
        alpha = int(110 * warn)
        layer = pygame.Surface((cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT),
                               pygame.SRCALPHA)
        layer.fill((255, 30, 20, alpha))
        screen.blit(layer, (ox, oy))
        pygame.draw.rect(screen, (255, 60, 40),
                         (ox, oy, cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT), 4)
        if warn > 0.6:
            font = _get_font(20)
            t = font.render("GOLDOR 接近！", True, (255, 110, 90))
            screen.blit(t, (ox + (cfg.BATTLE_AREA_WIDTH - t.get_width()) // 2,
                            oy + 14))
    if state["puzzle"] is None and not state.get("entering_center"):
        hint_font = _get_font(14)
        ht = hint_font.render("接近终端自动破解：←→↑↓ 移动　Z 选择　ESC 放弃",
                              True, (205, 214, 235))
        hl = pygame.Surface((ht.get_width() + 16, ht.get_height() + 6), pygame.SRCALPHA)
        hl.fill((10, 12, 26, 170))
        screen.blit(hl, (ox + (cfg.BATTLE_AREA_WIDTH - hl.get_width()) // 2,
                         oy + cfg.BATTLE_AREA_HEIGHT - 30))
        screen.blit(ht, (ox + (cfg.BATTLE_AREA_WIDTH - ht.get_width()) // 2,
                         oy + cfg.BATTLE_AREA_HEIGHT - 27))
    if state["puzzle"] is not None:
        state["puzzle"].draw(screen, ox, oy, warn)
    if state["banner"] is not None:
        text, frames = state["banner"]
        font = _get_font(22)
        t = font.render(text, True, (255, 235, 140))
        layer = pygame.Surface((t.get_width() + 24, t.get_height() + 12), pygame.SRCALPHA)
        layer.fill((10, 12, 26, 210))
        screen.blit(layer, (ox + (cfg.BATTLE_AREA_WIDTH - layer.get_width()) // 2, oy + 120))
        screen.blit(t, (ox + (cfg.BATTLE_AREA_WIDTH - t.get_width()) // 2, oy + 126))
    if state.get("entering_center"):
        cx, cy = int(GT_CENTER[0] + ox), int(GT_CENTER[1] + oy)
        prog = min(1.0, state["enter_timer"] / 70.0)
        r = int(20 + 220 * prog)
        layer = pygame.Surface((cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT),
                               pygame.SRCALPHA)
        pygame.draw.circle(layer, (255, 230, 140, int(160 * (1.0 - prog))),
                           (cx, cy), r, 3)
        screen.blit(layer, (ox, oy))
        font = _get_font(24)
        t = font.render("PURSUIT COMPLETE", True, (255, 240, 170))
        screen.blit(t, (ox + (cfg.BATTLE_AREA_WIDTH - t.get_width()) // 2,
                        oy + cfg.BATTLE_AREA_HEIGHT * 0.18))
