# 符卡特殊背景（东方风格）
# 展开符卡时覆盖在关卡背景上的特效层：
# 2D 贴图（web.png / 程序化图案）+ 简单数学动画（旋转/缩放/正弦扭曲/流动）+ 混合特效（叠加/暗角）
# 亮度刻意压低，避免影响读谱。

import math
import os
import random

import numpy as np
import pygame

from src.engine import settings as cfg
from src.engine.panorama3d import CylinderPanorama

AREA_W = int(cfg.BATTLE_AREA_WIDTH)       # 576
AREA_H = int(cfg.BATTLE_AREA_HEIGHT)      # 670
PATTERN_SIZE = 256                        # 图案原图边长（越小越省性能）

# 特效中心：略偏上，靠近 Boss
EFFECT_CENTER = (AREA_W / 2.0, AREA_H * 0.42)

FADE_IN = 20        # 开符淡入帧数
ROT_CACHE_STEP = 4.0    # 旋转层缓存角度步长（度），小于此步长的旋转直接复用上一帧结果
FADE_OUT = 36       # 结符淡出帧数
BURST_FRAMES = 45   # 开符瞬间扩散光环时长（帧）
FLASH_FRAMES = 14   # 开符瞬间的轻微闪光时长（帧）

# 基础暗色：符卡期间背景整体压暗，保证弹幕可读
BASE_COLOR = (7, 9, 20)


class _Layer:
    """一层特效：图案 + 每帧数学变换"""
    __slots__ = ("pattern", "rot_speed", "scale", "pulse", "freq", "scroll", "blend",
                 "orbit", "pos", "panorama", "image")

    def __init__(self, pattern, rot_speed=0.0, scale=1.0, pulse=0.0, freq=0.0,
                 scroll=None, blend="add", orbit=None, pos=None, panorama=None,
                 image=None):
        self.pattern = pattern          # 图案 key（见 _PATTERN_MAKERS）
        self.rot_speed = rot_speed      # 旋转速度（度/帧）
        self.scale = scale              # 基准缩放
        self.pulse = pulse              # 缩放脉动幅度
        self.freq = freq                # 脉动频率（Hz）
        self.scroll = scroll            # 平铺滚动速度 (x, y)（像素/帧）；None 表示旋转层
        self.blend = blend              # "add"=叠加发光 / "alpha"=普通透明混合
        self.orbit = orbit              # 环绕 (半径, 角速度度/帧)；None 表示居中旋转
        self.pos = pos                  # 固定绘制位置 (x, y)（画布坐标）；None 表示居中/环绕
        self.panorama = panorama        # 伪3D环形全景配置 dict（key/speed/fov...）；None 表示普通层
        self.image = image              # 全屏背景贴图 key（见 IMAGE_TEXTURES）；None 表示普通层


# --- 图案生成（程序化 + 贴图染色，均缓存） ---

_pattern_cache = {}

# 全景贴图注册表：key -> 左右无缝的 360° 环形全景图路径
PANORAMA_TEXTURES = {
    "stage3_bg1": os.path.join(cfg.BACKGROUNDS_DIR, "stage3", "bg1.png"),
    "scarf": os.path.join(cfg.BACKGROUNDS_DIR, "stage4", "scarf", "bg_scarf.png"),
    "sadan": os.path.join(cfg.BACKGROUNDS_DIR, "stage4", "sadan", "bg_sadan.png"),
    "professor": os.path.join(cfg.BACKGROUNDS_DIR, "stage5", "professor", "bg_professor.png"),
    "necron": os.path.join(cfg.BACKGROUNDS_DIR, "stage5", "necron", "bg_necron.png"),
    "thorn": os.path.join(cfg.BACKGROUNDS_DIR, "stage5", "thorn", "bg_thorn.png"),
    "livid": os.path.join(cfg.BACKGROUNDS_DIR, "stage5", "livid", "bg_livid.png"),
}

# 全屏背景贴图注册表：key -> 符卡期间整幅铺满战斗区域的背景图路径
IMAGE_TEXTURES = {
    "maxor": os.path.join(cfg.BACKGROUNDS_DIR, "stage5", "maxor", "bg.png"),
    "storm": os.path.join(cfg.BACKGROUNDS_DIR, "stage5", "storm", "bg.png"),
    "goldor": os.path.join(cfg.BACKGROUNDS_DIR, "stage5", "goldor", "bg.png"),
}


def _make_web_pattern(color, arms=8, rings=5):
    """程序化蛛网：放射臂 + 同心环（多层描边模拟辉光）"""
    size = PATTERN_SIZE
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size / 2.0
    r_max = size * 0.60
    for arm in range(arms):
        a = arm * math.tau / arms + math.pi * 0.125
        ex = cx + math.cos(a) * r_max
        ey = cy + math.sin(a) * r_max
        for width, alpha in ((3, 110), (6, 52), (12, 22)):
            pygame.draw.line(surf, (*color, alpha), (cx, cy), (ex, ey), width)
    for i in range(1, rings + 1):
        r = int(r_max * i / rings)
        for width, alpha in ((2, 92), (6, 36)):
            pygame.draw.circle(surf, (*color, alpha), (cx, cy), r, width)
    return surf


def _make_spiral_pattern(color, arms=2):
    """对数螺旋（龙卷风/漩涡）：臂尾渐亮，旋转时像旋转风暴"""
    size = PATTERN_SIZE
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size / 2.0
    turns = 4.2
    n = 260
    for arm in range(arms):
        prev = None
        for i in range(n + 1):
            t = i / n
            theta = t * turns * math.tau + arm * math.pi
            r = 6 + (size * 0.58 - 6) * t
            x = cx + math.cos(theta) * r
            y = cy + math.sin(theta) * r
            if prev is not None:
                alpha = int(24 + 82 * t)
                pygame.draw.line(surf, (*color, alpha), prev, (x, y), 2)
            prev = (x, y)
    return surf


def _make_thread_pattern(color, count=9, amp=9):
    """流动丝线：竖直正弦细线，整体随 y 同步摆动（横向/纵向均无缝平铺）"""
    size = PATTERN_SIZE
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    spacing = size / float(count)
    for i in range(count):
        base_x = (i + 0.5) * spacing
        prev = None
        for y in range(0, size + 1, 3):
            x = base_x + amp * math.sin(math.tau * y / size)
            if prev is not None:
                pygame.draw.line(surf, (*color, 58), prev, (x, y), 2)
                pygame.draw.line(surf, (*color, 20), prev, (x, y), 5)
            prev = (x, y)
    return surf


def _make_soul_pattern(color, count=30, seed=7):
    """魂灵光点：散布圆点 + 拖尾 + 微弱外环（旋转时像星海流动）"""
    size = PATTERN_SIZE
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    rng = random.Random(seed)
    cx = cy = size / 2.0
    for _ in range(count):
        x = rng.uniform(12, size - 12)
        y = rng.uniform(12, size - 12)
        r = rng.uniform(1.5, 4.0)
        a = rng.uniform(34, 96)
        pygame.draw.circle(surf, (*color, int(a)), (x, y), max(1, int(r)))
        pygame.draw.circle(surf, (*color, int(a * 0.5)), (x, y), int(r + 2))
        pygame.draw.circle(surf, (*color, int(a * 0.28)), (x, y), int(r + 4))
        for k in range(3):
            tx = x - (k + 1) * 3.5
            ty = y + (k + 1) * 1.5
            tr = max(1, int(r * (1 - k * 0.25)))
            pygame.draw.circle(surf, (*color, int(a * (0.5 - k * 0.13))),
                               (int(tx), int(ty)), tr)
    pygame.draw.circle(surf, (*color, 30), (cx, cy), size * 0.42, 2)
    pygame.draw.circle(surf, (*color, 16), (cx, cy), size * 0.42 + 4, 1)
    return surf


def _make_monolith_pattern(color, count=8):
    """环立巨石阵：一圈竖直石板（圆角 + 裂纹），旋转时像环绕祭坛的石柱群，避免蛛网感"""
    size = PATTERN_SIZE
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size / 2.0
    r = size * 0.33
    w, h = size * 0.075, size * 0.26
    for i in range(count):
        a = i * math.tau / count
        x = cx + math.cos(a) * r
        y = cy + math.sin(a) * r
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (int(x), int(y))
        for width, alpha in ((3, 100), (8, 38)):
            pygame.draw.rect(surf, (*color, alpha), rect, width, border_radius=5)
        # 风化裂纹：竖缝 + 斜缝
        top = rect.top
        mid = top + h * 0.45
        pygame.draw.line(surf, (*color, 72), (x, top + 8), (x, mid), 2)
        pygame.draw.line(surf, (*color, 46), (x, mid), (x + w * 0.4, mid + h * 0.16), 1)
        pygame.draw.line(surf, (*color, 46), (x, top + h * 0.78), (x - w * 0.3, top + h * 0.92), 1)
    # 内圈祭坛边：点状虚线环（无放射线，不织网）
    for k in range(54):
        ang = k * math.tau / 54
        px = cx + math.cos(ang) * r * 0.55
        py = cy + math.sin(ang) * r * 0.55
        pygame.draw.circle(surf, (*color, 48), (int(px), int(py)), 2)
    return surf


def _make_debris_pattern(color, count=26, seed=11):
    """飘浮碎石：散落的随机小石块 + 微尘，旋转时像环绕祭坛浮动的末地残骸"""
    size = PATTERN_SIZE
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    rng = random.Random(seed)
    cx = cy = size / 2.0
    for _ in range(count):
        ang = rng.uniform(0, math.tau)
        rad = rng.uniform(22, size * 0.44)
        x = cx + math.cos(ang) * rad
        y = cy + math.sin(ang) * rad
        s = rng.uniform(3, 9)
        rot = rng.uniform(0, math.tau)
        pts = []
        for k in range(4):
            rr = s * rng.uniform(0.5, 1.0)
            aa = rot + k * math.pi / 2 + rng.uniform(-0.4, 0.4)
            pts.append((x + math.cos(aa) * rr, y + math.sin(aa) * rr))
        alpha = rng.uniform(30, 82)
        pygame.draw.polygon(surf, (*color, int(alpha)), pts, 1)
        pygame.draw.circle(surf, (*color, int(alpha * 0.6)), (int(x), int(y)), 1)
    return surf


def _make_bolt_pattern(color, count=7, seed=3):
    """闪电：数道折线电弧，旋转时像雷云中不断闪动的电光"""
    size = PATTERN_SIZE
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    rng = random.Random(seed)
    cx = cy = size / 2.0
    for i in range(count):
        angle = i * math.tau / count + rng.uniform(-0.3, 0.3)
        x, y = cx, cy
        prev = (x, y)
        length = size * (0.28 + rng.uniform(0, 0.22))
        segs = rng.randint(4, 7)
        for k in range(segs):
            x += math.cos(angle) * length / segs + rng.uniform(-8, 8)
            y += math.sin(angle) * length / segs + rng.uniform(-8, 8)
            alpha = int(150 - 65 * k / segs)
            pygame.draw.line(surf, (*color, alpha), prev, (x, y), 3)
            pygame.draw.line(surf, (*color, alpha // 2), prev, (x, y), 7)
            prev = (x, y)
    return surf


def _tint_texture_asset(relpath, rgb):
    """加载任意背景贴图，等比缩放到 PATTERN_SIZE 高并染色压暗；失败返回 None"""
    path = os.path.join(cfg.ASSETS_DIR, "backgrounds", relpath)
    try:
        img = pygame.image.load(path)
        try:
            img = img.convert_alpha()
        except Exception:
            pass
        w, h = img.get_size()
        s = PATTERN_SIZE / float(h)
        img = pygame.transform.smoothscale(img, (max(1, int(w * s)), PATTERN_SIZE))
        img = img.convert_alpha()
        img.fill((*rgb, 255), special_flags=pygame.BLEND_RGB_MULT)
        return img
    except Exception:
        return None

def _tinted_web_asset(rgb):
    """加载 2D 贴图 web.png，缩放并染色压暗；失败则回退程序化蛛网"""
    img = _tint_texture_asset(os.path.join("stage1", "web.png"), rgb)
    return img if img is not None else _make_web_pattern(rgb)



def _make_rgba_surface(rgb, alpha):
    """由 numpy 数组构建带逐像素透明度的 Surface（数组按 [x, y] 索引）"""
    w, h = rgb.shape[0], rgb.shape[1]
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.surfarray.blit_array(surf, np.ascontiguousarray(rgb, dtype=np.uint8))
    pa = pygame.surfarray.pixels_alpha(surf)
    pa[:, :] = np.ascontiguousarray(alpha, dtype=np.uint8)
    del pa
    return surf


def _soft_blur(surf, factor=6):
    """廉价模糊：缩小再放大（用于图标光晕）"""
    w, h = surf.get_size()
    try:
        small = pygame.transform.smoothscale(surf, (max(2, w // factor), max(2, h // factor)))
        return pygame.transform.smoothscale(small, (w, h))
    except Exception:
        return pygame.transform.scale(surf, (w, h))


def _load_item_icon(filename, tint=(1.0, 1.0, 1.0), target_h=150, dim=0.6, glow=0.5,
                    folder="stage1"):
    """黑底物品图标 -> 半透明徽记：亮度抠底 + 裁剪 + 缩放 + 染色压暗 + 光晕"""
    path = os.path.join(cfg.ASSETS_DIR, "backgrounds", folder, filename)
    try:
        img = pygame.image.load(path)
        w, h = img.get_size()
        rgb = pygame.surfarray.array3d(img).astype(np.float32)          # (w, h, 3)
        lum = rgb.mean(axis=2)
        alpha = np.clip((lum - 6.0) / 24.0, 0.0, 1.0)                   # 亮度抠底（暗色主体也保留）
        # 尊重素材自带透明通道：透明像素不再被亮度抠底重新点亮
        if img.get_flags() & pygame.SRCALPHA:
            own_a = pygame.surfarray.array_alpha(img).astype(np.float32) / 255.0
            alpha = np.minimum(alpha, own_a)
        # 去除角部纯色方块底（如物品图标常见的灰/绿底）：边角色彩较亮且均匀时按主色全局抠除
        border_pts = np.concatenate(
            (rgb[:, 0], rgb[:, h - 1], rgb[0, :], rgb[w - 1, :]), axis=0)
        bg_color = np.median(border_pts, axis=0)
        if float(bg_color.mean()) > 25.0:
            bg_dist = np.abs(rgb - bg_color).sum(axis=2)
            alpha[bg_dist <= 48.0] = 0.0
        # ADD 混合会忽略源图 alpha、只叠加 RGB：透明像素残留的底色（如灰绿方块）也会被
        # 叠到画布上形成色块。将 RGB 按 alpha 预乘，使透明像素变为黑色（叠加贡献为 0）。
        rgb = rgb * alpha[:, :, None]
        mask = alpha > 0.05
        if not mask.any():
            return None
        ys, xs = np.nonzero(mask)
        pad = 8
        x0 = max(0, int(ys.min()) - pad); x1 = min(w - 1, int(ys.max()) + pad)
        y0 = max(0, int(xs.min()) - pad); y1 = min(h - 1, int(xs.max()) + pad)
        crop_rgb = rgb[x0:x1 + 1, y0:y1 + 1]
        crop_a = alpha[x0:x1 + 1, y0:y1 + 1]
        tmp = _make_rgba_surface(crop_rgb, crop_a * 255.0)
        s = target_h / float(tmp.get_height())
        nw = max(1, int(tmp.get_width() * s))
        try:
            icon = pygame.transform.smoothscale(tmp, (nw, target_h))
        except Exception:
            icon = pygame.transform.scale(tmp, (nw, target_h))
        # 染色 + 压暗
        arr = pygame.surfarray.array3d(icon).astype(np.float32)
        arr *= np.array(tint, dtype=np.float32) * dim
        np.clip(arr, 0, 255, out=arr)
        a_arr = pygame.surfarray.array_alpha(icon).astype(np.float32)
        icon = _make_rgba_surface(arr, a_arr)
        # 光晕：调亮 + 模糊 + 放大后垫底
        halo = _make_rgba_surface(np.clip(arr * 1.6, 0, 255), a_arr * glow)
        halo = _soft_blur(halo)
        halo = pygame.transform.smoothscale(halo,
                (max(2, int(halo.get_width() * 1.35)), max(2, int(halo.get_height() * 1.35))))
        out = pygame.Surface(halo.get_size(), pygame.SRCALPHA)
        out.blit(halo, (0, 0))
        out.blit(icon, ((out.get_width() - icon.get_width()) // 2,
                        (out.get_height() - icon.get_height()) // 2))
        return out
    except Exception:
        return None


_PATTERN_MAKERS = {
    # 蛛网贴图（染色）：金 / 紫 / 淡蓝 / 紫罗兰
    "web_gold":       lambda: _tinted_web_asset((150, 108, 46)),
    "web_gold_dim":   lambda: _tinted_web_asset((80, 58, 26)),
    "web_purple":     lambda: _tinted_web_asset((96, 56, 140)),
    "web_purple_dim": lambda: _tinted_web_asset((50, 30, 80)),
    "web_pale":       lambda: _tinted_web_asset((72, 92, 128)),
    "web_violet":     lambda: _tinted_web_asset((104, 50, 150)),
    # 程序化漩涡 / 丝线 / 魂灵
    "spiral_purple":      lambda: _make_spiral_pattern((118, 44, 160)),
    "spiral_purple_dim":  lambda: _make_spiral_pattern((64, 28, 92)),
    "spiral_red":         lambda: _make_spiral_pattern((132, 42, 72)),
    "thread_pale":        lambda: _make_thread_pattern((110, 144, 214)),
    "thread_gold":        lambda: _make_thread_pattern((178, 140, 66)),
    "soul_violet":        lambda: _make_soul_pattern((150, 66, 214)),
    # SkyBlock 物品图标（抠底徽记；缺失时回退程序化图案）
    "icon_spool":     lambda: _load_item_icon("Luxurious_Spool.png", tint=(1.05, 0.70, 0.32), target_h=150, dim=0.68, glow=0.55) or _make_spiral_pattern((120, 90, 40)),
    "icon_string":    lambda: _load_item_icon("Soul_String.png", tint=(0.75, 0.95, 1.15), target_h=150, dim=0.62, glow=0.45) or _make_thread_pattern((110, 150, 220)),
    "icon_arack":     lambda: _load_item_icon("Arack.png", tint=(0.80, 0.95, 0.75), target_h=185, dim=0.85, glow=0.60) or _make_spiral_pattern((100, 140, 90)),
    "icon_fang":      lambda: _load_item_icon("Arachne's_Fang.png", tint=(0.90, 0.78, 1.10), target_h=95, dim=0.55, glow=0.40) or _make_soul_pattern((150, 120, 200)),
    "icon_fragment":  lambda: _load_item_icon("Arachne_Fragment.png", tint=(0.85, 0.70, 1.20), target_h=150, dim=0.58, glow=0.50) or _make_soul_pattern((140, 90, 220)),
    "icon_essence":   lambda: _load_item_icon("Spider_Essence.png", tint=(0.70, 0.90, 0.65), target_h=95, dim=0.80, glow=0.55) or _make_soul_pattern((110, 150, 110)),
    # 第2面末地素材（末地石守护者）：末地石 / 末影珍珠 / 召唤之眼 / 末地石玫瑰 / 傀儡宠物 / 黑曜石柱
    "stone_floor":      lambda: _tint_texture_asset(os.path.join("stage2", "floor1.png"), (172, 164, 128)),
    "monolith_pale":    lambda: _make_monolith_pattern((222, 212, 168)),
    "debris_pale":      lambda: _make_debris_pattern((212, 202, 162)),
    "spiral_teal":      lambda: _make_spiral_pattern((74, 176, 168)),
    "icon_endstone":    lambda: _load_item_icon("Enchanted_End_Stone.png", tint=(1.02, 0.96, 0.78), target_h=150, dim=0.78, glow=0.55, folder="stage2") or _make_monolith_pattern((220, 210, 165)),
    "icon_pearl":       lambda: _load_item_icon("Enchanted_Ender_Pearl.png", tint=(0.55, 1.05, 1.05), target_h=90, dim=0.72, glow=0.60, folder="stage2") or _make_soul_pattern((90, 200, 200)),
    "icon_eye":         lambda: _load_item_icon("Summoning_Eye.webp", tint=(0.45, 0.95, 0.85), target_h=80, dim=0.66, glow=0.55, folder="stage2") or _make_soul_pattern((80, 190, 170)),
    "icon_rose":        lambda: _load_item_icon("End_stone_rose.png", tint=(0.95, 0.55, 0.80), target_h=70, dim=0.70, glow=0.50, folder="stage2") or _make_soul_pattern((200, 110, 160)),
    "icon_golem":       lambda: _load_item_icon("Golem_Pet.png", tint=(0.85, 0.90, 1.00), target_h=110, dim=0.70, glow=0.50, folder="stage2") or _make_monolith_pattern((150, 160, 180)),
    "pillar_left":      lambda: _load_item_icon("pillar1.png", tint=(0.85, 0.80, 1.05), target_h=300, dim=0.60, glow=0.40, folder="stage2") or _make_thread_pattern((90, 80, 130)),
    "pillar_right":     lambda: _load_item_icon("pillar2.png", tint=(0.80, 0.75, 1.10), target_h=300, dim=0.60, glow=0.40, folder="stage2") or _make_thread_pattern((90, 80, 130)),
    # 二面关底Boss（末影龙）：龙息 / 落雷 / 万龙 / 上位龙铠
    "bg_end":           lambda: _tint_texture_asset(os.path.join("stage2", "bg.png"), (168, 118, 200)),
    "bg_storm":         lambda: _tint_texture_asset(os.path.join("stage2", "bg2.png"), (96, 160, 210)),
    "bg_fire":          lambda: _tint_texture_asset(os.path.join("stage2", "bg2.png"), (216, 88, 38)),
    "bg_gold":          lambda: _tint_texture_asset(os.path.join("stage2", "bg.png"), (216, 168, 66)),
    "spiral_gold":      lambda: _make_spiral_pattern((212, 158, 64)),
    "soul_fire":        lambda: _make_soul_pattern((255, 118, 40), count=26, seed=13),
    "bolt_pale":        lambda: _make_bolt_pattern((168, 216, 255)),
    "icon_core":        lambda: _load_item_icon("Judgement_Core.png", tint=(1.05, 0.72, 0.35), target_h=130, dim=0.75, glow=0.65, folder="stage2") or _make_spiral_pattern((220, 150, 60)),
    "icon_terminator":  lambda: _load_item_icon("42px-Terminator.png", tint=(0.70, 1.05, 1.15), target_h=110, dim=0.70, glow=0.55, folder="stage2") or _make_bolt_pattern((120, 200, 255)),
    "icon_dragon_pet":  lambda: _load_item_icon("Ender_Dragon_Pet.png", tint=(1.05, 0.72, 1.20), target_h=170, dim=0.80, glow=0.55, folder="stage2") or _make_spiral_pattern((170, 90, 220)),
    "icon_claw":        lambda: _load_item_icon("Dragon_Claw.png", tint=(0.95, 0.68, 1.22), target_h=110, dim=0.62, glow=0.45, folder="stage2") or _make_soul_pattern((170, 90, 220)),
    "icon_scale":       lambda: _load_item_icon("Dragon_Scale.png", tint=(0.58, 1.02, 1.06), target_h=90, dim=0.66, glow=0.50, folder="stage2") or _make_soul_pattern((90, 200, 200)),
    "icon_helmet":      lambda: _load_item_icon("64px-Superior_Dragon_Helmet.png", tint=(1.30, 1.06, 0.42), target_h=120, dim=0.80, glow=0.65, folder="stage2") or _make_spiral_pattern((230, 190, 80)),
    "icon_superior_frag": lambda: _load_item_icon("64px-Superior_Dragon_Fragment.png", tint=(1.35, 0.92, 0.30), target_h=95, dim=0.72, glow=0.55, folder="stage2") or _make_soul_pattern((240, 180, 70)),
    # 第3面地下墓穴素材（The Watcher / Bonzo）：墓穴地板 / 注视之眼 / 骷髅 / 暗之宝珠 / 气球
    "catacomb_floor":   lambda: _tint_texture_asset(os.path.join("stage3", "floor.png"), (128, 150, 164)),
    "icon_watcher_eye": lambda: _load_item_icon("watcher_eye.png", tint=(0.80, 1.10, 1.12), target_h=110, dim=0.72, glow=0.55, folder="stage3") or _make_bolt_pattern((110, 210, 235)),
    "icon_skull":       lambda: _load_item_icon("skull.png", tint=(0.95, 1.05, 1.00), target_h=100, dim=0.66, glow=0.45, folder="stage3") or _make_soul_pattern((190, 190, 180)),
    "icon_dark_orb":    lambda: _load_item_icon("dark_orb.png", tint=(1.10, 0.55, 1.05), target_h=80, dim=0.70, glow=0.60, folder="stage3") or _make_soul_pattern((160, 60, 190)),
    "icon_balloon":     lambda: _load_item_icon("balloon.png", tint=(1.10, 0.75, 0.90), target_h=90, dim=0.72, glow=0.55, folder="stage3") or _make_spiral_pattern((220, 90, 130)),
    "icon_balloon_cyan": lambda: _load_item_icon("balloon.png", tint=(0.70, 1.10, 1.15), target_h=64, dim=0.70, glow=0.55, folder="stage3") or _make_spiral_pattern((80, 200, 210)),
    "icon_balloon_gold": lambda: _load_item_icon("balloon.png", tint=(1.15, 1.00, 0.55), target_h=64, dim=0.70, glow=0.55, folder="stage3") or _make_spiral_pattern((230, 200, 90)),
}


def _get_pattern(key):
    surf = _pattern_cache.get(key)
    if surf is None:
        maker = _PATTERN_MAKERS.get(key)
        if maker is None:
            raise KeyError("unknown spell bg pattern: %r" % (key,))
        surf = maker()
        _pattern_cache[key] = surf
    return surf


# --- 静态辅助贴图（暗角 / 中心微光 / 开符光环） ---


def _make_vignette(w, h, strength=0.42):
    """径向暗角：四周乘到 (1-strength)，中心不变"""
    x = np.arange(w, dtype=np.float32)[:, None]
    y = np.arange(h, dtype=np.float32)[None, :]
    d = np.sqrt(((x - w / 2.0) / (w * 0.62)) ** 2 + ((y - h / 2.0) / (h * 0.62)) ** 2)
    d = np.clip(d, 0.0, 1.0) ** 1.6
    val = 1.0 - strength * d
    arr = np.repeat((val * 255.0).astype(np.uint8)[..., None], 3, axis=2)
    surf = pygame.Surface((w, h))
    pygame.surfarray.blit_array(surf, arr)
    return surf


def _make_glow(w, h, cx, cy, radius, color):
    """中心径向微光（叠加用，颜色已压暗）"""
    x = np.arange(w, dtype=np.float32)[:, None]
    y = np.arange(h, dtype=np.float32)[None, :]
    d = np.sqrt(((x - cx) / radius) ** 2 + ((y - cy) / radius) ** 2)
    d = np.clip(1.0 - d, 0.0, 1.0) ** 2
    arr = np.empty((w, h, 3), dtype=np.uint8)
    for c_i in range(3):
        arr[:, :, c_i] = np.clip(color[c_i] * d, 0, 255).astype(np.uint8)
    surf = pygame.Surface((w, h))
    pygame.surfarray.blit_array(surf, arr)
    return surf


def _scale_cover(surf, w, h):
    """等比放大到铺满 w x h 后居中裁剪（保留整幅观感，不留黑边）"""
    sw, sh = surf.get_size()
    scale = max(w / float(sw), h / float(sh))
    nw, nh = max(1, int(round(sw * scale))), max(1, int(round(sh * scale)))
    try:
        scaled = pygame.transform.smoothscale(surf, (nw, nh))
    except Exception:
        scaled = pygame.transform.scale(surf, (nw, nh))
    x = (nw - w) // 2
    y = (nh - h) // 2
    return scaled.subsurface((x, y, w, h)).copy()


# --- 符卡风格配置 ---
# 每张符卡按名字印象选择一套“旋转/缩放/扭曲/流动”的组合

STYLES = {
    "spool": {  # 罠符「Luxurious Spool」：金色丝线纺轮
        "base": (9, 8, 16),
        "glow": (26, 20, 8),
        "ring": (255, 200, 110),
        "layers": [
            _Layer("web_gold", rot_speed=0.28, scale=2.0, pulse=0.04, freq=0.35),
            _Layer("web_gold_dim", rot_speed=-0.20, scale=2.7, pulse=0.05, freq=0.28),
            _Layer("thread_gold", scroll=(0.0, 0.5), blend="alpha"),
            _Layer("icon_spool", rot_speed=0.35, scale=0.72, pulse=0.05, freq=0.40),
        ],
    },
    "thread": {  # 丝符「Soul String」：银色魂丝流动
        "base": (6, 9, 18),
        "glow": (12, 20, 38),
        "ring": (170, 210, 255),
        "layers": [
            _Layer("thread_pale", scroll=(0.0, 0.85), blend="alpha"),
            _Layer("web_pale", rot_speed=0.10, scale=2.2, pulse=0.03, freq=0.3),
            _Layer("spiral_purple_dim", rot_speed=0.45, scale=1.6, pulse=0.05, freq=0.4),
            _Layer("icon_string", rot_speed=0.60, scale=0.72, pulse=0.07, freq=0.35),
        ],
    },
    "tornado": {  # 蛛符「Tarantula's Tornado」：蛛丝龙卷
        "base": (10, 6, 18),
        "glow": (30, 12, 40),
        "ring": (210, 90, 230),
        "layers": [
            _Layer("spiral_purple", rot_speed=1.4, scale=2.2, pulse=0.16, freq=0.55),
            _Layer("web_purple", rot_speed=-0.55, scale=2.4, pulse=0.08, freq=0.4),
            _Layer("spiral_red", rot_speed=-0.9, scale=1.35, pulse=0.10, freq=0.45),
            _Layer("icon_arack", rot_speed=2.20, scale=0.85, pulse=0.14, freq=0.55),
            _Layer("icon_essence", rot_speed=1.20, scale=0.42, orbit=(150, 0.90)),
        ],
    },
    "soul": {  # 魂符「Dark Queen's Soul」：暗紫魂灵
        "base": (8, 6, 20),
        "glow": (24, 10, 42),
        "ring": (190, 110, 255),
        "layers": [
            _Layer("soul_violet", rot_speed=0.24, scale=2.2, pulse=0.07, freq=0.3),
            _Layer("web_violet", rot_speed=-0.12, scale=2.6, pulse=0.05, freq=0.25),
            _Layer("thread_pale", scroll=(0.0, 0.35), blend="alpha"),
            _Layer("icon_fragment", rot_speed=0.40, scale=0.72, pulse=0.06, freq=0.35),
            _Layer("icon_fang", rot_speed=1.40, scale=0.50, orbit=(140, 1.00)),
        ],
    },
    "stone": {  # 石符「Immobile Protector's Wraith」：末地石守护者怨灵祭坛（整体压暗，突出弹幕）
        "base": (6, 5, 10),
        "glow": (16, 14, 8),
        "ring": (200, 190, 150),
        "dim": 0.58,
        "layers": [
            _Layer("stone_floor", scroll=(0.0, 0.28), blend="alpha"),
            _Layer("monolith_pale", rot_speed=0.10, scale=2.2, pulse=0.03, freq=0.25),
            _Layer("debris_pale", rot_speed=-0.06, scale=1.7, blend="alpha"),
            _Layer("spiral_teal", rot_speed=-0.45, scale=1.62, pulse=0.07, freq=0.40),
            _Layer("icon_endstone", rot_speed=0.28, scale=0.62, pulse=0.05, freq=0.35),
            _Layer("pillar_left", rot_speed=0.04, scale=0.62, pos=(62, AREA_H * 0.60)),
            _Layer("pillar_right", rot_speed=-0.04, scale=0.62, pos=(AREA_W - 62, AREA_H * 0.60)),
            _Layer("icon_golem", rot_speed=0.10, scale=0.46, pulse=0.04, freq=0.30, orbit=(158, 0.55)),
            _Layer("icon_pearl", rot_speed=0.80, scale=0.40, pulse=0.08, freq=0.50, orbit=(132, -0.75)),
            _Layer("icon_eye", rot_speed=-0.60, scale=0.36, pulse=0.07, freq=0.45, orbit=(186, 0.40)),
            _Layer("icon_rose", rot_speed=0.55, scale=0.32, pulse=0.09, freq=0.60, orbit=(104, -1.05)),
        ],
    },
    "fire": {  # 燃符「Fireball Barrage」：龙息火球
        "base": (16, 7, 5),
        "glow": (46, 18, 6),
        "ring": (255, 150, 60),
        "layers": [
            _Layer("bg_fire", scroll=(0.0, 0.30), blend="alpha"),
            _Layer("spiral_red", rot_speed=0.80, scale=2.1, pulse=0.10, freq=0.45),
            _Layer("soul_fire", rot_speed=-0.35, scale=1.9, pulse=0.06, freq=0.30),
            _Layer("icon_core", rot_speed=0.55, scale=0.66, pulse=0.08, freq=0.42),
            _Layer("icon_pearl", rot_speed=-1.10, scale=0.38, pulse=0.10, freq=0.55, orbit=(150, 0.9)),
        ],
    },
    "lightning": {  # 闪符「Non-Directional Lightning」：无定向落雷
        "base": (5, 8, 18),
        "glow": (12, 22, 46),
        "ring": (170, 220, 255),
        "dim": 0.45,
        "layers": [
            _Layer("bg_storm", scroll=(0.0, 0.55), blend="alpha"),
            _Layer("thread_pale", scroll=(0.0, 0.9), blend="alpha"),
            _Layer("bolt_pale", rot_speed=0.30, scale=1.9, pulse=0.10, freq=0.60),
            _Layer("spiral_teal", rot_speed=-0.60, scale=1.55, pulse=0.06, freq=0.35),
            _Layer("icon_terminator", rot_speed=1.10, scale=0.60, pulse=0.09, freq=0.50),
        ],
    },
    "dragon": {  # 龙符「One with the Dragons」：万龙共鸣
        "base": (10, 5, 18),
        "glow": (32, 12, 40),
        "ring": (215, 145, 255),
        "layers": [
            _Layer("bg_end", scroll=(0.0, 0.28), blend="alpha"),
            _Layer("spiral_purple", rot_speed=0.55, scale=2.2, pulse=0.07, freq=0.35),
            _Layer("web_violet", rot_speed=-0.25, scale=2.4, pulse=0.05, freq=0.28),
            _Layer("icon_dragon_pet", rot_speed=0.22, scale=0.62, pulse=0.05, freq=0.30),
            _Layer("icon_claw", rot_speed=1.20, scale=0.44, pulse=0.08, freq=0.45, orbit=(150, 0.85)),
            _Layer("icon_scale", rot_speed=-0.90, scale=0.38, pulse=0.07, freq=0.40, orbit=(178, -0.65)),
            _Layer("icon_pearl", rot_speed=0.60, scale=0.34, pulse=0.09, freq=0.55, orbit=(118, 1.10)),
        ],
    },
    "superiority": {  # 超符「Superiority」：黄金领域·龙鳞风暴
        "base": (14, 10, 4),
        "glow": (48, 36, 10),
        "ring": (255, 222, 120),
        "layers": [
            _Layer("bg_gold", scroll=(0.0, 0.35), blend="alpha"),
            _Layer("thread_gold", scroll=(0.0, 0.60), blend="alpha"),
            _Layer("spiral_gold", rot_speed=-0.70, scale=2.0, pulse=0.08, freq=0.40),
            _Layer("icon_helmet", rot_speed=0.40, scale=0.62, pulse=0.06, freq=0.35),
            _Layer("icon_superior_frag", rot_speed=1.30, scale=0.42, pulse=0.08, freq=0.50, orbit=(150, 1.00)),
            _Layer("icon_core", rot_speed=-0.80, scale=0.48, pulse=0.07, freq=0.45, orbit=(186, -0.80)),
            _Layer("icon_terminator", rot_speed=0.90, scale=0.42, pulse=0.09, freq=0.55, orbit=(122, 0.60)),
        ],
    },
    "watcher": {  # 眼符「Gaze of the Watcher」：注视之眼（青辉激光）
        "base": (4, 7, 14),
        "glow": (10, 26, 34),
        "ring": (120, 230, 240),
        "dim": 0.5,
        "layers": [
            _Layer("catacomb_floor", scroll=(0.0, 0.30), blend="alpha"),
            _Layer("bolt_pale", rot_speed=0.35, scale=2.0, pulse=0.08, freq=0.5),
            _Layer("thread_pale", scroll=(0.0, 0.8), blend="alpha"),
            _Layer("icon_watcher_eye", rot_speed=0.25, scale=0.62, pulse=0.06, freq=0.4),
            _Layer("icon_skull", rot_speed=1.10, scale=0.40, pulse=0.08, freq=0.5, orbit=(150, 0.8)),
        ],
    },
    "undead": {  # 唤符「Undead Legion」：亡灵军团（暗绿骷髅）
        "base": (7, 9, 8),
        "glow": (18, 26, 16),
        "ring": (150, 230, 120),
        "dim": 0.52,
        "layers": [
            _Layer(None, panorama=dict(key="stage3_bg1", speed=16.0, fov=60,
                                        floor=os.path.join(cfg.BACKGROUNDS_DIR,
                                                           "stage3", "bossfloor1.png")),
                   blend="alpha"),
            _Layer("soul_violet", rot_speed=0.30, scale=2.2, pulse=0.07, freq=0.35),
            _Layer("thread_pale", scroll=(0.0, 0.6), blend="alpha"),
            _Layer("icon_skull", rot_speed=0.50, scale=0.62, pulse=0.06, freq=0.4),
            _Layer("icon_dark_orb", rot_speed=1.20, scale=0.40, pulse=0.08, freq=0.5, orbit=(140, 0.9)),
        ],
    },
    "bonzo": {  # 球符「Balloon Barrage」：气球狂欢（马戏团色彩）
        "base": (16, 6, 18),
        "glow": (46, 12, 40),
        "ring": (255, 140, 200),
        "dim": 0.45,
        "layers": [
            _Layer(None, panorama=dict(key="stage3_bg1", speed=28.0, fov=60,
                                        floor=os.path.join(cfg.BACKGROUNDS_DIR,
                                                           "stage3", "bossfloor1.png")),
                   blend="alpha"),
            _Layer("spiral_red", rot_speed=0.80, scale=2.1, pulse=0.10, freq=0.45),
            _Layer("soul_fire", rot_speed=-0.40, scale=1.8, pulse=0.06, freq=0.30),
            _Layer("icon_balloon", rot_speed=0.45, scale=0.60, pulse=0.07, freq=0.40),
            _Layer("icon_balloon_cyan", rot_speed=1.20, scale=0.38, pulse=0.09, freq=0.55, orbit=(140, 0.9)),
            _Layer("icon_balloon_gold", rot_speed=-0.90, scale=0.34, pulse=0.08, freq=0.50, orbit=(172, -0.7)),
        ],
    },
    "scarf": {  # 队符「Necrotic Squad」：Scarf 专属（暂复制 Bonzo 背景占位）
        "base": (7, 9, 8),
        "glow": (18, 26, 16),
        "ring": (150, 230, 120),
        "dim": 0.52,
        "layers": [
            _Layer(None, panorama=dict(key="scarf", speed=16.0, fov=60,
                                        floor=os.path.join(cfg.BACKGROUNDS_DIR,
                                                           "stage4", "scarf", "fl_scarf.png")),
                   blend="alpha"),
            _Layer("soul_violet", rot_speed=0.30, scale=2.2, pulse=0.07, freq=0.35),
            _Layer("thread_pale", scroll=(0.0, 0.6), blend="alpha"),
            _Layer("icon_skull", rot_speed=0.50, scale=0.62, pulse=0.06, freq=0.4),
            _Layer("icon_dark_orb", rot_speed=1.20, scale=0.40, pulse=0.08, freq=0.5, orbit=(140, 0.9)),
        ],
    },
    "sadan": {  # Sadan 亡灵符卡专属（暂复制 Bonzo 背景占位）
        "base": (7, 9, 8),
        "glow": (18, 26, 16),
        "ring": (150, 230, 120),
        "dim": 0.52,
        "layers": [
            _Layer(None, panorama=dict(key="sadan", speed=16.0, fov=60,
                                        floor=os.path.join(cfg.BACKGROUNDS_DIR,
                                                           "stage4", "sadan", "fl_sadan.png")),
                   blend="alpha"),
            _Layer("soul_violet", rot_speed=0.30, scale=2.2, pulse=0.07, freq=0.35),
            _Layer("thread_pale", scroll=(0.0, 0.6), blend="alpha"),
            _Layer("icon_skull", rot_speed=0.50, scale=0.62, pulse=0.06, freq=0.4),
            _Layer("icon_dark_orb", rot_speed=1.20, scale=0.40, pulse=0.08, freq=0.5, orbit=(140, 0.9)),
        ],
    },
    "professor": {  # Professor 专属：绿色护符环形大厅
        "base": (7, 9, 8),
        "glow": (18, 26, 16),
        "ring": (150, 230, 120),
        "dim": 0.52,
        "layers": [
            _Layer(None, panorama=dict(key="professor", speed=16.0, fov=60,
                                        floor=os.path.join(cfg.BACKGROUNDS_DIR,
                                                           "stage5", "professor", "fl_professor.png")),
                   blend="alpha"),
            _Layer("soul_violet", rot_speed=0.30, scale=2.2, pulse=0.07, freq=0.35),
            _Layer("thread_pale", scroll=(0.0, 0.6), blend="alpha"),
            _Layer("icon_skull", rot_speed=0.50, scale=0.62, pulse=0.06, freq=0.4),
            _Layer("icon_dark_orb", rot_speed=1.20, scale=0.40, pulse=0.08, freq=0.5, orbit=(140, 0.9)),
        ],
    },
    "necron": {  # Necron 凋符专属（暂复制 Bonzo 背景占位）
        "base": (7, 9, 8),
        "glow": (18, 26, 16),
        "ring": (150, 230, 120),
        "dim": 0.52,
        "layers": [
            _Layer(None, panorama=dict(key="necron", speed=16.0, fov=60,
                                        floor=os.path.join(cfg.BACKGROUNDS_DIR,
                                                           "stage5", "necron", "fl_necron.png")),
                   blend="alpha"),
            _Layer("soul_violet", rot_speed=0.30, scale=2.2, pulse=0.07, freq=0.35),
            _Layer("thread_pale", scroll=(0.0, 0.6), blend="alpha"),
            _Layer("icon_skull", rot_speed=0.50, scale=0.62, pulse=0.06, freq=0.4),
            _Layer("icon_dark_orb", rot_speed=1.20, scale=0.40, pulse=0.08, freq=0.5, orbit=(140, 0.9)),
        ],
    },
    "thorn": {  # Thorn 专属（暂复制 Bonzo 背景占位）
        "base": (7, 9, 8),
        "glow": (18, 26, 16),
        "ring": (150, 230, 120),
        "dim": 0.52,
        "layers": [
            _Layer(None, panorama=dict(key="thorn", speed=16.0, fov=60,
                                        floor=os.path.join(cfg.BACKGROUNDS_DIR,
                                                           "stage5", "thorn", "fl_thorn.png")),
                   blend="alpha"),
            _Layer("soul_violet", rot_speed=0.30, scale=2.2, pulse=0.07, freq=0.35),
            _Layer("thread_pale", scroll=(0.0, 0.6), blend="alpha"),
            _Layer("icon_skull", rot_speed=0.50, scale=0.62, pulse=0.06, freq=0.4),
            _Layer("icon_dark_orb", rot_speed=1.20, scale=0.40, pulse=0.08, freq=0.5, orbit=(140, 0.9)),
        ],
    },
    "livid": {  # Livid 专属（暂复制 Bonzo 背景占位）
        "base": (7, 9, 8),
        "glow": (18, 26, 16),
        "ring": (150, 230, 120),
        "dim": 0.52,
        "layers": [
            _Layer(None, panorama=dict(key="livid", speed=16.0, fov=60,
                                        floor=os.path.join(cfg.BACKGROUNDS_DIR,
                                                           "stage5", "livid", "fl_livid.png")),
                   blend="alpha"),
            _Layer("soul_violet", rot_speed=0.30, scale=2.2, pulse=0.07, freq=0.35),
            _Layer("thread_pale", scroll=(0.0, 0.6), blend="alpha"),
            _Layer("icon_skull", rot_speed=0.50, scale=0.62, pulse=0.06, freq=0.4),
            _Layer("icon_dark_orb", rot_speed=1.20, scale=0.40, pulse=0.08, freq=0.5, orbit=(140, 0.9)),
        ],
    },
    "maxor": {  # Maxor 专属：凋零竞技场全屏背景
        "base": (9, 6, 6),
        "glow": (26, 14, 8),
        "ring": (255, 150, 70),
        "dim": 0.75,
        "layers": [
            _Layer(None, image="maxor"),
        ],
    },
    "storm": {  # Storm 专属：雷霆祭坛全屏背景
        "base": (6, 8, 14),
        "glow": (10, 20, 34),
        "ring": (170, 220, 255),
        "dim": 0.75,
        "layers": [
            _Layer(None, image="storm"),
        ],
    },
    "goldor": {  # Goldor 专属：金甲堡垒全屏背景
        "base": (10, 9, 5),
        "glow": (28, 22, 8),
        "ring": (255, 210, 90),
        "dim": 0.78,
        "layers": [
            _Layer(None, image="goldor"),
        ],
    },
}

DEFAULT_STYLE = "thread"


def detect_style(spell_name):
    """按符卡名印象挑选风格（也支持显式指定）"""
    n = (spell_name or "").lower()
    if "spool" in n or "罠" in n:
        return "spool"
    if "tornado" in n or "蛛" in n:
        return "tornado"
    if "string" in n or "thread" in n or "丝" in n:
        return "thread"
    if "soul" in n or "dark" in n or "魂" in n:
        return "soul"
    if "wraith" in n or "immobile" in n or "protector" in n or "stone" in n or "石" in n:
        return "stone"
    if "superiority" in n or "superior" in n or "超" in n:
        return "superiority"
    if "lightning" in n or "闪" in n:
        return "lightning"
    if "fireball" in n or "fire" in n or "燃" in n:
        return "fire"
    if "dragon" in n or "龙" in n:
        return "dragon"
    if "watcher" in n or "watch" in n or "gaze" in n or "eye" in n or "眼" in n:
        return "watcher"
    if "undead" in n or "wither" in n or "skull" in n or "骸" in n or "唤" in n:
        return "undead"
    if "balloon" in n or "气球" in n or "球符" in n:
        return "bonzo"
    return DEFAULT_STYLE


class SpellBackground:
    """一张符卡对应的动态背景：开符时淡入，结符时淡出。"""

    def __init__(self, spell_name="", bg_style=None):
        style = bg_style or detect_style(spell_name)
        if style not in STYLES:
            style = DEFAULT_STYLE
        self.style = style
        conf = STYLES[style]

        self.layers = conf["layers"]
        self.ring_color = conf["ring"]

        # 伪3D环形全景层：为带 panorama 配置的层创建渲染器（贴图缺失时回退普通层）
        self.panoramas = []
        for layer in self.layers:
            if layer.panorama is None:
                self.panoramas.append(None)
                continue
            pconf = dict(layer.panorama)
            path = PANORAMA_TEXTURES.get(pconf.pop("key", None))
            if not path or not os.path.exists(path):
                self.panoramas.append(None)
                continue
            self.panoramas.append(CylinderPanorama(
                path, AREA_W, AREA_H,
                fov=pconf.get("fov", 115.0),
                speed=pconf.get("speed", 12.0),
                yaw=pconf.get("yaw", 0.0),
                projection=pconf.get("projection", "cylinder"),
                floor_texture_path=pconf.get("floor"),
                floor_junction_v=pconf.get("floor_junction_v"),
                floor_depth_repeat=pconf.get("floor_depth_repeat")))
        # 全屏背景贴图层：为带 image 配置的层预缩放/裁剪到战斗区域尺寸
        self.images = []
        for layer in self.layers:
            if layer.image is None:
                self.images.append(None)
                continue
            path = IMAGE_TEXTURES.get(layer.image)
            if not path or not os.path.exists(path):
                self.images.append(None)
                continue
            try:
                img = pygame.image.load(path).convert()
            except Exception:
                self.images.append(None)
                continue
            self.images.append(_scale_cover(img, AREA_W, AREA_H))
        self.base_color = conf["base"]
        self.glow = _make_glow(AREA_W, AREA_H, *EFFECT_CENTER, AREA_H * 0.62, conf["glow"])
        self.vignette = _make_vignette(AREA_W, AREA_H)

        # 整体压暗系数：<1.0 时整幅背景统一乘以该亮度，保证弹幕可读
        self.dim = conf.get("dim", 1.0)
        dv = int(max(0, min(255, round(self.dim * 255))))
        self.dim_surf = pygame.Surface((AREA_W, AREA_H))
        self.dim_surf.fill((dv, dv, dv))

        # 开符瞬间扩散光环
        burst_r = 340
        self.burst = pygame.Surface((burst_r * 2, burst_r * 2), pygame.SRCALPHA)
        self._burst_r = burst_r

        self.canvas = pygame.Surface((AREA_W, AREA_H))
        # 旋转层缓存：角度/缩放分桶后复用 rotozoom 结果，避免每帧全量旋转
        self._sprite_cache = {}
        self.timer = 0
        self.fading = False
        self.fade_out_t = 0
        self.done = False

    # --- 生命周期 ---

    @property
    def is_opaque(self):
        """背景已完全覆盖关卡（可跳过伪3D背景绘制以省性能）"""
        return not self.fading and self.timer >= FADE_IN

    def begin_fade_out(self):
        if not self.fading:
            self.fading = True
            self.fade_out_t = 0

    def update(self, dt):
        if self.done:
            return
        self.timer += 1
        # 全景环绕独立推进（结符淡出期间也继续旋转）
        for pan in self.panoramas:
            if pan is not None:
                pan.update(dt)
        if self.fading:
            self.fade_out_t += 1
            if self.fade_out_t >= FADE_OUT:
                self.done = True

    # --- 绘制 ---

    def _overall_alpha(self):
        if self.fading:
            k = max(0.0, 1.0 - self.fade_out_t / float(FADE_OUT))
        else:
            k = min(1.0, self.timer / float(FADE_IN))
        return int(max(0, min(255, 255 * k)))

    def set_panorama_speed(self, speed, duration=0.0):
        """设置全景环绕速度（度/秒）；duration>0 时平滑过渡，便于符卡编排。"""
        for pan in self.panoramas:
            if pan is None:
                continue
            if duration > 0:
                pan.ramp_speed(speed, duration)
            else:
                pan.set_speed(speed)

    def _draw_sprite(self, canvas, layer, t, cx, cy):
        pat = _get_pattern(layer.pattern)
        angle = (t * layer.rot_speed) % 360.0
        pulse = 1.0 + layer.pulse * math.sin(t * 0.01 * layer.freq * 6.28)
        scale = layer.scale * pulse
        px, py = cx, cy
        if layer.orbit is not None:
            rad, spd = layer.orbit
            ang = math.radians(t * spd)
            px = cx + rad * math.cos(ang)
            py = cy + rad * math.sin(ang)
        if layer.pos is not None:
            px, py = layer.pos
        # 旋转/缩放分桶：视觉上不可感知的微小变化直接复用缓存，大幅降低开销
        key = (layer.pattern, int(angle // ROT_CACHE_STEP), int(scale / 0.04))
        img = self._sprite_cache.get(key)
        if img is None:
            img = pygame.transform.rotozoom(pat, angle, scale)
            if len(self._sprite_cache) > 24:
                self._sprite_cache.clear()
            self._sprite_cache[key] = img
        flags = pygame.BLEND_RGB_ADD if layer.blend == "add" else 0
        canvas.blit(img, (px - img.get_width() / 2.0, py - img.get_height() / 2.0),
                    special_flags=flags)

    def _draw_tiled(self, canvas, layer, t):
        pat = _get_pattern(layer.pattern)
        tw, th = pat.get_size()
        w, h = canvas.get_size()
        ox = int(-(layer.scroll[0] * t)) % tw
        oy = int(-(layer.scroll[1] * t)) % th
        for x in range(ox - tw, w + tw, tw):
            for y in range(oy - th, h + th, th):
                canvas.blit(pat, (x, y))

    def _draw_burst(self, canvas, t, cx, cy):
        if t >= BURST_FRAMES:
            return
        prog = t / float(BURST_FRAMES)
        ease = 1.0 - (1.0 - prog) ** 2          # ease-out
        r = int(24 + self._burst_r * ease)
        a = int(120 * (1.0 - prog))
        self.burst.fill((0, 0, 0, 0))
        pygame.draw.circle(self.burst, (*self.ring_color, a),
                           (self._burst_r, self._burst_r), r, 3)
        pygame.draw.circle(self.burst, (*self.ring_color, a // 2),
                           (self._burst_r, self._burst_r), r + 9, 1)
        canvas.blit(self.burst, (cx - self._burst_r, cy - self._burst_r))

    def _apply_warp(self, canvas, t, amp=6, freq=0.020, speed=0.10):
        """正弦扭曲：把画面切成横条做波浪位移，形成流动/扭曲感"""
        w, h = canvas.get_size()
        strip_h = 16
        for y in range(0, h, strip_h):
            sh = min(strip_h, h - y)
            off = int(amp * math.sin(y * freq + t * speed))
            if off == 0:
                continue
            src = canvas.subsurface((0, y, w, sh)).copy()
            canvas.blit(src, (off, y))

    def draw(self, screen, offset_x=0, offset_y=0):
        if self.done:
            return
        t = self.timer
        alpha = self._overall_alpha()
        if alpha <= 0:
            return

        canvas = self.canvas
        canvas.fill(self.base_color)

        cx, cy = EFFECT_CENTER
        for i, layer in enumerate(self.layers):
            if layer.panorama is not None:
                pan = self.panoramas[i] if i < len(self.panoramas) else None
                if pan is not None:
                    pan.draw(canvas)
            elif layer.image is not None:
                img = self.images[i] if i < len(self.images) else None
                if img is not None:
                    canvas.blit(img, (0, 0))
            elif layer.scroll is not None:
                self._draw_tiled(canvas, layer, t)
            else:
                self._draw_sprite(canvas, layer, t, cx, cy)

        # 开符瞬间：轻微闪光 + 扩散光环
        if t < FLASH_FRAMES:
            f = int(38 * (1.0 - t / float(FLASH_FRAMES)))
            canvas.fill((f, f, f), special_flags=pygame.BLEND_RGB_ADD)
        self._draw_burst(canvas, t, cx, cy)

        # 正弦扭曲（旋转/缩放/流动之上再加一层波浪位移）
        self._apply_warp(canvas, t)

        # 中心微光 + 四周暗角：提神但整体压暗，保证弹幕可读
        canvas.blit(self.glow, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        canvas.blit(self.vignette, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

        # 整体压暗（乘算，只影响背景，不影响弹幕）
        if self.dim < 1.0:
            canvas.blit(self.dim_surf, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

        canvas.set_alpha(alpha)
        screen.blit(canvas, (offset_x, offset_y))
