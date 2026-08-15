# -*- coding: utf-8 -*-
# Phase3「Infinite Rage」——Goldor 第二张符卡
# 核心机制：
#   Goldor 固定屏幕中央偏上，4 把巨大金色剑围绕他高速旋转，形成旋转剑盾。
#   凋零骷髅头从巨剑之间的空隙（剑隙）向外散射飞出；
#   同时金色圆弹环与米弹四臂螺旋持续铺场。
# 状态挂在 boss.goldor_rage 上；巨剑 / 盾环 / 剑隙提示由 draw_goldor_rage
# 绘制在弹幕之上（Stage5.draw_foreground 调用）。
import math
import os
import random

import pygame

from src.engine import settings as cfg
from src.entities.bullet import Bullet, create_bullet_angle

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
_GOLDOR_RAGE_SWORD_SPRITE = os.path.join(
    cfg.SPRITES_DIR, "enemies", "stage5", "goldor", "Big_Sword.png")
_GOLDOR_RAGE_WITHER_SKULL_SPRITE = os.path.join(
    cfg.BACKGROUNDS_DIR, "stage3", "Wither_Skull.png")

_GOLDOR_RAGE_BOSS_Y = 132.0            # Goldor 固定于屏幕中央偏上
_GOLDOR_RAGE_SPIN = 0.052              # 剑盾转速（弧度/帧，约 2 秒/圈）
_GOLDOR_RAGE_SWORD_RADIUS = 108.0      # 巨剑中心环绕半径（= 剑隙骷髅出生半径）
_GOLDOR_RAGE_SWORD_LEN = 96.0          # 巨剑剑身长度（px）
_GOLDOR_RAGE_SKULL_INTERVAL = 13       # 剑隙骷髅散射间隔（帧，3 倍密度）
_GOLDOR_RAGE_SKULL_PER_GAP = 1        # 每个剑隙一次散出的骷髅数
_GOLDOR_RAGE_SKULL_SPEED = 4.2         # 骷髅高速（px/帧）
_GOLDOR_RAGE_SKULL_SCATTER = 0.40     # 骷髅散射锥半宽（弧度）
_GOLDOR_RAGE_RING_INTERVAL = 15        # 金色圆弹环间隔（帧，3 倍密度）
_GOLDOR_RAGE_RING_COUNT = 10
_GOLDOR_RAGE_RING_SPEED = 1.9
_GOLDOR_RAGE_EXTRA_RING_INTERVAL = 40  # 白色慢速大环间隔（帧，3 倍密度）
_GOLDOR_RAGE_EXTRA_RING_COUNT = 14
_GOLDOR_RAGE_EXTRA_RING_SPEED = 1.5
_GOLDOR_RAGE_SPIRAL_INTERVAL = 13      # 米弹四臂螺旋间隔（帧，3 倍密度）
_GOLDOR_RAGE_SPIRAL_SPEED = 1.8
_GOLDOR_RAGE_SPIRAL_TURN = 0.11        # 螺旋旋转角速度（弧度/帧）
_GOLDOR_RAGE_SPIRAL_LIFETIME = 300

# ---------------------------------------------------------------------------
# 巨剑贴图（Big_Sword.png 为黑底方图：剑刃银白、护手金色，斜跨对角）
# ---------------------------------------------------------------------------
_goldor_rage_sword_base_attempted = set()
_goldor_rage_sword_base_cache = {}
_goldor_rage_sword_rot_cache = {}
_goldor_rage_glow_cache = {}


def _get_goldor_rage_sword_base(sword_len):
    """加载金色巨剑贴图：抠除黑底，按剑身长度等比缩放。"""
    key = int(round(sword_len))
    if key in _goldor_rage_sword_base_attempted:
        return _goldor_rage_sword_base_cache.get(key)
    _goldor_rage_sword_base_attempted.add(key)
    sprite = None
    try:
        img = pygame.image.load(_GOLDOR_RAGE_SWORD_SPRITE).convert_alpha()
        w, h = img.get_size()
        arr = pygame.surfarray.array3d(img)
        alpha = pygame.surfarray.array_alpha(img)
        alpha[arr.max(axis=2) < 26] = 0
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.surfarray.pixels_alpha(surf)[:] = alpha
        red = pygame.surfarray.pixels_red(surf)
        green = pygame.surfarray.pixels_green(surf)
        blue = pygame.surfarray.pixels_blue(surf)
        red[:] = arr[:, :, 0]
        green[:] = arr[:, :, 1]
        blue[:] = arr[:, :, 2]
        del red, green, blue
        side = max(1, int(round(sword_len / math.sqrt(2))))
        sprite = pygame.transform.smoothscale(surf, (side, side))
    except Exception as exc:
        print(f"[GoldorRage] Failed to load sword sprite: {exc}")
    _goldor_rage_sword_base_cache[key] = sprite
    return sprite


def _get_goldor_rage_sword_rotated(sword_len, sword_angle):
    """按剑位角旋转巨剑贴图：剑刃朝外、金色护手朝内（旋转角 = 角度 + 225°）。"""
    key = (int(round(sword_len)), int(round(math.degrees(sword_angle))) % 360)
    sprite = _goldor_rage_sword_rot_cache.get(key)
    if sprite is not None:
        return sprite
    base = _get_goldor_rage_sword_base(sword_len)
    if base is None:
        return None
    sprite = pygame.transform.rotate(base, math.degrees(sword_angle) + 225)
    _goldor_rage_sword_rot_cache[key] = sprite
    return sprite


def _get_goldor_rage_glow(radius):
    """巨剑底部柔和金色辉光（缓存）。"""
    key = int(radius)
    glow = _goldor_rage_glow_cache.get(key)
    if glow is not None:
        return glow
    size = key * 2
    glow = pygame.Surface((size, size), pygame.SRCALPHA)
    for r in range(key, 0, -1):
        alpha = int(42 * (1 - r / float(key)))
        pygame.draw.circle(glow, (255, 215, 130, alpha), (key, key), r)
    _goldor_rage_glow_cache[key] = glow
    return glow


# ---------------------------------------------------------------------------
# 符卡逻辑
# ---------------------------------------------------------------------------
def _goldor_rage_init(boss):
    """Phase3 开符初始化：固定中央偏上并展开旋转剑盾状态。"""
    boss.goldor_rage = {
        "angle": 0.0,              # 剑盾当前旋转角（剑 0 的角位置）
        "sword_radius": _GOLDOR_RAGE_SWORD_RADIUS,
        "sword_len": _GOLDOR_RAGE_SWORD_LEN,
    }
    boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, _GOLDOR_RAGE_BOSS_Y)


def _goldor_rage_skull_volley(boss, bullet_manager, state):
    """从 4 个剑隙（两把巨剑正中）散射骷髅：不瞄准，沿空隙向外散开。"""
    for i in range(4):
        gap = state["angle"] + (i + 0.5) * math.tau / 4
        sx = boss.x + math.cos(gap) * state["sword_radius"]
        sy = boss.y + math.sin(gap) * state["sword_radius"]
        for _ in range(_GOLDOR_RAGE_SKULL_PER_GAP):
            angle = gap + random.uniform(-_GOLDOR_RAGE_SKULL_SCATTER,
                                         _GOLDOR_RAGE_SKULL_SCATTER)
            speed = _GOLDOR_RAGE_SKULL_SPEED + random.uniform(-0.4, 0.4)
            bullet = create_bullet_angle(sx, sy, angle, speed,
                                         Bullet.TYPE_CIRCLE, radius=3.5,
                                         color=(205, 220, 240), lifetime=420)
            bullet.custom_sprite_path = _GOLDOR_RAGE_WITHER_SKULL_SPRITE
            bullet.custom_sprite_height = 32
            bullet.glow_color = (255, 235, 180)
            bullet.glow_padding = 4
            bullet_manager.add_enemy_bullet(bullet)


def spell_goldor_infinite_rage(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """Phase3「Infinite Rage」：Goldor 固定中央偏上，4 把金色巨剑高速环绕成旋转剑盾；
    凋零骷髅头从巨剑间隙散射飞出，金色圆弹环与米弹四臂螺旋铺满战场。"""
    if getattr(boss, "goldor_rage", None) is None:
        _goldor_rage_init(boss)
    state = boss.goldor_rage
    state["angle"] = (state["angle"] + _GOLDOR_RAGE_SPIN) % math.tau
    boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, _GOLDOR_RAGE_BOSS_Y)

    # 剑隙骷髅（核心机制：源点随剑盾旋转，不瞄准）
    if timer % _GOLDOR_RAGE_SKULL_INTERVAL == 0:
        _goldor_rage_skull_volley(boss, bullet_manager, state)

    # 金色圆弹环：基准角随剑盾旋转
    if timer % _GOLDOR_RAGE_RING_INTERVAL == 0:
        base_angle = state["angle"] * 1.7
        for i in range(_GOLDOR_RAGE_RING_COUNT):
            angle = base_angle + i * math.tau / _GOLDOR_RAGE_RING_COUNT
            bullet_manager.add_enemy_bullet(create_bullet_angle(
                boss.x, boss.y, angle, _GOLDOR_RAGE_RING_SPEED,
                Bullet.TYPE_CIRCLE, radius=3, color=(255, 210, 110)))

    # 白色慢速大环：反向旋转增加层次
    if timer % _GOLDOR_RAGE_EXTRA_RING_INTERVAL == 0:
        base_angle = -state["angle"] * 1.7
        for i in range(_GOLDOR_RAGE_EXTRA_RING_COUNT):
            angle = base_angle + i * math.tau / _GOLDOR_RAGE_EXTRA_RING_COUNT
            bullet_manager.add_enemy_bullet(create_bullet_angle(
                boss.x, boss.y, angle, _GOLDOR_RAGE_EXTRA_RING_SPEED,
                Bullet.TYPE_CIRCLE, radius=3, color=(245, 235, 200)))

    # 米弹四臂螺旋（持续旋转，制造米弹海）
    if timer % _GOLDOR_RAGE_SPIRAL_INTERVAL == 0:
        for arm in range(4):
            angle = timer * _GOLDOR_RAGE_SPIRAL_TURN + arm * math.pi / 2
            bullet_manager.add_enemy_bullet(create_bullet_angle(
                boss.x, boss.y, angle, _GOLDOR_RAGE_SPIRAL_SPEED,
                Bullet.TYPE_RICE, radius=2.5, color=(255, 200, 110),
                lifetime=_GOLDOR_RAGE_SPIRAL_LIFETIME))


# ---------------------------------------------------------------------------
# 绘制：旋转剑盾（绘制在弹幕之上）
# ---------------------------------------------------------------------------
def draw_goldor_rage(screen, boss, ox=0, oy=0):
    """盾环 / 巨剑尾迹 / 剑隙提示 / 金色巨剑本体。"""
    state = getattr(boss, "goldor_rage", None)
    if state is None or not boss.alive:
        return
    now = pygame.time.get_ticks()
    pulse = 0.5 + 0.5 * math.sin(now * 0.009)
    cx = boss.x + ox
    cy = boss.y + oy
    radius = state["sword_radius"]
    r_int = int(radius)

    # 盾环 + 尾迹 + 剑隙提示合并为一张轨道层
    layer = pygame.Surface((r_int * 2 + 10, r_int * 2 + 10), pygame.SRCALPHA)
    c = r_int + 5
    rect = pygame.Rect(5, 5, r_int * 2, r_int * 2)
    pygame.draw.circle(layer, (255, 205, 90, 28), (c, c), r_int, 1)
    pygame.draw.circle(layer, (255, 232, 170, 16), (c, c), r_int - 7, 1)
    angle = state["angle"]
    for i in range(4):
        sword_angle = angle + i * math.tau / 4
        start_a = (sword_angle - 0.62) % math.tau
        stop_a = sword_angle % math.tau
        if stop_a <= start_a:
            stop_a += math.tau
        pygame.draw.arc(layer, (255, 205, 110, int(34 + 30 * pulse)),
                        rect, start_a, stop_a, 2)
        gap = (sword_angle + math.tau / 8) % math.tau
        gap0 = (gap - 0.20) % math.tau
        gap1 = gap + 0.20
        if gap1 <= gap0:
            gap1 += math.tau
        pygame.draw.arc(layer, (255, 240, 190, int(115 + 85 * pulse)),
                        rect, gap0, gap1, 3)
    screen.blit(layer, (int(cx) - c, int(cy) - c))

    # 巨剑本体：金色辉光 + 旋转贴图（剑刃朝外）
    sword_len = state["sword_len"]
    glow = _get_goldor_rage_glow(int(sword_len * 0.55))
    for i in range(4):
        sword_angle = angle + i * math.tau / 4
        sx = cx + math.cos(sword_angle) * radius
        sy = cy + math.sin(sword_angle) * radius
        if glow is not None:
            screen.blit(glow, (int(sx) - glow.get_width() // 2,
                               int(sy) - glow.get_height() // 2))
        sprite = _get_goldor_rage_sword_rotated(sword_len, sword_angle)
        if sprite is not None:
            screen.blit(sprite, (int(sx) - sprite.get_width() // 2,
                                 int(sy) - sprite.get_height() // 2))