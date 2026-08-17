# -*- coding: utf-8 -*-
# 六面：最终进军 ~ Final Approach（通往凋零之王 Kaeman 的王座）
# 取消传统道中 Boss，整体为「最终进军」三段式：
#   - 前半段「进军」：Wither Miner / Wither Guard / Wither Husk 亡灵军队防线渐强；
#   - 中段「注视」：Kaeman 远程干涉——巨颅 Wither Skull 注视并锁定玩家区域、
#     黑色 Wither 能量持续侵入战场（游魂 + 侵入波），压迫感来自「被注视」；
#   - 后半段「要塞」：进入凋零要塞，敌人减少而弹幕更宏大，曾败北的
#     Maxor / Storm / Goldor / Necron 以残影短暂出现作为王之门徒象征；
#   - 突破王座前的最后防线后直面凋零之王 Kaeman（即 The Wither King），
#     六张符卡：五张通常符（1~5 已实装）+ 一张 Last Spell「终仪」（已实装）。

import math
import os
import random

import pygame

from src.engine import settings as cfg
from src.engine.pseudo3d import Pseudo3DFloor
from src.entities.boss import Boss, SpellCard, _get_font
from src.entities.bullet import Bullet, create_bullet_aimed, create_bullet_angle
from src.entities.enemy import Enemy, EnemyWave
from src.stages.stage1 import (
    Stage,
    BOSS_BG_RAMP_TIME,
    BOSS_COMBAT_DELAY,
    FINAL_BOSS_BG_SPEED_MULT,
)

# 时间轴（帧，60FPS）
MARCH_END = 42 * 60                 # 42s：亡灵军队进军结束
INTERFERENCE_END = 66 * 60          # 66s：进入凋零要塞
FORTRESS_FINAL_WAVE_AT = 100 * 60   # 100s：王座前最后防线

# Kaeman 巨颅注视节奏
KAEMAN_FIRST_ATTACK_IN = 4 * 60     # 进入干涉阶段 4s 后首次注视
KAEMAN_ATTACK_INTERVAL = 290        # 两次注视间隔（帧）
KAEMAN_WATCH_FRAMES = 78            # 注视追踪时长
KAEMAN_LOCK_FRAMES = 68             # 锁定玩家区域时长
KAEMAN_FADE_FRAMES = 55             # 巨颅退场时长

# 王之门徒残影（出现时刻 -> 残影配置）
GHOST_PLAN = (
    (70 * 60, "maxor"),
    (78 * 60, "storm"),
    (86 * 60, "goldor"),
    (94 * 60, "necron"),
)
GHOST_POSITIONS = {
    "maxor": (140, 116),
    "storm": (300, 100),
    "goldor": (432, 116),
    "necron": (300, 92),
}
GHOST_SPRITES = {
    "maxor": cfg.STAGE6_MAXOR_GHOST_SPRITE,
    "storm": cfg.STAGE6_STORM_GHOST_SPRITE,
    "goldor": cfg.STAGE6_GOLDOR_GHOST_SPRITE,
    "necron": cfg.STAGE6_NECRON_GHOST_SPRITE,
}
GHOST_GLOWS = {
    "maxor": (255, 130, 60),
    "storm": (120, 200, 255),
    "goldor": (255, 205, 90),
    "necron": (190, 60, 235),
}
GHOST_HEIGHT = 190
GHOST_MAX_AGE = 190
GHOST_FIRE_AT = 62

WKING_HP = 24000

# 贴图缓存
_sprite_cache = {}


def _load_sprite(path, target_height):
    key = (path, target_height)
    if key in _sprite_cache:
        return _sprite_cache[key]
    try:
        img = pygame.image.load(path).convert_alpha()
        w, h = img.get_size()
        new_w = max(1, int(round(w * target_height / h)))
        _sprite_cache[key] = pygame.transform.smoothscale(img, (new_w, target_height))
    except Exception as exc:
        print("[Stage6] Failed to load sprite %s: %s" % (path, exc))
        _sprite_cache[key] = None
    return _sprite_cache[key]


_relic_glow_cache = {}


def _get_relic_glow(radius, color):
    """Relic 光晕：同心圆叠加的柔和彩色柔光（纯视觉）。"""
    key = (int(radius), color)
    if key in _relic_glow_cache:
        return _relic_glow_cache[key]
    size = int(radius) * 2 + 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    steps = max(4, int(radius))
    for i in range(steps):
        rr = max(1, int(radius * (1.0 - i / steps)))
        alpha = int(12 + 64 * (i / steps))
        pygame.draw.circle(surf, (*color, alpha), (cx, cy), rr)
    _relic_glow_cache[key] = surf
    return surf


def _add(bullet_manager, bullet):
    bullet_manager.add_enemy_bullet(bullet)


def _clamp_x(x, margin=52):
    return max(margin, min(cfg.BATTLE_AREA_WIDTH - margin, x))


def _clamp_y(y, low=80, high=240):
    return max(low, min(high, y))


# ---------------------------------------------------------------------------
# 六面小怪（亡灵军队）
# ---------------------------------------------------------------------------
class WitherHuskEnemy(Enemy):
    """Wither Husk：迅捷亡灵近卫，逼近后自机狙。"""
    def __init__(self, x, y, move_pattern="strafe"):
        super().__init__(x, y, hp=95, score=700, size=14, color=(170, 90, 130),
                         sprite_paths=cfg.STAGE6_HUSK_SPRITES,
                         sprite_height=cfg.STAGE6_HUSK_SPRITE_HEIGHT, anim_speed=14)
        self.move_pattern = move_pattern
        self.move_speed = 1.5
        self.move_amplitude = 2.2
        self.shoot_interval = 96
        self.shoot_pattern = "none"

    def shoot(self, bullet_manager, player_x, player_y):
        base = math.atan2(player_y - self.y, player_x - self.x)
        _add(bullet_manager, create_bullet_angle(
            self.x, self.y, base, 2.6, Bullet.TYPE_CIRCLE,
            radius=2.5, color=(150, 60, 110)))


class WitherGuardEnemy(Enemy):
    """Wither Guard：重装骷髅守卫，扇形自机狙与圆环交替压制。"""
    def __init__(self, x, y):
        super().__init__(x, y, hp=260, score=1800, size=20, color=(150, 140, 90),
                         sprite_paths=cfg.STAGE6_GUARD_SPRITES,
                         sprite_height=cfg.STAGE6_GUARD_SPRITE_HEIGHT, anim_speed=22)
        self.move_pattern = "descend"
        self.move_speed = 0.7
        self.shoot_interval = 100
        self.shoot_pattern = "none"
        self._shots = 0

    def shoot(self, bullet_manager, player_x, player_y):
        self._shots += 1
        base = math.atan2(player_y - self.y, player_x - self.x)
        if self._shots % 2 == 0:
            for offset in (-0.18, 0.0, 0.18):
                _add(bullet_manager, create_bullet_angle(
                    self.x, self.y, base + offset, 2.5, Bullet.TYPE_RICE,
                    radius=2.5, color=(190, 150, 70)))
        else:
            for i in range(14):
                a = i * math.tau / 14 + self.age * 0.012
                _add(bullet_manager, create_bullet_angle(
                    self.x, self.y, a, 1.6, Bullet.TYPE_CIRCLE,
                    radius=2.5, color=(150, 120, 60)))


class WitherMinerEnemy(Enemy):
    """Wither Miner：凋零矿工，扇形碎弹 + 缓速挖矿大玉。"""
    def __init__(self, x, y):
        super().__init__(x, y, hp=150, score=1200, size=16, color=(90, 160, 130),
                         sprite_paths=cfg.STAGE6_MINER_SPRITES,
                         sprite_height=cfg.STAGE6_MINER_SPRITE_HEIGHT, anim_speed=16)
        self.move_pattern = "strafe"
        self.move_speed = 0.8
        self.move_amplitude = 2.2
        self.shoot_interval = 105
        self.shoot_pattern = "none"
        self._shots = 0

    def shoot(self, bullet_manager, player_x, player_y):
        self._shots += 1
        base = math.atan2(player_y - self.y, player_x - self.x)
        for i in range(5):
            a = base + (i - 2) * 0.14
            _add(bullet_manager, create_bullet_angle(
                self.x, self.y, a, 2.2, Bullet.TYPE_RICE,
                radius=2.5, color=(70, 140, 110)))
        if self._shots % 2 == 0:
            _add(bullet_manager, create_bullet_angle(
                self.x, self.y, math.pi / 2, 1.1, Bullet.TYPE_BIG,
                radius=5, color=(60, 120, 90)))

class WitherKnightEnemy(Enemy):
    """Wither Knight：凋零骑士，刀弹扇面 + 周期圆环。"""
    def __init__(self, x, y):
        super().__init__(x, y, hp=230, score=2000, size=19, color=(120, 130, 90),
                         sprite_paths=cfg.STAGE6_KNIGHT_SPRITES,
                         sprite_height=cfg.STAGE6_KNIGHT_SPRITE_HEIGHT, anim_speed=20)
        self.move_pattern = "strafe"
        self.move_speed = 0.9
        self.move_amplitude = 2.4
        self.shoot_interval = 110
        self.shoot_pattern = "none"
        self._shots = 0

    def shoot(self, bullet_manager, player_x, player_y):
        self._shots += 1
        base = math.atan2(player_y - self.y, player_x - self.x)
        for i in range(5):
            a = base + (i - 2) * 0.15
            _add(bullet_manager, create_bullet_angle(
                self.x, self.y, a, 2.6, Bullet.TYPE_KNIFE,
                radius=2.5, color=(140, 150, 80)))
        if self._shots % 3 == 0:
            for i in range(12):
                a = i * math.tau / 12 + self.age * 0.02
                _add(bullet_manager, create_bullet_angle(
                    self.x, self.y, a, 1.5, Bullet.TYPE_CIRCLE,
                    radius=2.5, color=(110, 120, 60)))


class _DeployEnemy(Enemy):
    """下降到部署位后停驻的防御型敌人。"""
    def __init__(self, x, y, deploy_y, hp, score, size, color,
                 sprite_paths, sprite_height, anim_speed, deploy_speed=1.0):
        super().__init__(x, y, hp=hp, score=score, size=size, color=color,
                         sprite_paths=sprite_paths, sprite_height=sprite_height,
                         anim_speed=anim_speed)
        self.move_pattern = "none"
        self.deploy_y = deploy_y
        self.deploy_speed = deploy_speed
        self.deployed = False
        self.entry_done = True

    def _move(self):
        if not self.deployed:
            self.y += self.deploy_speed
            if self.y >= self.deploy_y:
                self.y = self.deploy_y
                self.deployed = True
        else:
            self.x += math.sin(self.age * 0.012) * 0.35

    def can_shoot(self):
        return self.deployed and super().can_shoot()


class WitherTerracottaEnemy(_DeployEnemy):
    """Wither Golem（兵马俑守卫）：停驻要塞的自机狙与圆环。"""
    def __init__(self, x, y, deploy_y=150):
        super().__init__(x, y, deploy_y, hp=330, score=2400, size=20,
                         color=(150, 110, 80),
                         sprite_paths=[cfg.STAGE6_TERRACOTTA_SPRITE],
                         sprite_height=88, anim_speed=20, deploy_speed=1.0)
        self.shoot_interval = 115
        self.shoot_pattern = "none"
        self._shots = 0

    def shoot(self, bullet_manager, player_x, player_y):
        self._shots += 1
        if self._shots % 2 == 0:
            base = math.atan2(player_y - self.y, player_x - self.x)
            _add(bullet_manager, create_bullet_angle(
                self.x, self.y, base, 2.4, Bullet.TYPE_CIRCLE,
                radius=3, color=(190, 130, 80)))
        else:
            for i in range(16):
                a = i * math.tau / 16 + self.age * 0.01
                _add(bullet_manager, create_bullet_angle(
                    self.x, self.y, a, 1.6, Bullet.TYPE_RICE,
                    radius=2.5, color=(160, 110, 70)))


class WitherColossusEnemy(_DeployEnemy):
    """Wither Colossus：最后防线的巨型构造体，大玉与旋转环。"""
    def __init__(self, x, y, deploy_y=150):
        super().__init__(x, y, deploy_y, hp=1200, score=6000, size=30,
                         color=(110, 70, 150),
                         sprite_paths=[cfg.STAGE6_COLOSSUS_SPRITE],
                         sprite_height=120, anim_speed=26, deploy_speed=1.1)
        self.shoot_interval = 72
        self.shoot_pattern = "none"
        self._shots = 0

    def shoot(self, bullet_manager, player_x, player_y):
        self._shots += 1
        base = math.atan2(player_y - self.y, player_x - self.x)
        if self._shots % 2 == 0:
            _add(bullet_manager, create_bullet_angle(
                self.x, self.y, base, 1.9, Bullet.TYPE_BIG,
                radius=6, color=(120, 60, 180)))
            for i in range(8):
                a = i * math.tau / 8 + self.age * 0.012
                _add(bullet_manager, create_bullet_angle(
                    self.x, self.y, a, 1.2, Bullet.TYPE_RICE,
                    radius=2.5, color=(110, 55, 160)))
        else:
            for i in range(16):
                a = i * math.tau / 16 + self.age * 0.008
                _add(bullet_manager, create_bullet_angle(
                    self.x, self.y, a, 1.5, Bullet.TYPE_CIRCLE,
                    radius=2.5, color=(150, 80, 190)))


class WitherWispEnemy(Enemy):
    """Wither Wisp：Kaeman 远程投下的黑能量游魂（可击破）。"""
    def __init__(self, x, y):
        super().__init__(x, y, hp=70, score=400, size=13, color=(110, 60, 160),
                         sprite_paths=cfg.STAGE6_WISP_SPRITES,
                         sprite_height=cfg.STAGE6_WISP_SPRITE_HEIGHT, anim_speed=18)
        self.move_pattern = "sin"
        self.move_speed = 0.9
        self.move_amplitude = 2.6
        self.vx = random.choice((-0.9, 0.9))
        self.shoot_interval = 150
        self.shoot_pattern = "none"

    def shoot(self, bullet_manager, player_x, player_y):
        base = math.atan2(player_y - self.y, player_x - self.x)
        _add(bullet_manager, create_bullet_angle(
            self.x, self.y, base, 2.1, Bullet.TYPE_CIRCLE,
            radius=2.5, color=(90, 40, 140)))


# ---------------------------------------------------------------------------
# Kaeman 非符（开战首帧过渡，六张符卡接续战斗）
# ---------------------------------------------------------------------------
def _non_spell_kaeman(boss, bullet_manager, timer, player_x, player_y):
    """三头齐射：主头自机狙大玉 + 侧头刀弹扇面 + 旋转环 + 王座脉冲。"""
    if timer % 110 == 0:
        boss.move_to(_clamp_x(cfg.BATTLE_AREA_WIDTH / 2 + math.sin(timer * 0.013) * 160),
                     _clamp_y(104 + math.cos(timer * 0.021) * 14))
    base = math.atan2(player_y - boss.y, player_x - boss.x)
    if timer % 36 == 0:
        for offset in (-0.12, 0.0, 0.12):
            _add(bullet_manager, create_bullet_angle(
                boss.x, boss.y, base + offset, 2.9, Bullet.TYPE_BIG,
                radius=4.5, color=(120, 50, 180)))
    if timer % 62 == 0:
        for side, ang0 in ((-1, math.pi + 0.38), (1, -0.38)):
            hx = boss.x + side * 46
            for i in range(5):
                a = ang0 + (i - 2) * 0.16
                _add(bullet_manager, create_bullet_angle(
                    hx, boss.y + 16, a, 2.6, Bullet.TYPE_RICE,
                    radius=2.5, color=(200, 60, 150)))
    if timer % 96 == 0:
        for i in range(14):
            a = timer * 0.02 + i * math.tau / 14
            _add(bullet_manager, create_bullet_angle(
                boss.x, boss.y, a, 1.7, Bullet.TYPE_CIRCLE,
                radius=2.5, color=(60, 30, 90)))
    if timer % 160 == 0:
        for i in range(26):
            a = i * math.tau / 26
            _add(bullet_manager, create_bullet_angle(
                boss.x, boss.y, a, 2.1, Bullet.TYPE_RICE,
                radius=2.5, color=(150, 60, 200)))


# ---------------------------------------------------------------------------
# Kaeman 六张符卡（①~⑤ 已实装；Last Spell「终仪」已实装：吸收与狂暴放出）
# ---------------------------------------------------------------------------
# 王符「Wither King's Dominion」：Wither 王领域（Kaeman 第一符）
# 领域循环：开符时领域从最大缓慢缩至中间圆形装饰处（给玩家反应时间），
# 随后在中部小幅展开 → 全展开 → 收缩 → 短暂扩张 → 循环。
# 领域内部整体为安全区域；领域边缘由一圈完整的大玉构成（全部使用 etama
# 大玉贴图），随王徽阵缓慢旋转、扩张、收缩；王权裂隙沿径向延伸、中部断开
# （纯装饰）；领域边缘周期性生成向内压缩的 Wither 能量大玉，大玉受中央
# 吸引逐渐加速，仿佛被领域核心吸向中心；裂隙沿旋转射线甩出能量。
# ---------------------------------------------------------------------------
_DOM_OPEN = 210                # 开符阶段（帧）：领域从最大缓慢缩到中间装饰处
_DOM_LOOP_HOLD = 180           # 装饰处全展开持续时间（帧）
_DOM_LOOP_CONTRACT = 180       # 领域收缩持续时间（帧）
_DOM_LOOP_EXPAND = 60          # 短暂扩张持续时间（帧）
_DOM_CYCLE = 420               # 开符后的循环总长（帧，约 7s）
_DOM_R_OPEN = 620.0            # 开符最大半径：领域覆盖全场，随后缓慢缩回
_DOM_R_MAX = 380.0             # 循环最大半径：边框位于中间圆形装饰处
_DOM_R_MIN = 332.0             # 循环最小半径（收缩）
_DOM_SPIN = 0.0030              # 王徽阵 / 王权裂隙旋转角速度（弧度/帧）
_DOM_FISSURE_COUNT = 3          # 王权裂隙数量（沿领域径向均匀分布）
_DOM_BORDER_COUNT = 60          # 领域边框大玉数量（完整一圈，无缺口）
_DOM_BORDER_RADIUS = 6.0        # 边框大玉半径（6.0 触发图集 32px 大玉贴图，判定约为贴图一半）
_DOM_CRACK_BREAK = (0.40, 0.65) # 裂隙中部断开区间（占裂隙长度的比例）
_DOM_EDGE_INTERVAL = 70         # 领域边缘 Wither 能量大玉波次间隔（帧）
_DOM_EDGE_COUNT = 24            # 每波边缘大玉数（原 16 增加 50%）
_DOM_EDGE_ACCEL = 0.02          # 边缘大玉每帧加速度（受中央吸引，向中心加速）
_DOM_CRACK_ECHO_INTERVAL = 150  # 王权裂隙甩出能量的间隔（帧）


def _dom_lerp(a, b, f):
    return a + (b - a) * f


def _dom_ease(f):
    return f * f * (3 - 2 * f)


def _dom_fissure_angle(rot, k):
    """第 k 条王权裂隙的角度（随领域旋转）。"""
    return rot + k * math.tau / _DOM_FISSURE_COUNT


def _kaeman_dominion_init(boss):
    """开符初始化：领域中心跟随 Kaeman，边框大玉与裂隙随后逐帧生成。"""
    boss.kaeman_dominion = {
        "cx": boss.x,
        "cy": boss.y,
        "radius": _DOM_R_OPEN,   # 开符：领域从最大开始，随后缓慢缩到中间装饰处
        "rot": math.pi / 6,
        "border": [],   # 领域边框大玉列表（逐帧跟随中心/半径/旋转）
    }


def _kaeman_dominion_cycle(d, timer):
    """驱动领域循环：开符从最大缓慢缩至中间装饰处，之后中部小幅脉动。"""
    if timer < _DOM_OPEN:
        f = _dom_ease(timer / _DOM_OPEN)
        d["radius"] = _dom_lerp(_DOM_R_OPEN, _DOM_R_MAX, f)
    else:
        t = (timer - _DOM_OPEN) % _DOM_CYCLE
        if t < _DOM_LOOP_HOLD:
            d["radius"] = _DOM_R_MAX
        elif t < _DOM_LOOP_HOLD + _DOM_LOOP_CONTRACT:
            f = _dom_ease((t - _DOM_LOOP_HOLD) / _DOM_LOOP_CONTRACT)
            d["radius"] = _dom_lerp(_DOM_R_MAX, _DOM_R_MIN, f)
        else:
            f = _dom_ease((t - _DOM_LOOP_HOLD - _DOM_LOOP_CONTRACT) / _DOM_LOOP_EXPAND)
            d["radius"] = _dom_lerp(_DOM_R_MIN, _DOM_R_MAX, f)
    d["rot"] += _DOM_SPIN


def _kaeman_dominion_spawn_border(boss, bullet_manager, rot):
    """一次性生成领域边框大玉：完整一圈布在半径圆上（无缺口）。"""
    d = boss.kaeman_dominion
    if d.get("border"):
        return
    cx, cy, R = d["cx"], d["cy"], d["radius"]
    bullets = []
    for k in range(_DOM_BORDER_COUNT):
        a = k * math.tau / _DOM_BORDER_COUNT
        b = create_bullet_angle(
            cx + math.cos(rot + a) * R, cy + math.sin(rot + a) * R,
            0.0, 0.0, Bullet.TYPE_BIG,
            radius=_DOM_BORDER_RADIUS, color=(26, 12, 48), lifetime=999999)
        b.vx = 0.0
        b.vy = 0.0
        b.turn_rate = 0.0
        b.ignore_offscreen = True   # 边框大玉常驻，越界不消散（逐帧贴环重定位）
        b._dom_base = a   # 相对领域旋转角的固定偏移
        _add(bullet_manager, b)
        bullets.append(b)
    d["border"] = bullets


def _kaeman_dominion_reposition_border(d):
    """边框大玉逐帧跟随领域中心 / 半径 / 旋转。"""
    cx, cy, R, rot = d["cx"], d["cy"], d["radius"], d["rot"]
    for b in d["border"]:
        a = rot + b._dom_base
        b.x = cx + math.cos(a) * R
        b.y = cy + math.sin(a) * R


def _kaeman_dominion_bullets(boss, bullet_manager, timer):
    """领域弹幕：边框大玉 + 受中央吸引加速向内压缩的 Wither 能量大玉 + 裂隙甩出能量。"""
    d = boss.kaeman_dominion
    cx, cy = d["cx"], d["cy"]
    R = d["radius"]
    rot = d["rot"]

    # 领域边框：大玉构成的王徽阵边缘（完整一圈，无缺口），逐帧跟随旋转扩张
    _kaeman_dominion_spawn_border(boss, bullet_manager, rot)
    _kaeman_dominion_reposition_border(d)

    # 领域边缘周期性生成 Wither 能量大玉，受中央吸引逐渐加速向内压缩
    if timer % _DOM_EDGE_INTERVAL == 0:
        for k in range(_DOM_EDGE_COUNT):
            a = rot + k * math.tau / _DOM_EDGE_COUNT
            b = create_bullet_angle(
                cx + math.cos(a) * R, cy + math.sin(a) * R,
                a + math.pi,
                0.92 + (k % 4) * 0.14,
                Bullet.TYPE_BIG,
                radius=_DOM_BORDER_RADIUS,
                color=(26, 12, 48),
                lifetime=520)
            b.accel = _DOM_EDGE_ACCEL   # 仿佛被领域核心吸引，向中心加速
            b.ignore_offscreen = True   # 领域边缘多在屏外，允许大玉从边缘飞越全场奔向中央
            _add(bullet_manager, b)

    # 王权裂隙沿旋转射线甩出能量（不追踪玩家，贴合裂隙走向）
    if timer % _DOM_CRACK_ECHO_INTERVAL == 0:
        for k in range(_DOM_FISSURE_COUNT):
            a = _dom_fissure_angle(rot, k)
            for side in (-1, 1):
                for j in range(2):
                    b = create_bullet_angle(
                        cx, cy, a + side * 0.03, 1.4 + j * 0.24, Bullet.TYPE_KNIFE,
                        radius=2.3, color=(150, 64, 215), lifetime=400)
                    b.turn_rate = _DOM_SPIN
                    b.glow_color = (210, 140, 255)
                    b.glow_padding = 4
                    _add(bullet_manager, b)


def _kaeman_draw_dominion_crack(overlay, cx, cy, angle, length, seed, side,
                                break_range=_DOM_CRACK_BREAK):
    """绘制一条 jagged 王权裂隙：紫色光晕 + 黑暗裂纹本体 + 亮紫能量核心。

    裂隙中部断开（break_range 指定的长度比例区间），形成可供玩家穿行的
    缺口；内段与外段分两次绘制，断开处留出明显的空档。
    """
    steps = 10
    pts = []
    core = []
    nx = -math.sin(angle)
    ny = math.cos(angle)
    for i in range(steps + 1):
        t = i / steps
        r = length * t
        jit = math.sin(seed * 12.73 + i * 2.41 + side * 1.7) * (26.0 * t + 4.0 * t * t)
        x = cx + math.cos(angle) * r + nx * jit
        y = cy + math.sin(angle) * r + ny * jit
        pts.append((x, y))
        core.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
    lo = int(break_range[0] * steps)
    hi = int(math.ceil(break_range[1] * steps))
    for (i0, i1) in ((0, lo), (hi, steps)):
        if i1 - i0 < 2:
            continue
        piece = pts[i0:i1 + 1]
        core_piece = core[i0:i1 + 1]
        pygame.draw.lines(overlay, (90, 30, 160, 140), False, piece, 8)
        pygame.draw.lines(overlay, (12, 3, 22, 235), False, piece, 5)
        pygame.draw.lines(overlay, (195, 135, 255, 185), False, core_piece, 2)


def spell_kaeman_dominion(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """① 王符「Wither King's Dominion」：Wither 王领域。

    Kaeman 位于屏幕上方中央展开巨大的 Wither 王领域：开符时领域从最大
    缓慢缩至中间圆形装饰处，给玩家充足反应时间，随后在中部小幅扩张收缩
    循环。领域内部整体为安全区域，领域边缘由一圈完整的大玉（etama 大玉
    贴图）构成，随王徽阵缓慢旋转、扩张、收缩；王权裂隙沿径向延伸、中部
    断开（纯装饰）；领域边缘周期性生成向内压缩的 Wither 能量大玉，大玉
    受中央吸引逐渐加速，裂隙也会沿旋转射线甩出能量。
    """
    if getattr(boss, "kaeman_dominion", None) is None:
        _kaeman_dominion_init(boss)
    d = boss.kaeman_dominion

    # Kaeman 停留在屏幕上方中央，轻微悬浮
    boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 112 + math.sin(timer * 0.021) * 8)
    d["cx"] = boss.x
    d["cy"] = boss.y

    _kaeman_dominion_cycle(d, timer)
    _kaeman_dominion_bullets(boss, bullet_manager, timer)


# ---------------------------------------------------------------------------
# 冥符「Five Corrupted Relics」：五种 Relic 连成五边形绕中心旋转，各自发出
# 对应颜色的五臂螺旋弹。子弹本身不旋转、匀速直线；由于发射角持续旋转，
# 五条臂连成螺旋。五边形悬于战场中部，迫使玩家在中场弹幕缝隙间躲避。
# ---------------------------------------------------------------------------
_REL_SPIN = 0.0052              # 五边形旋转角速度（弧度/帧）
_REL_CENTER_Y = 258.0           # 五边形中心 Y：战场中部（迫使玩家在中场躲避）
_REL_RADIUS = 140.0             # 五边形外接圆半径（Relic 环绕半径）
_REL_RADIUS_PULSE = 0.10        # 环绕半径缓慢呼吸幅度（占比）
_REL_RADIUS_FREQ = 0.013        # 半径呼吸频率（弧度/帧）
_REL_SPRITE_HEIGHT = 70         # Relic 贴图显示高度（px）
_REL_SPIRAL_INTERVAL = 8        # 每颗 Relic 发射五臂螺旋的间隔（帧）
_REL_SPIRAL_STEP = 0.16         # 每次发射后基准发射角步进（弧度/轮，形成螺旋）
_REL_SPIRAL_SPEED = 1.85        # 螺旋弹速度（匀速直线）
_REL_SPIRAL_LIFETIME = 300      # 螺旋弹存活帧数

# 五种 Relic 对应颜色（红/橙/绿/蓝/紫，与贴图一致）
RELIC_COLORS = (
    (255, 74, 74),
    (255, 148, 58),
    (66, 208, 98),
    (66, 176, 228),
    (186, 84, 238),
)


def _kaeman_relics_init(boss):
    """开符初始化：五种 Relic 连成五边形悬于战场中部，缓慢旋转。"""
    boss.kaeman_relics = {
        "cx": cfg.BATTLE_AREA_WIDTH / 2,
        "cy": _REL_CENTER_Y,
        "radius": _REL_RADIUS,
        "rot": -math.pi / 2,   # 起始：一个 Relic 顶点朝上
        "burst": 0,            # 发射轮次（决定螺旋发射基准角）
    }


def _kaeman_relics_emit(boss, bullet_manager, st):
    """五颗 Relic 各自发出对应颜色的五臂螺旋弹。

    子弹匀速直线、自身不旋转；每轮发射后基准角旋转 _REL_SPIRAL_STEP，
    使五条臂连成不断旋转的螺旋。
    """
    cx, cy = st["cx"], st["cy"]
    R = st["radius"]
    rot = st["rot"]
    base = st["burst"] * _REL_SPIRAL_STEP + rot
    for i in range(5):
        a_pos = rot + i * math.tau / 5
        rx = cx + math.cos(a_pos) * R
        ry = cy + math.sin(a_pos) * R
        color = RELIC_COLORS[i]
        for arm in range(5):
            angle = base + arm * math.tau / 5
            _add(bullet_manager, create_bullet_angle(
                rx, ry, angle, _REL_SPIRAL_SPEED, Bullet.TYPE_RICE,
                radius=2.6, color=color, lifetime=_REL_SPIRAL_LIFETIME))
    st["burst"] += 1


def spell_kaeman_relics(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """② 冥符「Five Corrupted Relics」：五种 Relic 连成五边形绕中心旋转。

    Kaeman 悬浮屏幕上方；战场中部五种 Relic 组成旋转五边形，环绕半径缓慢
    呼吸。五颗 Relic 各自发出对应颜色的五臂螺旋弹（子弹匀速直线不旋转，
    发射角持续旋转而成螺旋状），五组螺旋交织成网，迫使玩家在中场缝隙间
    躲避。
    """
    if getattr(boss, "kaeman_relics", None) is None:
        _kaeman_relics_init(boss)
    st = boss.kaeman_relics

    # Kaeman 停留在屏幕上方中央，轻微悬浮
    boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 112 + math.sin(timer * 0.021) * 8)

    st["rot"] = (st["rot"] + _REL_SPIN) % math.tau
    st["radius"] = _REL_RADIUS * (
        1.0 + _REL_RADIUS_PULSE * math.sin(timer * _REL_RADIUS_FREQ))
    st["cy"] = _REL_CENTER_Y + math.sin(timer * 0.023) * 8

    if timer % _REL_SPIRAL_INTERVAL == 0:
        _kaeman_relics_emit(boss, bullet_manager, st)


# ---------------------------------------------------------------------------
# ③ 龙符「Withered Dragon」：枯龙巡场 + 五座雕像俯冲
#
# 枯龙在战场背景层沿固定的大型椭圆轨道高速巡场，途经屏幕边缘 / 战场中央 /
# 雕像附近时留下不同形状的腐化能量轨迹；巡场途中持续喷吐固定方向的火球与
# 灵魂碎片，与移动轨迹交织成不断变化的几何弹幕。五座不同颜色的 Dragon
# Statue 按固定顺序被点亮，提示枯龙下一次进入的区域；当枯龙轨道角接近点亮
# 雕像的方位时，雕像绽放大型弹幕爆发，枯龙沿雕像方向高速俯冲穿过整个战场
# 并留下短暂的危险轨迹。玩家需依据枯龙飞行方向、雕像位置与俯冲预告线提前
# 调整位置。
# ---------------------------------------------------------------------------
_DRAGON_GIF = os.path.join(cfg.ENEMY_SPRITES_DIR_STAGE6, "wither_king_dragon", "Dragon.gif")

_DRAGON_ORBIT_CX = cfg.BATTLE_AREA_WIDTH / 2
_DRAGON_ORBIT_CY = cfg.BATTLE_AREA_HEIGHT * 0.375
_DRAGON_ORBIT_RX = 246.0
_DRAGON_ORBIT_RY = 158.0
_DRAGON_ORBIT_SPEED = 0.0125          # 弧度/帧：枯龙高速巡场

# 五座 Dragon Statue：位置（战场内坐标）+ 对应颜色
_DRAGON_STATUES = (
    {"x": 66,  "y": 150, "color": (255, 92, 84)},     # S0 左上 赤
    {"x": 510, "y": 150, "color": (92, 172, 255)},    # S1 右上 苍蓝
    {"x": 288, "y": 640, "color": (110, 230, 120)},   # S2 下中 森绿
    {"x": 66,  "y": 470, "color": (255, 186, 70)},    # S3 左中 琥珀
    {"x": 510, "y": 470, "color": (205, 110, 255)},   # S4 右中 紫
)
# 固定点亮顺序（按轨道方位角递增：右中 → 下中 → 左中 → 左上 → 右上）
_DRAGON_STATUE_ORDER = (4, 2, 3, 0, 1)
# 每座雕像的俯冲方向（单位向量：枯龙沿此方向穿过整个战场）
_DRAGON_DIVE_DIRS = (
    (0.56, -0.83),    # S0 自左下向上右
    (-0.56, -0.83),   # S1 自右下向上左
    (0.0, -1.0),      # S2 自下向上穿过中央
    (1.0, 0.0),       # S3 自左向右横穿
    (-1.0, 0.0),      # S4 自右向左横穿
)

_DRAGON_TELEGRAPH_RANGE = 1.05    # 轨道角距雕像方位多近时点亮雕像（弧度，提前提示）
_DRAGON_DIVE_TRIGGER = 0.34       # 轨道角距雕像方位多近时触发俯冲（弧度）
_DRAGON_TELEGRAPH_FRAMES = 80     # 雕像点亮预兆时长（帧，点亮更久便于预判）
_DRAGON_DIVE_FRAMES = 42          # 俯冲穿越战场帧数
_DRAGON_POST_DIVE_GAP = 40        # 俯冲结束到下一次预兆的间隔（帧）
_DRAGON_TRAIL_MAX_AGE = 150       # 腐化能量轨迹视觉存留帧数
_DRAGON_DIVE_TRAIL_LIFE = 112     # 俯冲危险轨迹弹存留帧数


_wd_sprite_cache = {}
_wd_sprite_attempted = set()
_wd_glow_cache = {}


def _wd_glow(color, radius):
    """柔和圆形光晕（纯视觉，缓存）。"""
    key = (color, radius)
    if key not in _wd_glow_cache:
        size = max(2, radius * 2)
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        steps = max(4, radius)
        for i in range(steps):
            rr = max(1, int(radius * (1.0 - i / steps)))
            alpha = int(120 * (1.0 - i / steps) ** 1.4)
            pygame.draw.circle(surf, (*color, alpha), (radius, radius), rr)
        _wd_glow_cache[key] = surf
    return _wd_glow_cache[key]


def _get_withered_dragon_sprite(height):
    """加载枯龙贴图（GIF 首帧）并裁掉透明边距，缓存为指定高度。"""
    key = height
    if key in _wd_sprite_attempted:
        return _wd_sprite_cache.get(key)
    _wd_sprite_attempted.add(key)
    try:
        img = pygame.image.load(_DRAGON_GIF).convert_alpha()
        mask = pygame.mask.from_surface(img, threshold=24)
        rects = mask.get_bounding_rects()
        if rects:
            img = img.subsurface(rects[0].unionall(rects[1:]))
        w, h = img.get_size()
        if h <= 0:
            raise ValueError("invalid dragon sprite height")
        new_w = max(1, int(round(w * height / h)))
        img = pygame.transform.smoothscale(img, (new_w, height))
        # 轻微紫调压暗，突出「枯龙」质感
        tint = pygame.Surface(img.get_size(), pygame.SRCALPHA)
        tint.fill((140, 120, 185, 255))
        img.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        _wd_sprite_cache[key] = img
    except Exception as exc:
        print("[Stage6] Failed to load withered dragon sprite: %s" % exc)
    return _wd_sprite_cache.get(key)


_wd_outline_cache = {}


def _get_withered_dragon_outline(height, color=(235, 205, 255)):
    """枯龙剪影描边层：沿轮廓外扩 2px 的亮色边缘（缓存）。"""
    key = (height, color)
    if key in _wd_outline_cache:
        return _wd_outline_cache[key]
    sprite = _get_withered_dragon_sprite(height)
    if sprite is None:
        _wd_outline_cache[key] = None
        return None
    try:
        w, h = sprite.get_size()
        pad = 3
        mask = pygame.mask.from_surface(sprite, threshold=32)
        sil = mask.to_surface(setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
        out = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        for dx in (-2, 0, 2):
            for dy in (-2, 0, 2):
                out.blit(sil, (pad + dx, pad + dy))
        _wd_outline_cache[key] = out
    except Exception:
        _wd_outline_cache[key] = None
    return _wd_outline_cache[key]


def _wd_statue_angle(idx):
    """雕像相对轨道中心的方位角（弧度）。"""
    st = _DRAGON_STATUES[idx]
    return math.atan2(st["y"] - _DRAGON_ORBIT_CY, st["x"] - _DRAGON_ORBIT_CX)


def _wd_orbit_pos(angle):
    return (_DRAGON_ORBIT_CX + math.cos(angle) * _DRAGON_ORBIT_RX,
            _DRAGON_ORBIT_CY + math.sin(angle) * _DRAGON_ORBIT_RY)


def _wd_orbit_motion_angle(angle):
    """轨道运动方向（速度矢量角度），用于旋转枯龙贴图。"""
    vx = -math.sin(angle) * _DRAGON_ORBIT_RX * _DRAGON_ORBIT_SPEED
    vy = math.cos(angle) * _DRAGON_ORBIT_RY * _DRAGON_ORBIT_SPEED
    return math.atan2(vy, vx)


def _wd_dive_line(idx):
    """俯冲线两端：(entry, exit)——entry 为雕像后方入场端，exit 为穿越战场后的出界端。"""
    st = _DRAGON_STATUES[idx]
    dx, dy = _DRAGON_DIVE_DIRS[idx]
    pad = 90.0
    w, h = cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT
    ts = []
    if abs(dx) > 1e-6:
        ts.append((-pad - st["x"]) / dx)
        ts.append((w + pad - st["x"]) / dx)
    if abs(dy) > 1e-6:
        ts.append((-pad - st["y"]) / dy)
        ts.append((h + pad - st["y"]) / dy)
    t0, t1 = min(ts), max(ts)
    return ((st["x"] + dx * t0, st["y"] + dy * t0),
            (st["x"] + dx * t1, st["y"] + dy * t1))


def _kaeman_withered_dragon_init(boss):
    """开符初始化：五座雕像 + 枯龙轨道 + 预兆 / 俯冲状态。"""
    statues = [
        {"idx": idx, "x": st["x"], "y": st["y"], "color": st["color"],
         "lit": 0, "burst": 0}
        for idx, st in enumerate(_DRAGON_STATUES)
    ]
    start_angle = _wd_statue_angle(_DRAGON_STATUE_ORDER[-1]) - 1.2
    px, py = _wd_orbit_pos(start_angle)
    boss.kaeman_dragon = {
        "statues": statues,
        "order": list(_DRAGON_STATUE_ORDER),
        "order_pos": 0,
        "next_statue": _DRAGON_STATUE_ORDER[0],
        "angle": start_angle,
        "px": px, "py": py,
        "dragon_angle": _wd_orbit_motion_angle(start_angle),
        "dive": None,
        "telegraph": None,
        "trails": [],
        "history": [(px, py)],
        "cooldown": {"edge": 0, "center": 0, "statue": 0},
        "gap": 40,
        "phase_seed": random.uniform(0, math.tau),
    }


def _wd_statue_burst(bullet_manager, statue, player_x, player_y):
    """雕像被点亮后的短暂大型弹幕爆发。"""
    sx, sy = statue["x"], statue["y"]
    col = statue["color"]
    for i in range(22):
        a = i * math.tau / 22 + random.uniform(-0.04, 0.04)
        _add(bullet_manager, create_bullet_angle(
            sx, sy, a, 1.35, Bullet.TYPE_BIG, radius=4.0, color=col, lifetime=300))
    base = math.atan2(player_y - sy, player_x - sx)
    for i in range(5):
        a = base + (i - 2) * 0.14
        _add(bullet_manager, create_bullet_angle(
            sx, sy, a, 2.5, Bullet.TYPE_KNIFE, radius=2.4, color=col, lifetime=300))
    for i in range(10):
        a = i * math.tau / 10 + random.uniform(-0.08, 0.08)
        _add(bullet_manager, create_bullet_angle(
            sx, sy, a, 2.0, Bullet.TYPE_RICE, radius=2.1, color=col, lifetime=260))


def _wd_orbit_fire(bullet_manager, x, y, timer, seed):
    """巡场喷吐：固定方向火球 / 灵魂碎片 + 垂直运动的切向刀扇。

    发射方向随计时缓慢旋转（不自机狙），枯龙沿轨道移动使固定方向弹
    交织成不断变化的几何弹幕。
    """
    base = timer * 0.016 + seed
    if timer % 9 == 0:
        _add(bullet_manager, create_bullet_angle(
            x, y, base, 1.9, Bullet.TYPE_BIG, radius=3.8,
            color=(110, 235, 140), lifetime=430))
    if timer % 12 == 0:
        _add(bullet_manager, create_bullet_angle(
            x, y, base + math.pi / 3, 2.5, Bullet.TYPE_CIRCLE, radius=2.5,
            color=(205, 160, 255), lifetime=430))
    if timer % 72 == 0:
        tang = base + math.pi / 2
        for i in range(5):
            a = tang + (i - 2) * 0.16
            _add(bullet_manager, create_bullet_angle(
                x, y, a, 2.1, Bullet.TYPE_KNIFE, radius=2.4,
                color=(255, 160, 120), lifetime=380))


def _wd_leave_trail(bullet_manager, d, x, y, move_ang, timer):
    """枯龙途经边缘 / 中央 / 雕像附近时留下不同形状的腐化能量轨迹。"""
    w, h = cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT
    cd = d["cooldown"]
    for key in cd:
        cd[key] = max(0, cd[key] - 1)

    # 雕像附近：朝向雕像的短弧
    for st in d["statues"]:
        if cd["statue"] > 0:
            break
        if math.hypot(st["x"] - x, st["y"] - y) < 62:
            cd["statue"] = 46
            ang = math.atan2(st["y"] - y, st["x"] - x)
            pts = []
            for k in range(5):
                a = ang + (k - 2) * 0.30
                bx = x + math.cos(a) * (26 + k * 7)
                by = y + math.sin(a) * (26 + k * 7)
                pts.append((bx, by))
                if k % 2 == 0:
                    _add(bullet_manager, create_bullet_angle(
                        bx, by, 0.0, 0.0, Bullet.TYPE_CIRCLE, radius=2.4,
                        color=st["color"], lifetime=120))
            d["trails"].append({"pts": pts, "age": 0, "max_age": _DRAGON_TRAIL_MAX_AGE,
                                "color": st["color"]})
            break

    # 屏幕边缘：沿运动切线的短线
    if cd["edge"] <= 0 and (x < 42 or x > w - 42 or y < 52 or y > h - 42):
        cd["edge"] = 32
        tang = move_ang + math.pi / 2
        pts = []
        for k in range(3):
            bx = x + math.cos(tang) * (k - 1) * 17
            by = y + math.sin(tang) * (k - 1) * 17
            pts.append((bx, by))
            if k != 1:
                _add(bullet_manager, create_bullet_angle(
                    bx, by, 0.0, 0.0, Bullet.TYPE_CIRCLE, radius=2.4,
                    color=(120, 230, 150), lifetime=120))
        d["trails"].append({"pts": pts, "age": 0, "max_age": _DRAGON_TRAIL_MAX_AGE,
                            "color": (120, 230, 150)})

    # 战场中央：绕点小圆环
    if cd["center"] <= 0 and math.hypot(x - w / 2, y - h * 0.52) < 78:
        cd["center"] = 44
        cang = timer * 0.07
        pts = []
        for k in range(8):
            a = cang + k * math.tau / 8
            bx = x + math.cos(a) * 24
            by = y + math.sin(a) * 24
            pts.append((bx, by))
            if k % 2 == 0:
                _add(bullet_manager, create_bullet_angle(
                    bx, by, 0.0, 0.0, Bullet.TYPE_CIRCLE, radius=2.1,
                    color=(200, 150, 255), lifetime=120))
        d["trails"].append({"pts": pts, "age": 0, "max_age": _DRAGON_TRAIL_MAX_AGE,
                            "color": (200, 150, 255)})


def _wd_start_dive(d):
    """枯龙离开轨道，沿点亮雕像的方向高速俯冲穿过整个战场。"""
    idx = d["next_statue"]
    entry, exit_pt = _wd_dive_line(idx)
    d["dive"] = {
        "statue": idx,
        "sx": entry[0], "sy": entry[1],
        "ex": exit_pt[0], "ey": exit_pt[1],
        "t": 0,
        "frames": _DRAGON_DIVE_FRAMES,
    }
    d["telegraph"] = None


def _wd_update_dive(bullet_manager, d, player_x, player_y):
    """推进俯冲：沿途留下短暂危险轨迹 + 补喷自机狙，结束回到轨道。"""
    dv = d["dive"]
    dv["t"] += 1
    prog = min(1.0, dv["t"] / max(1, dv["frames"]))
    x = dv["sx"] + (dv["ex"] - dv["sx"]) * prog
    y = dv["sy"] + (dv["ey"] - dv["sy"]) * prog
    d["px"], d["py"] = x, y
    d["dragon_angle"] = math.atan2(dv["ey"] - dv["sy"], dv["ex"] - dv["sx"])

    if dv["t"] % 2 == 0:
        perp = d["dragon_angle"] + math.pi / 2
        col = _DRAGON_STATUES[dv["statue"]]["color"]
        for k in (-1, 1):
            bx = x + math.cos(perp) * k * 6
            by = y + math.sin(perp) * k * 6
            _add(bullet_manager, create_bullet_angle(
                bx, by, 0.0, 0.0, Bullet.TYPE_CIRCLE, radius=2.6,
                color=col, lifetime=_DRAGON_DIVE_TRAIL_LIFE))
    if dv["t"] % 8 == 0:
        base = math.atan2(player_y - y, player_x - x)
        col = _DRAGON_STATUES[dv["statue"]]["color"]
        for off in (-0.12, 0.12):
            _add(bullet_manager, create_bullet_angle(
                x, y, base + off, 2.8, Bullet.TYPE_KNIFE, radius=2.4,
                color=col, lifetime=360))

    if dv["t"] >= dv["frames"]:
        exit_ang = math.atan2(dv["ey"] - _DRAGON_ORBIT_CY,
                              dv["ex"] - _DRAGON_ORBIT_CX)
        d["dive"] = None
        d["angle"] = exit_ang
        d["order_pos"] = (d["order_pos"] + 1) % len(d["order"])
        d["next_statue"] = d["order"][d["order_pos"]]
        d["gap"] = _DRAGON_POST_DIVE_GAP


def spell_kaeman_withered_dragon(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """③ 龙符「Withered Dragon」：枯龙巡场 + 五座雕像俯冲。

    枯龙在背景层沿固定大型椭圆轨道高速巡场，途经边缘 / 中央 / 雕像附近时
    留下不同形状的腐化能量轨迹；五座 Dragon Statue 按固定顺序点亮预兆，
    枯龙轨道角接近点亮雕像方位时，雕像爆发大型弹幕，枯龙沿雕像方向高速
    俯冲穿过整个战场并留下短暂危险轨迹。
    """
    if getattr(boss, "kaeman_dragon", None) is None:
        _kaeman_withered_dragon_init(boss)
    d = boss.kaeman_dragon

    # Kaeman 悬浮于屏幕上方中央（枯龙在背景层绕场飞行）
    boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 118 + math.sin(timer * 0.021) * 6)

    # 雕像点亮 / 爆发闪光状态老化
    for st in d["statues"]:
        if st["lit"] > 0:
            st["lit"] -= 1
        if st["burst"] > 0:
            st["burst"] -= 1
    for t in d["trails"][:]:
        t["age"] += 1
        if t["age"] >= t["max_age"]:
            d["trails"].remove(t)

    if d["dive"] is not None:
        _wd_update_dive(bullet_manager, d, player_x, player_y)
        d["history"].append((d["px"], d["py"]))
        if len(d["history"]) > 90:
            d["history"] = d["history"][-90:]
        return

    if d["gap"] > 0:
        d["gap"] -= 1

    d["angle"] = (d["angle"] + _DRAGON_ORBIT_SPEED) % math.tau
    x, y = _wd_orbit_pos(d["angle"])
    d["px"], d["py"] = x, y
    d["dragon_angle"] = _wd_orbit_motion_angle(d["angle"])

    _wd_orbit_fire(bullet_manager, x, y, timer, d["phase_seed"])
    _wd_leave_trail(bullet_manager, d, x, y, d["dragon_angle"], timer)

    # 雕像预兆 + 俯冲触发：雕像按固定顺序点亮，提示枯龙下一次进入的区域
    st_idx = d["next_statue"]
    target_ang = _wd_statue_angle(st_idx)
    diff = (target_ang - d["angle"]) % math.tau
    if d["telegraph"] is None and d["gap"] <= 0 and diff < _DRAGON_TELEGRAPH_RANGE:
        d["telegraph"] = {"statue": st_idx, "age": 0}
        for st in d["statues"]:
            if st["idx"] == st_idx:
                st["lit"] = _DRAGON_TELEGRAPH_FRAMES
    if d["telegraph"] is not None:
        tg = d["telegraph"]
        tg["age"] += 1
        if diff < _DRAGON_DIVE_TRIGGER or tg["age"] >= _DRAGON_TELEGRAPH_FRAMES + 26:
            for st in d["statues"]:
                if st["idx"] == tg["statue"]:
                    st["burst"] = 26
                    _wd_statue_burst(bullet_manager, st, player_x, player_y)
            _wd_start_dive(d)

    d["history"].append((x, y))
    if len(d["history"]) > 90:
        d["history"] = d["history"][-90:]

# ---------------------------------------------------------------------------
# ④ 裂符「Dimensional Slash」：空间裂痕斩击 + 触手牵引
#
# Kaeman 周围不断生成短暂存在的空间裂痕：裂痕先以细小红色标记预警，约 1.2s
# 后沿固定方向延伸成平滑贯穿战场的十字 / 斜线 / 多次函数曲线斩击，
# 保证会扫过玩家活动区域；
# 斩击结束后裂痕不会立即消失，留下大量缓慢扩散的黑红碎片弹，迫使玩家
# 在密集弹幕中持续走位。随符卡推进生成间隔缩短、出现双裂痕，多道裂痕
# 交错出现。
# 同时 Kaeman 周围设有极小的危险范围：玩家过度靠近时出现触手预警，并迅速
# 被拖向 Kaeman。
# ---------------------------------------------------------------------------
_SLASH_WARN = 72                # 预警帧数（约 1.2s）
_SLASH_EXTEND = 14              # 斩击延伸帧数
_SLASH_BEAM_LIFE = 30           # 危险光束存留帧数（延伸后不立即消失）
_SLASH_FADE = 20                # 裂痕视觉淡出帧数
_SLASH_FIRST_AT = 80            # 第一道裂痕出现时间（帧）
_SLASH_INTERVAL = 84            # 初始生成间隔（帧）
_SLASH_INTERVAL_MIN = 36        # 最小生成间隔
_SLASH_CURVE_AT = 2              # 第几道裂痕起出现曲线斩击
_SLASH_DOUBLE_AT = 6            # 第几道裂痕起可能出现双裂痕
_SLASH_FRAGMENTS = 16           # 每次斩击后的黑红碎片弹数量
_SLASH_FRAG_SPEED = (0.9, 1.9)  # 碎片扩散速度范围
_SLASH_FRAG_LIFE = 360          # 碎片存留帧数
_SLASH_MARK_COLOR = (255, 84, 92)  # 预警细小红色标记
_SLASH_FRAG_COLORS = ((150, 22, 34), (190, 38, 52), (118, 14, 26))

# 触手危险范围
_SLASH_TENTACLE_R = 104         # Kaeman 周围危险半径（很小）
_SLASH_TENTACLE_WARN = 26       # 触手预警帧数
_SLASH_TENTACLE_PULL = 14       # 拉拽帧数
_SLASH_TENTACLE_COOLDOWN = 130  # 拉拽后的冷却帧数


def _slash_ray(ox, oy, angle, length, rng, step=36.0):
    """从原点沿固定方向生成一条带轻微锯齿的射线路径。"""
    pts = [(ox, oy)]
    n = max(1, int(length / step))
    for i in range(1, n + 1):
        f = i / float(n)
        px = ox + math.cos(angle) * length * f
        py = oy + math.sin(angle) * length * f
        if 0 < i < n:
            jx = math.cos(angle + math.pi / 2)
            jy = math.sin(angle + math.pi / 2)
            j = rng.uniform(-6.5, 6.5)
            px += jx * j
            py += jy * j
        pts.append((px, py))
    return pts


def _slash_line_paths(kind, ox, oy, angle, rng, px, py):
    """十字 / 斜线斩击路径：平滑贯穿整个战场的全屏直线段。

    斜线经过玩家附近锚点；十字中心取下部中场。路径两端伸入屏幕外的边界，
    让斩击真正横跨整个战斗区域。
    """
    w = cfg.BATTLE_AREA_WIDTH
    h = cfg.BATTLE_AREA_HEIGHT
    pad = 90.0

    def full_segment(cx, cy, ang):
        """过 (cx, cy) 沿 ang 的直线与扩大的战场边界相交的两端点。"""
        dx, dy = math.cos(ang), math.sin(ang)
        ts = []
        if abs(dx) > 1e-6:
            ts.append((-pad - cx) / dx)
            ts.append((w + pad - cx) / dx)
        if abs(dy) > 1e-6:
            ts.append((-pad - cy) / dy)
            ts.append((h + pad - cy) / dy)
        t0, t1 = min(ts), max(ts)
        if t1 - t0 > 1400.0:      # 浅角度下限制总长，让延伸扫过整个屏幕即可
            t0, t1 = -700.0, 700.0
        return ((cx + dx * t0, cy + dy * t0),
                (cx + dx * t1, cy + dy * t1))

    if kind == "cross":
        # 十字中心取下部中场，让十字斩击横跨玩家活动区域
        cx0 = rng.uniform(w * 0.24, w * 0.76)
        cy0 = rng.uniform(360, 470)
        a0 = rng.uniform(-0.9, 0.9)  # 主臂接近水平，副臂接近竖直
        return [list(full_segment(cx0, cy0, a0)),
                list(full_segment(cx0, cy0, a0 + math.pi / 2))]
    # 斜线：全屏直线段，锚点取玩家附近，确保下方玩家必须走位
    ax = min(w - 70.0, max(70.0, px + rng.uniform(-70, 70)))
    ay = min(560.0, max(210.0, py + rng.uniform(-36, 64)))
    return [list(full_segment(ax, ay, angle))]


def _slash_curve_path(ox, oy, rng, px, py):
    """多次函数曲线斩击路径：三次贝塞尔样条，平滑贯穿整个战场。

    曲线从屏幕上缘延伸到下缘，横向控制点形成平滑的 C 形 / S 形，
    中段偏向玩家所在区域，保证下方玩家需要走位。
    """
    w = cfg.BATTLE_AREA_WIDTH
    h = cfg.BATTLE_AREA_HEIGHT
    pad = 90.0
    mid = min(w - 60.0, max(60.0, px + rng.uniform(-100, 100)))
    p0 = (rng.uniform(w * 0.12, w * 0.88), -pad)
    p1 = (mid + rng.uniform(-140, 140), h * 0.26)
    p2 = (mid + rng.uniform(-140, 140), h * 0.64)
    p3 = (rng.uniform(w * 0.12, w * 0.88), h + pad)

    # 按控制多边形长度估算采样数，保证曲线足够平滑
    poly = (math.hypot(p1[0] - p0[0], p1[1] - p0[1]) +
            math.hypot(p2[0] - p1[0], p2[1] - p1[1]) +
            math.hypot(p3[0] - p2[0], p3[1] - p2[1]))
    n = max(24, min(90, int(poly / 22.0)))
    pts = []
    for i in range(n + 1):
        t = i / float(n)
        it = 1.0 - t
        x = ((it ** 3) * p0[0] + 3.0 * it * it * t * p1[0]
             + 3.0 * it * t * t * p2[0] + t ** 3 * p3[0])
        y = ((it ** 3) * p0[1] + 3.0 * it * it * t * p1[1]
             + 3.0 * it * t * t * p2[1] + t ** 3 * p3[1])
        pts.append((x, y))
    return [pts]


def _slash_path_metrics(paths):
    """计算每条路径的段长与总长。"""
    seg_lens = []
    total = 0.0
    for path in paths:
        segs = []
        for i in range(len(path) - 1):
            sl = math.hypot(path[i + 1][0] - path[i][0],
                            path[i + 1][1] - path[i][1])
            segs.append(sl)
            total += sl
        seg_lens.append(segs)
    return seg_lens, total


def _slash_pt_at(path, seg_lens, target_len):
    """路径上距起点 target_len 处的插值点。"""
    covered = 0.0
    for i, sl in enumerate(seg_lens):
        if covered + sl >= target_len:
            f = (target_len - covered) / max(1e-6, sl)
            return (path[i][0] + (path[i + 1][0] - path[i][0]) * f,
                    path[i][1] + (path[i + 1][1] - path[i][1]) * f)
        covered += sl
    return path[-1]


def _slash_reveal_targets(crack, frac):
    """按全局进度把每条路径应显示的长度摊开（十字各臂同步延伸）。"""
    target = frac * crack["total_len"]
    remaining = target
    out = []
    for pl in crack["path_lens"]:
        got = min(pl, max(0.0, remaining))
        remaining = max(0.0, remaining - pl)
        out.append(got)
    return out


def _slash_subpath_points(path, seg_lens, target_len):
    """取路径上距起点 target_len 为止的子点列表（绘制用）。"""
    pts = [path[0]]
    covered = 0.0
    for i, sl in enumerate(seg_lens):
        if covered + sl <= target_len:
            pts.append(path[i + 1])
            covered += sl
        else:
            if target_len - covered > 0.5:
                f = (target_len - covered) / max(1e-6, sl)
                pts.append((path[i][0] + (path[i + 1][0] - path[i][0]) * f,
                            path[i][1] + (path[i + 1][1] - path[i][1]) * f))
            break
    return pts


def _slash_spawn_mark(bullet_manager, x, y, color, lifetime=20):
    """细小红色预警标记（无判定）。"""
    b = create_bullet_angle(x, y, 0.0, 0.0, Bullet.TYPE_CIRCLE, radius=3.0,
                            color=color, lifetime=lifetime)
    b.harmless = True
    _add(bullet_manager, b)


def _slash_spawn_beam(bullet_manager, p0, p1):
    """两点之间的危险光束线段（空间裂痕的伤害判定）。"""
    x0, y0 = p0
    x1, y1 = p1
    dx = x1 - x0
    dy = y1 - y0
    dist = math.hypot(dx, dy)
    if dist < 5:
        return
    ang = math.atan2(dy, dx)
    b = create_bullet_angle(x0, y0, ang, 0.0, Bullet.TYPE_BEAM, radius=3.0,
                            color=(255, 70, 82), lifetime=_SLASH_BEAM_LIFE)
    b.angle = ang
    b.beam_length = dist
    _add(bullet_manager, b)


def _slash_reveal_path(bullet_manager, crack, pi, rev_len, target_len):
    """为路径 pi 上 [rev_len, target_len] 区间生成危险光束。"""
    path = crack["paths"][pi]
    segs = crack["seg_lens"][pi]
    covered = 0.0
    for i, sl in enumerate(segs):
        seg_end = covered + sl
        if seg_end <= rev_len:
            covered = seg_end
            continue
        if seg_end <= target_len:
            if sl > 4:
                _slash_spawn_beam(bullet_manager, path[i], path[i + 1])
        else:
            if target_len - covered > 3:
                f = (target_len - covered) / max(1e-6, sl)
                p = (path[i][0] + (path[i + 1][0] - path[i][0]) * f,
                     path[i][1] + (path[i + 1][1] - path[i][1]) * f)
                _slash_spawn_beam(bullet_manager, path[i], p)
            covered = seg_end
            break
        covered = seg_end


def _slash_spawn_fragments(bullet_manager, crack):
    """斩击结束后留下大量黑红碎片弹，向四周飞散（不追踪玩家）。"""
    rng = crack["rng"]
    for _ in range(_SLASH_FRAGMENTS):
        pi = rng.randrange(len(crack["paths"]))
        path = crack["paths"][pi]
        segs = crack["seg_lens"][pi]
        plen = crack["path_lens"][pi]
        x = y = 0.0
        for _ in range(10):
            tl = rng.uniform(plen * 0.05, plen * 0.98)
            x, y = _slash_pt_at(path, segs, tl)
            x += rng.uniform(-8, 8)
            y += rng.uniform(-8, 8)
            if 12 <= x <= cfg.BATTLE_AREA_WIDTH - 12 and 12 <= y <= cfg.BATTLE_AREA_HEIGHT - 12:
                break
        x = max(12.0, min(cfg.BATTLE_AREA_WIDTH - 12.0, x))
        y = max(12.0, min(cfg.BATTLE_AREA_HEIGHT - 12.0, y))
        col = rng.choice(_SLASH_FRAG_COLORS)
        ang = rng.uniform(0, math.tau)
        spd = rng.uniform(*_SLASH_FRAG_SPEED)
        b = create_bullet_angle(x, y, ang, spd, Bullet.TYPE_RICE, radius=2.7,
                                color=col, lifetime=_SLASH_FRAG_LIFE)
        b.wobble_amp = 1.2
        b.wobble_freq = 0.02
        b.wobble_phase = rng.uniform(0, math.tau)
        _add(bullet_manager, b)


def _slash_create_crack(boss, bullet_manager, st, seed, player_x, player_y):
    """在 Kaeman 周围生成一道空间裂痕（含覆盖战场的固定方向路径）。"""
    rng = random.Random(50000 + seed)
    ox = _clamp_x(boss.x + rng.uniform(-1.0, 1.0) * rng.uniform(30, 100))
    oy = _clamp_y(boss.y + rng.uniform(-1.0, 1.0) * rng.uniform(14, 78))
    count = st["spawn_count"]
    kinds = ["diag"]
    if count >= 2:
        kinds.append("cross")
    if count >= _SLASH_CURVE_AT:
        kinds.append("curve")
    kind = rng.choice(kinds)
    angle = rng.uniform(0, math.tau)
    if kind == "curve":
        paths = _slash_curve_path(ox, oy, rng, player_x, player_y)
        if paths:
            # 起点在屏幕外，取曲线在战场内的第一点作为斩击起点
            w_a = cfg.BATTLE_AREA_WIDTH
            h_a = cfg.BATTLE_AREA_HEIGHT
            for (cx0, cy0) in paths[0]:
                if 12 <= cx0 <= w_a - 12 and 12 <= cy0 <= h_a - 12:
                    ox, oy = cx0, cy0
                    break
    else:
        paths = _slash_line_paths(kind, ox, oy, angle, rng, player_x, player_y)
    if not paths:
        return
    seg_lens, total_len = _slash_path_metrics(paths)
    if total_len < 60:
        return
    st["cracks"].append({
        "x": ox, "y": oy,
        "kind": kind,
        "angle": angle,
        "t": 0,
        "paths": paths,
        "seg_lens": seg_lens,
        "path_lens": [sum(s) for s in seg_lens],
        "total_len": total_len,
        "path_revealed": [0.0] * len(paths),
        "fragments_spawned": False,
        "rng": rng,
    })
    _slash_spawn_mark(bullet_manager, ox, oy, _SLASH_MARK_COLOR,
                      lifetime=_SLASH_WARN + 6)


def _slash_update_cracks(boss, bullet_manager):
    """驱动所有裂痕：预警标记 -> 延伸斩击 -> 碎片残留 -> 淡出。"""
    st = boss.kaeman_slash
    for crack in st["cracks"][:]:
        crack["t"] += 1
        t = crack["t"]
        rng = crack["rng"]
        if t < _SLASH_WARN:
            # 预警：未来裂痕路径的细小红色标记改由 _draw_kaeman_slash 直接绘制
            # （保证密度与屏幕内可见性），此处只保留起点浮动标记。
            if t % 5 == 0:
                _slash_spawn_mark(bullet_manager, crack["x"], crack["y"],
                                  (255, 120, 128), lifetime=26)
        elif t < _SLASH_WARN + _SLASH_EXTEND:
            # 斩击：沿固定方向逐帧延伸危险光束
            frac = (t - _SLASH_WARN) / float(_SLASH_EXTEND)
            targets = _slash_reveal_targets(crack, frac)
            for pi in range(len(crack["paths"])):
                tl = targets[pi]
                rev = crack["path_revealed"][pi]
                if tl > rev + 0.5:
                    _slash_reveal_path(bullet_manager, crack, pi, rev, tl)
                    crack["path_revealed"][pi] = tl
            if t == _SLASH_WARN:
                # 起点爆闪：斩击触发瞬间的反馈
                for k in range(6):
                    a = k * math.tau / 6 + rng.uniform(-0.2, 0.2)
                    mx = crack["x"] + math.cos(a) * 18
                    my = crack["y"] + math.sin(a) * 18
                    _slash_spawn_mark(bullet_manager, mx, my,
                                      (255, 160, 170), lifetime=10)
        elif not crack["fragments_spawned"]:
            # 斩击结束：裂痕不立即消失，留下缓慢扩散的黑红碎片弹
            crack["fragments_spawned"] = True
            _slash_spawn_fragments(bullet_manager, crack)
        if t >= _SLASH_WARN + _SLASH_EXTEND + _SLASH_BEAM_LIFE + _SLASH_FADE:
            st["cracks"].remove(crack)


def _kaeman_slash_init(boss):
    boss.kaeman_slash = {
        "cracks": [],
        "next_spawn": _SLASH_FIRST_AT,
        "spawn_count": 0,
        "double_pending": 0,
        "tentacle": None,
        "tentacle_cd": 0,
        "grab_hit_active": False,
        "last_px": 0.0,
        "last_py": 0.0,
    }


def _slash_spawn_crack(boss, bullet_manager, st, player_x, player_y):
    """生成一道裂痕；后期双裂痕交错出现（14 帧后追加第二道）。"""
    _slash_create_crack(boss, bullet_manager, st, st["spawn_count"] * 37 + 5,
                        player_x, player_y)
    st["spawn_count"] += 1
    if st["spawn_count"] >= _SLASH_DOUBLE_AT and st["spawn_count"] % 3 == 0:
        st["double_pending"] = 14


def _slash_update_tentacle(boss, bullet_manager, player_x, player_y):
    """Kaeman 周围危险范围：触手预警 -> 迅速把玩家拉向 Kaeman。"""
    st = boss.kaeman_slash
    t = st.get("tentacle")
    if t is not None:
        t["t"] += 1
        t["px"], t["py"] = player_x, player_y
        if t["phase"] == "warn":
            if t["t"] >= _SLASH_TENTACLE_WARN:
                t["phase"] = "pull"
                t["t"] = 0
        elif t["phase"] == "pull":
            # 迅速把玩家拉向 Kaeman（逐帧覆盖自机位置）
            dx = boss.x - player_x
            dy = boss.y - player_y
            t["teleport_target"] = (player_x + dx * 0.26,
                                    player_y + dy * 0.26)
            if t["t"] >= _SLASH_TENTACLE_PULL or math.hypot(dx, dy) < 14.0:
                t["phase"] = "release"
                t["t"] = 0
                st["grab_hit_active"] = True   # 被拖到怀中：中弹
                out_ang = math.atan2(player_y - boss.y, player_x - boss.x)
                t["release_target"] = (boss.x + math.cos(out_ang) * 92,
                                       boss.y + math.sin(out_ang) * 92)
        else:  # release：被拉入怀中后弹开一小段
            if t["t"] == 1:
                t["teleport_target"] = t["release_target"]
            if t["t"] >= 3:
                st["tentacle"] = None
                st["tentacle_cd"] = _SLASH_TENTACLE_COOLDOWN
        return

    if st["tentacle_cd"] > 0:
        st["tentacle_cd"] -= 1
        return

    # 危险范围：玩家过于靠近 Kaeman -> 触手预警
    if math.hypot(player_x - boss.x, player_y - boss.y) < _SLASH_TENTACLE_R:
        st["tentacle"] = {
            "phase": "warn", "t": 0,
            "px": player_x, "py": player_y,
            "teleport_target": None, "release_target": None,
        }


def spell_kaeman_dimensional_slash(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """④ 裂符「Dimensional Slash」：空间裂痕斩击 + 触手牵引。"""
    if getattr(boss, "kaeman_slash", None) is None:
        _kaeman_slash_init(boss)
    st = boss.kaeman_slash
    st["last_px"], st["last_py"] = player_x, player_y

    # Kaeman 悬浮于屏幕上方中央（裂痕在其周围生成）
    boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 118 + math.sin(timer * 0.021) * 6)

    # 生成节奏：随符卡推进缩短间隔，多道裂痕交错出现
    if st["next_spawn"] <= 0:
        _slash_spawn_crack(boss, bullet_manager, st, player_x, player_y)
        interval = max(_SLASH_INTERVAL_MIN,
                       _SLASH_INTERVAL - st["spawn_count"] * 3)
        st["next_spawn"] = interval
    else:
        st["next_spawn"] -= 1

    # 双裂痕：第一道出现 14 帧后交错追加第二道
    if st["double_pending"] > 0:
        st["double_pending"] -= 1
        if st["double_pending"] == 0:
            _slash_create_crack(boss, bullet_manager, st,
                                st["spawn_count"] * 37 + 11,
                                player_x, player_y)
            st["spawn_count"] += 1

    _slash_update_cracks(boss, bullet_manager)
    _slash_update_tentacle(boss, bullet_manager, player_x, player_y)


# ---------------------------------------------------------------------------
# ⑤ 王符「Atomizing Ray」：原子化旋转扫射射线
#
# Kaeman 悬浮屏幕上方开始蓄力，出现一条明显的激光预警线；发射后光束以较慢
# 速度持续旋转，逐帧扫过战场，玩家必须沿着尚未被扫过的安全扇区移动。
# 第 N 轮共有 N 条光束均分 360°，本轮只需旋转 360/N 度即扫遍全场（图案
# 恰好平移一格后重复）；每轮旋转时长恒定（与第一轮相等），轮间立即衔接，
# 下一轮以「玩家后面的那条光线」为基准原地不动，其余光束围绕它重新均分。
# 被光束扫过的区域会残留大量缓慢扩散的黑红能量弹，使玩家无法简单地绕边
# 永久躲避。随轮数增加光束数量不断增多，安全扇区不断被压缩。
# ---------------------------------------------------------------------------
_ATOM_CHARGE = 104                 # 首轮蓄力时长（帧）
_ATOM_CYCLE = 540                  # 每轮扫射时长（帧，恒定，与第一轮相等）
_ATOM_MAX_BEAMS = 6                # 光束数量上限（每轮 +1 条）
_ATOM_FORM = 10                    # 轮间重排时光束成形闪光帧数
_ATOM_HIT_RADIUS = 8.0             # 光束判定半宽（px，另加玩家判定点半径）
_ATOM_BEAM_EDGE = 60               # 光束长度超出战场最远角的余量（px）
_ATOM_RESIDUE_INTERVAL = 10        # 残留黑红能量弹生成间隔（帧，整体密度减半）
_ATOM_RESIDUE_STEP = 46            # 沿光束的生成间距（px）
_ATOM_RESIDUE_ORIGIN = 34          # 光束原点附近不撒残留弹的距离（px）
_ATOM_RESIDUE_SPEED = (0.16, 0.72)  # 残留弹缓慢扩散速度范围
_ATOM_RESIDUE_LIFE = 300           # 残留弹存留帧数
_ATOM_RESIDUE_WOBBLE = (0.9, 2.4)  # 残留弹蛇形摆动幅度范围
_ATOM_RESIDUE_COLORS = ((148, 18, 32), (192, 34, 52), (112, 12, 24), (86, 8, 18))


def _kaeman_atomize_init(boss):
    """开符初始化：首轮蓄力 -> 逐轮扫射（360/N 度，光束数 +1，立即衔接）。"""
    boss.kaeman_atomize = {
        "phase": "charge",          # charge（仅首轮）/ sweep
        "t": 0,                     # 当前阶段帧计数
        "round": 0,                 # 已完成扫描轮数
        "dir": 1,                   # +1=顺时针 / -1=逆时针（屏幕坐标下角度递增为顺时针）
        "beam_count": 1,            # 本轮光束数量（round+1，上限 _ATOM_MAX_BEAMS）
        "angles": [math.pi / 2],    # 本轮各光束当前角度（均分 360°）
        "angle": math.pi / 2,       # 光束当前角度（朝下）
        "ref_angle": math.pi / 2,   # 本轮基准光束角度（玩家后面的那条光线）
        "swept": 0.0,               # 本轮已扫过角度（0 -> 360/N）
        "bx": boss.x, "by": boss.y, # 光束原点（跟随 Kaeman）
        "length": 680.0,            # 光束长度（覆盖全场）
        "hit_radius": _ATOM_HIT_RADIUS,
        "beam_active": False,       # 光束是否处于致命扫射状态
        "charge_prog": 0.0,         # 蓄力进度（0~1，预警线亮度用）
    }


def _atomize_geometry(st, boss):
    """光束原点跟随 Kaeman；长度覆盖战场最远角加余量。"""
    bx, by = boss.x, boss.y
    far = 0.0
    for px, py in ((0.0, 0.0), (cfg.BATTLE_AREA_WIDTH, 0.0),
                   (0.0, cfg.BATTLE_AREA_HEIGHT),
                   (cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT)):
        d = math.hypot(bx - px, by - py)
        if d > far:
            far = d
    st["bx"], st["by"] = bx, by
    st["length"] = far + _ATOM_BEAM_EDGE


def _atomize_speed(st):
    """本轮光束角速度：每轮时长恒定（_ATOM_CYCLE），本轮只转 360/N 度。"""
    return math.tau / st["beam_count"] / _ATOM_CYCLE


def _atomize_beam_count(st):
    """本轮光束数量：每完成一轮 +1 条（1 -> 2 -> 3 ...），上限 _ATOM_MAX_BEAMS。"""
    return min(st["round"] + 1, _ATOM_MAX_BEAMS)


def _atomize_update_angles(st):
    """按本轮光束数量把 360° 均分，刷新各光束角度。"""
    count = _atomize_beam_count(st)
    st["beam_count"] = count
    st["angles"] = [st["angle"] + k * math.tau / count
                    for k in range(count)]
    return st["angles"]


def _atomize_residue_interval(st):
    """残留弹生成间隔（光束变多时拉长，避免总弹量失控；密度减半）。"""
    return _ATOM_RESIDUE_INTERVAL + 4 * (st["beam_count"] - 1)


def _atomize_residue_step(st):
    """残留弹沿光束的生成间距（光束变多时拉大）。"""
    return _ATOM_RESIDUE_STEP + 6 * (st["beam_count"] - 1)


def _atomize_trailing_angle(st, player_x, player_y):
    """玩家后面的那条光束角度：顺时针方向距玩家最近、位于玩家后方的光束。"""
    pa = math.atan2(player_y - st["by"], player_x - st["bx"]) % math.tau
    best_ang = st["angles"][0] % math.tau
    best_diff = math.tau
    for ang in st["angles"]:
        a = ang % math.tau
        diff = (pa - a) % math.tau   # 该光束到玩家的顺时针弧长（越小越靠后）
        if diff < best_diff:
            best_diff = diff
            best_ang = a
    return best_ang


def _atomize_spawn_residue(bullet_manager, st):
    """沿当前全部光束撒下缓慢扩散的黑红能量弹（扫过区域的残留）。"""
    bx, by = st["bx"], st["by"]
    length = st["length"]
    step = _atomize_residue_step(st)
    for angle in st["angles"]:
        cx, cy = math.cos(angle), math.sin(angle)
        d = _ATOM_RESIDUE_ORIGIN
        while d < length:
            x = bx + cx * d + random.uniform(-12, 12)
            y = by + cy * d + random.uniform(-12, 12)
            if (10.0 <= x <= cfg.BATTLE_AREA_WIDTH - 10.0
                    and 10.0 <= y <= cfg.BATTLE_AREA_HEIGHT - 10.0):
                b = create_bullet_angle(
                    x, y, random.uniform(0.0, math.tau),
                    random.uniform(*_ATOM_RESIDUE_SPEED),
                    Bullet.TYPE_RICE, radius=2.6,
                    color=random.choice(_ATOM_RESIDUE_COLORS),
                    lifetime=_ATOM_RESIDUE_LIFE)
                b.wobble_amp = random.uniform(*_ATOM_RESIDUE_WOBBLE)
                b.wobble_freq = random.uniform(0.014, 0.042)
                b.wobble_phase = random.uniform(0.0, math.tau)
                _add(bullet_manager, b)
            d += step


def _atomize_ray_exit(bx, by, angle, length):
    """射线与战场矩形边界的交点（世界坐标）；无交点时返回射线端点。"""
    dx, dy = math.cos(angle), math.sin(angle)
    w, h = cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT
    t_best = None
    for fixed, axis in ((0.0, "x"), (w, "x"), (0.0, "y"), (h, "y")):
        if axis == "x":
            if abs(dx) < 1e-9:
                continue
            tt = (fixed - bx) / dx
        else:
            if abs(dy) < 1e-9:
                continue
            tt = (fixed - by) / dy
        if tt <= 1e-9 or tt > length:
            continue
        ix = bx + dx * tt
        iy = by + dy * tt
        if -1e-6 <= ix <= w + 1e-6 and -1e-6 <= iy <= h + 1e-6:
            if t_best is None or tt < t_best:
                t_best = tt
    if t_best is None:
        return bx + dx * length, by + dy * length
    return bx + dx * t_best, by + dy * t_best


def spell_kaeman_atomize_ray(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """⑤ 王符「Atomizing Ray」：旋转扫射射线，每轮只转 360/N 度并光束 +1。"""
    if getattr(boss, "kaeman_atomize", None) is None:
        _kaeman_atomize_init(boss)
    st = boss.kaeman_atomize

    # Kaeman 悬浮于屏幕中间偏上位置，轻微悬浮（光束由此向四周放射）
    boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 305 + math.sin(timer * 0.021) * 8)
    _atomize_geometry(st, boss)

    st["t"] += 1
    t = st["t"]

    if st["phase"] == "charge":
        # 仅首轮蓄力：预警线逐渐亮起，蓄力完成即发射
        st["charge_prog"] = min(1.0, t / float(_ATOM_CHARGE))
        if t >= _ATOM_CHARGE:
            st["phase"] = "sweep"
            st["t"] = 0
            st["swept"] = 0.0
            st["angle"] = st["ref_angle"]
            st["beam_active"] = True
            _atomize_update_angles(st)

    elif st["phase"] == "sweep":
        # 扫射：N 条光束同步旋转 360/N 度即扫遍全场，沿途撒下残留黑红能量弹
        w = _atomize_speed(st)
        st["angle"] += st["dir"] * w
        st["swept"] += w
        _atomize_update_angles(st)
        if st["t"] % _atomize_residue_interval(st) == 0:
            _atomize_spawn_residue(bullet_manager, st)
        if st["swept"] >= math.tau / st["beam_count"] - 1e-6:
            # 本轮结束：立即开始下一轮，光束 +1；以玩家后面的光束为基准保持不动
            st["round"] += 1
            st["ref_angle"] = _atomize_trailing_angle(st, player_x, player_y)
            st["angle"] = st["ref_angle"]
            st["t"] = 0
            st["swept"] = 0.0
            st["beam_active"] = True
            _atomize_update_angles(st)


# ---------------------------------------------------------------------------
# ★ Last Spell「终仪 The Wither King's Final Slumber」：吸收与狂暴放出
# 循环：大量紫色大玉与普通弹从场地外涌入，被 Kaeman 吸引逐渐加速，靠近后
# 被其吸收（白光一闪没入王座）；吸收一段时间后 Kaeman 将全部能量狂暴放出
# —— 场上正在飞入的弹幕瞬间倒卷向外，同时从王座喷出层层紫色弹幕圆环与
# 大量高速随机弹。放完后再进入下一轮吸收，循环直到 Kaeman 被击破。
# ---------------------------------------------------------------------------
_SLUMBER_GATHER = 300            # 吸收阶段时长（帧，约 5s）
_SLUMBER_RELEASE = 175           # 狂暴放出阶段时长（帧，约 2.9s）
_SLUMBER_WAVE_INTERVAL = 7       # 吸收阶段每波生成间隔（帧）
_SLUMBER_WAVE_BASE = 9           # 第一轮每波弹数
_SLUMBER_WAVE_GROWTH = 3         # 每轮每波弹数增量
_SLUMBER_WAVE_MAX = 18           # 每波弹数上限
_SLUMBER_MAX_GATHER = 340        # 场上同时存在的吸收弹上限
_SLUMBER_PULL_BASE = 0.030       # 基础吸引加速度（每帧）
_SLUMBER_PULL_GROWTH = 0.005     # 每轮吸引加速度增量
_SLUMBER_MAX_IN_SPEED = 6.2      # 吸收飞行速度上限
_SLUMBER_ABSORB_DIST = 26        # 距 Kaeman 该距离内即被吸收
_SLUMBER_MAX_PAYLOAD = 240       # 狂暴放出阶段从吸收能量中喷出的弹数上限
_SLUMBER_ERUPT_FRAMES = 60       # 吸收能量持续喷出的帧数
_SLUMBER_NOVA_BIG = 26           # 放出瞬间第一层大玉圆环数量
_SLUMBER_NOVA_CIRCLE = 36        # 放出瞬间第一层普通弹圆环数量
_SLUMBER_BIG_RADIUS = 6.0        # 紫色大玉半径（32px 贴图）
_SLUMBER_CIRCLE_RADIUS = 2.6     # 紫色普通弹半径
_SLUMBER_PURPLES = ((150, 60, 220), (125, 45, 205),
                    (175, 95, 255), (100, 48, 175))


def _slumber_color():
    return random.choice(_SLUMBER_PURPLES)


def _slumber_spawn_wave(boss, bullet_manager, st):
    """从场地外随机边缘生成一波紫色大玉与普通弹，被 Kaeman 吸引向内加速。"""
    W = cfg.BATTLE_AREA_WIDTH
    H = cfg.BATTLE_AREA_HEIGHT
    cx, cy = boss.x, boss.y
    for _ in range(st["wave_count"]):
        edge = random.randrange(4)
        if edge == 0:
            x, y = random.uniform(10, W - 10), random.uniform(-46, -18)
        elif edge == 1:
            x, y = random.uniform(10, W - 10), random.uniform(H + 18, H + 46)
        elif edge == 2:
            x, y = random.uniform(-46, -18), random.uniform(10, H - 10)
        else:
            x, y = random.uniform(W + 18, W + 46), random.uniform(10, H - 10)
        big = random.random() < 0.30
        b = create_bullet_angle(
            x, y, 0.0, 0.0,
            Bullet.TYPE_BIG if big else Bullet.TYPE_CIRCLE,
            radius=_SLUMBER_BIG_RADIUS if big else _SLUMBER_CIRCLE_RADIUS,
            color=_slumber_color(), lifetime=520)
        a = math.atan2(cy - y, cx - x)
        spd = random.uniform(1.1, 1.7)
        b.vx = math.cos(a) * spd
        b.vy = math.sin(a) * spd
        b.ignore_offscreen = True
        b._slumber_gather = True
        b._slumber_absorbed = False
        _add(bullet_manager, b)


def _slumber_gather_count(bullet_manager):
    count = 0
    for b in bullet_manager.enemy_bullets:
        if getattr(b, "_slumber_gather", False):
            count += 1
    return count


def _slumber_steer(boss, bullet_manager, st):
    """逐帧吸引场上吸收弹向 Kaeman 逐渐加速，靠近后即被吸收。"""
    cx, cy = boss.x, boss.y
    pull = st["pull"]
    for b in bullet_manager.enemy_bullets:
        if not getattr(b, "_slumber_gather", False) or b.cancel_timer > 0:
            continue
        dx = cx - b.x
        dy = cy - b.y
        dist = math.hypot(dx, dy)
        if dist < 1e-3:
            continue
        b.vx += dx / dist * pull
        b.vy += dy / dist * pull
        spd = math.hypot(b.vx, b.vy)
        if spd > _SLUMBER_MAX_IN_SPEED:
            b.vx *= _SLUMBER_MAX_IN_SPEED / spd
            b.vy *= _SLUMBER_MAX_IN_SPEED / spd
        if dist < _SLUMBER_ABSORB_DIST:
            b._slumber_gather = False
            b._slumber_absorbed = True
            b.harmless = True
            b.start_cancel()
            st["absorbed"] += 1


def _slumber_release_convert(boss, bullet_manager):
    """狂暴放出：场上仍在飞入的弹幕瞬间倒卷向外高速冲出。"""
    cx, cy = boss.x, boss.y
    for b in bullet_manager.enemy_bullets:
        if not getattr(b, "_slumber_gather", False):
            continue
        b._slumber_gather = False
        b.ignore_offscreen = False
        a = math.atan2(b.y - cy, b.x - cx) + random.uniform(-0.28, 0.28)
        spd = random.uniform(3.6, 6.6)
        b.vx = math.cos(a) * spd
        b.vy = math.sin(a) * spd


def _slumber_release_nova(boss, bullet_manager, st):
    """放出瞬间：从 Kaeman 喷出三层紫色弹幕圆环（大玉 + 普通弹）。"""
    cx, cy = boss.x, boss.y
    spin = 0.6 + st["cycle"] * 0.15
    for k in range(_SLUMBER_NOVA_BIG):
        a = k * math.tau / _SLUMBER_NOVA_BIG + random.uniform(-0.03, 0.03)
        b = create_bullet_angle(cx, cy, a, random.uniform(2.1, 2.9),
                                Bullet.TYPE_BIG, radius=_SLUMBER_BIG_RADIUS,
                                color=_slumber_color(), lifetime=420)
        b.turn_rate = random.choice((-1, 1)) * spin * 0.010
        _add(bullet_manager, b)
    for k in range(_SLUMBER_NOVA_CIRCLE):
        a = k * math.tau / _SLUMBER_NOVA_CIRCLE + random.uniform(-0.03, 0.03)
        b = create_bullet_angle(cx, cy, a, random.uniform(2.6, 3.6),
                                Bullet.TYPE_CIRCLE, radius=_SLUMBER_CIRCLE_RADIUS,
                                color=_slumber_color(), lifetime=420)
        b.turn_rate = random.choice((-1, 1)) * spin * 0.018
        _add(bullet_manager, b)
    # 第二层错位圆环：略慢、带小加速度，拉开层次
    second = max(8, _SLUMBER_NOVA_BIG - 6)
    for k in range(second):
        a = k * math.tau / second + 0.24 + random.uniform(-0.04, 0.04)
        b = create_bullet_angle(cx, cy, a, random.uniform(1.6, 2.2),
                                Bullet.TYPE_BIG, radius=_SLUMBER_BIG_RADIUS,
                                color=_slumber_color(), lifetime=460)
        b.accel = 0.012
        b.turn_rate = random.choice((-1, 1)) * spin * 0.012
        _add(bullet_manager, b)


def _slumber_release_erupt(boss, bullet_manager, st):
    """将本轮吸收的紫色能量从 Kaeman 狂暴喷出：大量高速随机弹。"""
    cx, cy = boss.x, boss.y
    speed = 3.8 + st["cycle"] * 0.4
    for _ in range(st["erupt_per"]):
        if st["erupt_left"] <= 0:
            return
        st["erupt_left"] -= 1
        a = random.uniform(0.0, math.tau)
        spd = random.uniform(speed - 1.2, speed + 1.8)
        big = random.random() < 0.28
        b = create_bullet_angle(
            cx, cy, a, spd,
            Bullet.TYPE_BIG if big else Bullet.TYPE_CIRCLE,
            radius=_SLUMBER_BIG_RADIUS if big else _SLUMBER_CIRCLE_RADIUS,
            color=_slumber_color(), lifetime=420)
        if random.random() < 0.35:
            b.turn_rate = random.uniform(-0.04, 0.04)
        _add(bullet_manager, b)


def spell_kaeman_last_spell(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """★ Last Spell「终仪 The Wither King's Final Slumber」。

    场地外大量紫色大玉与普通弹被 Kaeman 吸引逐渐加速并被其吸收；
    吸收一段时间后全部狂暴放出；放完后再进入下一轮吸收，直到被击破。
    """
    st = getattr(boss, "kaeman_slumber", None)
    if st is None:
        st = {
            "phase": "gather",
            "t": 0,
            "cycle": 0,
            "absorbed": 0,
            "wave_count": _SLUMBER_WAVE_BASE,
            "pull": _SLUMBER_PULL_BASE,
            "erupt_left": 0,
            "erupt_per": 0,
        }
        boss.kaeman_slumber = st
        # 终仪期间 Kaeman 原地不动：把移动目标锁在当前位置，全程不巡游
        boss.move_to(boss.x, boss.y)

    # 终仪期间 Kaeman 全程留在原位，不巡游不移动

    if st["phase"] == "gather":
        st["t"] += 1
        if (st["t"] % _SLUMBER_WAVE_INTERVAL == 0
                and _slumber_gather_count(bullet_manager) < _SLUMBER_MAX_GATHER):
            _slumber_spawn_wave(boss, bullet_manager, st)
        _slumber_steer(boss, bullet_manager, st)
        if st["t"] >= _SLUMBER_GATHER:
            # 吸收完成：狂暴放出
            st["phase"] = "release"
            st["t"] = 0
            _slumber_release_convert(boss, bullet_manager)
            _slumber_release_nova(boss, bullet_manager, st)
            payload = min(st["absorbed"], _SLUMBER_MAX_PAYLOAD)
            st["erupt_left"] = payload
            st["erupt_per"] = max(1, (payload + _SLUMBER_ERUPT_FRAMES - 1)
                                  // _SLUMBER_ERUPT_FRAMES)
    else:
        st["t"] += 1
        _slumber_release_erupt(boss, bullet_manager, st)
        if st["t"] >= _SLUMBER_RELEASE:
            # 放完：进入下一轮吸收（强度逐步提升）
            st["cycle"] += 1
            st["phase"] = "gather"
            st["t"] = 0
            st["absorbed"] = 0
            st["wave_count"] = min(_SLUMBER_WAVE_MAX,
                                   _SLUMBER_WAVE_BASE + _SLUMBER_WAVE_GROWTH * st["cycle"])
            st["pull"] = _SLUMBER_PULL_BASE + _SLUMBER_PULL_GROWTH * st["cycle"]


# ---------------------------------------------------------------------------
# Kaeman 巨颅注视
# ---------------------------------------------------------------------------
def _kaeman_fire(skull, bullet_manager, player_x, player_y):
    """锁定完成：巨颅能量球 + 锁定区域绽放 + 追尾刀弹。"""
    sx, sy = skull["x"], skull["y"]
    lx, ly = skull["lock_x"], skull["lock_y"]
    angle = math.atan2(ly - sy, lx - sx)
    _add(bullet_manager, create_bullet_angle(
        sx, sy, angle, 2.6, Bullet.TYPE_BIG, radius=7, color=(40, 20, 70)))
    for i in range(16):
        a = i * math.tau / 16
        _add(bullet_manager, create_bullet_angle(
            lx, ly, a, 1.7, Bullet.TYPE_CIRCLE, radius=2.5, color=(90, 40, 150)))
    for i in range(6):
        a = math.atan2(player_y - ly, player_x - lx) + (i - 2.5) * 0.16
        _add(bullet_manager, create_bullet_angle(
            lx, ly, a, 2.2, Bullet.TYPE_KNIFE, radius=2.5, color=(170, 60, 200)))


def _ghost_fire(ghost, bullet_manager, player_x, player_y):
    """残影离场前打出一组「门徒告别弹」：分别呼应四人的弹幕风格。"""
    gid = ghost["id"]
    gx, gy = ghost["x"], ghost["y"]
    if gid == "maxor":
        for i in range(8):
            a = math.atan2(player_y - gy, player_x - gx) + (i - 3.5) * 0.14
            _add(bullet_manager, create_bullet_angle(
                gx, gy + 42, a, 2.5, Bullet.TYPE_BIG,
                radius=5, color=(255, 120, 50)))
    elif gid == "storm":
        for dx in (-95, 95):
            top = 14.0
            beam = create_bullet_angle(
                gx + dx, top, math.pi / 2, 0.0, Bullet.TYPE_BEAM,
                radius=2.5, color=(140, 220, 255))
            beam.angle = math.pi / 2
            beam.beam_length = cfg.BATTLE_AREA_HEIGHT - 22
            beam.lifetime = 22
            _add(bullet_manager, beam)
        for i in range(10):
            a = math.atan2(player_y - gy, player_x - gx) + (i - 4.5) * 0.12
            _add(bullet_manager, create_bullet_angle(
                gx, gy, a, 2.3, Bullet.TYPE_CIRCLE,
                radius=2.5, color=(120, 200, 255)))
    elif gid == "goldor":
        for i in range(18):
            a = i * math.tau / 18 + ghost["age"] * 0.02
            _add(bullet_manager, create_bullet_angle(
                gx, gy + 36, a, 1.9, Bullet.TYPE_CIRCLE,
                radius=3, color=(255, 205, 90)))
        for i in range(6):
            a = math.atan2(player_y - gy, player_x - gx) + (i - 2.5) * 0.14
            _add(bullet_manager, create_bullet_angle(
                gx, gy + 30, a, 2.4, Bullet.TYPE_RICE,
                radius=2.5, color=(240, 190, 80)))
    else:  # necron
        for i in range(14):
            a = i * math.tau / 14 + ghost["age"] * 0.015
            _add(bullet_manager, create_bullet_angle(
                gx, gy + 42, a, 1.6, Bullet.TYPE_KNIFE,
                radius=2.5, color=(200, 70, 230)))

class Stage6_FinalApproach(Stage):
    """Stage 6: Final Approach（通往凋零之王 Kaeman 的王座）"""

    def __init__(self):
        super().__init__(6, "最终进军 ~ Final Approach", bg_color=(6, 4, 10))
        # 进军阶段复用四面墓穴风格；进入要塞后切换到自绘凋零要塞贴图。
        self.background = Pseudo3DFloor(
            cfg.STAGE6_FLOOR, cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT,
            bg_color=self.bg_color,
            wall_texture_path=cfg.STAGE6_WALL,
            horizon_ratio=0.34, tunnel_width=1.7,
            far_opening=30, floor_stretch=3.4, wall_stretch=1.0,
            wall_align_to_floor=True)
        self.background_fortress = Pseudo3DFloor(
            cfg.STAGE6_FORTRESS_FLOOR, cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT,
            bg_color=self.bg_color,
            wall_texture_path=cfg.STAGE6_FORTRESS_WALL,
            horizon_ratio=0.30, tunnel_width=1.55,
            far_opening=34, floor_stretch=3.4, wall_stretch=1.0,
            wall_align_to_floor=True)
        self.title_path = cfg.STAGE6_TITLE
        self.music_path = cfg.STAGE6_MUSIC_START
        self.music_loop_path = cfg.STAGE6_MUSIC_LOOP
        self.boss_music_start_path = cfg.STAGE6_BOSS_MUSIC_START
        self.boss_music_loop_path = cfg.STAGE6_BOSS_MUSIC_LOOP
        self.music_name = cfg.STAGE6_MUSIC_NAME
        self.boss_music_name = cfg.STAGE6_BOSS_MUSIC_NAME
        self.mid_boss_music_path = None
        self.background_darkness = 40

        # 阶段状态
        self.phase = "march"
        self._waves_setup = False
        self.final_wave = None

        # 阶段横幅
        self.banner_text = ""
        self.banner_timer = 0

        # Kaeman 干涉状态
        self.kaeman_skull = None
        self.kaeman_warnings = []
        self.kaeman_next_attack = 0

        # 黑能量入侵状态
        self.energy_wisps = []
        self.mist_particles = []
        self._energy_timer = 0

        # 王之门徒残影
        self.ghosts = []
        self.ghost_queue = list(GHOST_PLAN)

        # 战后对话：Kaeman（即 The Wither King）被击破后
        self.defeat_dialogue_lines = [
            ("Kaeman", "真是令人怀念。"),
            ("Kaeman", "已经很久没有这样战斗过了。"),
            ("魔法使 Mage", "结束了吗？"),
            ("Kaeman", "结束？"),
            ("Kaeman", "呵。"),
            ("魔法使 Mage", "什么意思？"),
            ("Kaeman", "地下城不会因为某个人而停止运转。"),
            ("Kaeman", "就像天空街不会因为某个人而改变一样。"),
            ("魔法使 Mage", "那你呢？"),
            ("Kaeman", "我只是有些累了。"),
            ("魔法使 Mage", "......"),
            ("Kaeman", "魔法使。"),
            ("Kaeman", "别让自己变成和我一样的人。"),
            ("魔法使 Mage", "我会记住的。"),
            ("Kaeman", "是吗？"),
            ("Kaeman", "那就好。"),
        ]
        self.defeat_dialogue_portraits = {
            "魔法使 Mage": cfg.SELF_SPRITE,
            "Kaeman": cfg.STAGE6_KAEMAN_PORTRAIT,
        }
        self.defeat_dialogue_portrait_sides = {
            "魔法使 Mage": "left",
            "Kaeman": "right",
        }
        # Kaeman 说话时立绘放大 1.5x
        self.dialogue_portrait_scales = {"Kaeman": 1.5}
        self.dialogue_portrait_offsets = {"Kaeman": 120}  # Kaeman 立绘右移 120px

        # 前景遮罩（锁定圈 / 边缘压暗用，避免每帧新建 Surface）
        self._fg_overlay = pygame.Surface(
            (cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT), pygame.SRCALPHA)
        self._dark_cache = {}
        self._dominion_overlay = None   # 王符领域视觉层缓存
        self._relic_overlay = None     # 冥符 Relic 五边形视觉层缓存
        self._dragon_overlay = None     # 龙符枯龙视觉层缓存
        self._dragon_ring = None       # 龙符轨道虚线缓存
        self._slumber_overlay = None  # 终仪吸收核心/冲击环视觉层缓存

    # ------------------------------------------------------------------
    # 基础接口
    # ------------------------------------------------------------------
    def setup_waves(self):
        if self._waves_setup:
            return
        self._waves_setup = True
        em = self.enemy_manager

        # 前半段：亡灵军队防线（0 ~ 42s，逐渐加强）
        march_waves = (
            (4 * 60, EnemyWave([
                WitherHuskEnemy(100, -24), WitherHuskEnemy(288, -48),
                WitherHuskEnemy(470, -24)], name="Wither Vanguard")),
            (9 * 60, EnemyWave([
                WitherGuardEnemy(140, -30), WitherGuardEnemy(430, -30),
                WitherHuskEnemy(200, -60), WitherHuskEnemy(380, -60)],
                name="Undead Line")),
            (14 * 60, EnemyWave([
                WitherMinerEnemy(80, -24), WitherMinerEnemy(288, -56),
                WitherMinerEnemy(492, -24), WitherHuskEnemy(160, -70),
                WitherHuskEnemy(420, -70)], name="Miner Phalanx")),
            (19 * 60, EnemyWave([
                WitherGuardEnemy(110, -40), WitherGuardEnemy(460, -40),
                WitherMinerEnemy(200, -60), WitherMinerEnemy(380, -60),
                WitherHuskEnemy(288, -80)], name="Fortress Gate")),
            (24 * 60, EnemyWave([
                WitherMinerEnemy(90, -24), WitherMinerEnemy(250, -56),
                WitherMinerEnemy(400, -24), WitherMinerEnemy(500, -56),
                WitherGuardEnemy(288, -70)], name="Wither Labor")),
            (29 * 60, EnemyWave([
                WitherGuardEnemy(130, -40), WitherGuardEnemy(320, -70),
                WitherGuardEnemy(450, -40), WitherHuskEnemy(80, -80),
                WitherHuskEnemy(230, -90), WitherHuskEnemy(420, -90)],
                name="Guard Wall")),
            (34 * 60, EnemyWave([
                WitherHuskEnemy(70, -24), WitherHuskEnemy(180, -56),
                WitherHuskEnemy(288, -80), WitherHuskEnemy(400, -56),
                WitherHuskEnemy(500, -24), WitherMinerEnemy(240, -90),
                WitherMinerEnemy(350, -90)], name="Last March")),
        )
        for t, wave in march_waves:
            em.add_timed_wave(t, wave)

        # 中段：Kaeman 干涉（42 ~ 66s）：普通敌人骤减，只剩少量游魂
        wisp_waves = (
            (45 * 60, EnemyWave([
                WitherWispEnemy(140, -30), WitherWispEnemy(430, -30)],
                name="Wither Wisp")),
            (52 * 60, EnemyWave([
                WitherWispEnemy(90, -40), WitherWispEnemy(288, -60),
                WitherWispEnemy(470, -40)], name="Soul Drift")),
            (59 * 60, EnemyWave([
                WitherWispEnemy(200, -30), WitherWispEnemy(360, -30)],
                name="Echo Wisp")),
        )
        for t, wave in wisp_waves:
            em.add_timed_wave(t, wave)

        # 后半段：凋零要塞（66 ~ 100s）：敌人减少、场面变大
        fortress_waves = (
            (68 * 60, EnemyWave([
                WitherGuardEnemy(130, -40), WitherGuardEnemy(430, -40),
                WitherKnightEnemy(288, -70)], name="Fortress Wall")),
            (75 * 60, EnemyWave([
                WitherMinerEnemy(110, -40), WitherMinerEnemy(360, -40),
                WitherKnightEnemy(210, -70)], name="Siege Detail")),
            (82 * 60, EnemyWave([
                WitherKnightEnemy(110, -50), WitherKnightEnemy(280, -50),
                WitherKnightEnemy(460, -50), WitherGuardEnemy(200, -80),
                WitherGuardEnemy(380, -80)], name="Knight Order")),
            (90 * 60, EnemyWave([
                WitherTerracottaEnemy(160, -40, deploy_y=150),
                WitherTerracottaEnemy(420, -40, deploy_y=150),
                WitherGuardEnemy(288, -60)], name="Golem Ward")),
        )
        for t, wave in fortress_waves:
            em.add_timed_wave(t, wave)

        # 王座前的最后防线（100s 出场）：突破后直接进入 Kaeman（The Wither King）战
        self.final_wave = EnemyWave([
            WitherColossusEnemy(288, -70, deploy_y=150),
            WitherTerracottaEnemy(110, -40, deploy_y=150),
            WitherTerracottaEnemy(466, -40, deploy_y=150),
            WitherGuardEnemy(150, -50),
            WitherGuardEnemy(430, -50),
            WitherKnightEnemy(220, -80),
            WitherKnightEnemy(360, -80),
        ], name="Final Defense")
        em.add_timed_wave(FORTRESS_FINAL_WAVE_AT, self.final_wave)

    def setup_mid_boss(self):
        pass

    def _add_post_midboss_waves(self):
        pass

    def setup_boss(self):
        """关底 Boss：Kaeman（即 The Wither King）——五张通常符 + 一张 Last Spell。"""
        self.boss = self._make_kaeman()

    def _make_kaeman(self):
        boss = Boss(
            "Kaeman", hp=WKING_HP,
            x=cfg.BATTLE_AREA_WIDTH / 2, y=-90,
            size=34, color=(90, 50, 140),
            spell_by_hp_only=True, spell_resistance=0.5,
            non_spell_min_duration=1,
            non_spell_func=_non_spell_kaeman,
            hp_bar_inset=16,
            sprite_path=cfg.STAGE6_WITHER_KING_BOSS_SPRITE,
            sprite_scale=2.0)
        boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 118)
        boss.drop_group = ["stage6_final_boss"]
        # 五张通常符：血量阈值 1.0 → 0.8 → 0.6 → 0.4 → 0.2 → 0.0（每张 4800 HP）
        boss.add_spell_card(SpellCard(
            "王符「Wither King's Dominion」", spell_kaeman_dominion,
            hp_threshold=1.0, end_hp_threshold=0.8, bg_style="kaeman_dominion",
            direct_next=True))
        boss.add_spell_card(SpellCard(
            "冥符「Five Corrupted Relics」", spell_kaeman_relics,
            hp_threshold=0.8, end_hp_threshold=0.6, bg_style="kaeman_relics",
            direct_next=True))
        boss.add_spell_card(SpellCard(
            "龙符「Withered Dragon」", spell_kaeman_withered_dragon,
            hp_threshold=0.6, end_hp_threshold=0.4, bg_style="kaeman_withered_dragon",
            direct_next=True))
        boss.add_spell_card(SpellCard(
            "裂符「Dimensional Slash」", spell_kaeman_dimensional_slash,
            hp_threshold=0.4, end_hp_threshold=0.2, bg_style="kaeman_slash",
            direct_next=True))
        boss.add_spell_card(SpellCard(
            "王符「Atomizing Ray」", spell_kaeman_atomize_ray,
            hp_threshold=0.2, end_hp_threshold=0.0, bg_style="kaeman_atomize"))
        # Last Spell「终仪 The Wither King's Final Slumber」：五张通常符全部击破后展开（独立血量）
        boss.last_spell_hp = 10400
        boss.set_last_spell(SpellCard(
            "终仪「The Wither King's Final Slumber」", spell_kaeman_last_spell,
            hp_threshold=0, bg_style="kaeman_slumber"))
        return boss

    def get_active_enemies(self):
        enemies = []
        if self.phase in ("march", "interference", "fortress", "final_wave"):
            enemies.extend(self.enemy_manager.get_active_enemies())
        elif (self.phase == "boss" and self.boss and self.boss.alive
                and self.boss.combat_enabled):
            enemies.append(self.boss)
        return enemies

    # ------------------------------------------------------------------
    # 阶段推进
    # ------------------------------------------------------------------
    def _set_banner(self, text, frames=170):
        self.banner_text = text
        self.banner_timer = frames

    def _check_phase_progress(self):
        if self.phase == "march" and self.timer >= MARCH_END:
            self.phase = "interference"
            self._set_banner("—— Kaeman 的注视 ——")
            self.kaeman_next_attack = KAEMAN_FIRST_ATTACK_IN
            self.background_darkness = 84
            return
        if self.phase == "interference" and self.timer >= INTERFERENCE_END:
            self.phase = "fortress"
            self._enter_fortress()
            self._set_banner("—— 凋零要塞 ——")
            return
        if self.phase == "fortress" and self.timer >= FORTRESS_FINAL_WAVE_AT:
            self.phase = "final_wave"
            self._set_banner("—— 王座前的最后防线 ——")
            self.background_darkness = 150
            return
        if self.phase == "final_wave" and self.enemy_manager.is_cleared():
            self._start_final_dialogue()

    def _enter_fortress(self):
        old = self.background
        fort = self.background_fortress
        if old is not None and fort is not None:
            fort.scroll = old.scroll
            fort.speed_mult = old.speed_mult
        self.background = fort
        self._ramp_background_speed(2.2, BOSS_BG_RAMP_TIME)
        self.background.ramp_view_height(70.0, 2.0)
        self.background_darkness = 120

    # ------------------------------------------------------------------
    # 更新循环
    # ------------------------------------------------------------------
    def update(self, dt, bullet_manager, player_x, player_y):
        if self.background:
            self.background.update(dt)
        self.timer += 1

        if self.phase in ("march", "interference", "fortress", "final_wave"):
            self.enemy_manager.update(dt, bullet_manager, player_x, player_y,
                                      stage_time=self.timer)
            self._update_kaeman(bullet_manager, player_x, player_y)
            self._update_energy(bullet_manager, player_x, player_y)
            self._update_ghosts(bullet_manager, player_x, player_y)
            self._check_phase_progress()

        elif self.phase == "dialogue":
            if self.boss and self.boss.alive:
                self.boss.update(dt, bullet_manager, player_x, player_y)

        elif self.phase == "boss":
            if self.boss:
                self.boss.update(dt, bullet_manager, player_x, player_y)
                # 裂符：触手拉拽请求 -> 下一帧应用到自机
                sl = getattr(self.boss, "kaeman_slash", None)
                if sl is not None and sl.get("tentacle") is not None:
                    tt = sl["tentacle"].get("teleport_target")
                    if tt is not None:
                        self.player_teleport_target = tt
                        sl["tentacle"]["teleport_target"] = None
                if not self.boss.alive:
                    self._start_defeat_dialogue()

        elif self.phase == "defeat_dialogue":
            # 战后对话：Boss 已击破但留在场上，仅推进符卡背景淡出
            if self.boss is not None and self.boss.spell_bg is not None:
                self.boss.update(dt, bullet_manager, player_x, player_y)

        elif self.phase == "cleared":
            if self.boss is not None and self.boss.spell_bg is not None:
                self.boss.update(dt, bullet_manager, player_x, player_y)

        if self.banner_timer > 0:
            self.banner_timer -= 1

    # ------------------------------------------------------------------
    # Kaeman 巨颅注视
    # ------------------------------------------------------------------
    def _update_kaeman(self, bullet_manager, player_x, player_y):
        if self.phase not in ("interference", "fortress", "final_wave"):
            return
        for w in self.kaeman_warnings[:]:
            w["age"] += 1
            if w["age"] >= w["max_age"]:
                self.kaeman_warnings.remove(w)

        sk = self.kaeman_skull
        if sk is None:
            self.kaeman_next_attack -= 1
            if self.kaeman_next_attack <= 0:
                self.kaeman_skull = {
                    "age": 0, "x": player_x, "y": -110,
                    "state": "watch", "lock_x": 0.0, "lock_y": 0.0,
                }
            return

        sk["age"] += 1
        if sk["state"] == "watch":
            sk["x"] += (player_x - sk["x"]) * 0.03
            sk["y"] = -110 + (sk["age"] / KAEMAN_WATCH_FRAMES) * 170
            if sk["age"] >= KAEMAN_WATCH_FRAMES:
                sk["state"] = "lock"
                sk["lock_x"] = player_x
                sk["lock_y"] = player_y
                self.kaeman_warnings.append({
                    "x": sk["lock_x"], "y": sk["lock_y"],
                    "age": 0, "max_age": KAEMAN_LOCK_FRAMES,
                })
        elif sk["state"] == "lock":
            sk["y"] = 60 + math.sin(sk["age"] * 0.06) * 5
            if sk["age"] >= KAEMAN_WATCH_FRAMES + KAEMAN_LOCK_FRAMES:
                _kaeman_fire(sk, bullet_manager, player_x, player_y)
                sk["state"] = "fade"
        elif sk["state"] == "fade":
            if sk["age"] >= (KAEMAN_WATCH_FRAMES + KAEMAN_LOCK_FRAMES
                             + KAEMAN_FADE_FRAMES):
                self.kaeman_skull = None
                self.kaeman_next_attack = KAEMAN_ATTACK_INTERVAL

    # ------------------------------------------------------------------
    # 黑能量入侵
    # ------------------------------------------------------------------
    def _update_energy(self, bullet_manager, player_x, player_y):
        if self.phase not in ("interference", "fortress", "final_wave"):
            self.energy_wisps = []
            self.mist_particles = []
            return
        self._energy_timer += 1

        # 游魂：飘入战场，周期性投出小型黑弹
        if self._energy_timer % 66 == 0 and self._energy_timer > 30:
            self.energy_wisps.append({
                "x": random.uniform(80, cfg.BATTLE_AREA_WIDTH - 80),
                "y": -24, "age": 0, "max_age": 230,
                "seed": random.uniform(0, math.tau),
            })
        for wisp in self.energy_wisps[:]:
            wisp["age"] += 1
            wisp["x"] += math.sin(wisp["age"] * 0.035 + wisp["seed"]) * 1.3
            wisp["y"] += 1.05
            # 追踪弹数量减半：发射间隔由 26 帧改为 52 帧
            if wisp["age"] % 52 == 0:
                _add(bullet_manager, create_bullet_aimed(
                    wisp["x"], wisp["y"], player_x, player_y, 2.0,
                    Bullet.TYPE_CIRCLE, radius=2.5, color=(70, 30, 110)))
            if wisp["age"] >= wisp["max_age"]:
                self.energy_wisps.remove(wisp)

        # 黑雾粒子：纯氛围，自底部缓缓升腾扩散（无碰撞）
        if self._energy_timer % 5 == 0 and len(self.mist_particles) < 36:
            self.mist_particles.append({
                "x": random.uniform(20, cfg.BATTLE_AREA_WIDTH - 20),
                "y": cfg.BATTLE_AREA_HEIGHT + 26,
                "vx": random.uniform(-0.35, 0.35),
                "vy": random.uniform(-1.5, -0.8),
                "r": random.uniform(16, 36),
                "alpha": random.uniform(42, 72),
                "fade": random.uniform(0.5, 0.95),
            })
        for p in self.mist_particles[:]:
            p["x"] += p["vx"] + math.sin(p["y"] * 0.012 + p["x"] * 0.02) * 0.4
            p["y"] += p["vy"]
            p["alpha"] -= p["fade"]
            if p["alpha"] <= 0 or p["y"] < -50 - p["r"]:
                self.mist_particles.remove(p)

    # ------------------------------------------------------------------
    # 王之门徒残影
    # ------------------------------------------------------------------
    def _update_ghosts(self, bullet_manager, player_x, player_y):
        if self.phase in ("fortress", "final_wave"):
            while self.ghost_queue and self.timer >= self.ghost_queue[0][0]:
                _, gid = self.ghost_queue.pop(0)
                gx, gy = GHOST_POSITIONS[gid]
                self.ghosts.append({
                    "id": gid, "x": gx, "y": gy,
                    "age": 0, "max_age": GHOST_MAX_AGE, "fired": False,
                })
        for ghost in self.ghosts[:]:
            ghost["age"] += 1
            if ghost["age"] == GHOST_FIRE_AT and not ghost["fired"]:
                ghost["fired"] = True
                _ghost_fire(ghost, bullet_manager, player_x, player_y)
            if ghost["age"] >= ghost["max_age"]:
                self.ghosts.remove(ghost)

    # ------------------------------------------------------------------
    # 对话与转场
    # ------------------------------------------------------------------
    def _set_dialogue(self, lines, portraits, sides, pending_action,
                      is_defeat=False):
        self.dialogue_lines = lines
        self.dialogue_portraits = portraits
        self.dialogue_portrait_sides = sides
        self.dialogue_is_defeat = is_defeat
        self.dialogue_active = True

    def _start_final_dialogue(self):
        """最后防线被突破：凋零之王 Kaeman（即 The Wither King）登场对话。"""
        self.kaeman_skull = None
        self.kaeman_warnings = []
        self.energy_wisps = []
        self.mist_particles = []
        self.ghosts = []
        self.enemy_manager.reset()
        self.boss = self._make_kaeman()
        self.boss.hold_combat()
        self._set_dialogue(
            [
                ("Kaeman", "你来了。"),
                ("魔法使 Mage", "看来，他们说得没错。"),
                ("魔法使 Mage", "你一直在等我。"),
                ("Kaeman", "不。"),
                ("Kaeman", "我只是在等一个能够来到这里的人。"),
                ("魔法使 Mage", "地下城最近的异常，果然和你有关。"),
                ("Kaeman", "是吗？"),
                ("Kaeman", "也许吧。"),
                ("魔法使 Mage", "所以，你究竟想做什么？"),
                ("Kaeman", "我只是做了一件魔法使都会做的事情。"),
                ("魔法使 Mage", "什么？"),
                ("Kaeman", "试图改变不应该改变的事情。"),
                ("魔法使 Mage", "看来，我们已经没有继续谈下去的必要了。"),
                ("Kaeman", "也许，从一开始就没有。"),
            ],
            {
                "魔法使 Mage": cfg.SELF_SPRITE,
                "Kaeman": cfg.STAGE6_KAEMAN_PORTRAIT,
            },
            {"魔法使 Mage": "left", "Kaeman": "right"},
            None)
        self.phase = "dialogue"
        self._ramp_background_speed(FINAL_BOSS_BG_SPEED_MULT, BOSS_BG_RAMP_TIME)
        self.background_darkness = 190

    def skip_to_kaeman_spell(self, spell_idx):
        """调试：六面战前对话中按 1~6 直接进入 Kaeman 第 1~6 张符卡。

        spell_idx 从 1 起：1~5 = 五张通常符，6 = Last Spell「终仪 The Wither King's Final Slumber」。
        跳过非符与入场，立即展开对应符卡（符卡结束后仍按 normal 流程接续）。
        """
        if self.phase != "dialogue" or self.dialogue_is_defeat:
            return False
        boss = self.boss
        if boss is None:
            return False
        if 1 <= spell_idx <= len(boss.spell_cards):
            card = boss.spell_cards[spell_idx - 1]
            boss.current_spell_idx = spell_idx - 1
            # 对齐正常流程：该符开符时血量已钳制到其 hp_threshold 对应值
            boss.hp = int(round(card.hp_threshold * boss.max_hp))
        elif spell_idx == len(boss.spell_cards) + 1 and boss.last_spell is not None:
            card = boss.last_spell
            boss.current_spell_idx = len(boss.spell_cards)
            # Last Spell：_start_spell 会自动补充 last_spell_hp，无需在此设置
        else:
            return False
        boss.arm_combat(0)
        boss.entering = False
        boss.entry_timer = 0
        boss._start_spell(card)
        self.phase = "boss"
        self.dialogue_active = False
        self._on_boss_combat_start()
        return True

    def on_dialogue_end(self):
        """战前对话结束：Kaeman 开战（五张通常符 + Last Spell）。"""
        self.dialogue_active = False
        if self.boss:
            self.boss.arm_combat(BOSS_COMBAT_DELAY)
        self.phase = "boss"
        self._on_boss_combat_start()

    def on_defeat_dialogue_end(self):
        """战后对话结束：六面通关结算。"""
        self.dialogue_active = False
        self.dialogue_is_defeat = False
        self.phase = "cleared"
        self._ramp_background_speed(1.0, BOSS_BG_RAMP_TIME)

    def _on_boss_combat_start(self):
        """Kaeman 开战时抬升视角，俯瞰王座；撤去黑能量入侵的压抑氛围。"""
        self.mist_particles = []
        self.background_darkness = 40
        if self.background is not None:
            self.background.ramp_view_height(122.0, 2.4)

    # ------------------------------------------------------------------
    # 绘制
    # ------------------------------------------------------------------
    def draw(self, screen, offset_x=0, offset_y=0):
        pygame.draw.rect(screen, self.bg_color,
                         (offset_x, offset_y, cfg.BATTLE_AREA_WIDTH,
                          cfg.BATTLE_AREA_HEIGHT))
        hide_floor = any(
            b is not None and b.spell_bg is not None and not b.spell_bg.done
            and b.spell_bg.is_opaque
            for b in (self.mid_boss, self.boss))
        if self.background and not hide_floor:
            self.background.draw(screen, offset_x, offset_y)
            if self.background_darkness:
                dark = self._dark_cache.get(self.background_darkness)
                if dark is None:
                    dark = pygame.Surface(
                        (cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT),
                        pygame.SRCALPHA)
                    dark.fill((0, 0, 0, self.background_darkness))
                    self._dark_cache[self.background_darkness] = dark
                screen.blit(dark, (offset_x, offset_y))

        for boss_ref in (self.mid_boss, self.boss):
            if boss_ref is not None and boss_ref.spell_bg is not None \
                    and not boss_ref.spell_bg.done:
                boss_ref.spell_bg.draw(screen, offset_x, offset_y)

        # 环境层：背景之上、敌人之下（巨颅 / 黑能量 / 门徒残影）
        self._draw_kaeman(screen, offset_x, offset_y)
        self._draw_energy(screen, offset_x, offset_y)
        self._draw_mist(screen, offset_x, offset_y)
        self._draw_ghosts(screen, offset_x, offset_y)
        self._draw_kaeman_dominion(screen, offset_x, offset_y)
        self._draw_kaeman_relics(screen, offset_x, offset_y)
        self._draw_kaeman_withered_dragon(screen, offset_x, offset_y)

        # 小怪
        if self.phase in ("march", "interference", "fortress", "final_wave"):
            self.enemy_manager.draw(screen, offset_x, offset_y)

        # 关底 Boss（战后对话期间 Boss 留在场上）
        if self.boss and (self.boss.alive or self.phase == "defeat_dialogue"):
            self.boss.draw(screen, offset_x, offset_y)
            # 裂符：空间裂痕与危险范围（绘制在 Boss 之下、子弹之下）
            self._draw_kaeman_slash(screen, offset_x, offset_y)
            # 王符：扫过的扇形区域提示（绘制在 Boss 之下、子弹之下）
            self._draw_kaeman_atomize_background(screen, offset_x, offset_y)
            # 终仪：吸收核心 / 狂暴放出冲击环（绘制在 Boss 之下、子弹之下）
            self._draw_kaeman_slumber(screen, offset_x, offset_y)

        # 阶段横幅
        self._draw_banner(screen, offset_x, offset_y)

    def draw_foreground(self, screen, offset_x=0, offset_y=0):
        """子弹与自机之上：锁定预警圈 + 黑能量入侵边缘压暗 + 枯龙俯冲危险轨迹。"""
        if self.phase not in ("march", "interference", "fortress", "final_wave", "boss"):
            return
        overlay = self._fg_overlay
        overlay.fill((0, 0, 0, 0))

        if self.phase in ("march", "interference", "fortress", "final_wave"):
            # Kaeman 锁定玩家区域的预警圈
            for w in self.kaeman_warnings:
                prog = w["age"] / max(1, w["max_age"])
                r = 12 + prog * 66
                cx = int(w["x"] + offset_x)
                cy = int(w["y"] + offset_y)
                alpha = 60 + int(180 * (0.5 + 0.5 * math.sin(prog * math.pi)))
                pygame.draw.circle(overlay, (255, 70, 90, alpha), (cx, cy), int(r), 2)
                pygame.draw.circle(overlay, (255, 40, 60, alpha // 2),
                                   (cx, cy), int(r * 0.85), 1)
                pygame.draw.line(overlay, (255, 80, 100, alpha),
                                 (cx - int(r) - 8, cy), (cx + int(r) + 8, cy), 1)
                pygame.draw.line(overlay, (255, 80, 100, alpha),
                                 (cx, cy - int(r) - 8), (cx, cy + int(r) + 8, cy), 1)

            # 黑能量入侵：上下边缘压暗（干涉/要塞阶段加深）
            if self.phase in ("interference", "fortress", "final_wave"):
                pulse = 38 + int(14 * math.sin(pygame.time.get_ticks() * 0.004))
                edge_alpha = 90
            else:
                pulse = 26 + int(14 * math.sin(pygame.time.get_ticks() * 0.004))
                edge_alpha = 70
            pygame.draw.rect(overlay, (0, 0, 0, edge_alpha),
                             (0, 0, cfg.BATTLE_AREA_WIDTH, pulse))
            pygame.draw.rect(overlay, (0, 0, 0, edge_alpha),
                             (0, cfg.BATTLE_AREA_HEIGHT - pulse,
                              cfg.BATTLE_AREA_WIDTH, pulse))

        # 枯龙本体（巡场 / 俯冲）绘制在子弹与自机之上
        if self.phase == "boss" and self.boss is not None and self.boss.alive:
            wd = getattr(self.boss, "kaeman_dragon", None)
            if wd is not None:
                if wd["dive"] is not None:
                    self._draw_dragon_dive_foreground(overlay, wd)
                else:
                    self._draw_withered_dragon(overlay, wd, wd["px"], wd["py"],
                                               wd.get("dragon_angle", 0.0),
                                               0, 0, alpha=255, height=110)

        # 裂符：触手牵引（绘制在子弹与自机之上）
        if self.phase == "boss" and self.boss is not None and self.boss.alive:
            sl = getattr(self.boss, "kaeman_slash", None)
            if sl is not None:
                self._draw_kaeman_tentacle(overlay, sl)

        # 王符「Atomizing Ray」：预警线 / 扫射光束（绘制在子弹与自机之上）
        if self.phase == "boss" and self.boss is not None and self.boss.alive:
            atom = getattr(self.boss, "kaeman_atomize", None)
            if atom is not None:
                self._draw_kaeman_atomize_foreground(overlay)
        screen.blit(overlay, (offset_x, offset_y))


    def _draw_kaeman(self, screen, offset_x=0, offset_y=0):
        # 干涉阶段顶部淡淡的注视之眼
        if self.phase in ("interference", "fortress", "final_wave"):
            eye = _load_sprite(cfg.STAGE6_WATCHFUL_EYE_SPRITE, 120)
            if eye is not None:
                eimg = eye.copy()
                eimg.set_alpha(42)
                ex = offset_x + cfg.BATTLE_AREA_WIDTH // 2 - eimg.get_width() // 2
                screen.blit(eimg, (ex, offset_y - 40))

        sk = self.kaeman_skull
        if sk is None:
            return
        sprite = _load_sprite(cfg.STAGE6_WITHER_SKULL_SPRITE, 118)
        if sprite is None:
            return
        state = sk["state"]
        if state == "watch":
            alpha = 130
        elif state == "lock":
            pulse = 0.75 + 0.25 * math.sin(pygame.time.get_ticks() * 0.02)
            alpha = int(190 + 60 * pulse)
        else:
            remain = (KAEMAN_WATCH_FRAMES + KAEMAN_LOCK_FRAMES
                      + KAEMAN_FADE_FRAMES - sk["age"])
            alpha = int(160 * max(0.0, min(1.0, remain / KAEMAN_FADE_FRAMES)))
        img = sprite.copy()
        img.set_alpha(max(0, alpha))
        x = int(sk["x"] + offset_x)
        y = int(sk["y"] + offset_y)
        # 巨颅光晕
        glow = pygame.Surface((img.get_width() + 44, img.get_height() + 44),
                              pygame.SRCALPHA)
        pygame.draw.circle(glow, (150, 40, 190, 55),
                           (glow.get_width() // 2, glow.get_height() // 2),
                           glow.get_width() // 2 - 8)
        screen.blit(glow, (x - glow.get_width() // 2, y - glow.get_height() // 2))
        screen.blit(img, (x - img.get_width() // 2, y - img.get_height() // 2))
        # 红紫双眼
        eye_r = 5 if state == "watch" else 7
        for dx in (-13, 13):
            ex = x + dx
            ey = y - 8
            pygame.draw.circle(screen, (255, 40, 90), (ex, ey), eye_r)
            pygame.draw.circle(screen, (255, 210, 220), (ex, ey), max(2, eye_r - 3))

    def _draw_energy(self, screen, offset_x=0, offset_y=0):
        for wisp in self.energy_wisps:
            sprite = _load_sprite(cfg.STAGE6_DARK_ORB_SPRITE, 42)
            if sprite is None:
                continue
            alpha = 170 if wisp["age"] < wisp["max_age"] - 20 else 120
            img = sprite.copy()
            img.set_alpha(alpha)
            x = int(wisp["x"] + offset_x)
            y = int(wisp["y"] + offset_y)
            trail = pygame.Surface((img.get_width() + 18, img.get_height() + 18),
                                   pygame.SRCALPHA)
            pygame.draw.circle(trail, (90, 30, 150, 60),
                               (trail.get_width() // 2, trail.get_height() // 2),
                               trail.get_width() // 2 - 7)
            screen.blit(trail, (x - trail.get_width() // 2, y - trail.get_height() // 2))
            screen.blit(img, (x - img.get_width() // 2, y - img.get_height() // 2))

    def _draw_mist(self, screen, offset_x=0, offset_y=0):
        """黑雾粒子：柔和的暗紫黑色雾团，缓缓升腾营造能量入侵感。"""
        if not self.mist_particles:
            return
        if not hasattr(self, "_mist_blob") or self._mist_blob is None:
            blob = pygame.Surface((96, 96), pygame.SRCALPHA)
            for i in range(48, 0, -1):
                a = int(120 * (1.0 - i / 48.0) ** 1.7)
                pygame.draw.circle(blob, (14, 5, 28, a), (48, 48), i)
            self._mist_blob = blob
            self._mist_cache = {}
        cache = self._mist_cache
        for p in self.mist_particles:
            r = max(10, int(p["r"]))
            key = r * 2
            img = cache.get(key)
            if img is None:
                img = pygame.transform.smoothscale(self._mist_blob, (key, key))
                cache[key] = img
            img = img.copy()
            img.set_alpha(max(0, min(255, int(p["alpha"]))))
            x = int(p["x"] + offset_x)
            y = int(p["y"] + offset_y)
            screen.blit(img, (x - r, y - r))

    def _draw_ghosts(self, screen, offset_x=0, offset_y=0):
        for ghost in self.ghosts:
            sprite = _load_sprite(GHOST_SPRITES[ghost["id"]], GHOST_HEIGHT)
            if sprite is None:
                continue
            age = ghost["age"]
            if age < 34:
                alpha = int(150 * age / 34)
            elif age > ghost["max_age"] - 46:
                alpha = int(150 * (ghost["max_age"] - age) / 46)
            else:
                alpha = 150
            img = sprite.copy()
            img.set_alpha(max(0, alpha))
            bob = math.sin(age * 0.05) * 4
            x = int(ghost["x"] + offset_x)
            y = int(ghost["y"] + offset_y + bob)
            glow_color = GHOST_GLOWS[ghost["id"]]
            glow = pygame.Surface((img.get_width() + 44, img.get_height() + 44),
                                  pygame.SRCALPHA)
            pygame.draw.circle(glow, glow_color + (48,),
                               (glow.get_width() // 2, glow.get_height() // 2),
                               glow.get_width() // 2 - 8)
            screen.blit(glow, (x - glow.get_width() // 2, y - glow.get_height() // 2))
            screen.blit(img, (x - img.get_width() // 2, y - img.get_height() // 2))

    def _draw_banner(self, screen, offset_x=0, offset_y=0):
        if not self.banner_text or self.banner_timer <= 0:
            return
        font = _get_font(22)
        text = font.render(self.banner_text, True, cfg.COLOR_WHITE)
        fade = min(255, int(255 * min(1.0, self.banner_timer / 60.0)))
        text.set_alpha(fade)
        x = offset_x + (cfg.BATTLE_AREA_WIDTH - text.get_width()) // 2
        y = offset_y + 96
        band = pygame.Surface((text.get_width() + 44, text.get_height() + 16),
                              pygame.SRCALPHA)
        band.fill((0, 0, 0, 150))
        screen.blit(band, (x - 22, y - 8))
        screen.blit(text, (x, y))

    # ------------------------------------------------------------------
    # 龙符「Withered Dragon」视觉层
    # ------------------------------------------------------------------
    def _dragon_ring_cache(self):
        """大型环形轨道的虚线提示层（缓存，纯装饰）。"""
        if self._dragon_ring is not None:
            return self._dragon_ring
        surf = pygame.Surface((cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT),
                              pygame.SRCALPHA)
        steps = 72
        for i in range(0, steps, 2):
            a0 = i * math.tau / steps
            a1 = (i + 1) * math.tau / steps
            x0 = _DRAGON_ORBIT_CX + math.cos(a0) * _DRAGON_ORBIT_RX
            y0 = _DRAGON_ORBIT_CY + math.sin(a0) * _DRAGON_ORBIT_RY
            x1 = _DRAGON_ORBIT_CX + math.cos(a1) * _DRAGON_ORBIT_RX
            y1 = _DRAGON_ORBIT_CY + math.sin(a1) * _DRAGON_ORBIT_RY
            pygame.draw.line(surf, (120, 78, 180, 60), (x0, y0), (x1, y1), 1)
        self._dragon_ring = surf
        return surf

    def _draw_dragon_statue(self, overlay, st):
        """Dragon Statue 占位：基座 + 柱身 + 彩色宝石（点亮时发光）。"""
        x = int(st["x"])
        y = int(st["y"])
        col = st["color"]
        lit = st["lit"] > 0
        burst = st["burst"] > 0
        now = pygame.time.get_ticks()
        if lit or burst:
            pulse = 0.72 + 0.28 * math.sin(now * 0.02)
            rad = int(34 * (1.15 if burst else 1.0)
                      * (0.9 + 0.1 * math.sin(now * 0.03)))
            glow = _wd_glow(col, rad).copy()
            glow.set_alpha(int(210 * pulse + (60 if burst else 0)))
            overlay.blit(glow, (x - rad, y - 30 - rad // 2))
            # 对应颜色的提示光环
            ring_r = int(25 + 6 * pulse)
            pygame.draw.circle(overlay, (*col, int(190 * pulse)),
                               (x, y - 12), ring_r, 2)
            pygame.draw.circle(overlay, (255, 255, 255, int(150 * pulse)),
                               (x, y - 12), max(3, ring_r - 3), 1)
        # 底座
        pygame.draw.rect(overlay, (22, 20, 30), (x - 22, y + 14, 44, 9), border_radius=3)
        pygame.draw.rect(overlay, (72, 68, 90), (x - 22, y + 14, 44, 9), 1, border_radius=3)
        # 柱身
        pygame.draw.rect(overlay, (34, 32, 46), (x - 10, y - 4, 20, 20))
        pygame.draw.rect(overlay, (86, 82, 108), (x - 10, y - 4, 20, 20), 1)
        # 顶部宝石
        gem = col if (lit or burst) else tuple(max(0, c - 120) for c in col)
        pygame.draw.polygon(overlay, gem, [
            (x, y - 24), (x + 9, y - 12), (x, y - 1), (x - 9, y - 12)])
        if lit:
            pygame.draw.polygon(overlay, (255, 245, 255), [
                (x, y - 21), (x + 5, y - 13), (x, y - 4)], 1)

    def _draw_dragon_telegraph(self, overlay, d):
        """雕像预兆：沿俯冲方向展开的危险预告线。"""
        tg = d["telegraph"]
        idx = tg["statue"]
        st = _DRAGON_STATUES[idx]
        (sx, sy), (ex, ey) = _wd_dive_line(idx)
        col = st["color"]
        prog = min(1.0, tg["age"] / 26.0)
        fade = max(0.0, 1.0 - max(0, tg["age"] - 30) / 40.0)
        alpha = int(150 * fade)
        # 整条穿越线（入场端 → 出界端）
        pygame.draw.line(overlay, (*col, alpha // 2),
                         (int(sx), int(sy)), (int(ex), int(ey)), 2)
        # 从入场端到雕像的展开亮段
        ex2 = sx + (st["x"] - sx) * prog
        ey2 = sy + (st["y"] - sy) * prog
        pygame.draw.line(overlay, (*col, alpha),
                         (int(sx), int(sy)), (int(ex2), int(ey2)), 4)
        pygame.draw.line(overlay, (255, 255, 255, alpha),
                         (int(sx), int(sy)), (int(ex2), int(ey2)), 1)
        # 入场端标记
        pygame.draw.circle(overlay, (255, 255, 255, alpha), (int(sx), int(sy)), 5, 1)

    def _draw_withered_dragon(self, target, d, x, y, ang, offset_x=0, offset_y=0,
                              alpha=255, height=110, outline=True):
        """绘制枯龙本体：100% 实心 + 剪影描边发光（按运动方向旋转）。"""
        sprite = _get_withered_dragon_sprite(height)
        if sprite is None:
            return
        px = int(x + offset_x)
        py = int(y + offset_y)
        img = pygame.transform.rotate(sprite, -math.degrees(ang))
        if math.cos(ang) < 0:
            img = pygame.transform.flip(img, True, False)
        # 柔和光晕
        glow = _wd_glow((70, 40, 110), max(12, int(img.get_width() * 0.30))).copy()
        glow.set_alpha(max(0, min(255, int(alpha * 0.45))))
        target.blit(glow, (px - glow.get_width() // 2, py - glow.get_height() // 2))
        # 剪影描边：沿轮廓外扩 2px 的亮色边缘
        if outline:
            rim = _get_withered_dragon_outline(height)
            if rim is not None:
                oimg = pygame.transform.rotate(rim, -math.degrees(ang))
                if math.cos(ang) < 0:
                    oimg = pygame.transform.flip(oimg, True, False)
                oimg.set_alpha(min(255, alpha))
                target.blit(oimg, (px - oimg.get_width() // 2, py - oimg.get_height() // 2))
        img.set_alpha(alpha)
        target.blit(img, (px - img.get_width() // 2, py - img.get_height() // 2))

    def _draw_kaeman_withered_dragon(self, screen, offset_x=0, offset_y=0):
        """龙符「Withered Dragon」视觉层：轨道 / 雕像 / 腐化轨迹（枯龙本体画在子弹之上）。"""
        boss = self.boss
        d = getattr(boss, "kaeman_dragon", None)
        if d is None or not boss.alive:
            return
        if self._dragon_overlay is None:
            self._dragon_overlay = pygame.Surface(
                (cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT), pygame.SRCALPHA)
        overlay = self._dragon_overlay
        overlay.fill((0, 0, 0, 0))

        ring = self._dragon_ring_cache()
        if ring is not None:
            overlay.blit(ring, (0, 0))

        # 五座雕像
        for st in d["statues"]:
            self._draw_dragon_statue(overlay, st)

        # 枯龙巡场尾迹（淡紫能量尾线）
        hist = d["history"]
        if len(hist) >= 2:
            for i in range(1, len(hist)):
                fade = i / len(hist)
                a = int(64 * fade)
                pygame.draw.line(overlay, (150, 110, 210, a),
                                 (int(hist[i - 1][0]), int(hist[i - 1][1])),
                                 (int(hist[i][0]), int(hist[i][1])), 3)

        # 腐化能量轨迹（不同形状：短弧 / 短线 / 小圆环）
        for t in d["trails"]:
            fade = 1.0 - t["age"] / max(1, t["max_age"])
            col = t["color"]
            for i, (px, py) in enumerate(t["pts"]):
                a = int(150 * fade * (0.5 + 0.5 * math.sin(i * 2.1)))
                if a <= 0:
                    continue
                r = 7
                glow = _wd_glow(col, r).copy()
                glow.set_alpha(a)
                overlay.blit(glow, (int(px) - r, int(py) - r))

        # 枯龙本体在 draw_foreground 中绘制（子弹之上），这里只绘场景元素

        # 雕像预兆线
        if d["telegraph"] is not None:
            self._draw_dragon_telegraph(overlay, d)

        screen.blit(overlay, (offset_x, offset_y))

    def _draw_dragon_dive_foreground(self, overlay, d):
        """俯冲危险轨迹：从入场端到当前位置的亮线 + 俯冲中的枯龙本体。"""
        dv = d["dive"]
        st = _DRAGON_STATUES[dv["statue"]]
        col = st["color"]
        x0, y0 = dv["sx"], dv["sy"]
        x1, y1 = d["px"], d["py"]
        total = math.hypot(x1 - x0, y1 - y0)
        steps = max(1, int(total / 26.0))
        for i in range(steps + 1):
            fx = x0 + (x1 - x0) * i / steps
            fy = y0 + (y1 - y0) * i / steps
            fade = i / steps
            a = int(60 + 150 * fade)
            pygame.draw.circle(overlay, (*col, a), (int(fx), int(fy)),
                               max(2, int(2 + 5 * fade)), 2)
        pygame.draw.line(overlay, (*col, 210), (int(x0), int(y0)),
                         (int(x1), int(y1)), 4)
        pygame.draw.line(overlay, (255, 255, 255, 210), (int(x0), int(y0)),
                         (int(x1), int(y1)), 1)
        self._draw_withered_dragon(overlay, d, d["px"], d["py"],
                                   d.get("dragon_angle", 0.0),
                                   0, 0, alpha=255, height=132)
    def _draw_kaeman_dominion(self, screen, offset_x=0, offset_y=0):
        """王符「Wither King's Dominion」视觉层：旋转王徽阵 + 中部断开的王权裂隙。

        领域内部整体为安全区域；领域边缘由一圈完整的大玉构成（大玉由弹幕层
        绘制），王权裂隙中部断开（纯装饰）。
        """
        boss = self.boss
        d = getattr(boss, "kaeman_dominion", None)
        if d is None or not boss.alive:
            return
        if self._dominion_overlay is None:
            self._dominion_overlay = pygame.Surface(
                (cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT), pygame.SRCALPHA)
        overlay = self._dominion_overlay
        overlay.fill((0, 0, 0, 0))
        now = pygame.time.get_ticks()
        cx = int(d["cx"])
        cy = int(d["cy"])
        R = d["radius"]
        rot = d["rot"]
        pulse = 0.82 + 0.18 * math.sin(now * 0.011)

        # 领域底色：内部为安全区域，仅保留淡淡的王权法阵光影
        pygame.draw.circle(overlay, (14, 6, 26, 52), (cx, cy), int(R))
        pygame.draw.circle(overlay, (22, 10, 38, 40), (cx, cy), int(R * 0.86))
        # 领域边界：淡淡的脉冲能量环（边框大玉叠加其上）
        er = int(R)
        pygame.draw.circle(overlay, (28, 12, 50, int(90 + 30 * pulse)), (cx, cy), er, 3)
        pygame.draw.circle(overlay, (120, 60, 190, int(70 + 30 * pulse)),
                           (cx, cy), max(1, er - 4), 2)

        # 旋转王徽内圈：缓慢旋转的王权法阵（外圈贴合边框大玉）
        rev = min(R, 470.0)
        inner = rev * 0.76
        outer = rev * 0.98
        pygame.draw.circle(overlay, (70, 24, 120, 84), (cx, cy), int(outer), 10)
        pygame.draw.circle(overlay, (170, 105, 235, 110), (cx, cy), int(outer), 2)
        pygame.draw.circle(overlay, (95, 40, 155, 96), (cx, cy), int(inner), 6)
        pygame.draw.circle(overlay, (205, 155, 255, 105), (cx, cy), int(inner), 2)
        for k in range(12):
            a = rot + k * math.tau / 12
            x0 = cx + math.cos(a) * inner
            y0 = cy + math.sin(a) * inner
            x1 = cx + math.cos(a) * outer
            y1 = cy + math.sin(a) * outer
            pygame.draw.line(overlay, (155, 88, 225, 120), (x0, y0), (x1, y1), 2)
        for k in range(12):
            a0 = rot + k * math.tau / 12
            a1 = a0 + 0.24
            pts = [(cx + math.cos(a) * outer, cy + math.sin(a) * outer)
                   for a in (a0, (a0 + a1) * 0.5, a1)]
            pygame.draw.lines(overlay, (235, 190, 120, 130), False, pts, 2)

        # 王权裂隙：中部断开（断开点为穿行口），随领域旋转
        for k in range(_DOM_FISSURE_COUNT):
            _kaeman_draw_dominion_crack(
                overlay, cx, cy, _dom_fissure_angle(rot, k), R * 0.98, k, 1)

        screen.blit(overlay, (offset_x, offset_y))


    def _draw_kaeman_relics(self, screen, offset_x=0, offset_y=0):
        """冥符「Five Corrupted Relics」视觉层：旋转五边形 + 五颗 Relic 本体。

        Relic 贴图置于五边形顶点并随五边形旋转，彩色光晕与发光连线构成
        五边形；纯视觉，弹幕与命中判定由符卡逻辑负责。
        """
        boss = self.boss
        st = getattr(boss, "kaeman_relics", None)
        if st is None or not boss.alive:
            return
        if self._relic_overlay is None:
            self._relic_overlay = pygame.Surface(
                (cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT), pygame.SRCALPHA)
        overlay = self._relic_overlay
        overlay.fill((0, 0, 0, 0))
        now = pygame.time.get_ticks()
        cx = int(st["cx"])
        cy = int(st["cy"])
        R = st["radius"]
        rot = st["rot"]
        pulse = 0.72 + 0.28 * math.sin(now * 0.013)

        # 环绕轨道：淡环提示五边形旋转范围
        pygame.draw.circle(overlay, (70, 46, 128, 34), (cx, cy), int(R), 1)
        pygame.draw.circle(overlay, (104, 64, 178, 22),
                           (cx, cy), max(1, int(R * 0.97)), 1)

        # 五边形连线：顶点间发光连线（Relic 各自颜色）
        pts = []
        for i in range(5):
            a = rot + i * math.tau / 5
            pts.append((cx + math.cos(a) * R, cy + math.sin(a) * R))
        for i in range(5):
            x0, y0 = int(pts[i][0]), int(pts[i][1])
            x1, y1 = int(pts[(i + 1) % 5][0]), int(pts[(i + 1) % 5][1])
            col = RELIC_COLORS[i]
            pygame.draw.line(overlay, (*col, int(110 * pulse)), (x0, y0), (x1, y1), 3)
            pygame.draw.line(overlay, (235, 215, 255, int(56 * pulse)), (x0, y0), (x1, y1), 1)
        screen.blit(overlay, (offset_x, offset_y))

        # 五颗 Relic 本体：彩色光晕 + 贴图（随五边形旋转，自身缓慢自旋）
        for i in range(5):
            a = rot + i * math.tau / 5
            px = cx + math.cos(a) * R
            py = cy + math.sin(a) * R
            sprite = _load_sprite(cfg.STAGE6_RELIC_SPRITES[i], _REL_SPRITE_HEIGHT)
            if sprite is None:
                continue
            color = RELIC_COLORS[i]
            glow = _get_relic_glow(
                int(_REL_SPRITE_HEIGHT * 0.85 * (0.8 + 0.2 * pulse)), color)
            gx = int(px + offset_x)
            gy = int(py + offset_y)
            screen.blit(glow, (gx - glow.get_width() // 2, gy - glow.get_height() // 2))
            spin = now * 0.00022 + i * math.tau / 5
            spr = pygame.transform.rotozoom(sprite, math.degrees(spin), 1.0)
            screen.blit(spr, (gx - spr.get_width() // 2, gy - spr.get_height() // 2))


    def _draw_kaeman_slash(self, screen, offset_x=0, offset_y=0):
        """裂符：Kaeman 周围危险范围 + 空间裂痕视觉层（纯视觉，判定由光束弹负责）。"""
        boss = self.boss
        if boss is None:
            return
        st = getattr(boss, "kaeman_slash", None)
        if st is None:
            return
        now = pygame.time.get_ticks()
        kx = int(boss.x + offset_x)
        ky = int(boss.y + offset_y)

        # Kaeman 周围极小的危险范围（淡淡红圈，提示勿靠近）
        pygame.draw.circle(screen, (64, 8, 16), (kx, ky), _SLASH_TENTACLE_R, 1)
        pulse = 0.5 + 0.5 * math.sin(now * 0.007)
        pr = int(_SLASH_TENTACLE_R * (0.96 + 0.05 * pulse))
        pygame.draw.circle(screen, (104, 14, 24), (kx, ky), pr, 1)
        for k in range(4):
            a = k * math.pi / 2 + now * 0.0012
            tx = kx + math.cos(a) * _SLASH_TENTACLE_R
            ty = ky + math.sin(a) * _SLASH_TENTACLE_R
            pygame.draw.line(screen, (128, 18, 30), (kx, ky), (int(tx), int(ty)), 1)

        for crack in st["cracks"]:
            t = crack["t"]
            if t < _SLASH_WARN:
                # 预警：起点红色脉冲标记 + 沿未来裂痕路径的细小红色标记
                prog = t / float(_SLASH_WARN)
                rr = max(2, int(5 + 9 * prog * (0.5 + 0.5 * math.sin(now * 0.02))))
                ox = int(crack["x"] + offset_x)
                oy = int(crack["y"] + offset_y)
                pygame.draw.circle(screen, (255, 70, 84), (ox, oy), rr, 1)
                pygame.draw.circle(screen, (255, 150, 158), (ox, oy), 2)
                # 细小红色标记：一开始就点出整条未来斩击线（仅屏幕内），
                # 亮度随预警进度增强，且一个亮点从起点扫向终点提示斩击方向。
                targets = _slash_reveal_targets(crack, prog)
                w_a = cfg.BATTLE_AREA_WIDTH
                h_a = cfg.BATTLE_AREA_HEIGHT
                glow = 0.55 + 0.45 * math.sin(now * 0.028)
                strength = 0.35 + 0.65 * prog
                for pi, path in enumerate(crack["paths"]):
                    segs = crack["seg_lens"][pi]
                    plen = crack["path_lens"][pi]
                    tl = targets[pi]
                    d = 0.0
                    while d <= plen:
                        x, y = _slash_pt_at(path, segs, d)
                        if 12 <= x <= w_a - 12 and 12 <= y <= h_a - 12:
                            jx = math.sin(d * 0.33 + pi * 1.7) * 3.0
                            jy = math.cos(d * 0.29 + pi * 2.3) * 3.0
                            sx = int(x + jx + offset_x)
                            sy = int(y + jy + offset_y)
                            if d <= tl + 14.0:
                                # 扫描亮点：亮度更高、颜色更亮
                                mr = max(2, int(3 + 1.6 * glow))
                                pygame.draw.circle(screen,
                                                   (int(205 + 50 * glow), 66, 80),
                                                   (sx, sy), mr)
                                pygame.draw.circle(screen, (255, 178, 182),
                                                   (sx, sy), max(1, mr - 1))
                            else:
                                mr = max(1, int(2 + 1.2 * glow))
                                pygame.draw.circle(
                                    screen,
                                    (int(112 + 118 * strength), int(30 + 20 * strength), 52),
                                    (sx, sy), mr)
                                pygame.draw.circle(
                                    screen,
                                    (int(196 + 56 * strength), 100, 112),
                                    (sx, sy), max(1, mr - 1))
                        d += 26.0
                continue
            if t < _SLASH_WARN + _SLASH_EXTEND:
                frac = (t - _SLASH_WARN) / float(_SLASH_EXTEND)
            else:
                frac = 1.0
            # 激光式生成：触发瞬间由细迅速变粗、保持厚实一段，再逐渐变细消失
            life = float(_SLASH_EXTEND + _SLASH_BEAM_LIFE + _SLASH_FADE)
            u = max(0.0, min(1.0, (t - _SLASH_WARN) / life))
            if u < 0.08:
                wm = u / 0.08
            elif u < 0.62:
                wm = 1.0
            else:
                wm = max(0.0, 1.0 - (u - 0.62) / 0.38)
            if wm <= 0.01:
                continue
            targets = _slash_reveal_targets(crack, frac)
            for pi, path in enumerate(crack["paths"]):
                pts = _slash_subpath_points(path, crack["seg_lens"][pi], targets[pi])
                if len(pts) < 2:
                    continue
                draw_pts = [(int(x + offset_x), int(y + offset_y)) for x, y in pts]
                a = min(1.0, wm * 1.4)   # 变粗过程中亮度同步增强
                dark = tuple(int(c * a) for c in (14, 6, 10))
                rim = tuple(int(c * a) for c in (140, 20, 34))
                hot = tuple(int(c * a) for c in (255, 82, 96))
                core = (int(180 + 75 * wm * a), int(150 + 76 * wm * a), int(150 + 78 * wm * a))
                pygame.draw.lines(screen, dark, False, draw_pts, max(1, int(16 * wm)))
                pygame.draw.lines(screen, rim, False, draw_pts, max(1, int(9 * wm)))
                pygame.draw.lines(screen, hot, False, draw_pts, max(1, int(5 * wm)))
                pygame.draw.lines(screen, core, False, draw_pts, max(1, int(1 + 5 * wm)))

    def _draw_kaeman_tentacle(self, overlay, st):
        """裂符：触手预警 / 拉拽特效（绘制在子弹与自机之上）。"""
        boss = self.boss
        t = st.get("tentacle")
        if t is None:
            return
        now = pygame.time.get_ticks()
        x0, y0 = boss.x, boss.y
        x1, y1 = t["px"], t["py"]
        phase = t["phase"]
        if phase == "warn":
            prog = t["t"] / float(_SLASH_TENTACLE_WARN)
        elif phase == "pull":
            prog = t["t"] / float(_SLASH_TENTACLE_PULL)
        else:
            prog = 1.0

        # 触手从 Kaeman 伸向玩家
        reach = 0.30 + 0.55 * prog if phase == "warn" else 1.0
        tx = x0 + (x1 - x0) * reach
        ty = y0 + (y1 - y0) * reach
        for k in range(4):
            side = (k - 1.5) * 0.5
            mx = (x0 + tx) / 2 + side * 26 + math.sin(now * 0.012 + k * 2.1) * 10
            my = (y0 + ty) / 2 + math.cos(now * 0.016 + k * 1.3) * 12
            pts = []
            for i in range(14):
                f = i / 13.0
                ix = (1 - f) ** 2 * x0 + 2 * (1 - f) * f * mx + f * f * tx
                iy = (1 - f) ** 2 * y0 + 2 * (1 - f) * f * my + f * f * ty
                pts.append((int(ix), int(iy)))
            if phase == "pull":
                pygame.draw.lines(overlay, (70, 8, 20, 205), False, pts, 5)
                pygame.draw.lines(overlay, (195, 42, 62, 235), False, pts, 2)
            else:
                pygame.draw.lines(overlay, (80, 12, 24, 175), False, pts, 3)
                pygame.draw.lines(overlay, (200, 70, 84, 205), False, pts, 1)

        # 玩家周围的红色结界圈
        pr = int(42 - prog * (24 if phase == "warn" else 30))
        if phase == "warn":
            alpha = 60 + int(150 * (0.5 + 0.5 * math.sin(now * 0.03)))
            pygame.draw.circle(overlay, (255, 60, 74, alpha), (int(x1), int(y1)), max(8, pr), 2)
            pygame.draw.circle(overlay, (255, 130, 140, alpha // 2), (int(x1), int(y1)), max(8, pr + 8), 1)
        elif phase == "pull":
            pygame.draw.circle(overlay, (255, 46, 60, 235), (int(x1), int(y1)), max(6, pr), 2)
        else:
            pygame.draw.circle(overlay, (255, 90, 100, 120), (int(x1), int(y1)), 22, 1)

    # ------------------------------------------------------------------
    # 王符「Atomizing Ray」绘制：扫过扇区提示（子弹之下）+ 预警线/光束（子弹之上）
    # ------------------------------------------------------------------
    def _draw_kaeman_atomize_background(self, screen, offset_x=0, offset_y=0):
        """王符：已扫过扇形区域的暗红半透明提示（绘制在子弹之下）。"""
        st = getattr(self.boss, "kaeman_atomize", None)
        if st is None or st["phase"] != "sweep" or st["swept"] <= 0.08:
            return
        overlay = self._fg_overlay
        overlay.fill((0, 0, 0, 0))
        bx, by = st["bx"], st["by"]
        radius = st["length"]
        swept = st["swept"]
        n = max(5, int(swept / 0.16) + 2)
        edge = min(swept, 0.45)
        m = max(3, int(edge / 0.12) + 2)
        # 光束多时楔形叠加变暗，透明度随光束数自适应
        wedge_alpha = max(8, int(30 / st["beam_count"]))
        edge_alpha = max(12, int(42 / st["beam_count"]))
        for a1 in st["angles"]:
            a0 = a1 - st["dir"] * swept
            # 该光束已扫过的扇形区域
            pts = [(bx, by)]
            for i in range(n + 1):
                a = a0 + (a1 - a0) * i / float(n)
                pts.append((bx + math.cos(a) * radius, by + math.sin(a) * radius))
            pygame.draw.polygon(overlay, (150, 10, 22, wedge_alpha), pts)
            # 扫描前沿：刚被光束扫过、残留弹最密集的一带稍亮
            epts = [(bx, by)]
            for i in range(m + 1):
                a = a1 - st["dir"] * edge * (1.0 - i / float(m))
                epts.append((bx + math.cos(a) * radius, by + math.sin(a) * radius))
            pygame.draw.polygon(overlay, (232, 30, 44, edge_alpha), epts)
        screen.blit(overlay, (offset_x, offset_y))

    def _draw_kaeman_atomize_foreground(self, overlay):
        """王符：首轮蓄力预警线 / 扫射光束（绘制在子弹与自机之上）。"""
        st = getattr(self.boss, "kaeman_atomize", None)
        if st is None:
            return
        bx, by = st["bx"], st["by"]
        phase = st["phase"]
        if phase == "charge":
            count = _atomize_beam_count(st)
            for k in range(count):
                ang = st["ref_angle"] + k * math.tau / count
                self._atomize_draw_warning(overlay, bx, by, ang,
                                           st["length"], st["charge_prog"])
            self._atomize_draw_charge_ring(overlay, bx, by, st["charge_prog"])
        elif phase == "sweep":
            for ang in st["angles"]:
                self._atomize_draw_beam(overlay, bx, by, ang,
                                        st["length"], 1.0)
            if st["t"] < _ATOM_FORM:
                # 轮间重排：新光束组瞬间出现的成形闪光
                k = 1.0 - st["t"] / float(_ATOM_FORM)
                for ang in st["angles"]:
                    ex = bx + math.cos(ang) * st["length"]
                    ey = by + math.sin(ang) * st["length"]
                    pygame.draw.line(overlay, (255, 255, 255, int(150 * k)),
                                     (bx, by), (ex, ey), 3)

    def _atomize_draw_warning(self, overlay, bx, by, angle, length, prog):
        """王符：激光预警线（虚线，随蓄力/预告进度变亮变粗）。"""
        now = pygame.time.get_ticks()
        pulse = 0.5 + 0.5 * math.sin(now * 0.022)
        alpha = int(70 + 160 * prog * (0.55 + 0.45 * pulse))
        width = max(1, int(1 + 3 * prog))
        r = int(255 - 60 * prog)
        g = int(60 + 130 * prog)
        dash, gap = 30.0, 22.0
        d = 0.0
        while d < length:
            d2 = min(d + dash, length)
            x1 = bx + math.cos(angle) * d
            y1 = by + math.sin(angle) * d
            x2 = bx + math.cos(angle) * d2
            y2 = by + math.sin(angle) * d2
            pygame.draw.line(overlay, (r, g, 70, alpha),
                             (x1, y1), (x2, y2), width)
            d = d2 + gap
        # 起点脉冲光球
        glow = 24 + int(18 * pulse)
        pygame.draw.circle(overlay, (255, 70 + int(130 * prog), 80,
                                     int(120 + 110 * prog)), (bx, by), glow, 2)
        pygame.draw.circle(overlay, (255, 190, 180, int(160 * prog + 40)),
                           (bx, by), max(2, glow - 12), 1)

    def _atomize_draw_charge_ring(self, overlay, bx, by, prog):
        """王符：蓄力时 Kaeman 胸前能量聚集环（随进度收紧变亮）。"""
        now = pygame.time.get_ticks()
        ring_r = int(64 - 36 * prog)
        alpha = int(70 + 120 * prog)
        for k in range(2):
            rr = max(2, ring_r + int(6 * math.sin(now * 0.03 + k * 2.1)))
            pygame.draw.circle(overlay, (255, 60 + int(160 * prog), 70, alpha),
                               (bx, by), rr, 2)
            pygame.draw.circle(overlay, (255, 140, 130, alpha // 2),
                               (bx, by), max(2, rr - 12), 1)
        core_r = int(3 + 6 * prog)
        pygame.draw.circle(overlay, (255, 240, 225, 220), (bx, by), core_r)
        pygame.draw.circle(overlay, (255, 90, 90, 180), (bx, by), core_r + 5, 1)

    def _atomize_draw_beam(self, overlay, bx, by, angle, length, alpha):
        """王符：扫射中的原子化激光光束（多层描边 + 边界冲击光）。"""
        now = pygame.time.get_ticks()
        flicker = 0.84 + 0.16 * math.sin(now * 0.05)
        a = int(255 * alpha * flicker)
        ex = bx + math.cos(angle) * length
        ey = by + math.sin(angle) * length
        # 外圈暗红光晕 -> 红色主体 -> 亮红内芯 -> 白热芯
        pygame.draw.line(overlay, (70, 4, 14, int(a * 0.55)), (bx, by), (ex, ey), 18)
        pygame.draw.line(overlay, (218, 28, 46, a), (bx, by), (ex, ey), 9)
        pygame.draw.line(overlay, (255, 100, 100, a), (bx, by), (ex, ey), 4)
        pygame.draw.line(overlay, (255, 240, 236, a), (bx, by), (ex, ey), 2)
        # 光束击中战场边界处的冲击光斑
        hx, hy = _atomize_ray_exit(bx, by, angle, length)
        pygame.draw.circle(overlay, (255, 210, 200, int(a * 0.85)), (hx, hy), 7)
        pygame.draw.circle(overlay, (255, 90, 90, int(a * 0.7)), (hx, hy), 13, 2)
        # 原点光源
        pygame.draw.circle(overlay, (255, 235, 225, a), (bx, by), 6)
        pygame.draw.circle(overlay, (255, 96, 96, int(a * 0.85)), (bx, by), 11, 2)


    def _draw_kaeman_slumber(self, screen, offset_x=0, offset_y=0):
        """终仪「The Wither King's Final Slumber」视觉层：吸收核心 + 放出冲击环。

        吸收阶段：Kaeman 胸前紫色能量核心随吸收量增大、脉动扩张；
        放出瞬间：从王座扩散一圈亮紫冲击环，随后核心剧烈脉动。
        """
        boss = self.boss
        st = getattr(boss, "kaeman_slumber", None)
        if st is None or not boss.alive:
            return
        if self._slumber_overlay is None:
            self._slumber_overlay = pygame.Surface(
                (cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT), pygame.SRCALPHA)
        overlay = self._slumber_overlay
        overlay.fill((0, 0, 0, 0))
        now = pygame.time.get_ticks()
        cx = int(boss.x)
        cy = int(boss.y)
        pulse = 0.5 + 0.5 * math.sin(now * 0.013)

        if st["phase"] == "gather":
            # 吸收能量核心：随吸收量增大变亮变强
            prog = min(1.0, st["absorbed"] / 120.0)
            core = int(26 + 30 * prog)
            alpha = int(70 + 150 * prog)
            pygame.draw.circle(overlay, (60, 18, 110, int(alpha * 0.5)),
                               (cx, cy), core)
            pygame.draw.circle(overlay, (150, 70, 220, alpha),
                               (cx, cy), core + int(4 + 3 * pulse), 2)
            pygame.draw.circle(overlay, (215, 150, 255, int(alpha * 0.8)),
                               (cx, cy), max(2, core - 8), 1)
            # 旋转吸能法阵：四枚小光点绕核心旋转
            for k in range(4):
                a = now * 0.006 + k * math.tau / 4
                r = core + 16 + int(3 * pulse)
                px = int(cx + math.cos(a) * r)
                py = int(cy + math.sin(a) * r)
                pygame.draw.circle(overlay, (235, 195, 255, alpha), (px, py), 3)
        else:
            # 放出阶段：核心剧烈脉动 + 扩散冲击环
            t = st["t"]
            core = int(20 + 8 * pulse + min(20, t * 0.4))
            pygame.draw.circle(overlay, (80, 24, 150, 140), (cx, cy), core)
            pygame.draw.circle(overlay, (225, 170, 255, 190),
                               (cx, cy), core + 4, 2)
            if t < 46:
                f = t / 46.0
                ring_r = int(16 + f * 300)
                ring_a = int(255 * (1.0 - f))
                pygame.draw.circle(overlay, (255, 210, 255, ring_a),
                                   (cx, cy), ring_r, 3)
                pygame.draw.circle(overlay, (170, 80, 230, ring_a // 2),
                                   (cx, cy), max(2, ring_r - 10), 2)

        screen.blit(overlay, (offset_x, offset_y))
