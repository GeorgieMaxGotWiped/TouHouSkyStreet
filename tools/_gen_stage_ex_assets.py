# -*- coding: utf-8 -*-
# 生成 Ex 面（裂隙 ~ The Rift）专属素材：裂隙地板 / 洞壁 / 关卡标题卡 / 五种裂隙生物。
# 运行：python tools/_gen_stage_ex_assets.py
#
# 美术方向：紫黑虚空里撕开的一道口子。地板是漂浮的暗紫石板、缝里透出紫光；洞壁是层叠
# 岩壁，竖直能量脉自下而上渐亮；小怪都是「从裂隙里爬出来的东西」——紫黑躯体配高饱和
# 发光器官，在暗背景上一眼能看清。Boss 立绘用的是 Hypixel SkyBlock Wiki 的 NPC 全身像，
# 不放这里生成（白底图先离线抠成透明 PNG 再放进 assets/sprites/bosses/new）。
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

os.makedirs(os.path.join("assets", "backgrounds", "stage_ex"), exist_ok=True)
os.makedirs(os.path.join("assets", "titles"), exist_ok=True)
os.makedirs(os.path.join("assets", "sprites", "enemies", "stage_ex"), exist_ok=True)

random.seed(20260916)
FONT2 = os.path.join("assets", "fonts", "font2.otf")

VOID_DARK = np.array([18, 12, 30], dtype=np.float32)
VOID_MID = np.array([44, 28, 70], dtype=np.float32)
RIFT_GLOW = np.array([168, 92, 246], dtype=np.float32)
RIFT_CORE = np.array([236, 200, 255], dtype=np.float32)


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


def save(img, path):
    img.save(path)
    print("saved", path, img.size)


# ------------------------- 背景贴图（可平铺） -------------------------

def gen_rift_floor(path, size=798):
    """裂隙地板：紫黑虚空石板 + 缝里透出的紫光 + 稀疏星点"""
    w = h = size
    rng = np.random.default_rng(20260916)
    blocks = periodic_blocks(w, 133, [0, 1, 2, 3])
    base = np.zeros((h, w, 3), dtype=np.float32)
    for i, col in enumerate((VOID_MID * 0.62, VOID_MID * 0.82, VOID_DARK, VOID_MID * 1.06)):
        base[blocks == i] = col
    mortar = periodic_noise(w, 11) / 255.0
    seam = periodic_noise(w, 133, blur=0.6) / 255.0
    seam_mask = (seam > 0.62) | (mortar > 0.965)
    base[seam_mask] *= 0.42
    macro = periodic_noise(w, 57) / 255.0
    fine = periodic_noise(w, 41) / 255.0
    base *= (0.84 + 0.26 * macro)[..., np.newaxis] * (0.95 + 0.06 * fine)[..., np.newaxis]
    # 发光裂隙：宽幅紫辉打底，正中再压一条近白亮线
    crack = periodic_noise(w, 23, blur=1.0) / 255.0
    halo = np.clip((crack - 0.92) / 0.08, 0.0, 1.0) ** 1.5
    base += halo[..., np.newaxis] * RIFT_GLOW * 0.62
    base[crack > 0.994] = RIFT_CORE * 0.92
    # 虚空反光：极少量的亮点
    base[rng.random((h, w)) > 0.9996] = np.array([214, 206, 255], dtype=np.float32)
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    save(img.filter(ImageFilter.GaussianBlur(0.3)), path)


def gen_rift_wall(path, w=512, h=128):
    """裂隙洞壁：紫黑岩层 + 自下而上的能量脉 + 贴壁悬空的碎块"""
    x = np.arange(w, dtype=np.float32)
    col_shade = 1.0 + 0.11 * np.sin(x / 49.0) + 0.06 * np.sin(x / 16.0 + 1.7)
    col_shade = col_shade * (0.93 + 0.12 * (periodic_noise(w, 32)[:1].ravel() / 255.0))
    base = np.zeros((h, w, 3), dtype=np.float32)
    base[:] = VOID_MID * 0.72
    row_shade = np.where((np.arange(h) % 28) < 3, 0.55, 1.0)[:, None]
    col_seam = np.where((np.arange(w) % 68) < 3, 0.62, 1.0)[None, :]
    base *= (row_shade * col_seam)[..., np.newaxis]
    base *= col_shade[np.newaxis, :, np.newaxis]
    for cx in range(18, w, 83):
        for dy in range(h):
            dx = int(round(3.2 * math.sin(dy / 10.0 + cx / 6.0)))
            px = (cx + dx) % w
            fade = 0.30 + 0.70 * (1.0 - dy / float(h))
            base[dy, px] = RIFT_GLOW * (0.45 + 0.55 * fade)
    speck = periodic_noise(w, 13)[:h] / 255.0
    base *= (0.94 + 0.09 * speck)[..., np.newaxis]
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    draw = ImageDraw.Draw(img, "RGBA")
    for cx in range(48, w, 96):
        draw.polygon([(cx, 24), (cx + 14, 38), (cx + 7, 60), (cx - 8, 54), (cx - 12, 34)],
                     fill=(58, 40, 90, 215), outline=(152, 100, 236, 205))
        draw.polygon([(cx + 32, 76), (cx + 42, 88), (cx + 35, 106), (cx + 24, 96)],
                     fill=(42, 30, 66, 190), outline=(122, 76, 204, 175))
        draw.ellipse((cx + 4, 40, cx + 10, 46), fill=(232, 190, 255, 220))
    save(img, path)


# ------------------------- 关卡标题卡 -------------------------

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


def text_shadow(draw, text, font, cx, y, shadow=(3, 3), fill=(242, 246, 250, 255)):
    bb = draw.textbbox((0, 0), text, font=font)
    x = cx - (bb[2] - bb[0]) // 2 - bb[0]
    draw.text((x + shadow[0], y + shadow[1]), text, font=font, fill=(6, 4, 12, 255))
    draw.text((x, y), text, font=font, fill=fill)


def rift_polygon(cx, top, bottom, scale=1.0, seed=20260916, steps=16):
    """裂口轮廓：上下收口、中间最宽的一道竖裂（左右分别抖动，像被撕开的口子）"""
    rng = random.Random(seed)
    left, right = [], []
    for i in range(steps + 1):
        t = i / steps
        y = top + (bottom - top) * t
        half = (10.0 + 30.0 * math.sin(math.pi * t) ** 0.75) * scale
        left.append((cx - half - rng.uniform(0, 7), y))
        right.append((cx + half + rng.uniform(0, 7), y))
    return left + right[::-1]


def gen_title(path, w=576, h=670):
    """关卡标题卡：EXTRA STAGE / 裂隙 / The Rift"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    label = ImageFont.truetype(FONT2, fit_font_width("EXTRA STAGE", 176))
    draw.text((36, 146), "EXTRA STAGE", font=label, fill=(244, 228, 255, 255))
    text_shadow(draw, "裂隙", ImageFont.truetype(FONT2, fit_font_width("裂隙", 240)),
                w // 2, 202, fill=(240, 220, 255, 255))
    text_shadow(draw, "The Rift", ImageFont.truetype(FONT2, fit_font_width("The Rift", 430)),
                w // 2, 326)
    text_shadow(draw, "通向多元宇宙的裂缝",
                ImageFont.truetype(FONT2, fit_font_width("通向多元宇宙的裂缝", 330)),
                w // 2, 412, shadow=(2, 2))
    # 装饰：画面下方一道撕开的裂隙，两侧透出紫光，周围浮着碎块
    cx, top, bottom = w // 2, 476, 650
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(glow).polygon(rift_polygon(cx, top, bottom, 1.25),
                                 fill=(150, 78, 244, 180))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(16)))
    draw.polygon(rift_polygon(cx, top, bottom, 1.0), fill=(126, 62, 214, 215))
    draw.polygon(rift_polygon(cx, top + 12, bottom - 14, 0.42), fill=(238, 210, 255, 235))
    rng = random.Random(778)
    for _ in range(14):
        sx = cx + rng.choice((-1, 1)) * rng.randint(70, 250)
        sy = rng.randint(top - 30, bottom - 10)
        r = rng.randint(3, 9)
        shard = Image.new("RGBA", (r * 4, r * 4), (0, 0, 0, 0))
        ImageDraw.Draw(shard).polygon(
            [(r * 2, 0), (r * 4, r * 2), (r * 2, r * 4), (0, r * 2)],
            fill=(150, 96, 236, 200))
        img.alpha_composite(shard.filter(ImageFilter.GaussianBlur(1.2)), (sx - r * 2, sy - r * 2))
    save(img, path)


# ------------------------- 小怪贴图（透明底） -------------------------

def gen_vermin_sprite(path, w=64, h=52):
    """裂隙虫：贴地爬行的暗紫甲虫，一对复眼品红发光"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2 + 4
    for dy in (-7, 0, 7):
        y = cy + dy
        draw.line((cx - 12, y, cx - 26, y + 9), fill=(44, 26, 70, 255), width=3)
        draw.line((cx + 12, y, cx + 26, y + 9), fill=(44, 26, 70, 255), width=3)
    draw.ellipse((cx - 19, cy - 13, cx + 19, cy + 15), fill=(52, 32, 82, 255))
    draw.ellipse((cx - 14, cy - 9, cx + 14, cy + 10), fill=(74, 44, 118, 255))
    for i in range(3):
        y = cy - 4 + i * 7
        draw.arc((cx - 15, y - 7, cx + 15, y + 7), 195, 345, fill=(34, 20, 56, 255), width=2)
    draw.ellipse((cx - 12, cy - 24, cx + 12, cy - 3), fill=(62, 38, 96, 255))
    draw.ellipse((cx - 9, cy - 21, cx - 2, cy - 11), fill=(255, 96, 210, 255))
    draw.ellipse((cx + 2, cy - 21, cx + 9, cy - 11), fill=(255, 96, 210, 255))
    draw.line((cx - 7, cy - 5, cx - 13, cy + 3), fill=(36, 22, 60, 255), width=2)
    draw.line((cx + 7, cy - 5, cx + 13, cy + 3), fill=(36, 22, 60, 255), width=2)
    save(img, path)


def gen_globowl_sprite(path, w=72, h=64):
    """Globowl：球形圆枭，双翼张开、巨眼青辉"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2 + 3
    draw.polygon([(cx - 18, cy - 6), (cx - 34, cy - 16), (cx - 30, cy + 8), (cx - 16, cy + 8)],
                 fill=(40, 62, 76, 255))
    draw.polygon([(cx + 18, cy - 6), (cx + 34, cy - 16), (cx + 30, cy + 8), (cx + 16, cy + 8)],
                 fill=(40, 62, 76, 255))
    draw.ellipse((cx - 20, cy - 22, cx + 20, cy + 20), fill=(56, 84, 98, 255))
    draw.ellipse((cx - 15, cy - 17, cx + 15, cy + 15), fill=(82, 118, 132, 255))
    draw.ellipse((cx - 13, cy - 12, cx - 3, cy + 2), fill=(18, 26, 34, 255))
    draw.ellipse((cx + 3, cy - 12, cx + 13, cy + 2), fill=(18, 26, 34, 255))
    draw.ellipse((cx - 10, cy - 9, cx - 5, cy - 2), fill=(140, 245, 225, 255))
    draw.ellipse((cx + 5, cy - 9, cx + 10, cy - 2), fill=(140, 245, 225, 255))
    draw.polygon([(cx - 4, cy + 4), (cx + 4, cy + 4), (cx, cy + 12)], fill=(226, 176, 96, 255))
    for dx in (-8, 8):
        draw.line((cx + dx, cy + 18, cx + dx - 3, cy + 25), fill=(212, 168, 96, 255), width=3)
    save(img, path)


def gen_blobbercyst_sprite(path, w=76, h=68):
    """Blobbercyst：半透明泡囊，体内悬着几颗更亮的囊肿"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2 + 6
    draw.ellipse((cx - 26, cy - 20, cx + 26, cy + 22), fill=(88, 48, 138, 205))
    draw.ellipse((cx - 20, cy - 15, cx + 20, cy + 17), fill=(126, 70, 186, 225))
    draw.polygon([(cx - 18, cy + 14), (cx + 18, cy + 14), (cx + 8, cy + 26), (cx - 6, cy + 26)],
                 fill=(96, 54, 150, 215))
    for dx, dy, r in ((-9, -6, 6), (6, 2, 5), (-2, 7, 4), (11, -9, 3)):
        draw.ellipse((cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r), fill=(206, 150, 255, 225))
        draw.ellipse((cx + dx - r + 1, cy + dy - r + 1, cx + dx + r - 3, cy + dy + r - 3),
                     fill=(238, 206, 255, 235))
    draw.ellipse((cx - 10, cy - 12, cx - 5, cy - 5), fill=(28, 16, 44, 235))
    draw.ellipse((cx + 2, cy - 12, cx + 7, cy - 5), fill=(28, 16, 44, 235))
    save(img, path)


def gen_vampire_sprite(path, w=96, h=132):
    """裂隙吸血鬼：蝠翼 + 立领斗篷 + 苍白面孔与红瞳"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = w // 2
    for side in (-1, 1):
        draw.polygon([(cx + side * 12, 44), (cx + side * 46, 26), (cx + side * 44, 62),
                      (cx + side * 28, 74), (cx + side * 14, 66)], fill=(48, 26, 74, 255))
        draw.line((cx + side * 14, 46, cx + side * 44, 34), fill=(96, 52, 142, 255), width=2)
    draw.polygon([(cx - 22, 40), (cx + 22, 40), (cx + 32, 126), (cx - 32, 126)],
                 fill=(38, 20, 60, 255))
    draw.polygon([(cx - 14, 44), (cx + 14, 44), (cx + 20, 124), (cx - 20, 124)],
                 fill=(56, 30, 86, 255))
    draw.polygon([(cx - 24, 40), (cx - 30, 16), (cx - 8, 34)], fill=(30, 16, 48, 255))
    draw.polygon([(cx + 24, 40), (cx + 30, 16), (cx + 8, 34)], fill=(30, 16, 48, 255))
    draw.ellipse((cx - 15, 12, cx + 15, 44), fill=(226, 214, 232, 255))
    draw.polygon([(cx - 15, 22), (cx - 11, 6), (cx - 2, 16), (cx + 2, 4), (cx + 12, 14),
                  (cx + 15, 22)], fill=(28, 16, 44, 255))
    draw.ellipse((cx - 10, 26, cx - 3, 34), fill=(238, 62, 82, 255))
    draw.ellipse((cx + 3, 26, cx + 10, 34), fill=(238, 62, 82, 255))
    draw.polygon([(cx - 5, 38), (cx - 2, 38), (cx - 3, 43)], fill=(255, 255, 255, 245))
    draw.polygon([(cx + 2, 38), (cx + 5, 38), (cx + 3, 43)], fill=(255, 255, 255, 245))
    draw.ellipse((cx - 5, 56, cx + 5, 66), fill=(196, 40, 74, 255))
    save(img, path)


def gen_crux_sprite(path, w=92, h=140):
    """Crux 刻印者：悬浮的刻印构造体——暗袍躯干 + 头顶法阵 + 十字刻印"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = w // 2
    draw.ellipse((cx - 40, 8, cx + 40, 52), outline=(128, 82, 226, 200), width=3)
    draw.ellipse((cx - 30, 15, cx + 30, 45), outline=(186, 130, 255, 160), width=2)
    draw.line((cx, 12, cx, 50), fill=(226, 188, 255, 235), width=4)
    draw.line((cx - 18, 26, cx + 18, 26), fill=(226, 188, 255, 235), width=4)
    draw.ellipse((cx - 36, 56, cx - 12, 78), fill=(58, 36, 92, 255))
    draw.ellipse((cx + 12, 56, cx + 36, 78), fill=(58, 36, 92, 255))
    draw.polygon([(cx - 20, 60), (cx + 20, 60), (cx + 32, 136), (cx - 32, 136)],
                 fill=(30, 18, 50, 255))
    draw.polygon([(cx - 12, 64), (cx + 12, 64), (cx + 18, 134), (cx - 18, 134)],
                 fill=(48, 30, 78, 255))
    draw.ellipse((cx - 15, 78, cx + 15, 108), fill=(16, 9, 28, 255))
    draw.ellipse((cx - 9, 86, cx - 3, 96), fill=(190, 140, 255, 255))
    draw.ellipse((cx + 3, 86, cx + 9, 96), fill=(190, 140, 255, 255))
    save(img, path)


def main():
    gen_rift_floor(os.path.join("assets", "backgrounds", "stage_ex", "floor.png"))
    gen_rift_wall(os.path.join("assets", "backgrounds", "stage_ex", "wall.png"))
    gen_title(os.path.join("assets", "titles", "stage_ex.png"))
    base = os.path.join("assets", "sprites", "enemies", "stage_ex")
    gen_vermin_sprite(os.path.join(base, "vermin.png"))
    gen_globowl_sprite(os.path.join(base, "globowl.png"))
    gen_blobbercyst_sprite(os.path.join(base, "blobbercyst.png"))
    gen_vampire_sprite(os.path.join(base, "vampire.png"))
    gen_crux_sprite(os.path.join(base, "crux.png"))


if __name__ == "__main__":
    main()
