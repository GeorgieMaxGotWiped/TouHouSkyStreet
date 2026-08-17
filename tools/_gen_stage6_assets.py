# -*- coding: utf-8 -*-
# 生成六面专属素材：凋零要塞地板 / 墙壁 / 关卡标题卡 / The Wither King 立绘。
# 运行：python tools/_gen_stage6_assets.py
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

os.makedirs(os.path.join("assets", "backgrounds", "stage6"), exist_ok=True)
os.makedirs(os.path.join("assets", "titles"), exist_ok=True)
os.makedirs(os.path.join("assets", "sprites", "bosses"), exist_ok=True)

random.seed(20260815)
FONT2 = os.path.join("assets", "fonts", "font2.otf")


def periodic_noise(size, cell, blur=0):
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
    grid = Image.new("L", (cell + 1, cell + 1))
    gd = grid.load()
    for y in range(cell + 1):
        for x in range(cell + 1):
            gd[x, y] = random.choice(categories)
    big = grid.resize((size + 1, size + 1), Image.NEAREST).crop((0, 0, size, size))
    return np.asarray(big, dtype=np.uint8)


def gen_fortress_floor(path, size=798):
    """凋零要塞地板：暗紫黑石砖 + 黑曜石脉 + 凋零骷髅纹路 + 黑能量裂隙"""
    w = h = size
    rng = np.random.default_rng(20260815)
    blocks = periodic_blocks(w, 133, [0, 1, 2, 3])
    base = np.zeros((h, w, 3), dtype=np.float32)
    stones = np.array([[[44, 34, 52], [52, 40, 62], [36, 28, 44], [60, 46, 70]]], dtype=np.float32)
    for i, col in enumerate(stones[0]):
        base[blocks == i] = col
    mortar = periodic_noise(w, 11) / 255.0
    seam = periodic_noise(w, 133, blur=0.6) / 255.0
    seam_mask = (seam > 0.62) | (mortar > 0.965)
    base[seam_mask] = base[seam_mask] * 0.4
    noise = periodic_noise(w, 57) / 255.0
    fine = periodic_noise(w, 19) / 255.0
    base *= (0.80 + 0.30 * noise)[..., np.newaxis] * (0.94 + 0.08 * fine)[..., np.newaxis]
    # 黑曜石深色斑
    obs = periodic_noise(w, 37, blur=1.4) / 255.0
    obs_mask = obs > 0.90
    dark = np.array([[[16, 12, 24]]], dtype=np.float32)
    base[obs_mask] = base[obs_mask] * 0.35 + dark[0, 0] * 0.65
    # 黑能量裂隙（暗紫辉光）
    crack = periodic_noise(w, 21, blur=1.1) / 255.0
    crack_mask = crack > 0.996
    vein = np.array([[[120, 40, 200]]], dtype=np.float32)
    base[crack_mask] = vein[0, 0] * 0.8 + base[crack_mask] * 0.2
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    img.save(path)
    print("saved", path, img.size)


def gen_fortress_wall(path, w=512, h=128):
    """凋零要塞墙壁：暗紫砖墙 + 每 128px 一座凋零骷髅浮雕 + 黑能量脉"""
    rng = np.random.default_rng(20260815)
    x = np.arange(w, dtype=np.float32)
    col_shade = 1.0 + 0.10 * np.sin(x / 47.0) + 0.06 * np.sin(x / 15.0 + 1.7)
    col_noise = periodic_noise(w, 32) / 255.0
    col_shade = col_shade * (0.94 + 0.10 * col_noise[:1].ravel())
    base = np.zeros((h, w, 3), dtype=np.float32)
    base[:] = np.array([56, 42, 68], dtype=np.float32)
    base *= col_shade[np.newaxis, :, np.newaxis]
    rows = (np.arange(h, dtype=np.float32)[:, None] % 32) < 3
    cols = (np.arange(w, dtype=np.float32)[None, :] % 64) < 3
    mortar = rows | cols
    base[mortar] = np.array([24, 18, 32], dtype=np.float32)
    # 黑能量脉（暗紫）
    for cx in range(20, w, 97):
        for dy in range(h):
            dx = int(round(2.5 * np.sin(dy / 9.0 + cx / 5.0)))
            px = (cx + dx) % w
            base[dy, px] = np.array([130, 44, 210], dtype=np.float32) * 0.85
    speck = periodic_noise(w, 13)[:h] / 255.0
    base *= (0.95 + 0.08 * speck)[..., np.newaxis]
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    draw = ImageDraw.Draw(img, "RGBA")
    # 凋零骷髅浮雕：中心 + 两个小侧颅，半透明浅灰
    for cx in range(64, w, 128):
        draw.ellipse((cx - 16, 52, cx + 16, 96), fill=(150, 138, 176, 90))
        draw.ellipse((cx - 10, 58, cx - 2, 76), fill=(24, 16, 34, 200))
        draw.ellipse((cx + 2, 58, cx + 10, 76), fill=(24, 16, 34, 200))
        draw.rectangle((cx - 7, 84, cx + 7, 90), fill=(24, 16, 34, 200))
        for dx in (-30, 30):
            draw.ellipse((cx + dx - 9, 62, cx + dx + 9, 86), fill=(118, 106, 142, 60))
    img.save(path)
    print("saved", path, img.size)


def fit_font_width(text, target_w, max_size=150):
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


def text_shadow(draw, text, font, cx, y, shadow=(2, 2), fill=(242, 246, 250, 255)):
    bb = draw.textbbox((0, 0), text, font=font)
    x = cx - (bb[2] - bb[0]) // 2 - bb[0]
    draw.text((x + shadow[0], y + shadow[1]), text, font=font, fill=(5, 4, 10, 255))
    draw.text((x, y), text, font=font, fill=fill)


def gen_title(path):
    w, h = 576, 670
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    label = ImageFont.truetype(FONT2, fit_font_width("STAGE 6", 150))
    draw.text((36, 150), "STAGE 6", font=label, fill=(245, 245, 245, 255))
    main = ImageFont.truetype(FONT2, fit_font_width("最终进军", 330))
    text_shadow(draw, "最终进军", main, w // 2, 210)
    sub = ImageFont.truetype(FONT2, fit_font_width("Final Approach", 420))
    text_shadow(draw, "Final Approach", sub, w // 2, 300, shadow=(2, 2))
    sub2 = ImageFont.truetype(FONT2, fit_font_width("通往凋零之王的王座", 300))
    text_shadow(draw, "通往凋零之王的王座", sub2, w // 2, 352, shadow=(2, 2))
    # 王座意象：黑曜石王座 + 凋零三头
    tx, ty = w // 2, 500
    draw.polygon([(tx - 90, 620), (tx - 70, 470), (tx + 70, 470), (tx + 90, 620)],
                 fill=(14, 10, 22, 235))
    draw.polygon([(tx - 78, 500), (tx - 52, 470), (tx - 30, 470), (tx - 30, 500)],
                 fill=(24, 18, 38, 255))
    draw.polygon([(tx + 30, 500), (tx + 30, 470), (tx + 52, 470), (tx + 78, 500)],
                 fill=(24, 18, 38, 255))
    draw.rectangle((tx - 30, 470, tx + 30, 620), fill=(18, 13, 30, 255))
    for r, col, a in ((64, (70, 34, 110), 45), (48, (130, 60, 170), 70), (34, (235, 90, 150), 90)):
        oval = Image.new("RGBA", (r * 2 + 4, r * 2 + 4), (0, 0, 0, 0))
        od = ImageDraw.Draw(oval)
        od.ellipse((2, 2, r * 2 + 2, r * 2 + 2), fill=col + (a,))
        img.alpha_composite(oval, (tx - r - 2, ty - r - 90))
    for dx in (-60, 0, 60):
        draw.ellipse((tx + dx - 18, ty - 108, tx + dx + 18, ty - 72), fill=(12, 9, 18, 240))
        draw.ellipse((tx + dx - 4, ty - 98, tx + dx + 4, ty - 84), fill=(255, 90, 150, 255))
    img.save(path)
    print("saved", path)


def draw_wither_king_core(draw, cx, cy, main, glow, eye):
    # 外圈黑紫柔光
    for r, a in ((110, 22), (90, 34), (70, 50)):
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=glow + (a,))
    # 巨大身躯（倒三角披风感）
    draw.polygon([(cx - 96, cy + 70), (cx - 60, cy - 40), (cx + 60, cy - 40), (cx + 96, cy + 70)],
                 fill=main + (255,))
    draw.polygon([(cx - 78, cy + 52), (cx - 48, cy - 30), (cx + 48, cy - 30), (cx + 78, cy + 52)],
                 fill=tuple(min(255, c + 20) for c in main) + (255,))
    # 中心主头
    draw.ellipse((cx - 46, cy - 128, cx + 46, cy - 36), fill=main + (255,))
    draw.ellipse((cx - 36, cy - 118, cx + 36, cy - 46), fill=tuple(min(255, c + 26) for c in main) + (255,))
    # 侧头
    for side in (-1, 1):
        sx = cx + side * 74
        draw.ellipse((sx - 34, cy - 96, sx + 34, cy - 28), fill=main + (255,))
        draw.ellipse((sx - 27, cy - 88, sx + 27, cy - 36), fill=tuple(min(255, c + 20) for c in main) + (255,))
    # 王冠
    draw.polygon([(cx - 34, cy - 128), (cx - 40, cy - 156), (cx - 20, cy - 138),
                  (cx, cy - 164), (cx + 20, cy - 138), (cx + 40, cy - 156), (cx + 34, cy - 128)],
                 fill=(26, 20, 40, 255), outline=(150, 120, 220, 255))
    # 眼睛（主头 + 侧头，红紫）
    for hx, hy, s in ((cx, cy - 84, 1.0), (cx - 74, cy - 62, 0.72), (cx + 74, cy - 62, 0.72)):
        r = int(9 * s)
        draw.ellipse((hx - 14 * s, hy - 10 * s, hx + 14 * s, hy + 10 * s), fill=eye + (255,))
        draw.ellipse((hx - 4 * s, hy - 4 * s, hx + 4 * s, hy + 2 * s), fill=(255, 235, 245, 255))
    # 嘴部裂纹
    draw.line((cx - 24, cy - 46, cx - 6, cy - 38), fill=(10, 6, 14, 240), width=3)
    draw.line((cx + 6, cy - 38, cx + 24, cy - 46), fill=(10, 6, 14, 240), width=3)


def gen_wither_king(path):
    w, h = 320, 320
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = w // 2, 160
    draw_wither_king_core(draw, cx, cy, (34, 24, 48), (110, 40, 170), (255, 70, 130))
    img.save(path)
    print("saved", path)


def main():
    gen_fortress_floor(os.path.join("assets", "backgrounds", "stage6", "fortress_floor.png"))
    gen_fortress_wall(os.path.join("assets", "backgrounds", "stage6", "fortress_wall.png"))
    gen_title(os.path.join("assets", "titles", "stage6.png"))
    gen_wither_king(os.path.join("assets", "sprites", "bosses", "wither_king.png"))


if __name__ == "__main__":
    main()
