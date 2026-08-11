# -*- coding: utf-8 -*-
# 生成三面占位素材：地下墓穴地面 / 墙壁 / 关卡标题卡 / Boss与小怪贴图 / 符卡背景图标
# 运行：python tools/_gen_stage3_assets.py
import os
import math
import random

os.makedirs(os.path.join("assets", "backgrounds", "stage3"), exist_ok=True)
os.makedirs(os.path.join("assets", "titles"), exist_ok=True)
os.makedirs(os.path.join("assets", "sprites", "bosses"), exist_ok=True)
os.makedirs(os.path.join("assets", "sprites", "enemies", "stage3"), exist_ok=True)

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

random.seed(20260810)
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
    """地下墓穴石地板：暗青石板砖 + 苔藓 + 裂隙青辉 + 枯骨斑"""
    w = h = size
    rng = np.random.default_rng(20260810)

    blocks = periodic_blocks(w, 133, [0, 1, 2, 3])
    base = np.zeros((h, w, 3), dtype=np.float32)
    stones = np.array([[[58, 64, 74], [66, 72, 84], [74, 82, 94], [48, 54, 62]]], dtype=np.float32)
    for i, col in enumerate(stones[0]):
        base[blocks == i] = col

    # 砖缝（暗色）
    mortar = periodic_noise(w, 11) / 255.0
    seam = periodic_noise(w, 133, blur=0.6) / 255.0
    seam_mask = (seam > 0.62) | (mortar > 0.965)
    base[seam_mask] = base[seam_mask] * 0.45

    noise = periodic_noise(w, 57) / 255.0
    fine = periodic_noise(w, 19) / 255.0
    base *= (0.80 + 0.30 * noise)[..., np.newaxis] * (0.94 + 0.08 * fine)[..., np.newaxis]

    # 苔藓绿斑
    moss = periodic_noise(w, 31, blur=1.2) / 255.0
    moss_mask = moss > 0.93
    green = np.array([[[46, 92, 66]]], dtype=np.float32)
    base[moss_mask] = base[moss_mask] * 0.5 + green[0, 0] * 0.5

    # 青辉裂隙（紫青）
    crack = periodic_noise(w, 21, blur=1.1) / 255.0
    crack_mask = crack > 0.996
    teal = np.array([[[92, 210, 210]]], dtype=np.float32)
    base[crack_mask] = teal[0, 0] * 0.85 + base[crack_mask] * 0.15

    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    img.save(path)
    print("saved", path, img.size)


def gen_wall(path, w=512, h=128):
    """地下墓穴墙壁：暗砖 + 壁龛枯骨 + 青辉脉"""
    rng = np.random.default_rng(20260810)

    x = np.arange(w, dtype=np.float32)
    col_shade = 1.0 + 0.10 * np.sin(x / 47.0) + 0.06 * np.sin(x / 15.0 + 1.7)
    col_noise = periodic_noise(w, 32) / 255.0
    col_shade = col_shade * (0.94 + 0.10 * col_noise[:1].ravel())

    base = np.zeros((h, w, 3), dtype=np.float32)
    base[:] = np.array([66, 72, 84], dtype=np.float32)
    base *= col_shade[np.newaxis, :, np.newaxis]

    # 砖缝
    rows = (np.arange(h, dtype=np.float32)[:, None] % 32) < 3
    cols = (np.arange(w, dtype=np.float32)[None, :] % 64) < 3
    mortar = rows | cols
    base[mortar] = np.array([30, 34, 42], dtype=np.float32)

    # 青辉脉
    for cx in range(20, w, 97):
        for dy in range(h):
            dx = int(round(2.5 * np.sin(dy / 9.0 + cx / 5.0)))
            px = (cx + dx) % w
            base[dy, px] = np.array([92, 210, 210], dtype=np.float32) * 0.9

    speck = periodic_noise(w, 13)[:h] / 255.0
    base *= (0.95 + 0.08 * speck)[..., np.newaxis]

    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    img.save(path)
    print("saved", path, img.size)


def fit_font_width(text, target_w, max_size=140):
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
    draw.text((x + shadow_offset[0], y + shadow_offset[1]), text,
              font=font, fill=(6, 8, 14, 255))
    draw.text((x, y), text, font=font, fill=(242, 246, 250, 255))
    return x, y


def gen_title(path, w=576, h=670):
    """关卡标题卡：STAGE 3 / 地下墓穴 / The Catacombs Floor 1"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 小标签：STAGE 3（左上）
    label_font = ImageFont.truetype(FONT2, fit_font_width("STAGE 3", 140))
    draw.text((36, 196), "STAGE 3", font=label_font, fill=(245, 245, 245, 255))

    # 主标题：地下墓穴
    main_font = ImageFont.truetype(FONT2, fit_font_width("地下墓穴", 340))
    draw_text_shadow(draw, "地下墓穴", main_font, w // 2, 256)

    # 副标题：The Catacombs Floor 1
    sub_font = ImageFont.truetype(FONT2, fit_font_width("The Catacombs Floor 1", 394))
    draw_text_shadow(draw, "The Catacombs Floor 1", sub_font, w // 2, 344, shadow_offset=(2, 2))

    # 底部装饰：一只微光之眼（道中Boss意象）
    ex, ey = w // 2, 470
    for r, col, a in ((40, (90, 220, 220), 60), (28, (150, 235, 235), 90), (18, (235, 90, 110), 150)):
        oval = Image.new("RGBA", (r * 2 + 6, r * 2 + 6), (0, 0, 0, 0))
        od = ImageDraw.Draw(oval)
        od.ellipse((3, 3, r * 2 + 3, r * 2 + 3), fill=col + (a,))
        img.alpha_composite(oval, (ex - r - 3, ey - r - 3))
    draw.ellipse((ex - 7, ey - 7, ex + 7, ey + 7), fill=(20, 24, 32, 220))

    img.save(path)
    print("saved", path, img.size)


# ------------------------- Boss 贴图（透明底） -------------------------

def gen_watcher_sprite(path, w=260, h=200):
    """The Watcher：悬浮之眼——暗色眼睑 + 青辉外环 + 猩红虹膜 + 竖瞳"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2

    # 外圈青辉（多层柔光）
    for r, a in ((86, 26), (72, 40), (60, 60)):
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(70, 200, 210, a))
    # 眼睑（暗紫灰）
    draw.ellipse((cx - 88, cy - 62, cx + 88, cy + 62), fill=(34, 38, 52, 255))
    # 眼白（灰蓝）
    draw.ellipse((cx - 72, cy - 52, cx + 72, cy + 52), fill=(104, 122, 140, 255))
    # 猩红虹膜
    draw.ellipse((cx - 44, cy - 44, cx + 44, cy + 44), fill=(188, 46, 66, 255))
    draw.ellipse((cx - 32, cy - 32, cx + 32, cy + 32), fill=(232, 84, 96, 255))
    # 竖瞳
    draw.ellipse((cx - 9, cy - 40, cx + 9, cy + 40), fill=(12, 10, 14, 255))
    # 高光
    draw.ellipse((cx - 22, cy - 20, cx - 8, cy - 6), fill=(255, 220, 220, 230))
    # 眼睑上下睫毛
    for k, (y0, y1) in enumerate(((-62, -52), (52, 62))):
        for i in range(5):
            x0 = cx - 60 + i * 30
            x1 = x0 + 26
            draw.line((x0, cy + y0, x1, cy + y0 - (16 if y0 < 0 else -16)),
                      fill=(20, 22, 32, 255), width=7)

    img.save(path)
    print("saved", path, img.size)


def gen_bonzo_sprite(path, w=240, h=250):
    """Bonzo：小丑魔术师——白头套 + 红鼻 + 咧嘴笑 + 紫发 + 手持气球"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = w // 2, 118

    # 气球（右上，两红一青）
    for bx, by, r, col in ((cx + 66, 34, 26, (222, 60, 90)),
                           (cx + 96, 52, 22, (80, 200, 220)),
                           (cx + 40, 22, 20, (230, 190, 70))):
        draw.ellipse((bx - r, by - r, bx + r, by + r), fill=col + (255,))
        draw.line((bx, by + r, bx + 6, by + r + 18), fill=(150, 160, 175, 255), width=3)
        draw.ellipse((bx - r * 0.5, by - r * 0.5, bx - r * 0.15, by - r * 0.15),
                     fill=(255, 240, 240, 200))

    # 身体（条纹衣肩）
    draw.ellipse((cx - 62, cy + 62, cx + 62, cy + 118), fill=(210, 60, 80, 255))
    for i in range(4):
        y0 = cy + 62 + i * 14
        draw.line((cx - 58, y0, cx + 58, y0), fill=(245, 240, 230, 255), width=5)

    # 头（白脸）
    draw.ellipse((cx - 62, cy - 64, cx + 62, cy + 64), fill=(246, 240, 232, 255))
    # 红鼻子
    draw.ellipse((cx - 13, cy + 6, cx + 13, cy + 32), fill=(220, 50, 60, 255))
    # 咧嘴笑
    draw.arc((cx - 42, cy + 6, cx + 42, cy + 58), 20, 160, fill=(40, 34, 46, 255), width=6)
    # 眼睛
    draw.ellipse((cx - 30, cy - 34, cx - 8, cy - 6), fill=(40, 34, 46, 255))
    draw.ellipse((cx + 8, cy - 34, cx + 30, cy - 6), fill=(40, 34, 46, 255))
    draw.ellipse((cx - 26, cy - 30, cx - 20, cy - 22), fill=(255, 255, 255, 255))
    draw.ellipse((cx + 12, cy - 30, cx + 18, cy - 22), fill=(255, 255, 255, 255))
    # 紫发（两侧卷毛）
    for side in (-1, 1):
        for i in range(3):
            x0 = cx + side * (58 - i * 8)
            y0 = cy - 40 + i * 18
            draw.arc((x0 - 18, y0 - 18, x0 + 18, y0 + 18), 0 if side < 0 else 180,
                     180 if side < 0 else 360, fill=(150, 60, 190, 255), width=8)
    # 顶部小礼帽
    draw.rectangle((cx - 26, cy - 96, cx + 26, cy - 64), fill=(40, 44, 60, 255))
    draw.rectangle((cx - 44, cy - 66, cx + 44, cy - 56), fill=(40, 44, 60, 255))
    draw.rectangle((cx - 18, cy - 66, cx + 18, cy - 62), fill=(220, 60, 90, 255))

    img.save(path)
    print("saved", path, img.size)


# ------------------------- 小怪贴图（透明底） -------------------------

def gen_undead_sprite(path, w=72, h=84):
    """亡灵僵尸：绿灰皮肤 + 破衣 + 红眼"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = w // 2

    # 手臂前伸
    draw.rounded_rectangle((cx - 44, 34, cx - 14, 48), radius=6, fill=(92, 108, 92, 255))
    draw.rounded_rectangle((cx + 14, 34, cx + 44, 48), radius=6, fill=(92, 108, 92, 255))
    # 身体（破衣）
    draw.polygon([(cx - 22, 34), (cx + 22, 34), (cx + 28, 82), (cx - 28, 82)],
                 fill=(74, 82, 96, 255))
    draw.line((cx - 10, 38, cx - 6, 78), fill=(40, 46, 56, 255), width=4)
    draw.line((cx + 10, 38, cx + 6, 78), fill=(40, 46, 56, 255), width=4)
    # 头
    draw.ellipse((cx - 20, 2, cx + 20, 40), fill=(104, 122, 96, 255))
    # 眼
    draw.ellipse((cx - 12, 14, cx - 4, 24), fill=(222, 40, 46, 255))
    draw.ellipse((cx + 4, 14, cx + 12, 24), fill=(222, 40, 46, 255))
    # 嘴（裂纹）
    draw.line((cx - 10, 30, cx + 10, 34), fill=(30, 36, 30, 255), width=3)

    img.save(path)
    print("saved", path, img.size)


def gen_soul_sprite(path, w=52, h=116):
    """墓穴幽魂：半透明白色魂体 + 青辉 + 波浪底"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = w // 2
    top_y = 8
    body_h = 74
    # 光晕
    draw.ellipse((cx - 24, top_y - 4, cx + 24, top_y + body_h + 20), fill=(120, 210, 220, 40))
    # 魂体
    pts = [(cx - 18, top_y + body_h), (cx - 18, top_y + 26),
           (cx - 12, top_y + 12), (cx, top_y), (cx + 12, top_y + 12),
           (cx + 18, top_y + 26), (cx + 18, top_y + body_h),
           (cx + 10, top_y + body_h - 10), (cx + 4, top_y + body_h),
           (cx - 4, top_y + body_h - 8), (cx - 10, top_y + body_h)]
    draw.polygon(pts, fill=(176, 226, 232, 190))
    # 眼（空洞）
    draw.ellipse((cx - 11, top_y + 26, cx - 1, top_y + 40), fill=(40, 60, 74, 230))
    draw.ellipse((cx + 1, top_y + 26, cx + 11, top_y + 40), fill=(40, 60, 74, 230))

    img.save(path)
    print("saved", path, img.size)


def gen_skeleton_sprite(path, w=60, h=108):
    """骷髅守卫：白骨 + 长剑"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = w // 2
    # 腿骨
    draw.line((cx - 8, 74, cx - 12, 102), fill=(214, 214, 208, 255), width=6)
    draw.line((cx + 8, 74, cx + 12, 102), fill=(214, 214, 208, 255), width=6)
    # 躯干骨架
    for (x0, y0, x1, y1) in ((cx - 14, 34, cx - 16, 74), (cx + 14, 34, cx + 16, 74),
                             (cx - 16, 74, cx + 16, 74)):
        draw.line((x0, y0, x1, y1), fill=(222, 222, 216, 255), width=7)
    # 肋骨
    for i in range(4):
        y = 42 + i * 8
        draw.line((cx - 12, y, cx + 12, y), fill=(222, 222, 216, 255), width=4)
    # 头骨
    draw.ellipse((cx - 14, 2, cx + 14, 32), fill=(226, 226, 220, 255))
    draw.ellipse((cx - 8, 12, cx - 2, 20), fill=(36, 40, 44, 255))
    draw.ellipse((cx + 2, 12, cx + 8, 20), fill=(36, 40, 44, 255))
    draw.line((cx - 5, 24, cx + 5, 26), fill=(36, 40, 44, 255), width=2)
    # 剑（右臂前举）
    draw.line((cx + 16, 30, cx + 34, 6), fill=(226, 230, 236, 255), width=5)
    draw.line((cx + 30, 2, cx + 36, 10), fill=(226, 230, 236, 255), width=4)

    img.save(path)
    print("saved", path, img.size)


# ------------------------- 符卡背景图标（黑底抠图用） -------------------------

def icon_canvas(w, h, color=(6, 8, 12)):
    return Image.new("RGB", (w, h), color)


def gen_caster_sprite(path, w=64, h=92):
    """墓穴唤魂者：兜帽魂体 + 青辉法球"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = w // 2
    # 底部魂尾（青辉）
    draw.polygon([(cx - 18, 76), (cx - 10, 58), (cx + 10, 58), (cx + 18, 76),
                  (cx + 10, 88), (cx - 10, 88)], fill=(70, 180, 170, 210))
    # 兜帽（暗紫青）
    draw.ellipse((cx - 24, 4, cx + 24, 62), fill=(46, 54, 74, 255))
    draw.polygon([(cx - 24, 54), (cx - 20, 84), (cx + 20, 84), (cx + 24, 54)],
                 fill=(46, 54, 74, 255))
    # 兜帽内脸（暗）
    draw.ellipse((cx - 15, 20, cx + 15, 46), fill=(18, 22, 30, 255))
    # 双眼（青辉）
    draw.ellipse((cx - 10, 28, cx - 3, 37), fill=(120, 240, 220, 255))
    draw.ellipse((cx + 3, 28, cx + 10, 37), fill=(120, 240, 220, 255))
    # 胸前法球
    draw.ellipse((cx - 10, 46, cx + 10, 68), fill=(96, 216, 196, 255))
    draw.ellipse((cx - 5, 50, cx + 2, 58), fill=(220, 255, 248, 230))

    img.save(path)
    print("saved", path, img.size)


def gen_icon_eye(path, w=160, h=120):
    img = icon_canvas(w, h)
    d = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2
    for r, a in ((70, 40), (58, 60)):
        d.ellipse((cx - r, cy - r * 0.6, cx + r, cy + r * 0.6), fill=(70, 200, 210, a))
    d.ellipse((cx - 64, cy - 42, cx + 64, cy + 42), fill=(120, 150, 170))
    d.ellipse((cx - 34, cy - 34, cx + 34, cy + 34), fill=(235, 60, 80))
    d.ellipse((cx - 8, cy - 30, cx + 8, cy + 30), fill=(6, 8, 12))
    img.save(path)
    print("saved", path, img.size)


def gen_icon_skull(path, w=120, h=110):
    img = icon_canvas(w, h)
    d = ImageDraw.Draw(img)
    cx = w // 2
    d.ellipse((cx - 44, 6, cx + 44, 84), fill=(232, 232, 226))
    d.rectangle((cx - 24, 72, cx + 24, 98), fill=(232, 232, 226))
    d.ellipse((cx - 24, 24, cx - 4, 48), fill=(8, 10, 12))
    d.ellipse((cx + 4, 24, cx + 24, 48), fill=(8, 10, 12))
    d.polygon([(cx - 16, 56), (cx + 16, 56), (cx + 12, 72), (cx - 12, 72)], fill=(8, 10, 12))
    for dx in (-12, 0, 12):
        d.line((cx + dx, 66, cx + dx, 88), fill=(200, 200, 194), width=5)
    img.save(path)
    print("saved", path, img.size)


def gen_icon_dark_orb(path, w=110, h=110):
    img = icon_canvas(w, h)
    d = ImageDraw.Draw(img)
    cx = cy = w // 2
    for r, a in ((50, 36), (42, 56), (34, 120)):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(150, 60, 190, a))
    d.ellipse((cx - 28, cy - 28, cx + 28, cy + 28), fill=(96, 28, 130))
    d.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), fill=(190, 110, 230))
    d.ellipse((cx - 18, cy - 18, cx - 10, cy - 10), fill=(235, 190, 255))
    img.save(path)
    print("saved", path, img.size)


def gen_icon_balloon(path, w=110, h=140):
    img = icon_canvas(w, h)
    d = ImageDraw.Draw(img)
    cx = w // 2
    d.ellipse((cx - 40, 8, cx + 40, 96), fill=(225, 70, 110))
    d.ellipse((cx - 14, 92, cx + 14, 112), fill=(225, 70, 110))
    d.polygon([(cx - 10, 108), (cx, 96), (cx + 10, 108)], fill=(225, 70, 110))
    d.line((cx, 108, cx, 128), fill=(210, 216, 226), width=3)
    d.ellipse((cx - 24, 24, cx - 6, 44), fill=(250, 210, 220))
    img.save(path)
    print("saved", path, img.size)


if __name__ == "__main__":
    gen_floor(os.path.join("assets", "backgrounds", "stage3", "floor.png"))
    gen_wall(os.path.join("assets", "backgrounds", "stage3", "wall.png"))
    gen_title(os.path.join("assets", "titles", "stage3.png"))
    gen_watcher_sprite(os.path.join("assets", "sprites", "bosses", "watcher.png"))
    gen_bonzo_sprite(os.path.join("assets", "sprites", "bosses", "bonzo.png"))
    gen_undead_sprite(os.path.join("assets", "sprites", "enemies", "stage3", "undead.png"))
    gen_soul_sprite(os.path.join("assets", "sprites", "enemies", "stage3", "soul.png"))
    gen_skeleton_sprite(os.path.join("assets", "sprites", "enemies", "stage3", "skeleton.png"))
    gen_caster_sprite(os.path.join("assets", "sprites", "enemies", "stage3", "caster.png"))
    gen_icon_eye(os.path.join("assets", "backgrounds", "stage3", "watcher_eye.png"))
    gen_icon_skull(os.path.join("assets", "backgrounds", "stage3", "skull.png"))
    gen_icon_dark_orb(os.path.join("assets", "backgrounds", "stage3", "dark_orb.png"))
    gen_icon_balloon(os.path.join("assets", "backgrounds", "stage3", "balloon.png"))
    print("done")