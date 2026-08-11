# -*- coding: utf-8 -*-
# 生成二面占位素材：末地地面 / 洞壁 / 关卡标题卡
# 运行：python _gen_stage2_assets.py
import os
import random

os.makedirs(os.path.join("assets", "backgrounds", "stage2"), exist_ok=True)
os.makedirs(os.path.join("assets", "titles"), exist_ok=True)

import numpy as np
from PIL import Image, ImageDraw, ImageFont

random.seed(20260808)
FONT2 = os.path.join("assets", "fonts", "font2.otf")


def periodic_noise(size, cell, blur=0):
    """生成横向/纵向都无缝的 0-255 噪声图（边长 size）"""
    grid = Image.new("L", (cell + 1, cell + 1))
    gd = grid.load()
    for y in range(cell + 1):
        for x in range(cell + 1):
            gd[x, y] = random.randint(0, 255)
    big = grid.resize((size + 1, size + 1), Image.BILINEAR).crop((0, 0, size, size))
    if blur:
        big = big.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(big, dtype=np.float32)


def periodic_blocks(size, cell, categories):
    """按 cell 分块、无缝的类别图，返回 uint8 数组（每像素=类别索引）"""
    grid = Image.new("L", (cell + 1, cell + 1))
    gd = grid.load()
    for y in range(cell + 1):
        for x in range(cell + 1):
            gd[x, y] = random.choice(categories)
    big = grid.resize((size + 1, size + 1), Image.NEAREST).crop((0, 0, size, size))
    return np.asarray(big, dtype=np.uint8)


def gen_floor(path, size=798):
    """末地石地板：黄白块状 + 黑曜石斑块 + 紫色裂隙"""
    w = h = size
    rng = np.random.default_rng(20260808)

    blocks = periodic_blocks(w, 133, [0, 1, 2, 3])
    base = np.zeros((h, w, 3), dtype=np.float32)
    end_stone = np.array([[[222, 228, 180], [206, 214, 162], [236, 242, 200]]], dtype=np.float32)
    obsidian = np.array([[[26, 20, 46]]], dtype=np.float32)
    for i, col in enumerate(end_stone[0]):
        base[blocks == i] = col
    base[blocks == 3] = obsidian[0, 0]

    noise = periodic_noise(w, 57) / 255.0
    fine = periodic_noise(w, 19) / 255.0
    base *= (0.78 + 0.28 * noise)[..., np.newaxis] * (0.94 + 0.08 * fine)[..., np.newaxis]

    crack = periodic_noise(w, 21, blur=1.2) / 255.0
    crack_mask = crack > 0.995
    purple = np.array([[[168, 92, 255]]], dtype=np.float32)
    base[crack_mask] = purple[0, 0] * 0.85 + base[crack_mask] * 0.15

    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    img.save(path)
    print("saved", path, img.size)


def gen_wall(path, w=512, h=128):
    """末地洞壁：纵向末地石柱 + 黑曜石柱 + 紫色晶脉"""
    rng = np.random.default_rng(20260808)

    x = np.arange(w, dtype=np.float32)
    col_shade = 1.0 + 0.10 * np.sin(x / 51.0) + 0.06 * np.sin(x / 17.0 + 1.7)
    col_noise = periodic_noise(w, 32) / 255.0
    col_shade = col_shade * (0.94 + 0.10 * col_noise[:1].ravel())

    base = np.zeros((h, w, 3), dtype=np.float32)
    base[:] = np.array([222, 228, 180], dtype=np.float32)
    base *= col_shade[np.newaxis, :, np.newaxis]

    # 黑曜石柱（周期 128，柱宽约 18）
    pillar = (x % 128) < 18
    base[:, pillar] = np.array([26, 20, 46], dtype=np.float32)

    # 紫色晶脉：几条纵向波动的细线
    for cx in range(30, w, 96):
        for dy in range(h):
            dx = int(round(2.5 * np.sin(dy / 9.0 + cx / 5.0)))
            px = (cx + dx) % w
            base[dy, px] = np.array([168, 92, 255], dtype=np.float32) * 0.9

    speck = periodic_noise(w, 13)[:h] / 255.0
    base *= (0.95 + 0.08 * speck)[..., np.newaxis]

    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    img.save(path)
    print("saved", path, img.size)


def fit_font_width(text, target_w, max_size=140):
    """按目标宽度选择字号（用于标题卡排版，与一面视觉一致）"""
    lo, hi, best = 8, max_size, 8
    while lo <= hi:
        mid = (lo + hi) // 2
        font = ImageFont.truetype(FONT2, mid)
        bb = font.getbbox(text)
        if bb[2] - bb[0] <= target_w:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def draw_text_shadow(draw, text, font, cx, y, shadow_offset=(3, 3)):
    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    x = cx - tw // 2 - bb[0]
    # 阴影
    draw.text((x + shadow_offset[0], y + shadow_offset[1]), text,
              font=font, fill=(8, 6, 24, 255))
    # 主体
    draw.text((x, y), text, font=font, fill=(245, 245, 245, 255))
    return x, y


def gen_title(path, w=576, h=670):
    """关卡标题卡：STAGE 2 / 末地最底层 / Dragon's Nest"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 小标签：STAGE 2（左上，与一面位置一致）
    label_font = ImageFont.truetype(FONT2, fit_font_width("STAGE 2", 140))
    draw.text((36, 196), "STAGE 2", font=label_font, fill=(245, 245, 245, 255))

    # 主标题：末地最底层（白字 + 深色投影，宽度与一面主标题相当）
    main_font = ImageFont.truetype(FONT2, fit_font_width("末地最底层", 340))
    draw_text_shadow(draw, "末地最底层", main_font, w // 2, 256)

    # 副标题：Dragon's Nest
    sub_font = ImageFont.truetype(FONT2, fit_font_width("Dragon's Nest", 394))
    draw_text_shadow(draw, "Dragon's Nest", sub_font, w // 2, 344, shadow_offset=(2, 2))

    img.save(path)
    print("saved", path, img.size)


if __name__ == "__main__":
    from PIL import ImageFilter  # noqa: F401  (periodic_noise 用到的 blur)
    gen_floor(os.path.join("assets", "backgrounds", "stage2", "floor.png"))
    gen_wall(os.path.join("assets", "backgrounds", "stage2", "wall.png"))
    gen_title(os.path.join("assets", "titles", "stage2.png"))
    print("done")
