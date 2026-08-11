# -*- coding: utf-8 -*-
"""敌弹图集：从一整张 etama.png 按格子裁剪出单个弹幕贴图。

图集布局（256x256，每格 32x32，内部再按 16x16 细分）：
- 第 1 带（y=0~16）方块 s0/s1/s4/s5/s8/s9/s12/s13：保留给线条渲染，不用作子弹
- 第 4 带（y=48~64）圆形 c0~c7：普通圆形子弹
- 顶部三格（第 1~3 格）：每格 4 颗珍珠（s0~s11 下半）；第 4 格上半 2 颗（s12,s13）
- 大弹 big0~big7：y=112~144 的 32x32 大圆（2 颗 x 2 颗子弹大小），同形异色
- 其余部分暂不使用
"""
import pygame
from src.engine import settings as cfg

# 槽位 → 源图裁剪区域 (x, y, w, h)，相对 etama.png 左上角
SLOT_RECTS = {
    "s0": (0, 0, 16, 16),
    "s1": (16, 0, 16, 16),
    "s2": (0, 16, 16, 16),
    "s3": (16, 16, 16, 16),
    "s4": (32, 0, 16, 16),
    "s5": (48, 0, 16, 16),
    "s6": (32, 16, 16, 16),
    "s7": (48, 16, 16, 16),
    "s8": (64, 0, 16, 16),
    "s9": (80, 0, 16, 16),
    "s10": (64, 16, 16, 16),
    "s11": (80, 16, 16, 16),
    "s12": (96, 0, 16, 16),
    "s13": (112, 0, 16, 16),
    # 第 4 带（y=48~64）普通圆形子弹
    "c0": (0, 48, 16, 16),
    "c1": (16, 48, 16, 16),
    "c2": (32, 48, 16, 16),
    "c3": (48, 48, 16, 16),
    "c4": (64, 48, 16, 16),
    "c5": (80, 48, 16, 16),
    "c6": (96, 48, 16, 16),
    "c7": (112, 48, 16, 16),
    # 第 4/5 格下半的珍珠（独立成槽）
    "s14": (96, 16, 16, 16),
    "s15": (112, 16, 16, 16),
    "s16": (128, 16, 16, 16),
    "s17": (144, 16, 16, 16),
    # 大弹：y=112~144 的 32x32 大圆（= 2 颗 x 2 颗子弹大小），8 个同形异色
    "big0": (0, 112, 32, 32),
    "big1": (32, 112, 32, 32),
    "big2": (64, 112, 32, 32),
    "big3": (96, 112, 32, 32),
    "big4": (128, 112, 32, 32),
    "big5": (160, 112, 32, 32),
    "big6": (192, 112, 32, 32),
    "big7": (224, 112, 32, 32),
}

_atlas = None             # 整张图集 Surface
_atlas_attempted = False
_cache = {}               # (slot, width, angle_deg, color) -> Surface


# 判定为"白芯"的最低通道阈值（>= 该值保留白色，如圆弹/珍珠的白色核心）
_WHITE_CORE_MIN = 180


def _tint(surf, color):
    """白芯保留白色，其余部分染成纯子弹颜色（圆弹=白芯+对应颜色外圈，无黑描边）。

    非白像素直接填成子弹颜色（不做亮度缩放，避免出现黑色描边），alpha 保持不变。
    """
    c_r, c_g, c_b = int(color[0]), int(color[1]), int(color[2])
    w, h = surf.get_size()
    out = surf.copy()
    for y in range(h):
        for x in range(w):
            r, g, b, a = surf.get_at((x, y))
            if a == 0 or min(r, g, b) >= _WHITE_CORE_MIN:
                continue
            out.set_at((x, y), (c_r, c_g, c_b, a))
    return out


def _load_atlas():
    """加载整张图集（只加载一次）；失败返回 None。"""
    global _atlas, _atlas_attempted
    if _atlas_attempted:
        return _atlas
    _atlas_attempted = True
    try:
        img = pygame.image.load(cfg.ENEMY_BULLET_ATLAS)
        try:
            img = img.convert_alpha()
        except Exception:
            pass
        _atlas = img
    except Exception as e:
        print(f"[BulletAtlas] Failed to load atlas: {e}")
        _atlas = None
    return _atlas


def get_native_size(slot):
    """槽位在 etama.png 中的原始像素尺寸 (w, h)；槽位不存在返回 None。"""
    rect = SLOT_RECTS.get(slot)
    if rect is None:
        return None
    return rect[2], rect[3]


def get_sprite(slot, width, angle_deg=None, tint_color=None):
    """取槽位贴图，缩放到指定宽度（保持源图宽高比），可按角度旋转、按颜色染色。

    返回 Surface；图集缺失或槽位不存在时返回 None。
    结果按 (slot, width, angle_deg, color) 缓存。
    """
    if slot not in SLOT_RECTS:
        return None
    atlas = _load_atlas()
    if atlas is None:
        return None
    angle = int(round(angle_deg)) % 360 if angle_deg else 0
    color_key = tuple(int(c) for c in tint_color) if tint_color else None
    key = (slot, width, angle, color_key)
    cached = _cache.get(key)
    if cached is not None:
        return cached
    rect = SLOT_RECTS[slot]
    crop = atlas.subsurface(rect).copy()   # subsurface 是视图，copy 后独立缩放
    sw, sh = crop.get_size()
    height = max(1, int(round(width * sh / sw)))
    width = max(1, width)
    if (width, height) != (sw, sh):
        crop = pygame.transform.smoothscale(crop, (width, height))
    if tint_color:
        crop = _tint(crop, tint_color)
    if angle:
        crop = pygame.transform.rotate(crop, angle)
    _cache[key] = crop
    return crop


def clear_cache():
    """清空贴图缓存（换图集后调用）。"""
    _cache.clear()
