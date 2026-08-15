# -*- coding: utf-8 -*-
"""敌弹图集：从一整张 etama.png 按格子裁剪出单个弹幕贴图。

图集布局（256x256）：
- y=0~111：7 行 16 列 16x16 小弹，槽位名为 g{行}_{列}
  默认描述名（自上而下）：
  第1行 激光、第2行 麟弹、第3行 环玉、第4行 小玉、
  第5行 米弹、第6行 苦无弹、第7行 针弹
- y=112~239：4 组 32x32 大弹，每组 8 个，槽位名为 big0~big31
  第8行 大玉（big0~big7），再往下 飞刀（big8~big15），更下方暂不明确
- y=240~255：最底部一行保留，不纳入槽位
"""
import colorsys

import pygame
from src.engine import settings as cfg

# 槽位 → 源图裁剪区域 (x, y, w, h)，相对 etama.png 左上角
# etama.png 上部为 7 行 16 列 16x16 小弹，下面为 4 组 32x32 大弹，底部一行保留不用。
# 小弹行名：激光 / 麟弹 / 环玉 / 小玉 / 米弹 / 苦无弹 / 针弹
_SMALL_ROWS = 7
_SMALL_COLS = 16
_BIG_BANDS = 4
_BIG_COLS = 8


def _build_slot_rects():
    """构建全部可用槽位。

    - 小弹槽位：g{行}_{列}，覆盖 y=0~111 的全部 16x16 格子
      第1行 激光、第2行 麟弹、第3行 环玉、第4行 小玉、
      第5行 米弹、第6行 苦无弹、第7行 针弹
    - 大弹槽位：big0~big31，覆盖 y=112~239 的 4 组 32x32 大弹
      第8行 大玉（big0~big7），再往下 飞刀（big8~big15），更下方暂不明确
    - 保留旧别名：s0~s17、c0~c15（映射到对应小弹格），不破坏现有弹种配置
    """
    rects = {}

    for row in range(_SMALL_ROWS):
        for col in range(_SMALL_COLS):
            rects[f"g{row:02d}_{col:02d}"] = (col * 16, row * 16, 16, 16)

    for band in range(_BIG_BANDS):
        for col in range(_BIG_COLS):
            rects[f"big{band * _BIG_COLS + col}"] = (
                col * 32, 112 + band * 32, 32, 32)

    # 旧槽位别名（保持既有配置和 sprite_slot 覆盖可用）
    rects.update({
        "s0": rects["g00_00"],
        "s1": rects["g00_01"],
        "s2": rects["g01_00"],
        "s3": rects["g01_01"],
        "s4": rects["g00_02"],
        "s5": rects["g00_03"],
        "s6": rects["g01_02"],
        "s7": rects["g01_03"],
        "s8": rects["g00_04"],
        "s9": rects["g00_05"],
        "s10": rects["g01_04"],
        "s11": rects["g01_05"],
        "s12": rects["g00_06"],
        "s13": rects["g00_07"],
        "s14": rects["g01_06"],
        "s15": rects["g01_07"],
        "s16": rects["g01_08"],
        "s17": rects["g01_09"],
        "c0": rects["g03_00"],
        "c1": rects["g03_01"],
        "c2": rects["g03_02"],
        "c3": rects["g03_03"],
        "c4": rects["g03_04"],
        "c5": rects["g03_05"],
        "c6": rects["g03_06"],
        "c7": rects["g03_07"],
        "c8": rects["g03_08"],
        "c9": rects["g03_09"],
        "c10": rects["g03_10"],
        "c11": rects["g03_11"],
        "c12": rects["g03_12"],
        "c13": rects["g03_13"],
        "c14": rects["g03_14"],
        "c15": rects["g03_15"],
    })
    return rects


SLOT_RECTS = _build_slot_rects()

_atlas = None             # 整张图集 Surface
_atlas_attempted = False
_cache = {}               # (slot, width, angle_deg, color) -> Surface
_color_sig_cache = {}     # slot -> (r, g, b) 原图代表性颜色
_color_pick_cache = {}    # (base_slot, color) -> 最接近的颜色槽位


# 判定为"白芯"的最低通道阈值（>= 该值保留白色，如圆弹/珍珠的白色核心）
_WHITE_CORE_MIN = 180


def _tint(surf, color):
    """白芯保留白色，其余部分按原图明度染成子弹颜色，保留原图渐变。

    非白像素的明度决定染色深浅：暗部仍偏暗、亮部仍偏亮，
    这样不会把原图渐变压平成纯色，alpha 保持不变。
    """
    c_r, c_g, c_b = int(color[0]), int(color[1]), int(color[2])
    w, h = surf.get_size()
    out = surf.copy()
    for y in range(h):
        for x in range(w):
            r, g, b, a = surf.get_at((x, y))
            if a == 0 or min(r, g, b) >= _WHITE_CORE_MIN:
                continue
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            factor = lum / 255.0
            out.set_at((x, y), (
                int(round(c_r * factor)),
                int(round(c_g * factor)),
                int(round(c_b * factor)),
                a,
            ))
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


def _slot_candidates(base_slot):
    """返回与 base_slot 同排 / 同大弹带的全部颜色变体槽位。"""
    rect = SLOT_RECTS.get(base_slot)
    if rect is None:
        return []
    x, y, w, h = rect
    if w == 16 and h == 16:
        row = y // 16
        return [f"g{row:02d}_{col:02d}" for col in range(_SMALL_COLS)]
    if w == 32 and h == 32:
        band = (y - 112) // 32
        if 0 <= band < _BIG_BANDS:
            return [f"big{band * _BIG_COLS + col}" for col in range(_BIG_COLS)]
    return []


def _slot_color_signature(slot):
    """计算槽位原图的代表性颜色；无色相（白/灰/黑）时返回 None。"""
    if slot in _color_sig_cache:
        return _color_sig_cache[slot]
    atlas = _load_atlas()
    rect = SLOT_RECTS.get(slot)
    if atlas is None or rect is None:
        _color_sig_cache[slot] = None
        return None
    crop = atlas.subsurface(rect)
    sw_r = sw_g = sw_b = 0.0
    total_weight = 0.0
    for py in range(crop.get_height()):
        for px in range(crop.get_width()):
            r, g, b, a = crop.get_at((px, py))
            if a < 20:
                continue
            max_channel = max(r, g, b)
            min_channel = min(r, g, b)
            if max_channel < 235 and (max_channel - min_channel) > 10:
                saturation = max_channel - min_channel
                weight = saturation * (0.35 + 0.65 * max_channel / 255.0)
                sw_r += r * weight
                sw_g += g * weight
                sw_b += b * weight
                total_weight += weight
    if total_weight <= 0:
        _color_sig_cache[slot] = None
        return None
    sig = (sw_r / total_weight, sw_g / total_weight, sw_b / total_weight)
    _color_sig_cache[slot] = sig
    return sig


def _hsv_distance(color_a, color_b):
    """按色相、饱和度和明度比较颜色，色相优先，避免绿色误配成青色。"""
    ha, sa, va = colorsys.rgb_to_hsv(*(channel / 255.0 for channel in color_a))
    hb, sb, vb = colorsys.rgb_to_hsv(*(channel / 255.0 for channel in color_b))
    hue_dist = min(abs(ha - hb), 1.0 - abs(ha - hb))
    return hue_dist * 0.7 + abs(sa - sb) * 0.25 + abs(va - vb) * 0.5


def pick_color_slot(base_slot, color):
    """在 base_slot 同排颜色变体中，选择原图颜色最接近 color 的槽位。

    color 接近白/灰/黑时直接返回 base_slot（中性原图），避免强行配成彩色。
    结果按 (base_slot, color) 缓存。
    """
    color_key = tuple(int(channel) for channel in color)
    cache_key = (base_slot, color_key)
    if cache_key in _color_pick_cache:
        return _color_pick_cache[cache_key]

    max_channel = max(color_key)
    min_channel = min(color_key)
    if max_channel < 40 or (max_channel - min_channel) < 20:
        _color_pick_cache[cache_key] = base_slot
        return base_slot

    best = None
    for slot in _slot_candidates(base_slot):
        sig = _slot_color_signature(slot)
        if sig is None:
            continue
        distance = _hsv_distance(color_key, sig)
        if best is None or distance < best[0]:
            best = (distance, slot)

    chosen = best[1] if best is not None else base_slot
    _color_pick_cache[cache_key] = chosen
    return chosen


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
    _color_sig_cache.clear()
    _color_pick_cache.clear()
